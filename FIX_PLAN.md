# 修复任务：4 个 bug + 按钮质感 + codemap

> 项目路径: D:/软件安装/line-dog-desktop-pet
> 用 OpenCode 执行，按顺序修复

---

## 修复 1：GIF 缩放 (`pet_window.py`)

**问题：** `setFixedSize` 只改了窗口大小，GIF 还是原始尺寸。
**修复：** 所有设置 movie 的地方，加一行 `movie.setScaledSize(self.label.size())`

涉及位置（搜索 `self.label.setMovie(movie)` 和 `movie.start()` 附近）：

1. `_play()` — 在 `self.label.setMovie(movie)` 之后加：
```python
movie.setScaledSize(self.label.size())
```

2. `_play_walk()` — 同上

3. `_play_once()` — 同上，并且在 `movie.start()` 之前加：
```python
movie.setLoopCount(1)  # 播一次就停，触发 finished 信号
movie.setScaledSize(self.label.size())
```

4. `mouseMoveEvent` 里 drag movie 设置处 — 也加 `movie.setScaledSize(self.label.size())`

5. `_enter_work()` 里 — 在 `self._play("work")` 调用后会设 movie，但 `_play` 内已经加过了所以不用改。

---

## 修复 2：喂食 + full 动画 (`pet_window.py`)

**当前代码（`_do_feed`）：**
```python
def _do_feed(self):
    if not self.stats.can_do("feed"):
        return
    self.stats.feed()
    if self.stats.is_full and self.anim.has_category("full"):
        self._play_once("full")
    else:
        self._play_once("eat")
```

**改为：**
```python
def _do_feed(self):
    if not self.stats.can_do("feed"):
        return
    # 饱了就弹 full，不消耗
    if self.stats.hunger >= 100:
        if self.anim.has_category("full"):
            self._play_once("full")
        return
    self.stats.feed()
    if self.stats.is_full and self.anim.has_category("full"):
        self._play_once("full")
    else:
        self._play_once("eat")
```

---

## 修复 3：打工模式动画 (`pet_window.py`)

**当前 `_enter_work`：**
```python
def _enter_work(self):
    self._work_prev_size = self.stats.pet_size
    self._set_size(WORK_MODE_SIZE)
    self.stats.pet_size = self._work_prev_size
    screen = QApplication.primaryScreen().availableGeometry()
    self.move(...)
    self.stats.topmost = True
    self.stats.click_through = True
    self._apply_topmost()      # ← 这里调了 show()，冲掉 movie
    self._apply_click_through()
    if self.anim.has_category("work"):
        self._play("work")     # ← movie 被冲掉了
```

**改为：把 `_play("work")` 移到 `_apply_topmost()` 之前：**
```python
def _enter_work(self):
    self._work_prev_size = self.stats.pet_size
    self._set_size(WORK_MODE_SIZE)
    self.stats.pet_size = self._work_prev_size
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
```

---

## 修复 4：预设按钮质感 (`pet_menu.py`)

**当前 `_add_size_control` 里的按钮样式：** 用了内联 f-string，按钮按下没有反馈。

**改为：** 去掉"高亮选中"逻辑（反正滑块指示值），统一按钮样式，加 `:pressed` 伪状态让按下有凹陷感：

把现有的 btn_row 循环体和 stylesheet 改为：

在 `_add_size_control` 方法中，把按钮样式 QSS 追加到主 stylesheet 末尾：

主 stylesheet 追加：
```css
QPushButton.szbtn {
    background: #3a3a3a;
    color: #ccc;
    border: 1px solid #555;
    border-radius: 3px;
    padding: 3px 6px;
    font-size: 10px;
}
QPushButton.szbtn:hover {
    background: #4a4a4a;
    border-color: #777;
}
QPushButton.szbtn:pressed {
    background: #2a2a2a;
    border-color: #4ec9b0;
    padding-top: 4px;
    padding-bottom: 2px;
}
```

然后把按钮创建简化为：
```python
for label, px in SIZE_PRESETS.items():
    btn = QPushButton(f"{label}\n{px}px")
    btn.setFixedHeight(36)
    btn.setProperty("class", "szbtn")
    btn.setStyleSheet("")  # 继承父级 stylesheet
    btn.clicked.connect(lambda checked, p=px: self._cb_size(p))
    btn_row.addWidget(btn)
```

> 注意：PySide6 的 QSS 用 `property` + 属性选择器 `.szbtn` 需要按钮设置 `property`。但更简单的方式是直接用 objectName。统一给按钮设 `objectName="szbtn"` 然后在 stylesheet 里用 `QPushButton#szbtn` 匹配... 但多个同名 id 不标准。干脆用类选择器 `.szbtn` 配合 `setProperty("class", "szbtn")`。

**实际上 PySide6 不支持 class 选择器。** 用更简单的方式：直接给所有 szbtn 设置同一个动态属性，然后用属性选择器：

```python
btn.setProperty("szbtn", True)
```

stylesheet 里：
```css
QPushButton[szbtn="true"] { ... }
QPushButton[szbtn="true"]:hover { ... }
QPushButton[szbtn="true"]:pressed { ... }
```

然后把 btn 的默认 stylesheet 清空让它继承父级：
```python
btn.setStyleSheet("")
```

同时删掉主 stylesheet 里旧的 `QPushButton { ... }` 和 `QPushButton:hover { ... }` 通用样式（因为和现在的专有样式冲突）。

---

## 新增：CODE_MAP.md

在项目根目录 `D:/软件安装/line-dog-desktop-pet/CODE_MAP.md` 创建：

```markdown
# 代码地图 — 线条小狗桌宠

## 文件导航

| 文件 | 职责 |
|------|------|
| `main.py` | 入口、单实例检测 |
| `pet_window.py` | 主窗口：透明窗、状态机、动画调度、鼠标交互、菜单回调 |
| `pet_stats.py` | 属性系统：饱食/清洁/好感 + CD + JSON 持久化 |
| `pet_animation.py` | GIF 素材加载、分类管理、方向选择 |
| `pet_menu.py` | 右键菜单 UI（属性条、按钮、滑块） |
| `config.py` | 全局常量 |
| `build.bat` | PyInstaller 打包 |
| `.github/workflows/release.yml` | CI 自动构建 |

## 功能 → 代码定位

### 窗口与显示
- 透明无边框窗口 → `pet_window.py: PetWindow.__init__` (L15-23)
- 窗口置顶切换 → `pet_window.py: _apply_topmost` (L69-76)
- 鼠标穿透切换 → `pet_window.py: _apply_click_through` (L78-82)
- 尺寸调整 → `pet_window.py: _set_size / _set_pet_size` (L65-73)
- 尺寸预设 → `config.py: SIZE_PRESETS` (L19)

### 动画播放
- 播放分类 GIF → `pet_window.py: _play` (L85-98)
- 播放一次后回 idle → `pet_window.py: _play_once` (L151-161)
- 走路动画（方向选择）→ `pet_window.py: _play_walk` (L100-113)
- GIF 加载与分类 → `pet_animation.py: PetAnimation._load_all` (L22-36)
- walk 方向奇偶判断 → `pet_animation.py: _file_parity` (L54-58)

### 鼠标交互
- 左键拖拽 → `pet_window.py: mousePressEvent / mouseMoveEvent / mouseReleaseEvent` (L209-257)
- 拖拽方向 → `pet_window.py: mouseMoveEvent` (L220-244)
- 鼠标经过打招呼 → `pet_window.py: enterEvent` (L259-274)
- 鼠标离开计时 → `pet_window.py: leaveEvent` (L276-278)
- 久置后鼠标进入震惊 → `pet_window.py: enterEvent` (L268-273)
- 右键菜单弹出 → `pet_window.py: _show_menu` (L280-295)

### 右键菜单
- 菜单构建 → `pet_menu.py: _build` (L31-78)
- 属性进度条 → `pet_menu.py: _add_stat_bar` (L80-120)
- 尺寸滑块 → `pet_menu.py: _add_size_control` (L122-172)
- 菜单回调 → `pet_window.py: _show_menu` callbacks (L287-296)

### 互动操作
- 喂食 → `pet_window.py: _do_feed` (L298-307)
- 洗澡 → `pet_window.py: _do_bath` (L309-313)
- 打招呼 → `pet_window.py: _do_greet` (L315-319)
- 玩耍 → `pet_window.py: _do_play` (L321-325)
- CD 检查 → `pet_stats.py: can_do` (L44-48)

### 属性系统
- 饱食度/清洁度/好感度 → `pet_stats.py` (L8-41)
- 属性衰减 → `pet_stats.py: tick` (L75-78)
- 互动数值变化 → `pet_stats.py: feed/bath/greet/play` (L54-72)
- 持久化保存 → `pet_stats.py: save` (L81-99)
- 持久化加载 → `pet_stats.py: _load` (L101-121)
- 衰减速率配置 → `config.py` (L20-22)

### 状态机
- 主循环 tick → `pet_window.py: _tick` (L116-149)
- 空闲 → 睡觉过渡 → `pet_window.py: _tick` (L140-142)
- 空闲 → 走路过渡 → `pet_window.py: _tick` (L144-145)
- 空闲计时配置 → `config.py` (L38-51)

### 打工模式
- 进入打工 → `pet_window.py: _enter_work` (L327-339)
- 退出打工 → `pet_window.py: _exit_work` (L341-347)

### 系统托盘
- 托盘初始化 → `pet_window.py: _setup_tray` (L361-377)
- 退出保存 → `pet_window.py: closeEvent / _quit` (L409-419)

### 打包 & 发布
- PyInstaller → `build.bat`
- GitHub Actions → `.github/workflows/release.yml`
```

---

## 执行顺序

1. 修改 `pet_window.py`：GIF 缩放 + 喂食 + 打工动画
2. 修改 `pet_menu.py`：按钮质感
3. 创建 `CODE_MAP.md`
4. 语法检查全部文件
5. 启动验证
