"""Press any key to see what pynput reports. Ctrl+C to quit."""
from pynput import keyboard

def on_press(key):
    print(f"[PRESS]   {key!r}")
    if hasattr(key, "vk"):
        print(f"          vk   = {key.vk}")
    if hasattr(key, "char"):
        print(f"          char = {key.char!r}")
    if hasattr(key, "name"):
        print(f"          name = {key.name!r}")

def on_release(key):
    print(f"[RELEASE] {key!r}\n")

print("Listening — press your custom key (Ctrl+C to quit)...\n")
with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
    try:
        listener.join()
    except KeyboardInterrupt:
        pass
