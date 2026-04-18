# Macro App

A lightweight Windows desktop macro tool. Record keyboard and mouse sequences, bind them to hotkeys, and replay them on demand — with support for holding keys/buttons down, looping, and per-action timing control.

## Features

- **Record sequences** of keyboard presses and mouse clicks (including side buttons X1/X2)
- **Separate down/up rows** — delete the release row to hold a key or mouse button down indefinitely
- **Per-action delay** — control the pause after each individual action
- **Global hotkeys** — trigger macros from anywhere, even when the app is minimised
- **Mouse button triggers** — assign a macro to a mouse button (middle, X1, X2, etc.)
- **Loop mode** — press the hotkey to start looping, press again to stop
- **Multiple macros** — saved to a local `macros.json` file
- **System tray** — runs quietly in the background; close the window to hide, right-click the tray icon to quit

## Requirements

- Windows 10/11
- Python 3.11+

## Setup

```bash
python -m venv venv
venv\Scripts\pip install -r requirements.txt
```

## Running

```bash
# With a console window (useful for debugging)
venv\Scripts\python.exe main.py

# Without a console window
venv\Scripts\pythonw.exe main.py
```

To launch automatically at startup, create a shortcut to `pythonw.exe main.py` and place it in your Windows Startup folder (`Win+R` → `shell:startup`).

## Usage

### Creating a macro

1. Click **New** in the main window
2. Enter a **name**
3. Click **Capture...** and press a key combination or mouse button to set the trigger hotkey
4. Tick **Loop** if you want the macro to repeat until the hotkey is pressed again
5. Click **Record**, perform your key presses and mouse clicks, then click **Stop**
6. Click **Save**

### Editing the sequence

After recording, the sequence appears as a table of actions:

| # | Action | Delay After (s) |
|---|--------|----------------|
| 1 | ↓ a | 0.0500 |
| 2 | ↑ a | 0.0200 |
| 3 | ↓ left-click (960, 540) | 0.1000 |
| 4 | ↑ left-click (960, 540) | 0.0200 |

- **↓** = press (key/button down), **↑** = release (key/button up)
- **Delete the ↑ row** to hold that key or button down for the remainder of the sequence
- **Double-click** the *Delay After* cell to edit the timing
- Use **↑ / ↓ buttons** to reorder rows

### Trigger hotkeys

Both keyboard combos and mouse buttons are supported:

| Format | Example |
|--------|---------|
| Key combination | `<ctrl>+<shift>+m` |
| Mouse middle button | `mouse:middle` |
| Side button 1 (Back) | `mouse:x1` |
| Side button 2 (Forward) | `mouse:x2` |

> **Note:** If the macro doesn't trigger in a specific app, try running Macro App as Administrator. Windows blocks simulated input from non-elevated processes targeting elevated windows.

## Files

| File | Purpose |
|------|---------|
| `main.py` | Entry point and app orchestration |
| `models.py` | `Macro` and `MacroKey` data classes |
| `store.py` | Load/save `macros.json` |
| `recorder.py` | Keyboard and mouse recording |
| `player.py` | Macro playback |
| `hotkeys.py` | Global hotkey listener |
| `tray.py` | System tray icon |
| `ui_main.py` | Main window |
| `ui_editor.py` | Macro editor dialog |

## Dependencies

| Package | Purpose |
|---------|---------|
| [pynput](https://github.com/moses-palmer/pynput) | Keyboard/mouse recording, playback, and global hotkeys |
| [pystray](https://github.com/moses-palmer/pystray) | System tray icon |
| [Pillow](https://python-pillow.org/) | Tray icon image rendering |
