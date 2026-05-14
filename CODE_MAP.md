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
