# -*- coding: utf-8 -*-
"""zoom_e001.py — 高解析放大 E-001 多人面（pack/7_1）效果文字。"""
from PIL import Image
import json

BASE = r'D:\Users\Simon\Desktop\GuildMaster-Godot-Windows-20261015-A077Fix'
cat = json.load(open(BASE + r'\GuildMaster-Godot-src\data\catalog.json', encoding='utf-8'))
spec = cat['atlas']['pack/7_1']
im = Image.open(BASE + r'\GuildMaster-Godot\art' + '\\' + spec['path'].replace('/', '\\'))
x, y, w, h = spec['box']
f = im.crop((x, y, x + w, y + h))
f.resize((int(w * 1.5), int(h * 1.5)), Image.LANCZOS).save(
    r'C:\Users\Simon\AppData\Local\Temp\opencode\zoom_E001_multi_full.png')
print('ok')
