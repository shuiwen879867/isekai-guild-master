# -*- coding: utf-8 -*-
"""probe_cards3.py — 印出四張卡在 guild_content 定義段的完整原文（安裝前）。"""
import io
import re

BASE = r'D:\Users\Simon\Desktop\GuildMaster-Godot-Windows-20261015-A077Fix\GuildMaster-Godot'
s = io.open(BASE + r'\rules\guild_content.py', encoding='utf-8').read()
for number, name in ((65, '老旧投影机'), (83, '大贤者'), (53, '完美默契'), (77, '库姬')):
    pat = r'_card\(%d, %s' % (number, repr(name).replace("'", "'"))
    m = re.search(re.escape("_card(%d, '%s'" % (number, name)), s)
    if not m:
        i = s.find("_card(%d, " % number)
        if i == -1:
            print('NOT FOUND', number, name)
            continue
        start = s.rfind('\n', 0, i)
        print('=' * 25, number, name)
        print(s[i: i + 620].replace('\n', ' | '))
        continue
    start = s.rfind('\n', 0, m.start())
    print('=' * 25, number, name)
    print(s[m.start(): m.start() + 560].replace('\n', ' | '))
