# 全面代码审查任务

> 项目: D:/软件安装/line-dog-desktop-pet
> 目标: 逐文件通读所有 Python 代码，检查逻辑漏洞、API 兼容性、边界情况

## 审查清单

### 1. 通读所有 Python 文件
- config.py
- pet_animation.py
- pet_stats.py
- pet_menu.py
- pet_window.py
- main.py

### 2. 重点检查项

#### PySide6 API 兼容性（PySide6 6.11.1）
已知问题：`setLoopCount` → 应改为 `loopCount = 1`（已修）
检查是否还有其他 API 调用不兼容。

#### 逻辑漏洞
- `_play_once` 结束后是否可靠回到 idle
- `_end_interaction` 是否会被多次调用（movie.finished 信号可能重复触发）
- `_tick` 中属性衰减是否与互动冲突
- `_random_walk` 边界检查是否正确（使用当前 size 而非 WINDOW_SIZE）
- `enterEvent` 守卫是否完善
- `mouseMoveEvent` 在拖拽结束后是否清理干净

#### 边界情况
- 素材文件夹为空或缺失时是否会崩溃
- JSON 文件损坏时能否优雅降级
- 窗口移出屏幕外能否恢复
- 打工模式切换各状态是否正确保存

#### 编码质量
- import 是否冗余（如 pet_window.py 里 `from config import *` 可能不必要）
- lambda 闭包是否有延迟绑定问题
- QTimer 是否正确清理，防止内存泄漏

### 3. 输出格式
对每个发现的问题，给出：
- 文件:行号
- 问题描述
- 修复建议（代码片段）

如果代码无问题就报告 "✅ clean"。

### 4. 验证
审查完成后运行 `python -m py_compile` 检查全部文件，确保语法无误会。
