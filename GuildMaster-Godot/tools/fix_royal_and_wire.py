# -*- coding: utf-8 -*-
"""fix_royal_and_wire.py — R-001/R-006/R-022 條件修正 + 王權卡面接線（成就卡.png）。"""
import io
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(os.path.dirname(ROOT), 'GuildMaster-Godot-src')
PACK = os.path.join(os.path.dirname(ROOT), '圖包')
ART = os.path.join(ROOT, 'art')
RULES = os.path.join(ROOT, 'rules')

# 成就卡.png：5 欄 × 6 列（列距 680、卡片 483×660）
COLS, ROWS = 5, 6
PITCH_Y, CARD_H = 680, 660
CELL_TO_ROYAL = {
    1: 'R-022', 2: 'R-001', 3: 'R-002', 4: 'R-003', 5: 'R-004',
    6: 'R-005', 7: 'R-006', 8: 'R-007', 9: 'R-008', 10: 'R-009',
    11: 'R-010', 12: 'R-011', 13: 'R-012', 14: 'R-013', 15: 'R-014',
    16: 'R-017', 17: 'R-018', 18: 'R-019', 19: 'R-020', 20: 'R-021',
    21: 'R-015', 22: 'R-016',
}

CONDITION_FIXES = {
    # R-001：零件/生活/商業任選一種 5（原本 requirements 是空的）
    'royal133': {'requirements': {'any': [{'tags': {'civ': 5}}, {'tags': {'gold': 5}}, {'tags': {'scrap': 5}}]}},
    # R-006：已打出 12 張事件卡（原本 cards:1，語意相同但數值錯）
    'royal138': {'requirements': {'played': 12}},
    # R-022：好感 5 + 1 張以上成就卡（原本只有 heart 5）
    'royal154': {'requirements': {'heart': 5, 'stat': 'earned_achievements', 'value': 1}},
}


def convert():
    from PIL import Image
    src = os.path.join(PACK, '成就卡.png')
    dst = os.path.join(ART, 'images', 'tts', 'packroyal.webp')
    if os.path.isfile(dst):
        print('royal webp exists'); return
    im = Image.open(src).convert('RGB')
    im.save(dst, 'WEBP', quality=92, method=4)
    print('converted packroyal.webp', im.size, '%.1fMB' % (os.path.getsize(dst) / 1048576))


def wire_faces():
    from PIL import Image
    cp = os.path.join(SRC, 'data', 'catalog.json')
    cat = json.load(io.open(cp, encoding='utf-8'))
    sheet = Image.open(os.path.join(PACK, '成就卡.png'))
    W, _H = sheet.size
    cw = W / COLS
    atlas = cat['atlas']
    ach = cat['achievements']
    for cell, code in CELL_TO_ROYAL.items():
        idx = cell - 1
        row, col = divmod(idx, COLS)
        x0 = int(round(col * cw))
        y0 = int(round(row * PITCH_Y))
        key = 'royal/%s' % code
        atlas[key] = {'path': 'images/tts/packroyal.webp',
                      'box': [x0, y0, int(round(cw)), CARD_H]}
        # 找對應的成就（printed_code = R-0xx）
        for k, v in ach.items():
            if v.get('printed_code') == code:
                v['image_path'] = key
                v['source'] = key
                break
    json.dump(cat, io.open(cp, 'w', encoding='utf-8', newline=''), ensure_ascii=False, separators=(',', ':'))
    print('atlas royal keys:', sum(1 for k in atlas if k.startswith('royal/')))


def fix_conditions():
    # 1) 引擎 _stat 支援 earned_achievements
    ep = os.path.join(RULES, 'guild_engine.py')
    s = io.open(ep, encoding='utf-8').read()
    if "stat == 'earned_achievements'" not in s:
        anchor = '        if stat == "heart":\n            return player["affection"]\n'
        add = anchor + '        if stat == "earned_achievements":\n            return len(player["earned_achievements"])\n'
        assert s.count(anchor) == 1
        s = s.replace(anchor, add)
        io.open(ep, 'w', encoding='utf-8', newline='').write(s)
        print('engine: _stat earned_achievements added')
    # 2) 條件修正：catalog + rules（corrections）
    cp = os.path.join(SRC, 'data', 'catalog.json')
    cat = json.load(io.open(cp, encoding='utf-8'))
    for key, upd in CONDITION_FIXES.items():
        if key in cat['achievements']:
            cat['achievements'][key].update(upd)
    json.dump(cat, io.open(cp, 'w', encoding='utf-8', newline=''), ensure_ascii=False, separators=(',', ':'))
    ccp = os.path.join(RULES, 'guild_card_corrections.py')
    sc = io.open(ccp, encoding='utf-8').read()
    if 'ROYAL_FIX' not in sc:
        block = ("    # 王權條件修正（2026-10 成就卡校對）\n"
                 "    ROYAL_FIX = %r\n"
                 "    for _key, _upd in ROYAL_FIX.items():\n"
                 "        if _key in royals:\n"
                 "            royals[_key].update(_upd)\n" % CONDITION_FIXES)
        anchor2 = '# Manually checked titles and verbatim excerpts'
        i2 = sc.find(anchor2)
        sc = sc[:i2] + block + '\n\n' + sc[i2:]
        io.open(ccp, 'w', encoding='utf-8', newline='').write(sc)
        print('rules: ROYAL_FIX added')
    print('conditions fixed:', list(CONDITION_FIXES))


if __name__ == '__main__':
    convert()
    wire_faces()
    fix_conditions()
    import sys
    sys.path.insert(0, RULES)
    import guild_content
    A = guild_content.ACHIEVEMENTS
    for k in ('royal133', 'royal138', 'royal154'):
        print(k, json.dumps(A[k].get('requirements'), ensure_ascii=False))
    cat = json.load(io.open(os.path.join(SRC, 'data', 'catalog.json'), encoding='utf-8'))
    print('royal wired:', sum(1 for v in cat['achievements'].values() if str(v.get('image_path', '')).startswith('royal/')))
