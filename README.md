# linux_free_uart

Linux serial GUI tool with grouped command buttons, drag/drop reordering, and a lightweight DSL runner. Includes a built-in monochrome icon and a language toggle (English / Simplified Chinese).

## Features
- Non-exclusive serial access, custom baud rate, port refresh.
- Command groups with color tags, collapse/expand, drag between groups, and persistence in `commands.json`.
- Script DSL: SEND (with optional EXPECT/TIMEOUT), DELAY/WAIT, LOOP, SET, variable expansion.
- Log export, clear log, and About dialog (author, email, license).
- Language selector (default English; switches UI text dynamically).
- Generates a monochrome app icon at runtime (`linux_free_uart.png`) for desktop/dock display.

## Requirements
- Python 3.x
- PyQt5
- pyserial

Install deps (example):
```bash
pip install pyqt5 pyserial
```

## Run
```bash
python3 linux_free_uart.py
```

## Usage Notes
- Commands persist in `commands.json` alongside the script.
- “Save as Button” lets you choose which group to add the command to.
- The icon is regenerated on launch; the saved `linux_free_uart.png` can be referenced by a `.desktop` launcher.

## License
MIT License (see LICENSE). Author: moonlitcodex (moonlitcodex@qq.com).
