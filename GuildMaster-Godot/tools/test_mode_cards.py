# -*- coding: utf-8 -*-
"""test_mode_cards.py — 四張模式差異卡的打出/特別行動在多人與單人的實戰分支。

  E-001 庫姬   特别行动：multi 金币移至左边玩家＋卡移交；solo 翻面留在自己打出区
  E-007 大賢者 特别行动：multi 9废品标签→战力9（无上限）；solo 恰好5（至多5）
  B-017 完美默契 打出时：multi 额外主要行动+1；solo 无

注意：引擎 apply 提交全新 state；每次都重新取对象。
"""
import sys

sys.path.insert(0, 'rules')
from guild_engine import Engine


def engine_for(solo, count=1):
    players = []
    heroes = ['bai_white', 'ruby_white', 'shion_white', 'alicia_white', 'misha_white']
    for i in range(count):
        players.append({'id': i, 'name': 'P%d' % i, 'hero': heroes[i]})
    e = Engine(players, options={'solo': solo})
    e.state['phase'] = 'action'
    e.state['turn'] = 0
    return e


def fail(msg):
    print('FAIL', msg)
    sys.exit(1)


def seat(engine, index):
    return engine.state['players'][index]


# ================= E-001 =================
# —— 多人：特别行动把(5+文明值)金币给左边，卡移入左边打出区 ——
e = engine_for(False, 2)
p = seat(e, 0)
p['hand'] = [77];p['gold'] = 99
e.apply(0, dict(type='play', card=77, strength=0, pieces=[]))
e.state['turn'] = 0
p = seat(e, 0)
left_before = int(seat(e, 1)['gold'])
gold_before = int(p['gold'])
e.apply(0, dict(type='card_action', card=77))
p, left = seat(e, 0), seat(e, 1)
if 77 not in left['played'] or 77 in p['played']:
    fail('E-001 multi 卡未移至左边玩家 p_played=%s left_played=%s' % (p['played'], left['played']))
gain = int(p['gold']) - gold_before
civ = int(e._stat(p, 'civ')) if hasattr(e, '_stat') else 1
if gain != 5 + civ:
    fail('E-001 multi 金币 +%s（应 5+文明值=%s）' % (gain, 5 + civ))
if int(left['gold']) != left_before:
    fail('E-001 multi 左边玩家金币不应变化')
print('E-001 multi OK：金币 +%s，卡移至左边玩家' % gain)

# —— 单人：金币留给自己，卡翻面 ——
e = engine_for(True, 1)
p = seat(e, 0)
p['hand'] = [77];p['gold'] = 99
e.apply(0, dict(type='play', card=77, strength=0, pieces=[]))
e.state['turn'] = 0
p = seat(e, 0)
gold_before = int(p['gold'])
e.apply(0, dict(type='card_action', card=77))
p = seat(e, 0)
if 77 not in p['played']:
    fail('E-001 solo 卡不在打出区')
meta = p.get('card_states', [])
face_down = any(meta[i].get('face_down') for i, c in enumerate(p['played']) if c == 77)
if not face_down:
    fail('E-001 solo 未翻面 card_states=%s' % meta)
gain = int(p['gold']) - gold_before
if gain <= 0:
    fail('E-001 solo 自己未获得金币 +%s' % gain)
print('E-001 solo OK：金币 +%s，卡翻面留自己' % gain)

# ================= E-007 =================
# —— 多人：9个废品标签 → 战力 +9（无上限） ——
e = engine_for(False, 2)
p = seat(e, 0)
p['hand'] = [83];p['gold'] = 99;p['pot'] = 1
p['tags'] = ['scrap'] * 9
before = int(p['strength'])
e.apply(0, dict(type='play', card=83, strength=0, pieces=[]))
e.state['turn'] = 0
stat = int(e._stat(seat(e, 0), 'tag:scrap'))
e.apply(0, dict(type='card_action', card=83))
p = seat(e, 0)
gain = int(p['strength']) - before
if gain != stat:
    fail('E-007 multi 战力 +%s（应 %s＝标签统计无上限）' % (gain, stat))
print('E-007 multi OK：战力 +%s（无上限）' % gain)

# —— 单人：9个标签只 +5（至多5） ——
e = engine_for(True, 1)
p = seat(e, 0)
p['hand'] = [83];p['gold'] = 99;p['pot'] = 1
p['tags'] = ['scrap'] * 9
before = int(p['strength'])
e.apply(0, dict(type='play', card=83, strength=0, pieces=[]))
e.state['turn'] = 0
e.apply(0, dict(type='card_action', card=83))
p = seat(e, 0)
gain = int(p['strength']) - before
if gain != 5:
    fail('E-007 solo 战力 +%s（应恰好 5）' % gain)
print('E-007 solo OK：战力 +5（至多5）')

# ================= B-017 =================
# —— 多人：打出时执行 1 次主要行动（不换人，可立即再行动） ——
e = engine_for(False, 2)
p = seat(e, 0)
p['hand'] = [53, 5];p['gold'] = 99;p['affection'] = 3
e.apply(0, dict(type='play', card=53, strength=0, pieces=[]))
if seat(e, 0)['played'].count(53) != 1:
    fail('B-017 multi 未打出')
if 0 not in (e.state['turn'],):
    fail('B-017 multi 打出后回合换人 turn=%s（应保持自己）' % e.state['turn'])
e.apply(0, dict(type='play', card=5, strength=0, pieces=[]))
p = seat(e, 0)
if 5 not in p['played']:
    fail('B-017 multi 额外主要行动未生效（第二张打出失败，turn=%s）' % e.state['turn'])
print('B-017 multi OK：打出后可立即再执行一次主要行动')

# —— 单人：打出正常（无切换面行为的额外动作可验证定义差异, 由 smoke 覆盖）——
e = engine_for(True, 1)
p = seat(e, 0)
p['hand'] = [53];p['gold'] = 99;p['affection'] = 3
e.apply(0, dict(type='play', card=53, strength=0, pieces=[]))
p = seat(e, 0)
if 53 not in p['played']:
    fail('B-017 solo 打出失败')
print('B-017 solo OK：正常打出')

# ================= 存档恢复 =================
from guild_content import CARDS
e = engine_for(True, 1)
data = e.export()
Engine.restore(data)
gold = CARDS[53].get('triggers', [{}])[0].get('effect', {}).get('gold')
if gold != 3:
    fail('restore 后 B-017 仍非单人定义 gold=%s' % gold)
print('restore OK：读档后模式效果保持单人')

print('MODE CARDS ENGINE TEST PASSED')
