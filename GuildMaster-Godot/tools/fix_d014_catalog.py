# -*- coding: utf-8 -*-
"""Update D-014 (card 334) in the Godot client catalog to match the printed scan."""
import sys
import json

sys.stdout.reconfigure(encoding='utf-8')
PATH = r'..\GuildMaster-Godot-src\data\catalog.json'
with open(PATH, encoding='utf-8') as handle:
    data = json.loads(handle.read())

card = data['cards']['334']
before = json.dumps(card, ensure_ascii=False, sort_keys=True)

card.update({
    'name': 'Phrase百貨',
    'price': 25,
    'gold': 0,
    'gold_pro': 7,
    'str_pro': 1,
    'civ': 1,
    'draw': 1,
    'point': 0,
    'strength': 0,
    'tags': ['gold'],
    'requirements': {'tags': {'gold': 2, 'civ': 2, 'scrap': 2}, 'heart': 0, 'pieces': 0,
                     'civ': 0, 'bases': 0, 'cards': 0},
    'consume_piece': 1,
    'costs': {},
    'scoring': [{'stat': 'best_event_point', 'per': 1, 'point': 1}],
    'printed_text': '遊戲結束時，指定一張已經打出的事件卡，獲得與該卡「名聲」相同數量的「名聲」'
                    '（包含因「獲得名聲」或「失去名聲」效果而變動的數值）。',
    'ui_summary': '规则说明：费用25金币＋支付1个迷宫板块；条件：商业2、生活2、零件2标记；'
                  '打出时：金币产能+7、战力产能+1、抽1张事件卡、文明+1；获得标记：商业；'
                  '终局指定一张已打出的正面事件，获得与该卡当前名声相同的名声；0+名声',
    'required_effects': ['scoring'],
})

out = json.dumps(data, ensure_ascii=False, separators=(',', ':'))
with open(PATH, 'w', encoding='utf-8', newline='') as handle:
    handle.write(out)
print('updated 334; before:', before[:120], '...')
print('after :', json.dumps(card, ensure_ascii=False)[:200], '...')
