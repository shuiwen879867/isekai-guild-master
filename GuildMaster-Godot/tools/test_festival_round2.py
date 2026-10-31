# -*- coding: utf-8 -*-
"""test_festival_round2.py - 第二輪卡面校正驗證（A-121/123/127/128、B-026、B-028、D-016）。

  A-128（330）迷宮時鐘：費用2+1板塊、前置4板塊、金產+3文明+1；branch：
      ①額外行動（選探索必要成本-10）②Pass：+10G 且本季無法再行動
  B-028（333）積分卡：打出價格個位數 0/5 的事件 → 立即 +2G
  D-016（336）：前置 35「金幣產量」或 2 板塊（非持有金幣）
  A-127（329）：無名聲；A-121（323）可戰力抵減；A-123（325）scaled=每零件標籤+3G
"""
import sys

sys.path.insert(0, 'rules')
from guild_content import CARDS
from guild_engine import Engine

failures = []


def check(label, actual, expected):
    if actual != expected:
        failures.append('%s: got %r, want %r' % (label, actual, expected))
        print('FAIL', label, actual, '!=', expected)
    else:
        print('OK  ', label, '=', actual)


def fresh(players=None, options=None):
    players = players or [{'id': 0, 'name': 'A', 'hero': 'bai_white'},
                          {'id': 1, 'name': 'B', 'hero': 'ruby_white'}]
    e = Engine(players, options=options or {})
    e.state['phase'] = 'action'
    e.state['turn'] = 0
    return e


def defs():
    c323, c325, c329, c330, c331, c336 = (CARDS[i] for i in (323, 325, 329, 330, 331, 336))
    check('A-121 can_trans', bool(c323.get('can_trans')), True)
    check('A-121 price', c323['price'], 15)
    check('A-123 scaled', c325.get('scaled'), [{'resource': 'gold', 'stat': 'tag:scrap', 'multiplier': 3}])
    check('A-127 point', c329.get('point'), 0)
    check('A-127 req any', len(c329.get('requirements', {}).get('any', [])), 2)
    check('A-127 steps', c329.get('steps'), [{'op': 'pen_reveal_use'}])
    check('A-128 price', c330['price'], 2)
    check('A-128 consume_piece', c330.get('consume_piece'), 1)
    check('A-128 pieces req', c330.get('requirements', {}).get('pieces'), 4)
    check('A-128 gold_pro', c330.get('gold_pro'), 3)
    check('A-128 civ', c330.get('civ'), 1)
    check('A-128 tags', c330.get('tags'), ['scrap'])
    check('A-128 point', c330.get('point'), 2)
    branch = c330.get('steps', [])
    check('A-128 branch shape', len(branch) == 1 and branch[0].get('op') == 'branch'
          and len(branch[0].get('options', [])) == 2, True)
    if branch and branch[0].get('op') == 'branch':
        opts = branch[0]['options']
        check('A-128 optA', opts[0]['effect'].get('steps'),
              [{'op': 'extra_action', 'explore_discount': 10}])
        check('A-128 optB', (opts[1]['effect'].get('gold'), opts[1]['effect'].get('steps')),
              (10, [{'op': 'pass_out'}]))
    check('B-026 tags', c331.get('tags'), [])
    check('B-026 discount', c331.get('build_surcharge_discount'), 5)
    check('D-016 req gold_pro', c336.get('requirements', {}).get('any'),
          [{'gold_pro': 35}, {'pieces': 2}])


# ---------- A-128 分支①：額外行動 + 探索成本-10 ----------
e = fresh()
p0 = e.state['players'][0]
p0['hand'].append(330)
p0['gold'] = 30
p0['tiles'] = ['tile8', 'tile9', 'tile1', 'tile3']
ok = e.apply(0, {'type': 'play', 'card': 330})
p0 = e.state['players'][0]
check('A-128 play', bool(ok), True)
check('A-128 paid price+1 tile', p0['gold'], 28)
check('A-128 tile consumed', len(p0['tiles']), 3)
check('A-128 gold_pro+3', p0['gold_pro'] >= 3, True)
pending = e.state.get('pending')
check('A-128 branch pending', pending is not None and len(pending['options']) == 2, True)

ok = e.apply(0, {'type': 'choice', 'choice_id': pending['id'], 'selected': [0]})
p0 = e.state['players'][0]
check('A-128 optA ok', bool(ok), True)
# 額外行動在 frame 完成時立即消耗（授予下一次行動機會），之後的探索成功即證明其生效
check('A-128 extra action consumed', p0['extra_actions'], 0)
check('A-128 explore discount flag', p0.get('next_explore_discount'), 10)

# 佈置探索目標：無主格 + 一個自己鄰格（合法）+ 兩個星3無主鄰格（抬高成本）
target = None
for cell in e.state['board']:
    if cell['owner'] is None and not cell.get('boss', False) and not cell.get('blocked', False):
        target = cell
        break
target.update(loot='tile21', revealed=True)          # 星0
adjacency_done = False
for n in e._neighbors(target):
    if n['owner'] is None and not n.get('boss', False) and not n.get('blocked', False):
        if not adjacency_done:
            n.update(owner=0, revealed=True)          # 相鄰合法
            adjacency_done = True
        else:
            n.update(owner=None, revealed=True, loot='tile7', star=3)  # 星3×N
hn = sum(e._visible_stars(n) for n in e._neighbors(target) if n['owner'] is None)
hole_id = target['id']

ok = e.apply(0, {'type': 'explore', 'tile': hole_id})
view = e.view(0)
pay = view['pending']['payment']
check('A-128 explore pending', view['pending']['player'] == 0, True)
check('A-128 discount in payment', pay['discount'], 10)
check('A-128 gold_base reduced', pay['gold_base'], max(10, 5 * (0 + hn) - 10))
pending2 = e.state.get('pending')
ok = e.apply(0, {'type': 'choice', 'choice_id': pending2['id'], 'selected': []})
p0 = e.state['players'][0]
check('A-128 explored', e._cell(hole_id)['owner'], 0)
check('A-128 gold spent discounted', p0['gold'], 28 - pay['gold_base'])
check('A-128 flag consumed', p0.get('next_explore_discount', 0), 0)

# ---------- A-128 分支②：Pass 得 10G 且本季無法再行動 ----------
e = fresh()
p0 = e.state['players'][0]
p0['hand'].append(330)
p0['gold'] = 10
p0['tiles'] = ['tile8', 'tile9', 'tile1', 'tile3']
ok = e.apply(0, {'type': 'play', 'card': 330})
pending = e.state.get('pending')
ok = e.apply(0, {'type': 'choice', 'choice_id': pending['id'], 'selected': [1]})
p0 = e.state['players'][0]
check('A-128 optB ok', bool(ok), True)
check('A-128 pass gold', p0['gold'], 10 - 2 + 10)
check('A-128 passed out', p0['passed'], True)
check('A-128 no extra actions', p0['extra_actions'], 0)

# ---------- B-028 積分卡：個位數 0/5 → +2G ----------
e = fresh()
p0 = e.state['players'][0]
p0['played'] = [333]
p0['card_states'] = [dict(uid=1, face_down=False, tiles=[], adventurers=0, counters=0)]
p0['hand'].extend([323, 336])           # 323 價格15（觸發）、336 價格14（不觸發）
p0['gold'] = 50
p0['tiles'] = ['tile8', 'tile9', 'tile10']
ok = e.apply(0, {'type': 'play', 'card': 323})
p0 = e.state['players'][0]
# 323 打出時「所有玩家獲得5金幣」也生效：50-15+2(個位數5)+5(全體) = 42
check('B-028 price15 +2G (incl. own all-gain)', p0['gold'], 42)
e.state['turn'] = 0
ok = e.apply(0, {'type': 'play', 'card': 336})
p0 = e.state['players'][0]
check('B-028 price14 no gain', p0['gold'], 42 - 14)

# ---------- D-016 前置：35 金幣產量 或 2 板塊 ----------
e = fresh()
p0 = e.state['players'][0]
p0['hand'].append(336)
p0['gold_pro'] = 40                     # 產量 40 ≥ 35 → 可打出
p0['gold'] = 30
p0['tiles'] = ['tile8', 'tile9']
ok = e.apply(0, {'type': 'play', 'card': 336})
check('D-016 gold_pro 40 playable', bool(ok), True)

e = fresh()
p0 = e.state['players'][0]
p0['hand'].append(336)
p0['gold'] = 40                          # 持有 40 金幣但產量 10、板塊只有 1 → 不可打出
p0['gold_pro'] = 10
p0['tiles'] = ['tile8']
try:
    e.apply(0, {'type': 'play', 'card': 336})
    check('D-016 holdings-only rejected', False, True)
except ValueError:
    check('D-016 holdings-only rejected', True, True)

if failures:
    print('ROUND2 TEST FAILED (%d)' % len(failures))
    sys.exit(1)
print('ROUND2 TEST PASSED')
