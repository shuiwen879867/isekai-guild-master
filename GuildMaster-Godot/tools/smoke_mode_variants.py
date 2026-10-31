# -*- coding: utf-8 -*-
"""smoke_mode_variants.py — 驗證 B-017/D-002/E-001/E-007 在 solo/multi 兩模式的定義。"""
import sys
sys.path.insert(0, r'D:\Users\Simon\Desktop\GuildMaster-Godot-Windows-20261015-A077Fix\GuildMaster-Godot\rules')

from guild_content import CARDS
from guild_mode_variants import apply_mode_variants

arch_before = {cid: CARDS[cid].get('image_path') for cid in (102, 103, 104, 105, 106)}

IDS = {'B-017': 53, 'D-002': 65, 'E-001': 77, 'E-007': 83}
EXPECT = {
    ('B-017', 'multi'): (('steps', 1, 'extra_action'), 'triggers.gold=5'),
    ('B-017', 'solo'):  (('steps', 0), 'triggers.gold=3'),
    ('D-002', 'multi'): ('scoring.no_max',),
    ('E-001', 'multi'): ('pass_left',),
    ('E-001', 'solo'):  ('flip',),
    ('E-007', 'multi'): ('action.no_max',),
    ('E-007', 'solo'):  ('action.max5',),
}

def fail(msg):
    print('FAIL', msg)
    sys.exit(1)

for mode in ('multi', 'solo'):
    apply_mode_variants({'solo': mode == 'solo'})
    for code, cid in IDS.items():
        c = CARDS[cid]
        trig = c.get('triggers') or []
        act = c.get('action') or {}
        score = c.get('scoring') or []
        steps = c.get('steps') or []
        if code == 'B-017':
            g = trig[0]['effect']['gold'] if trig else None
            want_g = 5 if mode == 'multi' else 3
            if g != want_g:
                fail('B-017 %s trigger gold=%s want %s' % (mode, g, want_g))
            want_steps = 1 if mode == 'multi' else 0
            if len(steps) != want_steps:
                fail('B-017 %s steps=%s want %s' % (mode, len(steps), want_steps))
            if mode == 'multi' and steps and steps[0].get('op') != 'extra_action':
                fail('B-017 multi steps op')
        elif code == 'D-002':
            rule = score[0] if score else None
            if not rule or rule.get('stat') != 'played' or rule.get('per') != 3 or rule.get('point') != 1:
                fail('D-002 %s scoring base' % mode)
            has_max = 'max' in rule
            if has_max == (mode == 'multi'):
                fail('D-002 %s max presence wrong' % mode)
            if has_max and rule['max'] != 6:
                fail('D-002 solo max value')
        elif code == 'E-001':
            ops = [s.get('op') for s in act.get('steps', [])]
            want = 'pass_left' if mode == 'multi' else 'flip'
            if not ops or ops[0] != want:
                fail('E-001 %s steps op=%s want %s' % (mode, ops, want))
            if act.get('gold') != 5:
                fail('E-001 %s gold!=5' % mode)
        elif code == 'E-007':
            sc = act.get('scaled', [{}])[0] if act.get('scaled') else {}
            if sc.get('stat') != 'tag:scrap' or sc.get('multiplier') != 1:
                fail('E-007 %s scaled' % mode)
            maxed = 'max' in sc
            if maxed != (mode == 'solo'):
                fail('E-007 %s max presence wrong' % mode)
            if maxed and sc['max'] != 5:
                fail('E-007 solo max value')
            if act.get('costs', {}).get('pot') != 1:
                fail('E-007 %s pot cost' % mode)
        # 其他欄位保持原值
        if c.get('price') in (None,) :
            fail('%s price lost' % code)
        # 卡面欄位按模式切換
        multi_face = {'B-017': 'pack/6_6', 'D-002': 'pack/8_6', 'E-001': 'pack/7_1', 'E-007': 'pack/7_7'}[code]
        solo_face = {'B-017': 'pack/9B_2', 'D-002': 'pack/9B_3', 'E-001': 'pack/9B_4', 'E-007': 'pack/9B_1'}[code]
        want_face = solo_face if mode == 'solo' else multi_face
        if c.get('image_path') != want_face or c.get('source') != want_face:
            fail('%s %s face=%s want %s' % (code, mode, c.get('source'), want_face))
    print('%s OK' % mode)

for cid, before in arch_before.items():
    if CARDS[cid].get('image_path') != before:
        fail('archive %s face changed: %s -> %s' % (cid, before, CARDS[cid].get('image_path')))

print('MODE VARIANT SMOKE PASSED')
