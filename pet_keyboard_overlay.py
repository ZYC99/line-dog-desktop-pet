import os

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QLabel, QWidget

from config import KEYBOARD_ASPECT_HEIGHT, KEYBOARD_ASPECT_WIDTH, KEYBOARD_ASSETS_DIR


def keyboard_height_for_width(width):
    return round(int(width) * KEYBOARD_ASPECT_HEIGHT / KEYBOARD_ASPECT_WIDTH)


class PetKeyboardOverlay(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._background_label = QLabel(self)
        self._background_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._background_label.setScaledContents(True)
        self._background = QPixmap(os.path.join(KEYBOARD_ASSETS_DIR, "background.png"))
        self.hide()

    def set_keyboard_width(self, width):
        width = int(width)
        height = keyboard_height_for_width(width)
        self.setFixedSize(width, height)
        self._background_label.setFixedSize(width, height)
        if not self._background.isNull():
            self._background_label.setPixmap(self._background)
