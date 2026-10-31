# -*- coding: utf-8 -*-
"""crop_d002.py — 高解析放大 D-002 / B-017 兩面的效果文字區。"""
from PIL import Image
import json

BASE = r'D:\Users\Simon\Desktop\GuildMaster-Godot-Windows-20261015-A077Fix'
cat = json.load(open(BASE + r'\GuildMaster-Godot-src\data\catalog.json', encoding='utf-8'))
atlas = cat['atlas']

def face(key):
    spec = atlas[key]
    im = Image.open(BASE + r'\GuildMaster-Godot\art' + '\\' + spec['path'].replace('/', '\\'))
    x, y, w, h = spec['box']
    return im.crop((x, y, x + w, y + h))

for code, base_key, solo_key in (('D002', 'pack/8_6', 'pack/9B_3'), ('B017', 'pack/6_6', 'pack/9B_2')):
    f = face(base_key)
    W, H = f.size
    mid = f.crop((0, int(H * 0.30), W, int(H * 0.72))).resize((int(W * 1.6), int(H * 0.42 * 1.6)), Image.LANCZOS)
    mid.save(r'C:\Users\Simon\AppData\Local\Temp\opencode\zoom_%s_multi.png' % code)
    f2 = face(solo_key)
    mid2 = f2.crop((0, int(H * 0.30), W, int(H * 0.72))).resize((int(W * 1.6), int(H * 0.42 * 1.6)), Image.LANCZOS)
    mid2.save(r'C:\Users\Simon\AppData\Local\Temp\opencode\zoom_%s_solo.png' % code)
print('done')
