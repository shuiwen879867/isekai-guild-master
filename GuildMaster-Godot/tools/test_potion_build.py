# -*- coding: utf-8 -*-
"""test_potion_build.py — 驗證秘藥「據點化」不會再被扣而無效果。

覆盖：
  A) 營地存在但全部付不起鄰接追加費 → 拒絕＋彈窗提示，秘藥未消耗（舊版會被扣掉卻無效果）
  B) 沒有任何自己的營地             → 拒絕＋提示，秘藥未消耗
  C) 條件正常                       → 必選一個可負擔營地完成據點化（不可略過）

注意：引擎每一次 apply 都會提交全新 state（deepcopy trial），必须每次都从
s.engine.state 重新取对象，不能引用旧字典。
"""
import sys

sys.path.insert(0, 'rules')
from guild_session import Session


def prepare(action_name):
    s = Session()
    s.local_lobby('QA-' + action_name)
    s.lobby('set_options', options={'solo': True})
    s.lobby('start')
    s.lobby('set_hero', character=s.room['hero_offers'][0], variant='white')
    s.engine.state['phase'] = 'action'
    s.toast = ''
    return s


def camp_of(s):
    for cell in s.engine.state['board']:
        if (cell['q'], cell['r']) == (0, -1):
            return cell
    raise KeyError('camp cell not found')


def build_base_ring(s, count):
    """把营地四周 count 个邻格设成已有据点（无主但有 base 标记 → 任何英雄都会被计追加费）。"""
    cell = camp_of(s)
    for n in s.engine._neighbors(cell)[:count]:
        n.update(owner=None, base=True, revealed=True, blocked=False)


# —— 场景 B：无任何营地 → 拒绝 ——
s = prepare('NoCamp')
for c in s.engine.state['board']:
    c['owner'] = None
p = s.engine.state['players'][0]
p['pot'] = 1
s.toast = ''
ok = s.action('potion', option='build')
p = s.engine.state['players'][0]
print('B) 无营地 ok=%s toast=%r' % (ok, s.toast))
assert not ok and '据点化' in s.toast
assert p['pot'] == 1 and s.engine.state['potions_used'] == [] and not s.game.get('pending')

# —— 场景 A：营地存在但追加费全部付不起 → 拒绝（旧版会白扣）——
s = prepare('Unaffordable')
p = s.engine.state['players'][0]
build_base_ring(s, 3)          # 三面邻接自有据点 → 追加费最高
cell = camp_of(s)
cell.update(owner=0, base=False, revealed=True, blocked=False)
p = s.engine.state['players'][0]
p['lab'] = None
p.update(gold=0, strength=0, pot=2)
s.toast = ''
ok = s.action('potion', option='build')
p = s.engine.state['players'][0]
print('A) 全部付不起 ok=%s toast=%r' % (ok, s.toast))
assert not ok and '追加费用' in s.toast, s.toast
assert p['pot'] == 2, '秘药不应被消耗'
assert s.engine.state['potions_used'] == [] and not s.game.get('pending')

# —— 场景 C：条件正常 → 必选据点化，完成、扣秘药、付追加费 ——
s = prepare('Normal')
p = s.engine.state['players'][0]
build_base_ring(s, 2)          # 两面邻接 → 追加费中等但付得起
cell = camp_of(s)
cell.update(owner=0, base=False, revealed=True, blocked=False)
p = s.engine.state['players'][0]
p.update(gold=40, strength=0, pot=4)
pot_before, gold_before = p['pot'], p['gold']
s.toast = ''
ok = s.action('potion', option='build')
pending = s.game.get('pending')
print('C) 使用秘药 ok=%s pending=%r' % (ok, pending['title'] if pending else None))
assert ok and pending and pending['title'] == '选择据点位置', pending
assert pending['options'] and pending.get('optional') is False, '据点化选择必须是必选'
p = s.engine.state['players'][0]
assert p['pot'] == pot_before - 2, '秘药费用 2 应已扣'
assert 'build' in s.engine.state['potions_used']
s.toast = ''
ok = s.action('choice', choice_id=pending['id'], selected=[0], action={})
cell = camp_of(s)
print('C) 选择据点 ok=%s base=%s 金币 %s→%s' % (ok, cell['base'], gold_before, s.engine.state['players'][0]['gold']))
assert ok and cell['base'] is True, '据点化应已完成'
p = s.engine.state['players'][0]
assert p['gold'] == gold_before - 10, '两面邻接的追加费应全额支付'
assert not s.game.get('pending')

print('PASS: 秘药据点化三个场景全部通过（拒绝即退回＋提示，正常使用正确结算）')
