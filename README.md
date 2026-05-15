# Line Dog Desktop Pet

PySide6 桌面宠物应用，提供桌面小狗动画、属性状态、互动菜单、工作模式、随机移动和 GitHub Actions 发布构建。

## 快速开始

```powershell
.\.venv\Scripts\python.exe main.py
```

## 动作预览

点击下面的 GIF 链接可以预览内置动作素材：

| 动作 | 预览 |
|------|------|
| 待机 | [idle_01.gif](assets/gif/idle/idle_01.gif) |
| 走路 | [walk_01.gif](assets/gif/walk/walk_01.gif) |
| 拖拽 | [drag_01.gif](assets/gif/drag/drag_01.gif) |
| 打招呼 | [greet_01.gif](assets/gif/greet/greet_01.gif) |
| 喂食 | [eat_01.gif](assets/gif/eat/eat_01.gif) |
| 洗澡 | [bath_01.gif](assets/gif/bath/bath_01.gif) |
| 玩耍 | [play_01.gif](assets/gif/play/play_01.gif) |
| 开心 | [happy_01.gif](assets/gif/happy/happy_01.gif) |
| 睡觉 | [sleep_01.gif](assets/gif/sleep/sleep_01.gif) |
| 打工 | [work_01.gif](assets/gif/work/work_01.gif) |
| 告别 | [bye_01.gif](assets/gif/bye/bye_01.gif) |

## 验证

```powershell
$env:QT_QPA_PLATFORM='offscreen'; .\.venv\Scripts\python.exe -m unittest test_regressions.py
.\.venv\Scripts\python.exe -m py_compile main.py config.py pet_stats.py pet_animation.py pet_menu.py pet_window.py test_regressions.py
git diff --check
```

## 文档

- [项目文档索引](docs/README.md)
- [代码编写规范](CLAUDE.md)
- [GIF 资源说明](assets/gif/README.md)

## 发布

Release 构建由 GitHub Actions 负责。推送 `v*` 标签后，工作流会安装依赖、运行测试、执行 PyInstaller，并上传 `LineDogPet.exe` 到 GitHub Release。
