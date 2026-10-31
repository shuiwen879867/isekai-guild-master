# -*- coding: utf-8 -*-
"""debug_e002.py — 檢視 multi card_action 結算前後。"""
import sys
sys.path.insert(0, 'rules')
from guild_engine import Engine

e = Engine([{'id': 0, 'name': 'A', 'hero': 'bai_white'},
            {'id': 1, 'name': 'B', 'hero': 'ruby_white'}], options={'solo': False})
e.state['phase'] = 'action';e.state['turn'] = 0
p = e.state['players'][0]
p['hand'] = [77];p['gold'] = 99
e.apply(0, dict(type='play', card=77, strength=0, pieces=[]))
e.state['turn'] = 0
print('after play: gold', p['gold'], 'left gold', e.state['players'][1]['gold'],
      'played', p['played'], 'civ state', e.state['civ'], 'stat', e._stat(p, 'civ'))
left_before = e.state['players'][1]['gold']
gold_before = p['gold']
e.apply(0, dict(type='card_action', card=77))
p0 = e.state['players'][0];p1 = e.state['players'][1]
print('after action: gold', p0['gold'], '(before %s)' % gold_before,
      'left gold', p1['gold'], '(before %s)' % left_before)
print('p0 played', p0['played'], 'p1 played', p1['played'])
print('pending', e.state.get('pending'))
for m in e.state['log'][-5:]:
    print('LOG', m.get('message'))
