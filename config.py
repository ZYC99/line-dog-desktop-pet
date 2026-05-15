import os, sys

# 路径
if getattr(sys, 'frozen', False):
    BASE_DIR = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

ASSETS_DIR = os.path.join(BASE_DIR, "assets", "gif")
DATA_DIR = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "LineDogPet")
DATA_FILE = os.path.join(DATA_DIR, "pet_data.json")
os.makedirs(DATA_DIR, exist_ok=True)

# 窗口
WINDOW_SIZE = 180
WORK_MODE_SIZE = 135
TICK_MS = 100
DEFAULT_RIGHT_MARGIN_RATIO = 0.10

# 尺寸预设
SIZE_PRESETS = {"大": 270, "中": 180, "小": 120}
SIZE_MIN = 80
SIZE_MAX = 400
INTERACTION_MIN_MS = 5_000
INTERACTION_TIMEOUT_MS = 5_000
MOOD_SHORT_CHECK_MS = 20_000
MOOD_SHORT_PLAY_MS = 5_000
MOOD_LONG_CHECK_MS = 60_000
MOOD_LONG_PLAY_MS = 60_000

# 属性衰减 (per tick, 100ms per tick)
HUNGER_DECAY = 0.001     # 0.6/min → 满条约 2.8 小时耗尽
CLEAN_DECAY = 0.001
AFFECTION_DECAY = 0.0004  # ~0.24/min → 满条约 7 小时耗尽

# CD (秒)
COOLDOWN = {
    "feed": 30,
    "bath": 30,
    "greet": 15,
    "play": 20,
}

# 空闲计时 (秒)
IDLE_SWITCH_MIN = 15      # 至少空闲 15 秒才切待机 GIF
IDLE_WALK_MIN = 30
IDLE_WALK_MAX = 120
IDLE_SLEEP_MIN = 120
IDLE_SLEEP_MAX = 300
IDLE_ASTONISH = 300  # 鼠标离开超过此秒数，再次进入时触发震惊

# 鼠标经过行为
GREET_HOVER_CD = 30     # 鼠标经过打招呼的 CD (秒)
ASTONISH_AWAY = 300      # 鼠标离开超过此秒数触发震惊

# 互动数值变化
FEED_HUNGER = 30
FEED_AFFECTION = 5
BATH_CLEAN = 40
BATH_AFFECTION = 5
GREET_AFFECTION = 10
PLAY_HUNGER_COST = 5
PLAY_CLEAN_COST = 10
PLAY_AFFECTION = 15

# 打工模式位置（屏幕右下角偏移）
WORK_MARGIN_RIGHT = 50
WORK_MARGIN_BOTTOM = 80

# 开机自启注册表键
STARTUP_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
STARTUP_NAME = "LineDogPet"
