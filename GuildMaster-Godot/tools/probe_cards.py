# -*- coding: utf-8 -*-
"""probe_cards.py — 檢視 guild_content.py 中四張模式差異卡的原始定義。"""
import io
import re
import sys

s = io.open(r'..\..\rules\guild_content.py' if False else None, encoding='utf-8').read() if False else io.open(r'D:\Users\Simon\Desktop\GuildMaster-Godot-Windows-20261015-A077Fix\GuildMaster-Godot\rules\guild_content.py', encoding='utf-8').read()
print('file len', len(s))
codes = ['B-017', 'D-002', 'E-001', 'E-007']
names = ['完美默契', '老舊的放映機', '老舊的放映机', '異界穿梭者', '大賢者']
for pat in names + codes:
    idxs = [m.start() for m in re.finditer(re.escape(pat), s)]
    print(repr(pat), idxs[:8])
# 印出這四個 id 附近的定義
for cid in (53, 65, 77, 83, 103, 104, 105, 106):
    m = re.search(r"^\s*%d:" % cid, s, re.M)
    if m:
        seg = s[m.start():m.start() + 520]
        print('=' * 20, 'id', cid)
        print(seg.replace('\n', ' | '))
