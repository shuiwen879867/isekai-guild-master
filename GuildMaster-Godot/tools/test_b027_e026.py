# -*- coding: utf-8 -*-
"""test_b027_e026.py - B-027 能量飲料 Bring Feather / E-026 劍聖阿茲姬 實戰驗證。

B-027（332）：費用 9G＋1秘藥；打出時 戰力產能+1、力量+1；獲得 生活標籤；名聲0；
              常時：結束階段（終局）行動用完時，獲得10G並再執行一次主要行動（多人＋單人）。
E-026（338）：費用 11G＋3金幣產能；前置 持有2板塊；打出時 戰力產能+2、執行探索
              （可探索深淵洞穴，按普通板塊計成本；BOSS除外）；獲得 人物標籤；名聲2。
注意：引擎 apply 每次提交新 state；測試每次都重新取物件。
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


c332 = CARDS[332]
check('B-027 price', c332['price'], 9)
check('B-027 costs', c332['costs'], {'pot': 1})
check('B-027 tags', c332['tags'], ['civ'])
check('B-027 str_pro', c332['str_pro'], 1)
check('B-027 strength', c332['strength'], 1)
check('B-027 draw', c332['draw'], 0)
check('B-027 point', c332['point'], 0)
check('B-027 final_bonus', c332.get('final_bonus'), {'gold': 10, 'action': 1})
c338 = CARDS[338]
check('E-026 price', c338['price'], 11)
check('E-026 costs', c338['costs'], {'gold_pro': 3})
check('E-026 pieces req', c338['requirements'].get('pieces'), 2)
check('E-026 tags', c338['tags'], ['character'])
check('E-026 str_pro', c338['str_pro'], 2)
check('E-026 point', c338['point'], 2)
check('E-026 step', c338['steps'], [{'op': 'explore', 'hole_claim': True}])

# ---------- E-026：打出 → 探索已公開的深淵洞穴並獲得 ----------
players = [{'id': 0, 'name': 'A', 'hero': 'bai_white'},
           {'id': 1, 'name': 'B', 'hero': 'ruby_white'}]
e = Engine(players, options={})
e.state['phase'] = 'action'
e.state['turn'] = 0
p0 = e.state['players'][0]
str_pro_before = p0['str_pro']
p0['hand'].append(338)
p0['gold'] = 30
p0['gold_pro'] = 5          # 支付 3 金幣產能成本
p0['tiles'] = ['tile8', 'tile9']
p0['strength'] = 0
# 自己先擁有起始格：把第一個無主格改成深淵洞穴，並把其任一鄰格劃給自己以滿足鄰接條件。
hole_cell = None
for cell in e.state['board']:
    if cell['owner'] is None and not cell.get('blocked', False) and not cell.get('boss', False):
        hole_cell = cell
        break
hole_cell.update(loot='tile14', revealed=True)   # tile14 = 深淵洞穴（ishole）
for neighbor in e._neighbors(hole_cell):
    # Keep the payment deterministic; random revealed high-star neighbors
    # could otherwise make the fixture unaffordable after paying for E-026.
    neighbor.update(loot='tile21',revealed=True,back_star=1)
for n in e._neighbors(hole_cell):
    if n['owner'] is None and not n.get('boss', False) and not n.get('blocked', False):
        n.update(owner=0, revealed=True)
        break
hole_id = hole_cell['id']

ok = e.apply(0, {'type': 'play', 'card': 338})
p0 = e.state['players'][0]
check('E-026 play ok', bool(ok), True)
check('E-026 paid 11 gold', p0['gold'], 19)
check('E-026 paid 3 gold_pro', p0['gold_pro'], 2)
check('E-026 str_pro +2', p0['str_pro'], str_pro_before + 2)
pending = e.state.get('pending')
check('E-026 explore pending', pending is not None and pending['player'] == 0, True)
options = e.view(0).get('pending', {}).get('options', [])
targets = [o['value'] for o in options]
check('E-026 hole in options', hole_id in targets, True)

gold_before_explore = p0['gold']
ok = e.apply(0, {'type': 'choice', 'choice_id': pending['id'], 'selected': [targets.index(hole_id)]})
p0 = e.state['players'][0]
check('E-026 target chosen ok', bool(ok), True)
pending2 = e.state.get('pending')
check('E-026 payment pending', pending2 is not None and pending2.get('mode') == 'payment', True)
# 探索支付：目標星數 0（視為普通板塊）＋鄰格格星數 3 → 15 金幣；選空支付即可。
ok = e.apply(0, {'type': 'choice', 'choice_id': pending2['id'], 'selected': []})
p0 = e.state['players'][0]
check('E-026 explore ok', bool(ok), True)
check('E-026 hole claimed (owner)', e._cell(hole_id)['owner'], 0)
check('E-026 no pending left', e.state.get('pending'), None)
check('E-026 gained hole tile', 'tile14' in [str(t) for t in p0['tiles']], True)
check('E-026 gold decreased', p0['gold'] < gold_before_explore, True)

# ---------- B-027：多人結束階段行動用完 → +10G ＋ 一次主要行動 ----------
e = Engine([{'id': 0, 'name': 'A', 'hero': 'bai_white'},
            {'id': 1, 'name': 'B', 'hero': 'ruby_white'}], options={})
e.state['phase'] = 'final'
e.state['turn'] = 0
e.state['final_remaining'] = [0, 0]
e.state['final_actions_taken'] = 2
e.state.pop('final_bonus_started', None)
p = e.state['players'][0]
p['played'] = [332]
p['card_states'] = [dict(uid=1, face_down=False, tiles=[], adventurers=0, counters=0)]
p['passed'] = False
gold_before = p['gold']
e.state['action_frame'] = dict(player=0, index=0, phase='final')
e._complete_action_frame()
p = e.state['players'][0]
check('B-027 bonus gold', p['gold'], gold_before + 10)
check('B-027 one more final action', e.state['final_remaining'][0], 1)
check('B-027 not finished', e.state['phase'], 'final')

# ---------- B-027：單人同樣觸發 ----------
se = Engine([{'id': 0, 'name': 'S', 'hero': 'bai_white'}], options={'solo': True})
se.state['round'] = se.rules['solo_rounds']
sp = se.state['players'][0]
sp['played'] = [332]
sp['card_states'] = [dict(uid=1, face_down=False, tiles=[], adventurers=0, counters=0)]
sp['passed'] = True
gold_before = sp['gold']
se._season()
sp = se.state['players'][0]
check('B-027 solo bonus gold', sp['gold'], gold_before + 10)
check('B-027 solo extra action', se.state.get('solo_final_action'), True)

if failures:
    print('B027/E026 TEST FAILED (%d)' % len(failures))
    sys.exit(1)
print('B027/E026 TEST PASSED')
