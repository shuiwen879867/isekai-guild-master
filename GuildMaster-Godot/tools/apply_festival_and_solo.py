# -*- coding: utf-8 -*-
"""apply_festival_and_solo.py — Phase B 第二波

1. 216/217：改用單人模式王權掃描（JP 原版 2768×1940），重算 atlas、移除原生版面
2. 185/187：atlas() 容錯 + 移除 manifest/atlas 死資料（英雄已全走 new_art）
3. 卡牌-15 → images/tts/pack15.webp；tts_128_* 重新指向 pack15
   ＋ 5 張缺卡（A-127 惡魔羽毛筆、A-128 迷宮時鐘、B-027 能量飲料、D-014 巨大建築物百貨、E-026 劍聖阿茲姬）
   ＋ 全慶典卡印碼（A-118~A-128、B-026~B-028、D-014~D-016、E-025/E-026）
"""
import io
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(os.path.dirname(ROOT), 'GuildMaster-Godot-src')
PACK = os.path.join(os.path.dirname(ROOT), '圖包')
ART = os.path.join(ROOT, 'art')
RULES = os.path.join(ROOT, 'rules')

SOLO_SIZES = {'216': (2768, 1940), '217': (2768, 1940)}
K15 = '卡牌-15(冒險者的慶典擴充).jpg'
K15_COLS, K15_ROWS = 7, 3

CODE_BY_NAME = {
    '勇敢行者': 'A-118', '與運輸公會的合作': 'A-119', '巨獸貝希摩斯的覺醒': 'A-120',
    '討伐礦石獸': 'A-121', '侵占救援物資': 'A-122', '方舟遺跡': 'A-123', '意外邂逅': 'A-124',
    '魔獸的生態調查': 'A-125', '開發魔法爐': 'A-126', '惡魔羽毛筆': 'A-127', '迷宮時鐘': 'A-128',
    '加蕾特建築公司': 'B-026', '能量飲料 Bring Feather': 'B-027', '積分卡': 'B-028',
    '巨大建築物百貨': 'D-014', '精靈的居住園地': 'D-015', '魔力工業聯合體': 'D-016',
    '情報販子琪修': 'E-025', '劍聖阿茲姬': 'E-026',
}
NEW_CARDS = [
    dict(id=329, name='惡魔羽毛筆', code='A-127', price=9, point=2, steps=[],
         ui='費用9金幣；揭示事件牌庫頂2張，選1張使用其「打出時效果」，之後丟棄所有揭示的卡；2名聲（特殊效果未實作）'),
    dict(id=330, name='迷宮時鐘', code='A-128', price=2, point=2,
         steps=[{'op': 'extra_action'}],
         ui='費用2金幣；執行一個額外行動；選探索則必要成本-10，選Pass則獲得10金幣並翻面；2名聲（折扣/Pass分支未實作）'),
    dict(id=332, name='能量飲料 Bring Feather', code='B-027', price=9, point=1, draw=1, steps=[],
         ui='費用9金幣；永久：結束階段結束時獲得10金幣並額外行動（單人：遊戲結束前）；打出時抽1；1名聲（永久效果未實作）'),
    dict(id=334, name='巨大建築物百貨', code='D-014', price=25, gold=7, draw=1, civ=1, point=0,
         scoring=[{'stat': 'holes', 'per': 1, 'point': 2}], steps=[],
         ui='費用25金幣；+7金幣、抽1、文明+1；終局每持有1張深淵洞穴板塊獲得聲望（以每張2點近似）；0+名聲'),
    dict(id=338, name='劍聖阿茲姬', code='E-026', price=11, point=2,
         steps=[{'op': 'explore', 'optional': True}],
         ui='費用11金幣；執行「探索」；探索成本視目標為普通板塊（可探深淵洞穴）；2名聲（成本規則簡化）'),
]


def convert(src_name, dst_name):
    from PIL import Image
    src = os.path.join(PACK, src_name)
    dst = os.path.join(ART, 'images', 'tts', dst_name)
    if os.path.isfile(dst):
        print('exists:', dst_name)
        return
    im = Image.open(src).convert('RGB')
    im.save(dst, 'WEBP', quality=92, method=4)
    print('converted:', dst_name, im.size, '%.1fMB' % (os.path.getsize(dst) / 1048576))


def wire_solo():
    from PIL import Image
    convert('單人模式王權專用版一般難度.jpg', '216.webp')
    convert('單人模式王權專用版困難難度.jpg', '217.webp')
    cp = os.path.join(SRC, 'data', 'catalog.json')
    cat = json.load(io.open(cp, encoding='utf-8'))
    atlas = cat['atlas']
    for num, (w, h) in SOLO_SIZES.items():
        for i in range(6):
            col, row = i % 3, i // 3
            atlas['tts_%s_%d' % (num, i)] = {
                'path': 'images/tts/%s.webp' % num,
                'box': [int(w * (.054 + col * .244)), int(h * (.06 + row * .456)),
                        int(w * .214), int(h * .422)]}
    json.dump(cat, io.open(cp, 'w', encoding='utf-8', newline=''), ensure_ascii=False, separators=(',', ':'))
    # 移除原生版面（改用掃描面）
    lp = os.path.join(SRC, 'data', 'card_layouts.json')
    lay = json.load(io.open(lp, encoding='utf-8'))
    removed = 0
    for k in [k for k in lay if k.startswith(('tts_216_', 'tts_217_'))]:
        lay.pop(k); removed += 1
    json.dump(lay, io.open(lp, 'w', encoding='utf-8', newline=''), ensure_ascii=False, indent=1)
    print('solo: atlas updated, layouts removed:', removed)


def clean_185_187():
    # atlas() 容錯
    p = os.path.join(RULES, 'guild_new_content.py')
    s = io.open(p, encoding='utf-8').read()
    old = ("def atlas(number,index,cols,rows,box=None):\n"
           "    name='tts_%s_%s'%(number,index)\n"
           "    w,h=ASSETS[str(number)]['size']\n")
    new = ("def atlas(number,index,cols,rows,box=None):\n"
           "    name='tts_%s_%s'%(number,index)\n"
           "    entry=ASSETS.get(str(number))\n"
           "    if entry is None:\n"
           "        return name\n"
           "    w,h=entry['size']\n")
    if old in s:
        s = s.replace(old, new)
        io.open(p, 'w', encoding='utf-8', newline='').write(s)
        print('rules: atlas() tolerant')
    else:
        print('rules atlas(): pattern not found (already patched?)')
    # manifest 移除
    mp = os.path.join(RULES, 'guild_asset_manifest.json')
    man = json.load(io.open(mp, encoding='utf-8'))
    gone = [k for k in ('185', '187') if k in man]
    for k in gone:
        man.pop(k)
    json.dump(man, io.open(mp, 'w', encoding='utf-8', newline=''), ensure_ascii=False, indent=4)
    # atlas 鍵移除
    cp = os.path.join(SRC, 'data', 'catalog.json')
    cat = json.load(io.open(cp, encoding='utf-8'))
    dead = [k for k in cat['atlas'] if k.startswith(('tts_185_', 'tts_187_'))]
    for k in dead:
        cat['atlas'].pop(k)
    json.dump(cat, io.open(cp, 'w', encoding='utf-8', newline=''), ensure_ascii=False, separators=(',', ':'))
    print('185/187 cleaned: manifest', gone, '| atlas keys -%d' % len(dead))


def wire_festival():
    from PIL import Image
    convert(K15, 'pack15.webp')
    im_size = Image.open(os.path.join(PACK, K15)).size
    w, h = im_size
    cp = os.path.join(SRC, 'data', 'catalog.json')
    cat = json.load(io.open(cp, encoding='utf-8'))
    atlas = cat['atlas']
    for i in range(K15_COLS * K15_ROWS):
        col, row = i % K15_COLS, i // K15_COLS
        atlas['tts_128_%d' % i] = {
            'path': 'images/tts/pack15.webp',
            'box': [int(w * col / K15_COLS), int(h * row / K15_ROWS),
                    int(w * (col + 1) / K15_COLS) - int(w * col / K15_COLS),
                    int(h * (row + 1) / K15_ROWS) - int(h * row / K15_ROWS)]}
    # 印碼
    for c in cat['cards'].values():
        nm = c.get('name') or ''
        if nm in CODE_BY_NAME:
            c['printed_code'] = CODE_BY_NAME[nm]
            c['expansion'] = 'festival_events'
    # 新卡
    template = cat['cards']['320']
    by_name = {c.get('name'): cid for cid, c in cat['cards'].items()}
    for spec in NEW_CARDS:
        if spec['id'] in [int(k) for k in cat['cards']]:
            print('exists card', spec['id']); continue
        c = dict(template)
        c.update(id=spec['id'], name=spec['name'], price=spec['price'], kind='event',
                 image=spec['id'], image_path='tts_128_%d' % (spec['id'] - 320),
                 source='tts_128_%d' % (spec['id'] - 320),
                 printed_code=spec['code'], expansion='festival_events',
                 available=True, verified=True, printed_text='', subtitle='',
                 ui_summary=spec['ui'], steps=spec.get('steps', []))
        for f in ('gold', 'strength', 'pot', 'gold_pro', 'str_pro', 'pot_pro', 'civ', 'point', 'draw'):
            c[f] = spec.get(f, 0)
        c['scoring'] = spec.get('scoring', [])
        c['requirements'] = {'tags': {}, 'heart': 0, 'pieces': 0, 'civ': 0, 'bases': 0, 'cards': 0}
        cat['cards'][str(spec['id'])] = c
        print('added card', spec['id'], spec['name'], spec['code'])
    json.dump(cat, io.open(cp, 'w', encoding='utf-8', newline=''), ensure_ascii=False, separators=(',', ':'))
    # 規則端：E() 新卡
    ep = os.path.join(RULES, 'guild_new_events.py')
    s = io.open(ep, encoding='utf-8').read()
    if 'E(9,' not in s:
        add = "\n    E(9,'恶魔羽毛笔',9,point=2,steps=[])\n" \
              "    E(10,'迷宫时钟',2,point=2,steps=[dict(op='extra_action')])\n" \
              "    E(12,'能量饮料 Bring Feather',9,point=1,draw=1,steps=[])\n" \
              "    E(14,'巨大建筑物百货',25,gold=7,draw=1,civ=1,point=0,scoring=[dict(stat='holes',per=1,point=2)])\n" \
              "    E(18,'剑圣阿兹姬',11,point=2,steps=[dict(op='explore',optional=True)])\n"
        # 插在 install 結尾（下一個頂層 def 或檔尾）
        idx = s.find('\ndef ')
        # 找 install 函式區塊結束：最後一個 E(17...) 之後
        i17 = s.find("E(17,")
        if i17 != -1:
            j = s.find('\n', s.find("E(17,", i17) + len("E(17,"))
            # 安全做法：在檔尾附加（install 內縮排 4）
            s = s + '\n' + add
        io.open(ep, 'w', encoding='utf-8', newline='').write(s)
        print('rules: E() new festival cards appended')
    else:
        print('rules E(): already has E(9..')
    # 規則端印碼
    ccp = os.path.join(RULES, 'guild_card_corrections.py')
    sc = io.open(ccp, encoding='utf-8').read()
    if '慶典擴充' not in sc:
        block = ("    # 慶典擴充事件卡印碼（2026-10）\n"
                 "    _fest_codes = %r\n"
                 "    for _card in cards.values():\n"
                 "        _code = _fest_codes.get(_card.get('name'))\n"
                 "        if _code:\n"
                 "            _card['printed_code'] = _code\n"
                 "            _card['expansion'] = 'festival_events'\n" % CODE_BY_NAME)
        anchor = '# Manually checked titles and verbatim excerpts'
        idx2 = sc.find(anchor)
        assert idx2 != -1
        sc = sc[:idx2] + block + '\n\n' + sc[idx2:]
        io.open(ccp, 'w', encoding='utf-8', newline='').write(sc)
        print('rules: festival codes appended')


if __name__ == '__main__':
    wire_solo()
    clean_185_187()
    wire_festival()
    import sys
    sys.path.insert(0, RULES)
    import guild_content
    C = guild_content.CARDS
    print('engine OK. festival cards:', sum(1 for c in C.values() if c.get('expansion') == 'festival_events'))
    for cid in (320, 329, 330, 332, 334, 338):
        c = C.get(cid)
        print(' #%s %s code=%s price=%s point=%s' % (cid, (c or {}).get('name'), (c or {}).get('printed_code'), (c or {}).get('price'), (c or {}).get('point')))
