import sys
sys.path.insert(0, ".")
from PIL import Image
from tray import _make_icon_image

img = _make_icon_image()
sizes = [(s, s) for s in (16, 32, 48, 64, 128, 256)]
images = [img.resize(s, Image.LANCZOS) for s in sizes]
images[0].save("icon.ico", format="ICO", sizes=sizes, append_images=images[1:])
print("icon.ico written.")
