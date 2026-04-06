#!/usr/bin/env python3
"""Переименование иконок под application_id."""
import os
import shutil

BASE = "/home/mrpower/Разработка/VlezeApp/data/icons/hicolor"
LOCAL = os.path.expanduser("~/.local/share/icons/hicolor")
OLD = "com.github.fagtrm.VlezeApp.png"
NEW = "com.vlezeapp.app.png"

SIZES = ["16x16", "32x32", "48x48", "64x64", "128x128", "256x256", "scalable"]

for size in SIZES:
    for dest in [BASE, LOCAL]:
        src = os.path.join(dest, size, "apps", OLD)
        dst = os.path.join(dest, size, "apps", NEW)
        if os.path.exists(src):
            shutil.move(src, dst)
            print(f"Renamed: {size}/{os.path.basename(dst)}")

print("Done!")
