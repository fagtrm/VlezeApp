#!/usr/bin/env python3
"""Конвертация PNG иконки во все нужные размеры для GTK4 приложения."""

from PIL import Image
import os

SRC = "/home/mrpower/Разработка/AppImgages/vlezeappico_fixed.png"
BASE = "/home/mrpower/Разработка/VlezeApp/data/icons/hicolor"
ICON_ID = "com.vlezeapp.app"

SIZES = [16, 32, 48, 64, 128, 256]


def main() -> None:
    img = Image.open(SRC)
    if img.mode != "RGBA":
        img = img.convert("RGBA")

    for size in SIZES:
        resized = img.resize((size, size), Image.LANCZOS)
        dir_path = os.path.join(BASE, f"{size}x{size}", "apps")
        os.makedirs(dir_path, exist_ok=True)
        path = os.path.join(dir_path, f"{ICON_ID}.png")
        resized.save(path, "PNG")
        print(f"Создан: {size}x{size}")

    # Scalable — версия 256x256
    scalable_dir = os.path.join(BASE, "scalable", "apps")
    os.makedirs(scalable_dir, exist_ok=True)
    scalable_path = os.path.join(scalable_dir, f"{ICON_ID}.png")
    img.resize((256, 256), Image.LANCZOS).save(scalable_path, "PNG")
    print("Создан: scalable (256x256)")

    print("\nГотово!")


if __name__ == "__main__":
    main()
