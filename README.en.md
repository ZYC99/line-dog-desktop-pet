<p align="right">
  <a href="README.md">中文</a> |
  <a href="README.en.md">English</a>
</p>

<h1 align="center">Line Dog Desktop Pet</h1>

<p align="center">
  A lightweight PySide6 desktop pet with transparent floating display, interaction animations, stats, work mode, tray controls, and a goodbye animation.
</p>

<p align="center">
  <a href="https://github.com/ZYC99/line-dog-desktop-pet/releases/latest">Download latest</a>
  ·
  <a href="assets/gif/README.md">GIF asset guide</a>
  ·
  <a href="docs/README.md">Project docs</a>
</p>

## Features

- Transparent floating desktop dog, shown on top by default, with tray show/hide controls.
- Right-click interaction menu: feed, bath, greet, play, work mode, and size controls.
- Pet stats: hunger, cleanliness, and affection change over time.
- Mood and state animations: idle, walk, happy, angry, hungry, dirty, sleep, and more.
- Work mode: shrinks to 135px and locks the work animation to reduce desktop distraction.
- Goodbye animation: plays the `bye` animation before saving state and quitting.
- GitHub Actions builds the Release executable and uploads `LineDogPet.exe` with the dog icon.

## Animation Preview

GIFs can be embedded directly in GitHub Markdown. This section shows representative animations. See the [GIF asset guide](assets/gif/README.md) for the full asset list.

| Idle | Walk | Drag | Greet |
|------|------|------|-------|
| <img src="assets/gif/idle/idle_01.gif" width="120" alt="Idle"> | <img src="assets/gif/walk/walk_01.gif" width="120" alt="Walk"> | <img src="assets/gif/drag/drag_01.gif" width="120" alt="Drag"> | <img src="assets/gif/greet/greet_01.gif" width="120" alt="Greet"> |

| Feed | Bath | Play | Happy |
|------|------|------|-------|
| <img src="assets/gif/eat/eat_01.gif" width="120" alt="Feed"> | <img src="assets/gif/bath/bath_01.gif" width="120" alt="Bath"> | <img src="assets/gif/play/play_01.gif" width="120" alt="Play"> | <img src="assets/gif/happy/happy_01.gif" width="120" alt="Happy"> |

| Sleep | Work | Bye | Astonished |
|-------|------|-----|------------|
| <img src="assets/gif/sleep/sleep_01.gif" width="120" alt="Sleep"> | <img src="assets/gif/work/work_01.gif" width="120" alt="Work"> | <img src="assets/gif/bye/bye_01.gif" width="120" alt="Bye"> | <img src="assets/gif/astonishing/astonishing_01.gif" width="120" alt="Astonished"> |

## Quick Start

End users can download `LineDogPet.exe` from [Releases](https://github.com/ZYC99/line-dog-desktop-pet/releases/latest).

Run from source:

```powershell
.\.venv\Scripts\python.exe main.py
```

## Verification

```powershell
$env:QT_QPA_PLATFORM='offscreen'; .\.venv\Scripts\python.exe -m unittest test_regressions.py
.\.venv\Scripts\python.exe -m py_compile main.py config.py pet_stats.py pet_animation.py pet_menu.py pet_window.py test_regressions.py
git diff --check
```

## Packaging

Maintainers can build locally with:

```powershell
.\build.bat
```

Release builds are handled by GitHub Actions. Pushing a `v*` tag installs dependencies, runs tests, executes PyInstaller, and uploads the dog-icon `LineDogPet.exe` to GitHub Releases.

## Documentation

- [Project documentation index](docs/README.md)
- [Coding guidelines](CLAUDE.md)
- [GIF asset guide](assets/gif/README.md)
- [中文 README](README.md)
