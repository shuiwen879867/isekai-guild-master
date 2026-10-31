# -*- coding: utf-8 -*-
"""probe_cards4.py — 找 id 53 / 77 定義與 46..63 區塊原文。"""
import io
import re

BASE = r'D:\Users\Simon\Desktop\GuildMaster-Godot-Windows-20261015-A077Fix\GuildMaster-Godot'
s = io.open(BASE + r'\rules\guild_content.py', encoding='utf-8').read()
for target in ('_card(53', '_card(77', '_card(103', '_card(104', '_card(105', '_card(106', '_card(46', '_card(48'):
    i = s.find(target)
    print('====', target, '->', i)
    if i != -1:
        print(s[i:i + 520].replace('\n', ' | '))
# 完美默契上下文
for pat in ('完美默契', '完美默契', '结婚', '結婚'):
    for m in re.finditer(re.escape(pat), s):
        seg = s[m.start()-250:m.start()+300].replace('\n', ' | ')
        print('---', pat, '@', m.start())
        print(seg[:560])
