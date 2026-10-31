# -*- coding: utf-8 -*-
"""debug_e001.py — 檢視 multi 下打出 E-001 的實際結算。"""
import sys
sys.path.insert(0, 'rules')
from guild_engine import Engine

e = Engine([{'id': 0, 'name': 'A', 'hero': 'bai_white'},
            {'id': 1, 'name': 'B', 'hero': 'ruby_white'}])
e.state['phase'] = 'action'
print('turn', e.state['turn'], 'passed', [pp.get('passed') for pp in e.state['players']],
      'phase', e.state['phase'])
p = e.state['players'][0]
p['hand'] = [77];p['gold'] = 99
try:
    e.apply(0, dict(type='play', card=77, strength=0, pieces=[]))
    state = e.state
    p0 = state['players'][0];p1 = state['players'][1]
    print('p0 gold', p0['gold'], 'played', p0['played'])
    print('p1 gold', p1['gold'], 'played', p1['played'])
    print('pending', state.get('pending'))
    for m in state['log'][-6:]:
        print('LOG', m.get('message'))
except Exception as exc:
    import traceback
    traceback.print_exc()
