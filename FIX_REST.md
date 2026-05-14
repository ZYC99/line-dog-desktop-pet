# 中等+轻微问题修复（14项）

> 项目: D:/软件安装/line-dog-desktop-pet
> 一次全部修复

---

## 配置同步（🟡#3 + 🟢#15）

### pet_stats.py — 使用 config 常量替换硬编码

导入改为：
```python
from config import DATA_FILE, DATA_DIR, COOLDOWN, WINDOW_SIZE, \
    FEED_HUNGER, FEED_AFFECTION, BATH_CLEAN, BATH_AFFECTION, \
    GREET_AFFECTION, PLAY_HUNGER_COST, PLAY_CLEAN_COST, PLAY_AFFECTION
```

然后把 `feed/bath/greet/play` 四个方法中的 `30/40/10/5/15` 替换为对应常量：
- `feed()`: `self.hunger + 30` → `FEED_HUNGER`, `self.affection + 5` → `FEED_AFFECTION`
- `bath()`: `self.cleanliness + 40` → `BATH_CLEAN`, `self.affection + 5` → `BATH_AFFECTION`
- `greet()`: `self.affection + 10` → `GREET_AFFECTION`
- `play()`: `self.hunger - 5` → `PLAY_HUNGER_COST`, `self.cleanliness - 10` → `PLAY_CLEAN_COST`, `self.affection + 15` → `PLAY_AFFECTION`

### config.py — 删除未使用的常量

删除以下用不到的：
```python
# 删除这三行
THRESHOLD_LOW = 20
THRESHOLD_HIGH = 80
THRESHOLD_VERY_LOW = 10
```

这些阈值在 pet_stats 里通过 is_hungry/is_dirty 等方法硬编码了 20/10/80，把那些方法也改用常量（或者直接删除这三行常量，减少歧义）。最简单的做法：**直接删除这三行**，因为 pet_stats 里的 `is_*` property 自己写了阈值。

---

## 内存泄漏（🟡#5）

### pet_window.py — _hover_timer 复用

**当前：** `enterEvent` 里每次 `QTimer(self)` 新建。
**改为：** `__init__` 中创建一次，`enterEvent` 只 `start()`。

在 `__init__` 中 `self._hover_timer = None` 改为：
```python
self._hover_timer = QTimer(self)
self._hover_timer.setSingleShot(True)
self._hover_timer.timeout.connect(self._do_hover_greet)
```

在 `enterEvent` 中删除原来的定时器创建逻辑，改为：
```python
    if now - self._last_hover_greet > GREET_HOVER_CD and self.anim.has_category("greet"):
        self._hover_timer.start(500)
```

在 `leaveEvent` 中删除 `self._hover_timer = None`，只保留：
```python
    self._hover_timer.stop()
```

---

## 拖拽稳健（🟡#6 + 🟡#8）

### pet_window.py — mousePressEvent 加 grabMouse，release 加守卫

**mousePressEvent：**
```python
def mousePressEvent(self, event):
    if event.button() == Qt.MouseButton.LeftButton:
        self._drag_start = event.globalPosition().toPoint() - self.pos()
        self._last_mouse_pos = event.globalPosition().toPoint()
        self.grabMouse()
    elif event.button() == Qt.MouseButton.RightButton:
        self._show_menu(event.globalPosition().toPoint())
```

**mouseReleaseEvent：**
```python
def mouseReleaseEvent(self, event):
    if self._drag_start:
        self.releaseMouse()
        self._drag_start = None
        self._last_mouse_pos = None
        self.stats.x = self.x()
        self.stats.y = self.y()
        if not self._interaction_in_progress:
            self._play("idle")
```

---

## 屏幕外恢复（🟡#7）

### pet_stats.py — _load 末尾加边界修复

在 `_load()` 方法末尾（`except Exception: pass` 之后）加：
```python
    def _load(self):
        ...
        except Exception:
            pass
        self._clamp_position()

    def _clamp_position(self):
        """确保坐标在屏幕范围内"""
        try:
            from PySide6.QtWidgets import QApplication
            app = QApplication.instance()
            if app:
                screen = app.primaryScreen().availableGeometry()
                self.x = max(0, min(self.x, screen.width() - self.pet_size))
                self.y = max(0, min(self.y, screen.height() - self.pet_size))
        except Exception:
            pass
```

---

## 超时保护（🟡#10）

### pet_window.py — _play_once 加 5 秒超时

在 `_play_once` 末尾：
```python
    movie.finished.connect(lambda: self._end_interaction())
    # 超时保护：5 秒后强制结束
    QTimer.singleShot(5000, self._force_end_interaction)
```

新增方法：
```python
def _force_end_interaction(self):
    if self._interaction_in_progress:
        self._interaction_in_progress = False
        self._play("idle")
```

---

## 刷动画（🟡#11）

### pet_window.py — _do_feed 饱了也消耗 CD

```python
def _do_feed(self):
    if not self.stats.can_do("feed"):
        return
    if self.stats.hunger >= 100:
        self.stats.do_action("feed")  # 消耗 CD
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

## tick 边界盲区（🟢#9）

### pet_window.py — `>` 改为 `>=`

```python
if idle_time >= IDLE_SLEEP_MIN and random.random() < 0.001:
```

---

## 死代码删除（🟢#13）

### pet_stats.py — 删除 clamp() 方法

删除这三行：
```python
def clamp(self):
    for attr in ["hunger", "cleanliness", "affection"]:
        setattr(self, attr, max(0, min(100, getattr(self, attr))))
```

---

## 冗余字段删除（🟢#16）

### pet_stats.py — 删除 idle_since

- `__init__`: 删除 `self.idle_since = time.time()`
- `save()`: 删除 `"idle_since": self.idle_since,`
- `_load()`: 删除 `self.idle_since = data.get("idle_since", time.time())`

---

## 双重保存（🟢#17）

### pet_window.py — _quit + closeEvent 加标志

```python
def _quit(self):
    self._quitting = True
    self.stats.x = self.x()
    self.stats.y = self.y()
    self.stats.save()
    QApplication.quit()

def closeEvent(self, event):
    if not getattr(self, '_quitting', False):
        self.stats.x = self.x()
        self.stats.y = self.y()
        self.stats.save()
    event.accept()
```

（不需要在 __init__ 加 `self._quitting = False`，`getattr` 默认 False）

---

## 方向降级（🟢#19）

### pet_animation.py — get_walk 方向 0 时明确返回 None

```python
def get_walk(self, direction: int) -> QMovie | None:
    if direction == 0:
        return self.get_random("jump")  # 没有 jump 就 None
```

删除 `or self.get_random("walk")` 回退。

---

## import * 污染（🟢#14）

### pet_window.py — 用 `import config as cfg` 替换 `from config import *`

改第6行：
```python
import config as cfg
```

然后全文搜索替换所有大写常量引用（如 `TICK_MS` → `cfg.TICK_MS`，`WINDOW_SIZE` → `cfg.WINDOW_SIZE` ...），或者更简单：

**更简单的方案：** 保持 `from config import *` 不变，只删 config 里用不到的常量。因为 pet_window 确实用了 config 里绝大多数常量，`import *` 在这里利大于弊。这项**跳过不做**。

---

## 执行顺序

按文件逐个改：
1. `config.py` — 删除未使用的 THRESHOLD 三行
2. `pet_stats.py` — 硬编码→常量、删除 clamp、删除 idle_since、加 _clamp_position
3. `pet_window.py` — hover_timer 复用、grabMouse、超时保护、刷动画、tick>=、双重保存
4. `pet_animation.py` — get_walk 降级

全部改完后语法检查。
