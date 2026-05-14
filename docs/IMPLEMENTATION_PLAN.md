# 线条小狗桌宠 — 完整实现计划

> 项目路径: D:/软件安装/line-dog-desktop-pet
> 技术栈: Python 3.11+, PySide6, PyInstaller
> GitHub: https://github.com/ZYC99/line-dog-desktop-pet

## 素材约定

素材在 `assets/gif/` 下，按文件夹分类。程序读取时：
- 每个文件夹名 = 动作名
- 同名内 GIF 文件名 = `{动作名}_{编号}.gif`（如 idle_01.gif）
- walk 特殊：奇数编号=右行，偶数编号=左行，程序根据移动方向自动选择
- 无素材的文件夹（如 climb/）自动跳过

## 文件清单

### 1. `config.py` — 全局常量
```python
import os, sys

# 路径
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

ASSETS_DIR = os.path.join(BASE_DIR, "assets", "gif")
DATA_DIR = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "LineDogPet")
DATA_FILE = os.path.join(DATA_DIR, "pet_data.json")
os.makedirs(DATA_DIR, exist_ok=True)

# 窗口
WINDOW_SIZE = 200
WORK_MODE_SIZE = 80
TICK_MS = 100

# 属性衰减 (per tick, 100ms per tick)
HUNGER_DECAY = 0.006     # ~1 per 16.7s, ~3.6/min → 约 28min 从满到空
CLEAN_DECAY = 0.006
AFFECTION_DECAY = 0.002  # ~1 per 50s

# 属性阈值
THRESHOLD_LOW = 20
THRESHOLD_HIGH = 80
THRESHOLD_VERY_LOW = 10

# CD (秒)
COOLDOWN = {
    "feed": 30,
    "bath": 30,
    "greet": 15,
    "play": 20,
}

# 空闲计时 (秒)
IDLE_SWITCH_MIN = 3
IDLE_WALK_MIN = 30
IDLE_WALK_MAX = 120
IDLE_SLEEP_MIN = 120
IDLE_SLEEP_MAX = 300
IDLE_ASTONISH = 300  # 超过此时间点击触发震惊

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
```

### 2. `pet_animation.py` — GIF 加载与播放
```python
import os, random
from collections import defaultdict
from PySide6.QtGui import QMovie
from PySide6.QtCore import QObject, Signal
from config import ASSETS_DIR

class PetAnimation(QObject):
    """管理所有 GIF 素材的加载和播放"""
    animation_done = Signal()  # 非循环动画播完

    def __init__(self):
        super().__init__()
        self._movies: dict[str, list[QMovie]] = defaultdict(list)
        self._current_category = "idle"
        self._current_movie: QMovie = None
        self._load_all()

    def _load_all(self):
        """扫描 assets/gif/ 下所有文件夹，加载 GIF"""
        if not os.path.isdir(ASSETS_DIR):
            return
        for category in sorted(os.listdir(ASSETS_DIR)):
            cat_path = os.path.join(ASSETS_DIR, category)
            if not os.path.isdir(cat_path):
                continue
            gifs = sorted(
                [f for f in os.listdir(cat_path) if f.lower().endswith('.gif')]
            )
            for gif in gifs:
                path = os.path.join(cat_path, gif)
                movie = QMovie(path)
                movie.setCacheMode(QMovie.CacheMode.CacheAll)
                self._movies[category].append(movie)

    def has_category(self, category: str) -> bool:
        return len(self._movies.get(category, [])) > 0

    def get_random(self, category: str) -> QMovie | None:
        """获取指定分类的随机 GIF（循环播放）"""
        pool = self._movies.get(category, [])
        if not pool:
            return None
        movie = random.choice(pool)
        movie.jumpToFrame(0)
        self._current_category = category
        self._current_movie = movie
        return movie

    def get_walk(self, direction: int) -> QMovie | None:
        """
        获取走路 GIF，根据方向选奇数(右)或偶数(左)
        direction: 1=右, -1=左, 0=上(jump)
        """
        if direction == 0:
            return self.get_random("jump") or self.get_random("walk")
        pool = self._movies.get("walk", [])
        if not pool:
            return None
        # 按文件名数字排序，奇数=右，偶数=左
        target_parity = 1 if direction > 0 else 0
        matching = [
            m for m in pool
            if self._file_parity(m) == target_parity
        ]
        if not matching:
            return random.choice(pool)
        movie = random.choice(matching)
        movie.jumpToFrame(0)
        self._current_category = "walk"
        self._current_movie = movie
        return movie

    def _file_parity(self, movie: QMovie) -> int:
        """从文件名提取编号奇偶性"""
        name = os.path.basename(movie.fileName())
        digits = ''.join(c for c in name if c.isdigit())
        if digits:
            return int(digits) % 2
        return 0

    def stop(self):
        if self._current_movie:
            self._current_movie.stop()

    def categories(self) -> list[str]:
        return list(self._movies.keys())
```

### 3. `pet_stats.py` — 属性系统
```python
import json, os, time
from datetime import datetime
from config import DATA_FILE, DATA_DIR, COOLDOWN

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
        self.idle_since = time.time()
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

    def clamp(self):
        for attr in ["hunger", "cleanliness", "affection"]:
            setattr(self, attr, max(0, min(100, getattr(self, attr))))

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
        self.hunger = min(100, self.hunger + 30)
        self.affection = min(100, self.affection + 5)
        self.do_action("feed")

    def bath(self):
        self.cleanliness = min(100, self.cleanliness + 40)
        self.affection = min(100, self.affection + 5)
        self.do_action("bath")

    def greet(self):
        self.affection = min(100, self.affection + 10)
        self.do_action("greet")

    def play(self):
        self.hunger = max(0, self.hunger - 5)
        self.cleanliness = max(0, self.cleanliness - 10)
        self.affection = min(100, self.affection + 15)
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
            "idle_since": self.idle_since,
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
            self.idle_since = data.get("idle_since", time.time())
            self._last_action["feed"] = data.get("last_feed")
            self._last_action["bath"] = data.get("last_bath")
            self._last_action["greet"] = data.get("last_greet")
            self._last_action["play"] = data.get("last_play")
        except Exception:
            pass
```

### 4. `pet_menu.py` — 右键菜单
```python
from PySide6.QtWidgets import QMenu, QAction, QWidgetAction, QProgressBar, QLabel, QVBoxLayout, QWidget
from PySide6.QtGui import QAction as QtAction
from PySide6.QtCore import Qt

class PetMenu(QMenu):
    def __init__(self, stats, callbacks: dict, parent=None):
        super().__init__(parent)
        self.stats = stats
        self.cb = callbacks  # {action_name: callable}
        self.setStyleSheet("""
            QMenu {
                background: #2b2b2b;
                color: #e0e0e0;
                border: 1px solid #555;
                border-radius: 6px;
                padding: 4px;
            }
            QMenu::item {
                padding: 6px 20px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background: #4a4a4a;
            }
            QMenu::item:disabled {
                color: #666;
            }
        """)
        self._build()

    def _build(self):
        # 状态条
        self._add_stat_bar()

        self.addSeparator()

        # 互动项（根据CD禁用）
        self._add_action("🍖 喂食", "feed", self.stats.can_do("feed"))
        self._add_action("🛁 洗澡", "bath", self.stats.can_do("bath"))
        self._add_action("👋 打招呼", "greet", self.stats.can_do("greet"))
        self._add_action("🎾 玩耍", "play", self.stats.can_do("play"))

        self.addSeparator()

        # 模式切换
        work_text = "💼 退出打工" if self.stats.work_mode else "💼 打工模式"
        self._add_action(work_text, "toggle_work", True)
        self._add_check("📌 置顶显示", "toggle_topmost", self.stats.topmost)
        self._add_check("🖱 鼠标穿透", "toggle_click_through", self.stats.click_through)

        self.addSeparator()

        self._add_action("💾 保存状态", "save", True)
        self._add_action("🚪 退出", "quit", True)

    def _add_stat_bar(self):
        """添加属性条"""
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(4)

        for label, value, color in [
            ("😊 好感度", self.stats.affection, "#4ec9b0"),
            ("🍔 饱食度", self.stats.hunger, "#ce9178"),
            ("🛁 清洁度", self.stats.cleanliness, "#569cd6"),
        ]:
            row = QVBoxLayout()
            lbl = QLabel(f"{label} {int(value)}")
            lbl.setStyleSheet("color: #ccc; font-size: 11px;")
            bar = QProgressBar()
            bar.setRange(0, 100)
            bar.setValue(int(value))
            bar.setTextVisible(False)
            bar.setFixedHeight(6)
            bar.setStyleSheet(f"""
                QProgressBar {{
                    background: #3a3a3a;
                    border-radius: 3px;
                    border: none;
                }}
                QProgressBar::chunk {{
                    background: {color};
                    border-radius: 3px;
                }}
            """)
            row.addWidget(lbl)
            row.addWidget(bar)
            layout.addLayout(row)

        wa = QWidgetAction(self)
        wa.setDefaultWidget(w)
        self.addAction(wa)

    def _add_action(self, text, key, enabled):
        action = QAction(text, self)
        action.setEnabled(enabled)
        if key in self.cb:
            action.triggered.connect(self.cb[key])
        self.addAction(action)

    def _add_check(self, text, key, checked):
        action = QAction(text, self)
        action.setCheckable(True)
        action.setChecked(checked)
        if key in self.cb:
            action.triggered.connect(lambda c, k=key: self.cb[k]())
        self.addAction(action)
```

### 5. `pet_window.py` — 主窗口
```python
import sys, os, random, time
from PySide6.QtWidgets import QApplication, QMainWindow, QLabel, QSystemTrayIcon, QMenu as QSysMenu
from PySide6.QtGui import QAction, QIcon, QPixmap, QMovie
from PySide6.QtCore import Qt, QTimer, QPoint, Signal
from PySide6 import QtWin

from config import *
from pet_animation import PetAnimation
from pet_stats import PetStats
from pet_menu import PetMenu

class PetWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        # 无边框透明窗
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.Tool |
            Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        # 不在任务栏
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)

        # 组件
        self.anim = PetAnimation()
        self.stats = PetStats()

        # GIF 显示标签
        self.label = QLabel(self)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setCentralWidget(self.label)

        # 状态
        self._state = "idle"
        self._drag_start = None
        self._walk_timer_id = None
        self._last_state_change = time.time()
        self._interaction_in_progress = False

        # 主循环
        self._tick_timer = QTimer(self)
        self._tick_timer.timeout.connect(self._tick)
        self._tick_timer.start(TICK_MS)

        # 初始化
        self._set_size(WINDOW_SIZE)
        self.move(self.stats.x, self.stats.y)
        self._play("idle")
        self._apply_topmost()
        self._apply_click_through()

        # 系统托盘
        self._setup_tray()

        # 持久化定时
        self._save_timer = QTimer(self)
        self._save_timer.timeout.connect(self.stats.save)
        self._save_timer.start(60_000)  # 每分钟自动保存

    # ===== 窗口 =====
    def _set_size(self, size):
        self.setFixedSize(size, size)
        self.label.setFixedSize(size, size)

    def _apply_topmost(self):
        flags = self.windowFlags()
        if self.stats.topmost:
            flags |= Qt.WindowType.WindowStaysOnTopHint
        else:
            flags &= ~Qt.WindowType.WindowStaysOnTopHint
        self.setWindowFlags(flags)
        self.show()

    def _apply_click_through(self):
        if self.stats.click_through:
            self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        else:
            self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)

    # ===== 动画 =====
    def _play(self, category: str, once: bool = False):
        """播放指定分类的 GIF"""
        if self._interaction_in_progress and category not in ("walk", "idle", "jump"):
            return  # 互动中不被打断

        movie = self.anim.get_random(category)
        if movie is None:
            return

        self.label.setMovie(movie)
        movie.start()

        self._state = category
        self._last_state_change = time.time()

    def _play_walk(self, dx: int, dy: int):
        """播放走路/跳跃动画"""
        if dy < 0:  # 向上走
            movie = self.anim.get_walk(0)  # jump
        elif dx > 0:
            movie = self.anim.get_walk(1)
        else:
            movie = self.anim.get_walk(-1)

        if movie:
            self.label.setMovie(movie)
            movie.start()
            self._state = "walk"
            self._last_state_change = time.time()

    # ===== 主循环 =====
    def _tick(self):
        """100ms 一次"""
        self.stats.tick(HUNGER_DECAY, CLEAN_DECAY, AFFECTION_DECAY)

        if self._interaction_in_progress:
            return

        idle_time = time.time() - self._last_state_change

        # 状态触发（高优先级）
        if self.stats.is_angry and self.anim.has_category("angry"):
            self._play_once("angry"); return
        if self.stats.is_hungry and self.anim.has_category("hungry"):
            self._play_once("hungry"); return
        if self.stats.is_dirty and self.anim.has_category("dirty"):
            self._play_once("dirty"); return
        if self.stats.is_sad and self.anim.has_category("sad"):
            self._play_once("sad"); return

        # 好感度高随机开心
        if self.stats.is_happy and self.anim.has_category("happy") and random.random() < 0.005:
            self._play_once("happy"); return

        # 空闲分层
        if idle_time > IDLE_SLEEP_MIN and random.random() < 0.001:
            if self.anim.has_category("sleep"):
                self._play("sleep"); return

        if IDLE_WALK_MIN < idle_time < IDLE_WALK_MAX and random.random() < 0.003:
            self._random_walk(); return

        # IDLE 切换 GIF
        if idle_time > IDLE_SWITCH_MIN and random.random() < 0.01:
            self._play("idle")

    def _play_once(self, category: str):
        """播放一次非循环动画，然后回到 idle"""
        movie = self.anim.get_random(category)
        if not movie:
            return
        self.label.setMovie(movie)
        movie.start()
        self._state = category
        self._interaction_in_progress = True
        # 动画播完后回到 idle
        movie.finished.connect(lambda: self._end_interaction())

    def _end_interaction(self):
        self._interaction_in_progress = False
        self._play("idle")

    def _random_walk(self):
        """随机走动一段距离"""
        screen = QApplication.primaryScreen().availableGeometry()
        dx = random.randint(-200, 200)
        dy = random.randint(-100, 100)
        new_x = max(0, min(screen.width() - WINDOW_SIZE, self.x() + dx))
        new_y = max(0, min(screen.height() - WINDOW_SIZE, self.y() + dy))

        self._play_walk(new_x - self.x(), new_y - self.y())
        self._animate_move(self.pos(), QPoint(new_x, new_y))

    def _animate_move(self, start: QPoint, end: QPoint):
        """平滑移动到目标位置（分步）"""
        steps = 20
        dx = (end.x() - start.x()) / steps
        dy = (end.y() - start.y()) / steps
        self._walk_step = 0
        self._walk_target = end

        def step():
            if self._walk_step >= steps:
                self._play("idle")
                self.stats.x = self.x()
                self.stats.y = self.y()
                return
            self.move(int(start.x() + dx * self._walk_step),
                      int(start.y() + dy * self._walk_step))
            self._walk_step += 1
            QTimer.singleShot(50, step)

        step()

    # ===== 鼠标事件 =====
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            idle_time = time.time() - self._last_state_change
            if idle_time > IDLE_ASTONISH and self.anim.has_category("astonishing"):
                self._play_once("astonishing")
            else:
                self._drag_start = event.globalPosition().toPoint() - self.pos()
        elif event.button() == Qt.MouseButton.RightButton:
            self._show_menu(event.globalPosition().toPoint())

    def mouseMoveEvent(self, event):
        if self._drag_start and not self.stats.work_mode:
            self._play("drag")
            self.move(event.globalPosition().toPoint() - self._drag_start)

    def mouseReleaseEvent(self, event):
        if self._drag_start:
            self._drag_start = None
            self.stats.x = self.x()
            self.stats.y = self.y()
            self._play("idle")

    def enterEvent(self, event):
        """鼠标进入窗口 — 唤醒睡觉"""
        if self._state == "sleep":
            self._play("idle")

    # ===== 菜单 =====
    def _show_menu(self, pos):
        self.stats.x = self.x()
        self.stats.y = self.y()

        callbacks = {
            "feed": self._do_feed,
            "bath": self._do_bath,
            "greet": self._do_greet,
            "play": self._do_play,
            "toggle_work": self._toggle_work,
            "toggle_topmost": self._toggle_topmost,
            "toggle_click_through": self._toggle_click_through,
            "save": self.stats.save,
            "quit": self._quit,
        }

        menu = PetMenu(self.stats, callbacks, self)
        menu.exec(pos)

    def _do_feed(self):
        if not self.stats.can_do("feed"):
            return
        self.stats.feed()
        if self.stats.is_full and self.anim.has_category("full"):
            self._play_once("full")
        else:
            self._play_once("eat")

    def _do_bath(self):
        if not self.stats.can_do("bath"):
            return
        self.stats.bath()
        self._play_once("bath")

    def _do_greet(self):
        if not self.stats.can_do("greet"):
            return
        self.stats.greet()
        self._play_once("greet")

    def _do_play(self):
        if not self.stats.can_do("play"):
            return
        self.stats.play()
        self._play_once("play")

    def _toggle_work(self):
        self.stats.work_mode = not self.stats.work_mode
        if self.stats.work_mode:
            self._enter_work()
        else:
            self._exit_work()

    def _enter_work(self):
        self._set_size(WORK_MODE_SIZE)
        screen = QApplication.primaryScreen().availableGeometry()
        self.move(
            screen.width() - WORK_MODE_SIZE - WORK_MARGIN_RIGHT,
            screen.height() - WORK_MODE_SIZE - WORK_MARGIN_BOTTOM,
        )
        self.stats.topmost = True
        self.stats.click_through = True
        self._apply_topmost()
        self._apply_click_through()
        if self.anim.has_category("work"):
            self._play("work")

    def _exit_work(self):
        self._set_size(WINDOW_SIZE)
        self.stats.click_through = False
        self._apply_click_through()
        self._apply_topmost()
        self.move(self.stats.x, self.stats.y)
        self._play("idle")

    def _toggle_topmost(self):
        self.stats.topmost = not self.stats.topmost
        self._apply_topmost()

    def _toggle_click_through(self):
        self.stats.click_through = not self.stats.click_through
        self._apply_click_through()

    # ===== 系统托盘 =====
    def _setup_tray(self):
        self.tray = QSystemTrayIcon(self)
        # 用第一个 idle GIF 当图标，没有就用系统默认
        icon = QIcon()
        idle_gifs = self.anim._movies.get("idle", [])
        if idle_gifs:
            pixmap = idle_gifs[0].currentPixmap()
            if not pixmap.isNull():
                icon = QIcon(pixmap)
        self.tray.setIcon(icon)
        self.tray.setToolTip("线条小狗")

        menu = QSysMenu()
        show_action = QAction("显示/隐藏", self)
        show_action.triggered.connect(self._toggle_visible)
        menu.addAction(show_action)
        menu.addSeparator()
        quit_action = QAction("退出", self)
        quit_action.triggered.connect(self._quit)
        menu.addAction(quit_action)

        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self._tray_click)
        self.tray.show()

    def _tray_click(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self._toggle_visible()

    def _toggle_visible(self):
        if self.isVisible():
            self.hide()
        else:
            self.show()

    # ===== 生命周期 =====
    def closeEvent(self, event):
        self.stats.x = self.x()
        self.stats.y = self.y()
        self.stats.save()
        event.accept()

    def _quit(self):
        self.stats.x = self.x()
        self.stats.y = self.y()
        self.stats.save()
        QApplication.quit()
```

### 6. `main.py` — 入口
```python
import sys, os
from PySide6.QtWidgets import QApplication
from pet_window import PetWindow

def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)  # 关闭窗口不退出，托盘控制

    # 检查是否已运行（简单单实例）
    from PySide6.QtNetwork import QLocalSocket
    socket = QLocalSocket()
    socket.connectToServer("LineDogPet")
    if socket.waitForConnected(500):
        print("LineDogPet 已在运行")
        sys.exit(0)

    window = PetWindow()
    window.show()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()
```

### 7. `build.bat` — PyInstaller 打包
```bat
@echo off
pyinstaller --onefile --noconsole ^
    --name "LineDogPet" ^
    --add-data "assets;assets" ^
    --icon "assets/icon.ico" ^
    main.py
echo Build done: dist\LineDogPet.exe
pause
```

### 8. `.github/workflows/release.yml` — 自动构建
```yaml
name: Build Release

on:
  push:
    tags:
      - 'v*'

jobs:
  build:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Install deps
        run: pip install PySide6 pyinstaller
      - name: Build
        run: |
          pyinstaller --onefile --noconsole --name LineDogPet --add-data "assets;assets" main.py
      - name: Release
        uses: softprops/action-gh-release@v1
        with:
          files: dist/LineDogPet.exe
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

### 9. `requirements.txt`
```
PySide6>=6.5.0
pyinstaller>=6.0.0
```

---

## 实现顺序

按依赖关系依次创建文件：
1. `requirements.txt`
2. `config.py`
3. `pet_animation.py`
4. `pet_stats.py`
5. `pet_menu.py`
6. `pet_window.py`
7. `main.py`
8. `build.bat`
9. `.github/workflows/release.yml`

每个文件创建后用 `python -c "import ast; ast.parse(open('<file>').read()); print('OK')"` 做语法检查。

---

## 验收标准

完成后运行测试：
1. `pip install PySide6` — 安装依赖
2. `python main.py` — 启动桌宠
3. 验证：小狗出现在桌面，右键菜单正常，拖拽正常
4. 验证：喂食/洗澡/打招呼/玩耍 4 个互动正常
5. 验证：打工模式切换正常
6. 验证：置顶/穿透切换正常
7. 验证：退出后重启，属性保持
8. `pyinstaller --onefile --noconsole --name LineDogPet --add-data "assets;assets" main.py` 打包测试

## 注意事项
- Windows 平台，路径用 `os.path` 处理
- GIF 播放用 QMovie，注意 CacheMode
- 透明窗口需要 `WA_TranslucentBackground`
- 属性衰减用浮点，显示取整
- 素材文件夹如果不存在或为空，`_play()` 自动跳过不报错
