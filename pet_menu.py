from PySide6.QtWidgets import QMenu, QWidgetAction, QProgressBar, QLabel, QVBoxLayout, QHBoxLayout, QWidget, QSlider, QPushButton
from PySide6.QtGui import QAction
from PySide6.QtCore import Qt

class PetMenu(QMenu):
    def __init__(self, stats, callbacks: dict, parent=None, startup_enabled=False):
        super().__init__(parent)
        self.stats = stats
        self.cb = callbacks  # {action_name: callable}
        self.startup_enabled = startup_enabled
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
            QSlider::groove:horizontal {
                height: 6px;
                background: #3a3a3a;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                width: 14px;
                height: 14px;
                margin: -4px 0;
                background: #4ec9b0;
                border-radius: 7px;
            }
            QPushButton[szbtn="true"] {
                background: #3a3a3a;
                color: #ccc;
                border: 1px solid #555;
                border-radius: 3px;
                padding: 3px 6px;
                font-size: 10px;
            }
            QPushButton[szbtn="true"]:hover {
                background: #4a4a4a;
                border-color: #777;
            }
            QPushButton[szbtn="true"]:pressed {
                background: #2a2a2a;
                border-color: #4ec9b0;
                padding-top: 4px;
                padding-bottom: 2px;
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
        self._add_check("开机自启", "toggle_startup", self.startup_enabled)

        self.addSeparator()

        # 尺寸调整
        self._add_size_control()

        self.addSeparator()

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

    def _add_size_control(self):
        """添加尺寸调节：预设按钮 + 滑块"""
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(6)

        self._size_label = QLabel()
        self._size_label.setStyleSheet("color: #ccc; font-size: 11px;")
        layout.addWidget(self._size_label)

        # 预设按钮行
        btn_row = QHBoxLayout()
        from config import SIZE_PRESETS, SIZE_MIN, SIZE_MAX
        current = int(self.stats.pet_size)
        for label, px in SIZE_PRESETS.items():
            btn = QPushButton(f"{label}\n{px}px")
            btn.setFixedHeight(36)
            btn.setProperty("szbtn", True)
            btn.setStyleSheet("")
            btn.clicked.connect(lambda checked, p=px: self._set_slider_size(p))
            btn_row.addWidget(btn)
        layout.addLayout(btn_row)

        # 滑块
        self._size_slider = QSlider(Qt.Orientation.Horizontal)
        self._size_slider.setRange(SIZE_MIN, SIZE_MAX)
        self._size_slider.setValue(current)
        self._size_slider.setFixedHeight(20)
        self._size_slider.valueChanged.connect(self._cb_size)
        layout.addWidget(self._size_slider)
        self._update_size_label(current)

        wa = QWidgetAction(self)
        wa.setDefaultWidget(w)
        self.addAction(wa)

    def _set_slider_size(self, value):
        if self._size_slider.value() == value:
            self._cb_size(value)
            return
        self._size_slider.setValue(value)

    def _cb_size(self, value):
        self._update_size_label(value)
        if "set_size" in self.cb:
            self.cb["set_size"](value)

    def _update_size_label(self, value):
        self._size_label.setText(f"🔍 尺寸 {int(value)}px")

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
