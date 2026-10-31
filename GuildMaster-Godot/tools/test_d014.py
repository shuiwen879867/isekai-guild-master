# -*- coding: utf-8 -*-
"""test_d014.py - D-014 Phrase百貨 定義與終局計分驗證。
掃描圖校對：費用25G＋支付1板塊；條件 商業2/生活2/零件2；打出時 金幣產能+7、戰力產能+1、抽1、文明+1；
獲得商業標籤×1；名聲0+；終局指定一張已打出的事件卡，獲得該卡當前名聲（含變動後的值）。"""
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


c = CARDS[334]
check('name', c['name'], 'Phrase百貨')
check('price', c['price'], 25)
check('consume_piece', c['consume_piece'], 1)
check('costs', c['costs'], {})
check('tags', c['tags'], ['gold'])
check('requirements', c['requirements'].get('tags'), {'gold': 2, 'civ': 2, 'scrap': 2})
check('gold_pro', c['gold_pro'], 7)
check('str_pro', c['str_pro'], 1)
check('draw', c['draw'], 1)
check('civ', c['civ'], 1)
check('point', c['point'], 0)
check('scoring', c['scoring'], [{'stat': 'best_event_point', 'per': 1, 'point': 1}])
check('no holes scoring', [r for r in c['scoring'] if r.get('stat') == 'holes'], [])
check('printed_text', bool(c.get('printed_text')), True)

players = [{'id': 0, 'name': 'A', 'hero': 'bai_white'},
           {'id': 1, 'name': 'B', 'hero': 'ruby_white'}]
e = Engine(players, options={'solo': False})
p = e.state['players'][0]
e.state['phase'] = 'final'

# 手動佈置已打出區：D-014 本身、A-002(名聲2)、A-117?(名聲-4)、翻面的 A-003(名聲2→失去)、
# 以及帶計數標記的 193（每計數1名聲）。
# 手動佈置已打出區：D-014 本身、A-002(名聲2)、名聲-4 的卡、翻面的 A-003(名聲2→失去)、
# 以及帶計數標記的 193（每計數1名聲）。
p['played'] = [334, 2, 117, 3, 193]
e.state['players'][0]['card_states'] = [
    {'uid': 'u334', 'face_down': False, 'tiles': [], 'adventurers': 0, 'counters': 0},
    {'uid': 'u2', 'face_down': False, 'tiles': [], 'adventurers': 0, 'counters': 0},
    {'uid': 'u117', 'face_down': False, 'tiles': [], 'adventurers': 0, 'counters': 0},
    {'uid': 'u3', 'face_down': True, 'tiles': [], 'adventurers': 0, 'counters': 0},
    {'uid': 'u193', 'face_down': False, 'tiles': [], 'adventurers': 0, 'counters': 3},
]
p['tags'] = ['gold', 'gold', 'gold']  # no interference with candidate points

# best_event_point 直接查詢：候選 名聲 = 334:0(+其自身best禁遞迴)、2:2、117:-4、193:0+3
check('best_event_point stat', e._stat(p, 'best_event_point'), 3)
breakdown = e.score_breakdown(0)
# cards 總和 = D-014(0+3=3) + A-002(2) + (-4) + 翻面A-003(0) + 193(3) = 4
check('score_breakdown cards', breakdown['cards'], 4)
check('best is 193 counters', e._points(p, dict(CARDS[193], _meta={'counters': 3})), 3)

if failures:
    print('D014 TEST FAILED (%d)' % len(failures))
    sys.exit(1)
print('D014 TEST PASSED')
