# 审查后修复：4 个 bug

> 项目: D:/软件安装/line-dog-desktop-pet

---

## Bug 1：`_force_end_interaction` 竞态

**文件:** pet_window.py
**修复:** 用交互计数器代替全局标志。`_play_once` 每次 `self._interaction_id += 1`，`_force_end_interaction` 检查 ID 是否匹配。

```python
# __init__ 加:
self._interaction_id = 0

# _play_once 改为:
def _play_once(self, category: str):
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

# _force_end_interaction 改为:
def _force_end_interaction(self, interaction_id):
    if self._interaction_in_progress and self._interaction_id == interaction_id:
        self._interaction_in_progress = False
        self._play("idle")
```

---

## Bug 2：打工模式下 Ctrl+滚轮可缩放

**文件:** pet_window.py wheelEvent
**修复:** 打工模式时禁用滚轮缩放。

```python
def wheelEvent(self, event):
    if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
        if self.stats.work_mode:
            return  # 打工模式禁止缩放
        delta = event.angleDelta().y()
        new_size = self.width() + (10 if delta > 0 else -10)
        self._set_pet_size(new_size)
        event.accept()
    else:
        super().wheelEvent(event)
```

---

## Bug 3：拖拽被 tick 打断

**文件:** pet_window.py mouseMoveEvent
**修复:** 拖拽时更新 `_last_state_change`，防止 tick 覆盖动画。

在 `mouseMoveEvent` 中设置 `_state = "drag"` 后新增一行：
```python
self._last_state_change = time.time()
```

---

## Bug 4：`loopCount` 污染

**文件:** pet_window.py _play 方法
**修复:** `_play()` 中设置 `movie.loopCount = -1`（无限循环），避免 `_play_once` 残留的 `loopCount=1` 影响后续循环播放。

在 `_play` 方法中 `movie.start()` 之前加：
```python
movie.loopCount = -1  # 确保循环播放
```

---

## 执行顺序

1. 改 pet_window.py 四处
2. 语法检查
