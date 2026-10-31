# -*- coding: utf-8 -*-
"""test_pen_reveal.py — 驗證惡魔羽毛筆（#329）的完整效果鏈。"""
import io
import json as J
import sys

sys.path.insert(0, 'rules')
from guild_session import Session

s = Session()
s.local_lobby('QA')
s.lobby('set_options', options={'solo': True})
s.lobby('start')
s.lobby('set_hero', character=s.room['hero_offers'][0], variant='white')
s.engine.state['phase'] = 'action'
p = s.engine.state['players'][0]
p['tags'] = ['gold', 'gold', 'gold']        # 满足打出条件：3 商业标记
p['hand'] = [329]
s.engine.state['deck'] = [1, 50, 2, 3]      # 牌库顶两张 = 1(四吨重卡车残骸) / 50(群狼军势)
s.engine.state['discard'] = []

before = dict(gold_pro=p['gold_pro'], strength=p['strength'], hand=len(p['hand']), tags=len(p['tags']))
s.toast = ''
ok = s.action('play', card=329, strength=0, pieces=[], double=False)
print('1) 打出羽毛笔 ok=%s toast=%r' % (ok, s.toast))
pending = s.game.get('pending')
print('2) pending title:', pending['title'] if pending else None)
print('   options:', J.dumps(pending['options'], ensure_ascii=False) if pending else None)

# 选择第 1 张（卡号 1：gold_pro+4 / 抽3张 / 另支付1板块 → 羽毛笔只结算效果，不支付板块）
s.toast = ''
s.action('choice', choice_id=pending['id'], selected=[0], action={'strength': 0, 'pot': 0, 'flash': False, 'lab': False})
print('3) 选牌 toast=%r' % s.toast)
print('4) gold_pro: %s → %s（应 +4 = %s）' % (before['gold_pro'], p['gold_pro'], before['gold_pro'] + 4))
print('   strength: %s（羽毛笔自身打出效果）' % p['strength'])
print('   hand_count: %s → %s（选中的卡不进手牌）' % (before['hand'], len(p['hand'])))
print('   tags_count: %s → %s（选中的卡标记不获得）' % (before['tags'], len(p['tags'])))
print('   played:', p['played'], '（应只有羽毛笔 329）')
print('   deck:', s.engine.state['deck'], '（应剩 [2,3]）')
print('   discard:', s.engine.state['discard'], '（应含翻开的 1、50）')
print('   pending now:', s.game.get('pending'))
print('logs:')
for m in s.engine.state['log'][-8:]:
    print('   ', m.get('message'))
