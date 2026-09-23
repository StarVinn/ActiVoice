"""PyQt6-based Grace overlay HUD.

The HUD intentionally uses native Qt layouting for responsive resizing:
- QPixmap.scaled() keeps Grace's avatar proportional.
- resizeEvent() recalculates the visual contents whenever the HUD changes size.
- QHBoxLayout/QVBoxLayout automatically distribute the speech bubble, avatar,
  and resize controls without hard-coded widget coordinates.
"""

import os
import sys
import threading

try:
  import psutil
except ImportError:
  psutil = None

from PyQt6.QtCore import (
    QEvent,
    QObject,
    QPoint,
    Qt,
    QThread,
    QTimer,
    pyqtSignal,
    pyqtSlot,
)
from PyQt6.QtGui import QFont, QMouseEvent, QPixmap
from PyQt6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QSizeGrip,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

ASSET_NAMES = {
    "WORKING": "grace_working.png",
    "IDLE": "grace_idle.png",
    "THINKING": "grace_thinking.png",
    "ANGRY": "grace_angry.png",
    "SLEEP": "grace_sleep.png",
    "SHUTDOWN": "grace_shutdown.png",
    "DRAG": "grace_drag.png",
    "TIRED": "grace_tired.png",
    "SAD": "grace_sad.png",
}


class GraceHUD(QWidget):

  """Thread-safe, frameless PyQt6 HUD for Grace."""

  state_requested = pyqtSignal(str, object, object)
  finish_requested = pyqtSignal(float)
  shutdown_requested = pyqtSignal()

  def __init__(self, assets_dir=None):
    self._app = QApplication.instance() or QApplication(sys.argv)
    super().__init__()

    self.assets_dir = assets_dir or os.path.join(
        os.path.dirname(__file__), "assets"
    )
    self._positioned = False
    self._monitor_stop = threading.Event()
    self._drag_offset = QPoint()
    self._dragging = False
    self._dialogue_generation = 0
    self._hide_timer = QTimer(self)
    self._hide_timer.setSingleShot(True)
    self._hide_timer.timeout.connect(self._clear_dialogue)
    self._typewriter_timer = QTimer(self)
    self._typewriter_timer.setInterval(18)
    self._typewriter_timer.timeout.connect(self._type_next)
    self._fallback_timer = QTimer(self)
    self._fallback_timer.setSingleShot(True)
    self._fallback_timer.timeout.connect(self._clear_dialogue)
    self._typewriter_index = 0
    self.current_text = ""
    self._active_state = "IDLE"
    self._current_image_path = ""

    # Dimensi dasar HUD yang lebih lega
    self._hud_width = 640
    self._hud_height = 380
    self._min_width = 420
    self._min_height = 260
    self._max_width = 1280
    self._max_height = 800

    self.setWindowFlags(
        Qt.WindowType.FramelessWindowHint
        | Qt.WindowType.Tool
        | Qt.WindowType.WindowStaysOnTopHint
    )
    self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
    self.setMinimumSize(self._min_width, self._min_height)
    self.setMaximumSize(self._max_width, self._max_height)
    self.resize(self._hud_width, self._hud_height)

    # Main vertical layout
    self.root_layout = QVBoxLayout(self)
    self.root_layout.setContentsMargins(8, 8, 8, 8)
    self.root_layout.setSpacing(4)

    self.top_layout = QHBoxLayout()
    self.top_layout.setContentsMargins(0, 0, 0, 0)
    self.top_layout.setSpacing(12)
    self.root_layout.addLayout(self.top_layout, 1)

    # Speech Bubble Panel
    self.speech_panel = QFrame(self)
    self.speech_panel.setObjectName("speechPanel")
    self.speech_panel.setStyleSheet(
        "QFrame#speechPanel { background: #2A2638; border-radius: 14px; }"
    )
    self.speech_panel.setSizePolicy(
        QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
    )
    self.speech_panel.hide()

    speech_layout = QVBoxLayout(self.speech_panel)
    speech_layout.setContentsMargins(16, 12, 16, 12)
    speech_layout.setSpacing(0)

    self.bubble = QLabel(self.speech_panel)
    self.bubble.setObjectName("speechText")
    self.bubble.setStyleSheet(
        "QLabel#speechText { color: #F5F3FF; background: transparent; }"
    )
    self.bubble.setWordWrap(True)
    self.bubble.setAlignment(
        Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft
    )
    self.bubble.setSizePolicy(
        QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
    )
    speech_layout.addWidget(self.bubble)

    # Avatar Label
    self.image_label = QLabel(self)
    self.image_label.setAlignment(
        Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom
    )
    self.image_label.setSizePolicy(
        QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
    )
    self.image_label.setStyleSheet("background: transparent;")

    # Pembagian porsi layout: speech panel (3), image label (2)
    self.top_layout.addWidget(self.speech_panel, 3)
    self.top_layout.addWidget(
        self.image_label,
        2,
        Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom,
    )

    # Resize Grip Bottom Row
    self.bottom_layout = QHBoxLayout()
    self.bottom_layout.setContentsMargins(0, 0, 0, 0)
    self.bottom_layout.addStretch(1)

    self.resize_grip = QSizeGrip(self)
    self.resize_grip.setFixedSize(20, 20)
    self.resize_grip.setCursor(Qt.CursorShape.SizeFDiagCursor)
    self.resize_grip.setToolTip("Drag to resize Grace")
    self.bottom_layout.addWidget(
        self.resize_grip,
        0,
        Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom,
    )
    self.root_layout.addLayout(self.bottom_layout, 0)

    self._font = QFont("Segoe UI", 11)
    self.bubble.setFont(self._font)
    self._pixmap = QPixmap()

    self.state_requested.connect(self._update)
    self.finish_requested.connect(self._schedule_dialogue_clear)
    self.shutdown_requested.connect(self._destroy)

    for widget in (self, self.speech_panel, self.bubble, self.image_label):
      widget.installEventFilter(self)

    self._set_expression("IDLE")
    self._layout_content()
    self._position_bottom_right()

    threading.Thread(
        target=self._system_expression_loop,
        daemon=True,
        name="hud-system-monitor",
    ).start()

  def run(self):
    """Start the Qt event loop. Must be called from the main thread."""
    app = QApplication.instance() or self._app
    app.setQuitOnLastWindowClosed(False)
    self.show()
    self.raise_()
    self.activateWindow()
    return app.exec()

  def resizeEvent(self, _event):
    """Reflow the avatar and speech bubble whenever the HUD is resized."""
    super().resizeEvent(_event)
    self._layout_content()
    self._render_avatar()

  def _layout_content(self):
    if not self.isVisible() and not self._positioned:
      pass

    width = max(self._min_width, self.width())
    height = max(self._min_height, self.height())

    self.speech_panel.setVisible(bool(self.current_text))

    base_size = max(10, min(18, int(min(width, height) / 25)))
    self._font.setPointSize(base_size)
    self.bubble.setFont(self._font)

    # Kalkulasi ukuran avatar agar tampil besar & seimbang sama text box
    target_avatar_height = max(180, int(height * 0.88))
    target_avatar_width = int(width * 0.45)

    self.image_label.setMinimumSize(180, target_avatar_height)
    self.image_label.setFixedWidth(target_avatar_width)
    self._render_avatar()

  def _position_bottom_right(self):
    if self._positioned:
      return
    screen = QApplication.primaryScreen()
    if screen:
      available = screen.availableGeometry()
      x = max(0, available.right() - self.width() - 24)
      y = max(0, available.bottom() - self.height() - 24)
      self.move(x, y)
    self._positioned = True

  def _render_avatar(self):
    """Scale the current avatar with QPixmap.scaled() and preserve aspect ratio."""
    if not self._current_image_path or not os.path.exists(
        self._current_image_path
    ):
      return
    if self.image_label.width() <= 0 or self.image_label.height() <= 0:
      return

    source = QPixmap(self._current_image_path)
    if source.isNull():
      return

    target = source.scaled(
        self.image_label.size(),
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )
    self._pixmap = target
    self.image_label.setPixmap(self._pixmap)

  def _set_expression(self, state):
    state = (state or "IDLE").upper()
    if state not in ASSET_NAMES:
      state = "IDLE"
    self._active_state = state
    filename = ASSET_NAMES[state]
    path = os.path.join(self.assets_dir, filename)
    if not os.path.exists(path):
      path = os.path.join(self.assets_dir, ASSET_NAMES["IDLE"])
    self._current_image_path = path
    self._render_avatar()

    if state == "DRAG":
      self._active_state = "DRAG"

  def _system_expression_loop(self):
    while not self._monitor_stop.wait(10):
      if not psutil:
        continue
      try:
        battery = psutil.sensors_battery()
        low_battery = bool(
            battery and not battery.power_plugged and battery.percent < 40
        )
        overloaded = (
            psutil.cpu_percent(interval=0.5) > 95
            or psutil.virtual_memory().percent > 95
        )
        if low_battery or overloaded:
          self.set_state("TIRED")
        elif self._active_state == "TIRED":
          self.set_state("IDLE")
      except (psutil.Error, OSError):
        continue

  def eventFilter(self, watched: QObject, event: QEvent):
    """Allow dragging from the visual area without hijacking resize buttons."""
    if watched in (self, self.speech_panel, self.bubble, self.image_label):
      if event.type() == QEvent.Type.MouseButtonPress:
        mouse = event
        if (
            isinstance(mouse, QMouseEvent)
            and mouse.button() == Qt.MouseButton.LeftButton
        ):
          self._dragging = True
          self._drag_offset = (
              mouse.globalPosition().toPoint() - self.frameGeometry().topLeft()
          )
          self._set_expression("DRAG")
          return True
      elif event.type() == QEvent.Type.MouseMove and self._dragging:
        mouse = event
        if (
            isinstance(mouse, QMouseEvent)
            and mouse.buttons() & Qt.MouseButton.LeftButton
        ):
          self.move(mouse.globalPosition().toPoint() - self._drag_offset)
          return True
      elif event.type() == QEvent.Type.MouseButtonRelease and self._dragging:
        mouse = event
        if (
            isinstance(mouse, QMouseEvent)
            and mouse.button() == Qt.MouseButton.LeftButton
        ):
          self._dragging = False
          self._set_expression("IDLE")
          return True
    return super().eventFilter(watched, event)

  def _show_dialogue(self, text, seconds=None):
    self._dialogue_generation += 1
    self.current_text = str(text)
    self._typewriter_index = 0
    self._hide_timer.stop()
    self._fallback_timer.stop()
    self._typewriter_timer.stop()
    self.bubble.setText("")
    self.speech_panel.show()
    self._layout_content()
    self._typewriter_timer.start()

    if seconds is not None:
      self._hide_timer.start(max(1, int(seconds * 1000)))
    else:
      fallback_seconds = max(3.0, len(self.current_text) * 0.08)
      self._fallback_timer.start(int(fallback_seconds * 1000))

  def _type_next(self):
    if self._typewriter_index >= len(self.current_text):
      self._typewriter_timer.stop()
      return
    self._typewriter_index += 1
    self.bubble.setText(self.current_text[: self._typewriter_index])

  def _clear_dialogue(self):
    self._dialogue_generation += 1
    self._typewriter_timer.stop()
    self._fallback_timer.stop()
    self._hide_timer.stop()
    self.bubble.clear()
    self.current_text = ""
    self.speech_panel.hide()
    self._layout_content()

  def finish_dialogue(self, hold_seconds=1.0):
    self.finish_requested.emit(float(hold_seconds))

  @pyqtSlot(float)
  def _schedule_dialogue_clear(self, hold_seconds):
    self._fallback_timer.stop()
    self._hide_timer.start(max(0, int(hold_seconds * 1000)))

  def set_state(self, state, text=None, seconds=4):
    self.state_requested.emit(str(state or "IDLE"), text, seconds)

  @pyqtSlot(str, object, object)
  def _update(self, state, text, seconds):
    self._set_expression(state)
    if text:
      self._show_dialogue(text, seconds)

  def shutdown(self, wait=False):
    self._monitor_stop.set()
    done = threading.Event() if wait else None

    def close_and_signal():
      self._destroy()
      if done:
        done.set()

    if QThread.currentThread() == self.thread():
      close_and_signal()
    else:
      self.shutdown_requested.emit()
      if done:
        done.wait(timeout=2)

  @pyqtSlot()
  def _destroy(self):
    self._monitor_stop.set()
    self._typewriter_timer.stop()
    self._fallback_timer.stop()
    self._hide_timer.stop()
    self.close()

    app = QApplication.instance()
    if app:
      app.quit()