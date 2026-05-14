# Line Dog Desktop Pet

PySide6 桌面宠物应用，提供桌面小狗动画、属性状态、互动菜单、工作模式、随机移动和 GitHub Actions 发布构建。

## 快速开始

```powershell
.\.venv\Scripts\python.exe main.py
```

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
