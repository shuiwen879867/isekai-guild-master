# -*- coding: utf-8 -*-
"""probe_cards2.py — 從匯入鏈還原四張卡的「原始定義」與「補正後定義」。"""
import io
import re
import json

BASE = r'D:\Users\Simon\Desktop\GuildMaster-Godot-Windows-20261015-A077Fix\GuildMaster-Godot'
s = io.open(BASE + r'\rules\guild_content.py', encoding='utf-8').read()
# 找 _card( 呼叫的真實定義位置
for m in re.finditer(r'\b_card\(', s):
    seg = s[m.start():m.start() + 120].replace('\n', ' | ')
    print('%5d %s' % (m.start(), seg[:110]))
print('---- install callers ----')
for f in ('guild_content.py', 'guild_session.py', 'guild_engine.py', 'guild_modes.py'):
    ss = io.open(BASE + '\\rules\\' + f, encoding='utf-8').read()
    for m in re.finditer(r'install\(|card_corrections|card_layouts', ss):
        seg = ss[max(0, m.start()-60):m.end()+80].replace('\n', ' | ')
        print(f, '@%d' % m.start(), seg[:160])
