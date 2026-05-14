import sys, os, random, time
from PySide6.QtWidgets import QApplication, QMainWindow, QLabel, QSystemTrayIcon, QMenu as QSysMenu
from PySide6.QtGui import QAction, QIcon, QPixmap, QMovie
from PySide6.QtCore import Qt, QTimer, QPoint, Signal

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
        self._last_mouse_pos = None      # 用于计算拖拽方向
        self._walk_timer_id = None
        self._last_state_change = time.time()
        self._interaction_in_progress = False
        self._interaction_id = 0
        self._last_mouse_leave = time.time()
        self._last_hover_greet = 0        # 上次鼠标经过打招呼时间
        self._hover_timer = QTimer(self)
        self._hover_timer.setSingleShot(True)
        self._hover_timer.timeout.connect(self._do_hover_greet)

        # 主循环
        self._tick_timer = QTimer(self)
        self._tick_timer.timeout.connect(self._tick)
        self._tick_timer.start(TICK_MS)

        # 初始化
        self._set_size(self.stats.pet_size)
        self.move(self.stats.x, self.stats.y)
        self._play("idle")
        self._apply_topmost()
        self._apply_click_through()

        # 系统托盘
        self._setup_tray()

        # 恢复打工模式
        if self.stats.work_mode:
            self.stats.work_mode = False
            self._toggle_work()

        # 持久化定时
        self._save_timer = QTimer(self)
        self._save_timer.timeout.connect(self.stats.save)
        self._save_timer.start(60_000)  # 每分钟自动保存

    # ===== 窗口 =====
    def _set_size(self, size):
        self.setFixedSize(size, size)
        self.label.setFixedSize(size, size)
        self.stats.pet_size = size

    def _set_pet_size(self, size):
        """统一尺寸调整入口（菜单回调）"""
        size = max(SIZE_MIN, min(SIZE_MAX, int(size)))
        self._set_size(size)

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
        movie.setScaledSize(self.label.size())
        movie.loopCount = -1
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
            movie.setScaledSize(self.label.size())
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
        if idle_time >= IDLE_SLEEP_MIN and random.random() < 0.001:
            if self.anim.has_category("sleep"):
                self._play("sleep"); return

        if IDLE_WALK_MIN < idle_time < IDLE_WALK_MAX and random.random() < 0.003:
            self._random_walk(); return

        # IDLE 切换 GIF
        if idle_time >= IDLE_SWITCH_MIN and random.random() < 0.005:
            self._play("idle")

    def _play_once(self, category: str):
        """播放一次非循环动画，然后回到 idle"""
        movie = self.anim.get_random(category)
        if not movie:
            return
        self.label.setMovie(movie)
        movie.loopCount = 1
        movie.setScaledSize(self.label.size())
        movie.start()
        self._state = category
        self._interaction_in_progress = True
        self._interaction_id += 1
        current_id = self._interaction_id
        try:
            movie.finished.disconnect()
        except RuntimeError:
            pass
        movie.finished.connect(lambda: self._end_interaction())
        QTimer.singleShot(5000, lambda: self._force_end_interaction(current_id))

    def _end_interaction(self):
        self._interaction_in_progress = False
        self._play("idle")

    def _force_end_interaction(self, interaction_id):
        if self._interaction_in_progress and self._interaction_id == interaction_id:
            self._interaction_in_progress = False
            self._play("idle")

    def _random_walk(self):
        """随机走动一段距离"""
        screen = QApplication.primaryScreen().availableGeometry()
        size = self.width()
        dx = random.randint(-200, 200)
        dy = random.randint(-100, 100)
        new_x = max(0, min(screen.width() - size, self.x() + dx))
        new_y = max(0, min(screen.height() - size, self.y() + dy))

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
            self._drag_start = event.globalPosition().toPoint() - self.pos()
            self._last_mouse_pos = event.globalPosition().toPoint()
            self.grabMouse()
        elif event.button() == Qt.MouseButton.RightButton:
            self._show_menu(event.globalPosition().toPoint())

    def mouseMoveEvent(self, event):
        if self._drag_start is None or self.stats.work_mode:
            return

        pos = event.globalPosition().toPoint()

        # 首次进入拖拽时设置 drag movie（只设一次）
        if self._state != "drag":
            if self.anim.has_category("drag"):
                movies = self.anim._movies.get("drag", [])
                if self._last_mouse_pos:
                    dx = pos.x() - self._last_mouse_pos.x()
                else:
                    dx = 0
                if len(movies) >= 2:
                    movie = movies[0] if dx >= 0 else movies[1]
                else:
                    movie = movies[0] if movies else None
                if movie:
                    self.label.setMovie(movie)
                    movie.setScaledSize(self.label.size())
                    movie.start()
                    self._state = "drag"
                    self._last_state_change = time.time()
            else:
                self._play("drag")

        self._last_mouse_pos = pos
        self.move(pos - self._drag_start)

    def mouseReleaseEvent(self, event):
        if self._drag_start:
            self.releaseMouse()
            self._drag_start = None
            self._last_mouse_pos = None
            self.stats.x = self.x()
            self.stats.y = self.y()
            if not self._interaction_in_progress:
                self._play("idle")

    def enterEvent(self, event):
        """鼠标进入窗口"""
        now = time.time()

        # 唤醒睡觉
        if self._state == "sleep":
            self._play("idle")

        # 拖拽中或互动中不触发任何 enter 行为
        if self._drag_start is not None or self._interaction_in_progress:
            return

        # 长时间离开 → 震惊
        away_time = now - self._last_mouse_leave
        if away_time > ASTONISH_AWAY and self.anim.has_category("astonishing"):
            self._play_once("astonishing")
            self._last_mouse_leave = now
            return

        # 延迟打招呼：停留 500ms 后才触发
        if now - self._last_hover_greet > GREET_HOVER_CD and self.anim.has_category("greet"):
            self._hover_timer.start(500)

    def _do_hover_greet(self):
        """延迟触发的鼠标经过打招呼"""
        if self._drag_start is not None or self._interaction_in_progress:
            return
        self._play_once("greet")
        self._last_hover_greet = time.time()

    def leaveEvent(self, event):
        """鼠标离开窗口"""
        self._last_mouse_leave = time.time()
        self._hover_timer.stop()

    def wheelEvent(self, event):
        """Ctrl + 滚轮调整宠物大小"""
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            if self.stats.work_mode:
                return
            delta = event.angleDelta().y()
            new_size = self.width() + (10 if delta > 0 else -10)
            self._set_pet_size(new_size)
            event.accept()
        else:
            super().wheelEvent(event)

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
            "set_size": self._set_pet_size,
            "quit": self._quit,
        }

        menu = PetMenu(self.stats, callbacks, self)
        menu.exec(pos)

    def _do_feed(self):
        if not self.stats.can_do("feed"):
            return
        if self.stats.hunger >= 100:
            self.stats.do_action("feed")
            if self.anim.has_category("full"):
                self._play_once("full")
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
        self._work_prev_size = self.stats.pet_size  # 记住用户尺寸
        self._set_size(WORK_MODE_SIZE)
        self.stats.pet_size = self._work_prev_size   # 保留用户尺寸，不被工作模式覆盖
        screen = QApplication.primaryScreen().availableGeometry()
        self.move(
            screen.width() - WORK_MODE_SIZE - WORK_MARGIN_RIGHT,
            screen.height() - WORK_MODE_SIZE - WORK_MARGIN_BOTTOM,
        )
        self.stats.topmost = True
        self.stats.click_through = True
        self._apply_click_through()
        self._apply_topmost()
        # 先 show 再设动画
        if self.anim.has_category("work"):
            self._play("work")

    def _exit_work(self):
        self._set_size(self.stats.pet_size)
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
        # 从第一个 idle GIF 提取图标
        icon = QIcon()
        idle_gifs = self.anim._movies.get("idle", [])
        if idle_gifs:
            movie = idle_gifs[0]
            movie.start()
            movie.jumpToFrame(0)
            # 等一帧渲染
            QTimer.singleShot(100, lambda: self._set_tray_icon(movie))
        else:
            self.tray.setIcon(self.style().standardIcon(
                self.style().StandardPixmap.SP_ComputerIcon))
        self.tray.setToolTip("线条小狗")
        self._setup_tray_menu()
        self.tray.show()

    def _set_tray_icon(self, movie):
        pixmap = movie.currentPixmap()
        if not pixmap.isNull():
            self.tray.setIcon(QIcon(pixmap))
        movie.stop()

    def _setup_tray_menu(self):
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
        if not getattr(self, '_quitting', False):
            self.stats.x = self.x()
            self.stats.y = self.y()
            self.stats.save()
        event.accept()

    def _quit(self):
        self._quitting = True
        self.stats.x = self.x()
        self.stats.y = self.y()
        self.stats.save()
        QApplication.quit()
