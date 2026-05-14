import json, os, time
from datetime import datetime
from config import DATA_FILE, DATA_DIR, COOLDOWN, WINDOW_SIZE, \
    FEED_HUNGER, FEED_AFFECTION, BATH_CLEAN, BATH_AFFECTION, \
    GREET_AFFECTION, PLAY_HUNGER_COST, PLAY_CLEAN_COST, PLAY_AFFECTION, \
    SIZE_MIN, SIZE_MAX, DEFAULT_RIGHT_MARGIN_RATIO, WORK_MARGIN_BOTTOM

class PetStats:
    """三属性 + CD + 持久化"""
    def __init__(self, data_file=DATA_FILE, data_dir=DATA_DIR):
        self.data_file = data_file
        self.data_dir = data_dir
        self.hunger = 100
        self.cleanliness = 100
        self.affection = 100
        self.x = 800
        self.y = 500
        self.topmost = True
        self.click_through = False
        self.work_mode = False
        self.pet_size = WINDOW_SIZE
        self._loaded_from_file = False
        self._last_action = {
            "feed": None,
            "bath": None,
            "greet": None,
            "play": None,
        }
        self._load()
        if not self._loaded_from_file:
            self._set_default_position()

    # ---- 属性读取 ----
    @property
    def is_hungry(self):  return self.hunger <= 20
    @property
    def is_full(self):    return self.hunger >= 100
    @property
    def is_dirty(self):   return self.cleanliness <= 20
    @property
    def is_sad(self):     return self.affection <= 20
    @property
    def is_angry(self):   return self.affection <= 10
    @property
    def is_happy(self):   return self.affection >= 80

    # ---- CD 检查 ----
    def can_do(self, action: str) -> bool:
        last = self._last_action.get(action)
        if last is None:
            return True
        return (time.time() - last) >= COOLDOWN.get(action, 0)

    def do_action(self, action: str):
        self._last_action[action] = time.time()

    # ---- 互动 ----
    def feed(self):
        self.hunger = min(100, self.hunger + FEED_HUNGER)
        self.affection = min(100, self.affection + FEED_AFFECTION)
        self.do_action("feed")

    def bath(self):
        self.cleanliness = min(100, self.cleanliness + BATH_CLEAN)
        self.affection = min(100, self.affection + BATH_AFFECTION)
        self.do_action("bath")

    def greet(self):
        self.affection = min(100, self.affection + GREET_AFFECTION)
        self.do_action("greet")

    def play(self):
        self.hunger = max(0, self.hunger - PLAY_HUNGER_COST)
        self.cleanliness = max(0, self.cleanliness - PLAY_CLEAN_COST)
        self.affection = min(100, self.affection + PLAY_AFFECTION)
        self.do_action("play")

    # ---- 衰减（每 tick 调用） ----
    def tick(self, hunger_decay, clean_decay, affection_decay):
        self.hunger = max(0, self.hunger - hunger_decay)
        self.cleanliness = max(0, self.cleanliness - clean_decay)
        self.affection = max(0, self.affection - affection_decay)

    # ---- 持久化 ----
    def save(self):
        os.makedirs(self.data_dir, exist_ok=True)
        data = {
            "hunger": self.hunger,
            "cleanliness": self.cleanliness,
            "affection": self.affection,
            "x": self.x,
            "y": self.y,
            "topmost": self.topmost,
            "click_through": self.click_through,
            "work_mode": self.work_mode,
            "pet_size": self.pet_size,
            "last_feed": self._last_action.get("feed"),
            "last_bath": self._last_action.get("bath"),
            "last_greet": self._last_action.get("greet"),
            "last_play": self._last_action.get("play"),
        }
        with open(self.data_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _load(self):
        if not os.path.exists(self.data_file):
            return
        try:
            with open(self.data_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            self._loaded_from_file = True
            self.hunger = self._coerce_number(data.get("hunger"), 100, 0, 100)
            self.cleanliness = self._coerce_number(data.get("cleanliness"), 100, 0, 100)
            self.affection = self._coerce_number(data.get("affection"), 100, 0, 100)
            self.x = self._coerce_int(data.get("x"), 800, 0, 100000)
            self.y = self._coerce_int(data.get("y"), 500, 0, 100000)
            self.topmost = self._coerce_bool(data.get("topmost"), True)
            self.click_through = self._coerce_bool(data.get("click_through"), False)
            self.work_mode = self._coerce_bool(data.get("work_mode"), False)
            self.pet_size = self._coerce_int(data.get("pet_size"), WINDOW_SIZE, SIZE_MIN, SIZE_MAX)
            self._last_action["feed"] = self._coerce_timestamp(data.get("last_feed"))
            self._last_action["bath"] = self._coerce_timestamp(data.get("last_bath"))
            self._last_action["greet"] = self._coerce_timestamp(data.get("last_greet"))
            self._last_action["play"] = self._coerce_timestamp(data.get("last_play"))
        except Exception:
            pass
        self._clamp_position()

    def _set_default_position(self):
        try:
            from PySide6.QtWidgets import QApplication
            app = QApplication.instance()
            if app:
                screen = app.primaryScreen().availableGeometry()
                right_margin = int(screen.width() * DEFAULT_RIGHT_MARGIN_RATIO)
                self.x = screen.x() + screen.width() - self.pet_size - right_margin
                self.y = screen.y() + screen.height() - self.pet_size - WORK_MARGIN_BOTTOM
                self._clamp_position()
        except Exception:
            pass

    def _coerce_number(self, value, default, minimum, maximum):
        try:
            value = float(value)
        except (TypeError, ValueError):
            return default
        return max(minimum, min(maximum, value))

    def _coerce_int(self, value, default, minimum, maximum):
        try:
            value = int(value)
        except (TypeError, ValueError):
            return default
        return max(minimum, min(maximum, value))

    def _coerce_bool(self, value, default):
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return bool(value)
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in ("true", "1", "yes", "on"):
                return True
            if normalized in ("false", "0", "no", "off"):
                return False
        return default

    def _coerce_timestamp(self, value):
        try:
            value = float(value)
        except (TypeError, ValueError):
            return None
        return value if value >= 0 else None

    def _clamp_position(self):
        try:
            from PySide6.QtWidgets import QApplication
            app = QApplication.instance()
            if app:
                screen = app.primaryScreen().availableGeometry()
                self.x = max(0, min(self.x, screen.width() - self.pet_size))
                self.y = max(0, min(self.y, screen.height() - self.pet_size))
        except Exception:
            pass
