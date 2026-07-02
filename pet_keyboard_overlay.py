import os

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QLabel, QWidget

from config import KEYBOARD_ASPECT_HEIGHT, KEYBOARD_ASPECT_WIDTH, KEYBOARD_ASSETS_DIR


_LEFT_KEY_ASSETS = {
    0x08: "Backspace.png",
    0x09: "Tab.png",
    0x0D: "Return.png",
    0x14: "CapsLock.png",
    0x1B: "Escape.png",
    0x20: "Space.png",
    0x2E: "Delete.png",
    0x5B: "Meta.png",
    0x5C: "Meta.png",
    0xBF: "Slash.png",
    0xC0: "BackQuote.png",
}

_ARROW_KEY_ASSETS = {
    0x25: "LeftArrow.png",
    0x26: "UpArrow.png",
    0x27: "RightArrow.png",
    0x28: "DownArrow.png",
}


def key_asset_for_event(vk_code: int, scan_code: int, extended: bool):
    if 0x41 <= vk_code <= 0x5A:
        return "left-keys", f"Key{chr(vk_code)}.png"
    if 0x30 <= vk_code <= 0x39:
        return "left-keys", f"Num{chr(vk_code)}.png"
    if vk_code in _ARROW_KEY_ASSETS:
        return "right-keys", _ARROW_KEY_ASSETS[vk_code]

    if vk_code == 0xA0:
        return "left-keys", "ShiftLeft.png"
    if vk_code == 0xA1:
        return "left-keys", "ShiftRight.png"
    if vk_code == 0x10:
        filename = {
            0x2A: "ShiftLeft.png",
            0x36: "ShiftRight.png",
        }.get(scan_code, "Shift.png")
        return "left-keys", filename

    if vk_code in (0x11, 0xA2, 0xA3):
        is_right = vk_code == 0xA3 or (vk_code == 0x11 and extended)
        filename = "ControlRight.png" if is_right else "ControlLeft.png"
        return "left-keys", filename

    if vk_code in (0x12, 0xA4, 0xA5):
        is_right = vk_code == 0xA5 or (vk_code == 0x12 and extended)
        filename = "AltGr.png" if is_right else "Alt.png"
        return "left-keys", filename

    filename = _LEFT_KEY_ASSETS.get(vk_code)
    if filename is not None:
        return "left-keys", filename
    return None


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
