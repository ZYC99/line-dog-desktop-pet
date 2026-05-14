# 修复任务 2：鼠标乱跳 + 无法拖动 + 滚轮调大小

> 项目路径: D:/软件安装/line-dog-desktop-pet
> 用 OpenCode 执行

---

## 问题诊断

### 问题1：鼠标经过乱跳动作
**原因：** `enterEvent` 无脑触发 greet，鼠标扫过就播。
**修复：** 加 500ms 延迟定时器，鼠标停留超时才触发 greet。`leaveEvent` 取消定时器。

### 问题2：无法拖动
**原因：** `enterEvent` 触发的 `_play_once("greet")` 与 `mouseMoveEvent` 的 drag movie 互相覆盖：
1. 鼠标进入 → greet 动画开始 → `_interaction_in_progress = True`
2. 用户点击拖动 → `mouseMoveEvent` 设置 drag movie
3. greet 动画的 `finished` 信号触发 → `_end_interaction()` → `_play("idle")` → 冲掉 drag movie

额外问题：`mouseMoveEvent` 每帧都从 `anim._movies` 取新 movie 对象并 `.start()`，极其浪费。
**修复：**
- `enterEvent` 加守卫：正在拖拽中（`_drag_start is not None`）或 `_interaction_in_progress` 时跳过 greet
- `mouseMoveEvent`：只首次进入拖拽时设 movie，后续帧只 `move()`，不再重复设 movie
- `_play_drag_raw` 废弃，逻辑合并到 mouseMoveEvent

### 问题3：大中小按钮应绑定滚轮
**修复：** `wheelEvent`：Ctrl+滚轮调大小 ±10px，范围 80~400。

---

## 具体修改

### 修改 `pet_window.py`

#### 1. `__init__` 追加属性
在 `self._last_hover_greet = 0` 后面加一行：
```python
self._hover_timer = None          # 鼠标停留计时器
```

#### 2. 重写 `enterEvent`
```python
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
        if self._hover_timer is not None:
            self._hover_timer.stop()
        self._hover_timer = QTimer(self)
        self._hover_timer.setSingleShot(True)
        self._hover_timer.timeout.connect(self._do_hover_greet)
        self._hover_timer.start(500)

def _do_hover_greet(self):
    """延迟触发的鼠标经过打招呼"""
    if self._drag_start is not None or self._interaction_in_progress:
        return
    self._play_once("greet")
    self._last_hover_greet = time.time()
```

#### 3. 修改 `leaveEvent`
```python
def leaveEvent(self, event):
    """鼠标离开窗口"""
    self._last_mouse_leave = time.time()
    # 取消延迟打招呼
    if self._hover_timer is not None:
        self._hover_timer.stop()
        self._hover_timer = None
```

#### 4. 重写 `mouseMoveEvent`（简化 + 修复）
```python
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
        else:
            self._play("drag")

    self._last_mouse_pos = pos
    self.move(pos - self._drag_start)
```

#### 5. 删除 `_play_drag_raw` 方法（不再需要）

#### 6. 新增 `wheelEvent`
```python
def wheelEvent(self, event):
    """Ctrl + 滚轮调整宠物大小"""
    if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
        delta = event.angleDelta().y()
        new_size = self.width() + (10 if delta > 0 else -10)
        self._set_pet_size(new_size)
        event.accept()
    else:
        super().wheelEvent(event)
```

---

## 执行顺序

1. 修改 `pet_window.py`：上述 6 处修改
2. 语法检查
3. 启动验证
