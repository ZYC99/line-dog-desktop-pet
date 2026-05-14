import json, os, time
from datetime import datetime
from config import DATA_FILE, DATA_DIR, COOLDOWN, WINDOW_SIZE, \
    FEED_HUNGER, FEED_AFFECTION, BATH_CLEAN, BATH_AFFECTION, \
    GREET_AFFECTION, PLAY_HUNGER_COST, PLAY_CLEAN_COST, PLAY_AFFECTION

class PetStats:
    """三属性 + CD + 持久化"""
    def __init__(self):
        self.hunger = 100
        self.cleanliness = 100
        self.affection = 50
        self.x = 800
        self.y = 500
        self.topmost = True
        self.click_through = False
        self.work_mode = False
        self.pet_size = WINDOW_SIZE
        self._last_action = {
            "feed": None,
            "bath": None,
            "greet": None,
            "play": None,
        }
        self._load()

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
        os.makedirs(DATA_DIR, exist_ok=True)
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
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _load(self):
        if not os.path.exists(DATA_FILE):
            return
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.hunger = data.get("hunger", 100)
            self.cleanliness = data.get("cleanliness", 100)
            self.affection = data.get("affection", 50)
            self.x = data.get("x", 800)
            self.y = data.get("y", 500)
            self.topmost = data.get("topmost", True)
            self.click_through = data.get("click_through", False)
            self.work_mode = data.get("work_mode", False)
            self.pet_size = data.get("pet_size", WINDOW_SIZE)
            self._last_action["feed"] = data.get("last_feed")
            self._last_action["bath"] = data.get("last_bath")
            self._last_action["greet"] = data.get("last_greet")
            self._last_action["play"] = data.get("last_play")
        except Exception:
            pass
        self._clamp_position()

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
