# -*- coding: utf-8 -*-
"""debug_b017.py — 檢視 multi 打出 B-017 的效果佇列與額外行動。"""
import sys
sys.path.insert(0, 'rules')
from guild_engine import Engine

e = Engine([{'id': 0, 'name': 'A', 'hero': 'bai_white'},
            {'id': 1, 'name': 'B', 'hero': 'ruby_white'}], options={'solo': False})
e.state['phase'] = 'action';e.state['turn'] = 0
p = e.state['players'][0]
p['hand'] = [53];p['gold'] = 99;p['affection'] = 3
e.apply(0, dict(type='play', card=53, strength=0, pieces=[]))
s = e.state
p = s['players'][0]
print('extra_actions', p.get('extra_actions'), 'used', p.get('used'), 'turn', s['turn'],
      'round', s['round'], 'season', s['season'])
print('pending', s.get('pending'))
print('effects queue', s.get('effects'))
for m in s['log'][-4:]:
    print('LOG', m.get('message'))
