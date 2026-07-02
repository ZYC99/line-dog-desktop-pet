import sys, os, random, time, warnings
from PySide6.QtWidgets import QApplication, QMainWindow, QLabel, QSystemTrayIcon, QMenu as QSysMenu, QWidget, QVBoxLayout
from PySide6.QtGui import QAction, QIcon, QPixmap, QMovie
from PySide6.QtCore import Qt, QTimer, QPoint, Signal

from config import *
import pet_startup
from pet_animation import PetAnimation
from pet_stats import PetStats
from pet_menu import PetMenu
from pet_keyboard_overlay import PetKeyboardOverlay, keyboard_height_for_width
from keyboard_hook import KeyboardHook

class PetWindow(QMainWindow):
    def __init__(self, keyboard_hook=None):
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
        self._content = QWidget(self)
        self._content_layout = QVBoxLayout(self._content)
        self._content_layout.setContentsMargins(0, 0, 0, 0)
        self._content_layout.setSpacing(0)
        self.label = QLabel(self._content)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.keyboard_overlay = PetKeyboardOverlay(self._content)
        self._content_layout.addWidget(self.label, 0, Qt.AlignmentFlag.AlignHCenter)
        self._content_layout.addWidget(self.keyboard_overlay, 0, Qt.AlignmentFlag.AlignHCenter)
        self.setCentralWidget(self._content)
        self.keyboard_hook = keyboard_hook if keyboard_hook is not None else KeyboardHook(parent=self)
        self.keyboard_hook.key_event.connect(self.keyboard_overlay.set_key_pressed)

        # 状态
        self._state = "idle"
        self._drag_start = None
        self._last_mouse_pos = None      # 用于计算拖拽方向
        self._walk_timer_id = None
        self._last_state_change = time.time()
        self._interaction_in_progress = False
        self._interaction_id = 0
        self._interaction_started_at = 0
        self._mood_id = 0
        self._mood_until = 0
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
        if self.anim.has_category("greet"):
            self._play_startup_greet()
        else:
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

        # 心情动画
        self._mood_timer = QTimer(self)
        self._mood_timer.timeout.connect(self._run_mood_cycle)
        self._reset_mood_timer()

    # ===== 窗口 =====
    def _set_size(self, size):
        keyboard_width = self._keyboard_width(size)
        total_width = max(size, keyboard_width)
        total_height = size + self._keyboard_height(keyboard_width)
        self.setFixedSize(total_width, total_height)
        self._content.setFixedSize(total_width, total_height)
        self.label.setFixedSize(size, size)
        self.keyboard_overlay.set_keyboard_width(keyboard_width)
        self._apply_keyboard_overlay()
        self._content_layout.activate()
        self.stats.pet_size = size
        self._sync_current_movie_size()

    def _keyboard_width(self, size):
        if not self._keyboard_should_show():
            return size
        return max(size, KEYBOARD_WORK_MODE_WIDTH)

    def _keyboard_height(self, keyboard_width):
        return keyboard_height_for_width(keyboard_width) if self._keyboard_should_show() else 0

    def _keyboard_should_show(self):
        return self.stats.work_mode and self.stats.keyboard_visible

    def _apply_keyboard_overlay(self):
        self.keyboard_overlay.setVisible(self._keyboard_should_show())

    def _show_typing_dog(self):
        pixmap = QPixmap(TYPING_DOG_IMAGE)
        if pixmap.isNull():
            return False
        movie = self.label.movie()
        if movie:
            movie.stop()
        self.label.clear()
        pixmap = pixmap.scaled(
            self.label.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.label.setPixmap(pixmap)
        self._state = "work"
        return True

    def _refresh_keyboard_follow(self):
        active = self._keyboard_should_show()
        self.keyboard_overlay.setVisible(active)
        if active and self._show_typing_dog():
            self.keyboard_hook.start()
            return
        self._stop_keyboard_follow()
        if self.stats.work_mode and self.anim.has_category("work"):
            self._play("work")

    def _stop_keyboard_follow(self):
        self.keyboard_hook.stop()
        self.keyboard_overlay.clear_pressed_keys()
        self.keyboard_overlay.hide()

    def _work_mode_pet_size(self):
        return KEYBOARD_WORK_MODE_PET_SIZE if self.stats.keyboard_visible else WORK_MODE_SIZE

    def _sync_current_movie_size(self):
        movie = self.label.movie()
        if movie:
            frame = movie.currentFrameNumber()
            movie.setScaledSize(self.label.size())
            if frame >= 0:
                movie.jumpToFrame(frame)

    def _set_pet_size(self, size):
        """统一尺寸调整入口（菜单回调）"""
        size = max(SIZE_MIN, min(SIZE_MAX, int(size)))
        center = self.frameGeometry().center()
        self._set_size(size)
        self.move(center - self.rect().center())
        self._clamp_window_position()
        self.stats.x = self.x()
        self.stats.y = self.y()

    def _clamp_window_position(self):
        screen = QApplication.primaryScreen().availableGeometry()
        max_x = screen.x() + screen.width() - self.width()
        max_y = screen.y() + screen.height() - self.height()
        x = max(screen.x(), min(self.x(), max_x))
        y = max(screen.y(), min(self.y(), max_y))
        self.move(x, y)

    def _effective_topmost(self):
        return self.stats.topmost or self.stats.work_mode

    def _effective_click_through(self):
        return self.stats.click_through

    def _apply_topmost(self):
        flags = self.windowFlags()
        if self._effective_topmost():
            flags |= Qt.WindowType.WindowStaysOnTopHint
        else:
            flags &= ~Qt.WindowType.WindowStaysOnTopHint
        self.setWindowFlags(flags)
        self.show()

    def _apply_click_through(self):
        self.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents,
            self._effective_click_through(),
        )

    # ===== 动画 =====
    def _play(self, category: str, once: bool = False):
        """播放指定分类的 GIF"""
        if self.stats.work_mode and category != "work":
            return
        if self._interaction_in_progress:
            return  # 互动中不被打断

        movie = self.anim.get_random(category)
        if movie is None:
            return

        self._disconnect_movie_signals(movie)
        self.label.setMovie(movie)
        movie.setScaledSize(self.label.size())
        movie.start()

        self._state = category
        self._last_state_change = time.time()

    def _play_walk(self, dx: int, dy: int):
        """播放走路/跳跃动画"""
        if self.stats.work_mode or self._interaction_in_progress:
            return
        if dy < 0:  # 向上走
            movie = self.anim.get_walk(0)  # jump
        elif dx > 0:
            movie = self.anim.get_walk(1)
        else:
            movie = self.anim.get_walk(-1)

        if movie:
            self._disconnect_movie_signals(movie)
            self.label.setMovie(movie)
            movie.setScaledSize(self.label.size())
            movie.start()
            self._state = "walk"
            self._last_state_change = time.time()

    # ===== 主循环 =====
    def _play_status(self, category: str):
        if self._state != category:
            self._play(category)

    def _tick(self):
        """100ms 一次"""
        self.stats.tick(HUNGER_DECAY, CLEAN_DECAY, AFFECTION_DECAY)

        if self._interaction_in_progress:
            return
        if self.stats.work_mode:
            return

        idle_time = time.time() - self._last_state_change

        if time.time() < self._mood_until:
            return

        # 状态触发（高优先级）
        if self.stats.is_hungry and self.anim.has_category("hungry"):
            self._play_status("hungry"); return
        if self.stats.is_dirty and self.anim.has_category("dirty"):
            self._play_status("dirty"); return

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
        if self.stats.work_mode or self._interaction_in_progress:
            return False
        movie = self.anim.get_random(category)
        if not movie:
            return False
        self._mood_until = 0
        self.label.setMovie(movie)
        movie.setScaledSize(self.label.size())
        self._state = category
        self._interaction_in_progress = True
        self._interaction_id += 1
        self._interaction_started_at = time.time()
        current_id = self._interaction_id
        self._disconnect_movie_signals(movie)
        movie.frameChanged.connect(
            lambda frame, m=movie, cid=current_id: self._end_once_movie(m, frame, cid)
        )
        movie.finished.connect(lambda cid=current_id: self._end_interaction(cid))
        movie.start()
        self._schedule_single_shot(
            INTERACTION_TIMEOUT_MS,
            lambda: self._force_end_interaction(current_id),
        )
        return True

    def _schedule_single_shot(self, ms, callback):
        QTimer.singleShot(ms, callback)

    def _play_startup_greet(self):
        if self.anim.has_category("greet"):
            self._play_once("greet")

    def _reset_mood_timer(self):
        interval = MOOD_LONG_CHECK_MS if self.stats.affection > 90 else MOOD_SHORT_CHECK_MS
        self._mood_timer.start(interval)

    def _run_mood_cycle(self):
        if self.stats.work_mode or self._interaction_in_progress:
            self._reset_mood_timer()
            return

        affection = self.stats.affection
        if affection > 90:
            self._mood_timer.setInterval(MOOD_LONG_CHECK_MS)
            category = random.choice(["idle", "happy"])
            if category == "happy":
                self._play_timed_mood("happy", MOOD_LONG_PLAY_MS)
            else:
                self._play("idle")
            return

        self._mood_timer.setInterval(MOOD_SHORT_CHECK_MS)
        if affection > 80:
            if random.random() < 0.5:
                self._play_timed_mood("happy", MOOD_SHORT_PLAY_MS)
            else:
                self._play("idle")
            return

        if affection > 50:
            self._play("idle")
            return

        if random.random() < 0.5:
            self._play_timed_mood("angry", MOOD_SHORT_PLAY_MS)
        else:
            self._play("idle")

    def _play_timed_mood(self, category, duration_ms):
        if self._interaction_in_progress or self.stats.work_mode or not self.anim.has_category(category):
            return False
        self._mood_id += 1
        current_id = self._mood_id
        self._mood_until = time.time() + duration_ms / 1000
        self._play(category)
        self._schedule_single_shot(duration_ms, lambda: self._end_mood(current_id))
        return True

    def _end_mood(self, mood_id):
        if self._mood_id != mood_id or self._interaction_in_progress:
            return
        self._mood_until = 0
        self._play("idle")

    def _disconnect_movie_signals(self, movie):
        for signal in (movie.finished, movie.frameChanged):
            self._safe_disconnect(signal)

    @staticmethod
    def _safe_disconnect(signal, slot=None):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            try:
                if slot is None:
                    signal.disconnect()
                else:
                    signal.disconnect(slot)
            except (RuntimeError, TypeError):
                pass

    def _end_once_movie(self, movie, frame, interaction_id):
        if not self._interaction_in_progress or self._interaction_id != interaction_id:
            return
        frame_count = movie.frameCount()
        if frame_count > 0 and frame >= frame_count - 1:
            if (time.time() - self._interaction_started_at) * 1000 < INTERACTION_MIN_MS:
                return
            movie.stop()
            QTimer.singleShot(0, lambda: self._end_interaction(interaction_id))

    def _end_interaction(self, interaction_id=None):
        if interaction_id is not None and self._interaction_id != interaction_id:
            return
        self._interaction_in_progress = False
        self._play("idle")

    def _force_end_interaction(self, interaction_id):
        if self._interaction_in_progress and self._interaction_id == interaction_id:
            self._interaction_in_progress = False
            self._play("idle")

    def _play_bye_before_quit(self):
        movie = self.anim.get_random("bye")
        if not movie:
            return False
        self._quitting = True
        self._quit_in_progress = True
        self._hover_timer.stop()
        self._interaction_id += 1
        self._interaction_in_progress = False
        self._mood_id += 1
        self._mood_until = 0

        self.label.setMovie(movie)
        movie.setScaledSize(self.label.size())
        self._state = "bye"
        self._last_state_change = time.time()
        self._quit_animation_id = getattr(self, "_quit_animation_id", 0) + 1
        quit_id = self._quit_animation_id
        self._disconnect_movie_signals(movie)
        movie.frameChanged.connect(
            lambda frame, m=movie, qid=quit_id: self._end_bye_movie(m, frame, qid)
        )
        movie.finished.connect(lambda qid=quit_id: self._finish_quit(qid))
        movie.start()
        self._schedule_single_shot(
            INTERACTION_TIMEOUT_MS,
            lambda qid=quit_id: self._finish_quit(qid),
        )
        return True

    def _end_bye_movie(self, movie, frame, quit_id):
        if getattr(self, "_quit_animation_id", None) != quit_id:
            return
        frame_count = movie.frameCount()
        if frame_count > 0 and frame >= frame_count - 1:
            movie.stop()
            QTimer.singleShot(0, lambda: self._finish_quit(quit_id))

    def _finish_quit(self, quit_id=None):
        if quit_id is not None and getattr(self, "_quit_animation_id", None) != quit_id:
            return
        if getattr(self, "_quit_finished", False):
            return
        self._quit_finished = True
        self._quitting = True
        self._stop_keyboard_follow()
        self._sync_position_for_save()
        self.stats.save()
        QApplication.quit()

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
        self._sync_position_for_save()

        callbacks = {
            "feed": self._do_feed,
            "bath": self._do_bath,
            "greet": self._do_greet,
            "play": self._do_play,
            "toggle_work": self._toggle_work,
            "toggle_topmost": self._toggle_topmost,
            "toggle_click_through": self._toggle_click_through,
            "toggle_keyboard": self._toggle_keyboard,
            "toggle_startup": self._toggle_startup,
            "set_size": self._set_pet_size,
            "quit": self._quit,
        }

        menu = PetMenu(
            self.stats,
            callbacks,
            self,
            startup_enabled=self._is_startup_enabled(),
        )
        menu.exec(pos)

    def _do_feed(self):
        if self._interaction_in_progress or not self.stats.can_do("feed"):
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
        if self._interaction_in_progress or not self.stats.can_do("bath"):
            return
        self.stats.bath()
        self._play_once("bath")

    def _do_greet(self):
        if self._interaction_in_progress or not self.stats.can_do("greet"):
            return
        self.stats.greet()
        self._play_once("greet")

    def _do_play(self):
        if self._interaction_in_progress or not self.stats.can_do("play"):
            return
        self.stats.play()
        self._play_once("play")

    def _toggle_work(self):
        if self.stats.work_mode:
            self.stats.work_mode = False
            self._exit_work()
        else:
            self._sync_position_for_save()
            self.stats.work_mode = True
            self._enter_work()

    def _enter_work(self):
        self._cancel_transient_animations_for_work()
        self._work_prev_size = self.stats.pet_size  # 记住用户尺寸
        self._set_size(self._work_mode_pet_size())
        self._refresh_keyboard_follow()
        self.stats.pet_size = self._work_prev_size   # 保留用户尺寸，不被工作模式覆盖
        screen = QApplication.primaryScreen().availableGeometry()
        self.move(
            screen.width() - self.width() - WORK_MARGIN_RIGHT,
            screen.height() - self.height() - WORK_MARGIN_BOTTOM,
        )
        self._apply_click_through()
        self._apply_topmost()
        self._setup_tray_menu()
        # 先 show 再设动画
        if not self.stats.keyboard_visible and self.anim.has_category("work"):
            self._play("work")

    def _cancel_transient_animations_for_work(self):
        self._hover_timer.stop()
        if self._interaction_in_progress:
            self._interaction_id += 1
        self._interaction_in_progress = False
        self._mood_id += 1
        self._mood_until = 0

    def _exit_work(self):
        self._stop_keyboard_follow()
        self._set_size(self.stats.pet_size)
        self._apply_click_through()
        self._apply_topmost()
        self._setup_tray_menu()
        self.move(self.stats.x, self.stats.y)
        self._clamp_window_position()
        self._play("idle")

    def _toggle_topmost(self):
        self.stats.topmost = not self.stats.topmost
        self._apply_topmost()

    def _toggle_click_through(self):
        self.stats.click_through = not self.stats.click_through
        self._apply_click_through()
        self._setup_tray_menu()

    def _toggle_keyboard(self):
        self.stats.keyboard_visible = not self.stats.keyboard_visible
        current_size = self._work_mode_pet_size() if self.stats.work_mode else self.stats.pet_size
        saved_size = self.stats.pet_size
        self._set_size(current_size)
        self._refresh_keyboard_follow()
        if self.stats.work_mode:
            self.stats.pet_size = saved_size
        self._clamp_window_position()

    def _is_startup_enabled(self):
        return pet_startup.is_startup_enabled()

    def _toggle_startup(self):
        pet_startup.set_startup_enabled(not self._is_startup_enabled())

    # ===== 系统托盘 =====
    def _setup_tray(self):
        self.tray = QSystemTrayIcon(self)
        # 从第一个 idle GIF 提取图标
        icon = QIcon()
        idle_gifs = self.anim._movies.get("idle", [])
        if idle_gifs:
            movie = QMovie(idle_gifs[0].fileName())
            movie.setCacheMode(QMovie.CacheMode.CacheAll)
            self._tray_icon_movie = movie
            self._tray_icon_movie.start()
            self._tray_icon_movie.jumpToFrame(0)
            # 等一帧渲染
            QTimer.singleShot(100, lambda: self._set_tray_icon(self._tray_icon_movie))
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
        if self.stats.click_through:
            click_action = QAction("关闭鼠标穿透", self)
            click_action.triggered.connect(self._disable_click_through)
            menu.addAction(click_action)
        if self.stats.work_mode:
            work_action = QAction("退出打工模式", self)
            work_action.triggered.connect(self._exit_work_from_tray)
            menu.addAction(work_action)
        menu.addSeparator()
        quit_action = QAction("退出", self)
        quit_action.triggered.connect(self._quit)
        menu.addAction(quit_action)

        self.tray.setContextMenu(menu)
        self._safe_disconnect(self.tray.activated, self._tray_click)
        self.tray.activated.connect(self._tray_click)

    def _tray_click(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self._toggle_visible()

    def _toggle_visible(self):
        if self.isVisible():
            self.hide()
        else:
            self._apply_topmost()

    def _disable_click_through(self):
        self.stats.click_through = False
        self._apply_click_through()
        self._setup_tray_menu()

    def _exit_work_from_tray(self):
        if self.stats.work_mode:
            self._toggle_work()
        self._setup_tray_menu()

    # ===== 生命周期 =====
    def _sync_position_for_save(self):
        if not self.stats.work_mode:
            self.stats.x = self.x()
            self.stats.y = self.y()

    def closeEvent(self, event):
        self._stop_keyboard_follow()
        if not getattr(self, '_quitting', False):
            self._sync_position_for_save()
            self.stats.save()
        event.accept()

    def _quit(self):
        if getattr(self, "_quit_in_progress", False):
            return
        if self.anim.has_category("bye") and self._play_bye_before_quit():
            return
        self._finish_quit()
