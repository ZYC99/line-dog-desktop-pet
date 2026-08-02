<p align="right">
  <a href="README.md">中文</a> |
  <a href="README.en.md">English</a>
</p>

<h1 align="center">Line Dog Desktop Pet</h1>

<p align="center">
  A lightweight PySide6 desktop dog supporting transparent floating, interactive animations, attribute states, work mode, tray control, and exit farewell animation.
</p>

<p align="center">
  <a href="https://github.com/ZYC99/line-dog-desktop-pet/releases/latest">Download Latest</a>
  ·
  <a href="assets/gif/README.md">View Material Guide</a>
  ·
  <a href="docs/README.md">Project Documentation</a>
</p>

## Features

- Desktop transparent floating dog, displayed on top by default, can be shown/hidden via tray.
- Right-click interactive menu: feeding, bathing, greeting, playing, work mode, size adjustment.
- Attribute states: hunger, cleanliness, and affection change over time.
- Mood and status animations: idle, walking, happy, angry, hungry, dirty, sleeping, etc.
- Work mode: shrinks to 135px, locks work animation, reduces desktop interference.
- Exit farewell animation: plays the `bye` animation before closing the application, then saves state and exits.
- GitHub Actions automatically builds Release and uploads `LineDogPet.exe` with a dog icon.

## Action Preview

GIFs can be played directly in the GitHub README. Only representative actions are shown here; the complete material list is available at [GIF Resource Guide](assets/gif/README.md).

| Idle | Walk | Drag | Greet |
|------|------|------|--------|
| <img src="assets/gif/idle/idle_01.gif" width="120" alt="Idle"> | <img src="assets/gif/walk/walk_01.gif" width="120" alt="Walk"> | <img src="assets/gif/drag/drag_01.gif" width="120" alt="Drag"> | <img src="assets/gif/greet/greet_01.gif" width="120" alt="Greet"> |

| Feed | Bath | Play | Happy |
|------|------|------|------|
| <img src="assets/gif/eat/eat_01.gif" width="120" alt="Feed"> | <img src="assets/gif/bath/bath_01.gif" width="120" alt="Bath"> | <img src="assets/gif/play/play_01.gif" width="120" alt="Play"> | <img src="assets/gif/happy/happy_01.gif" width="120" alt="Happy"> |

| Sleep | Work | Bye | Astonished |
|------|------|------|------|
| <img src="assets/gif/sleep/sleep_01.gif" width="120" alt="Sleep"> | <img src="assets/gif/work/work_01.gif" width="120" alt="Work"> | <img src="assets/gif/bye/bye_01.gif" width="120" alt="Bye"> | <img src="assets/gif/astonishing/astonishing_01.gif" width="120" alt="Astonished"> |

## Quick Start

General users can directly download `LineDogPet.exe` from [Releases](https://github.com/ZYC99/line-dog-desktop-pet/releases/latest).

Development run:

```powershell
.\.venv\Scripts\python.exe main.py
```

## Testing

```powershell
$env:QT_QPA_PLATFORM='offscreen'; .\.venv\Scripts\python.exe -m unittest test_regressions.py
.\.venv\Scripts\python.exe -m py_compile main.py config.py pet_stats.py pet_animation.py pet_menu.py pet_window.py test_regressions.py
git diff --check
```

## Packaging

Local maintainers can use:

```powershell
.\build.bat
```

Release builds are handled by GitHub Actions. After pushing a `v*` tag, the workflow installs dependencies, runs tests, executes PyInstaller, and uploads `LineDogPet.exe` with a dog icon to the GitHub Release.

## Documentation

- [Project Documentation Index](docs/README.md)
- [Code Writing Guidelines](CLAUDE.md)
- [GIF Resource Guide](assets/gif/README.md)
- [English README](README.en.md) 
</p>
