# -*- coding: utf-8 -*-
"""debug_b017b.py — 對比兩模式打出 B-017 後回合推進。"""
import sys
sys.path.insert(0, 'rules')
from guild_engine import Engine

for solo in (False, True):
    players = [{'id': 0, 'name': 'A', 'hero': 'bai_white'}]
    if not solo:
        players.append({'id': 1, 'name': 'B', 'hero': 'ruby_white'})
    e = Engine(players, options={'solo': solo})
    e.state['phase'] = 'action';e.state['turn'] = 0
    p = e.state['players'][0]
    p['hand'] = [53];p['gold'] = 99;p['affection'] = 3
    e.apply(0, dict(type='play', card=53, strength=0, pieces=[]))
    s = e.state;p = s['players'][0]
    print('solo=%s turn=%s round=%s season=%s phase=%s extra_used=%s' % (
        solo, s['turn'], s['round'], s['season'], s['phase'], p.get('extra_actions')))
