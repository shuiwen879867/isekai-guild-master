# -*- coding: utf-8 -*-
"""Update B-027 (332) and E-026 (338) in the Godot client catalog per printed scans/user notes."""
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')
PATH = r'..\GuildMaster-Godot-src\data\catalog.json'
with open(PATH, encoding='utf-8') as handle:
    data = json.loads(handle.read())

card332 = data['cards']['332']
card332.update({
    'name': '能量飲料 Bring Feather',
    'price': 9,
    'gold': 0,
    'gold_pro': 0,
    'strength': 1,
    'str_pro': 1,
    'civ': 0,
    'draw': 0,
    'point': 0,
    'tags': ['civ'],
    'kind': 'passive',
    'requirements': {'tags': {}, 'heart': 0, 'pieces': 0, 'civ': 0, 'bases': 0, 'cards': 0},
    'consume_piece': 0,
    'costs': {'pot': 1},
    'final_bonus': {'gold': 10, 'action': 1},
    'printed_text': '遊戲「結束階段」結束時，獲得10枚金幣，並再執行一次「主要行動」。',
    'ui_summary': '规则说明：费用9金币＋支付1秘药；打出时：战力产能+1、力量+1；获得标记：生活；'
                  '常时：游戏结束阶段结束时，获得10金币并再执行一次主要行动',
})

card338 = data['cards']['338']
card338.update({
    'name': '劍聖阿茲姬',
    'price': 11,
    'str_pro': 2,
    'point': 2,
    'tags': ['character'],
    'requirements': {'tags': {}, 'heart': 0, 'pieces': 2, 'civ': 0, 'bases': 0, 'cards': 0},
    'consume_piece': 0,
    'costs': {'gold_pro': 3},
    'steps': [{'op': 'explore', 'hole_claim': True}],
    'printed_text': '執行一次「探索」，此時，在計算成本時，目標板塊視為普通迷宮板塊。'
                    '(BOSS除外，此效果可探索「深淵洞穴」)',
    'ui_summary': '规则说明：费用11金币＋支付3金币产能；条件：持有2个迷宫板块；'
                  '打出时：战力产能+2、执行探索（可探索深渊洞穴，按普通迷宫板块计算成本；BOSS除外）；'
                  '获得标记：人物',
})

out = json.dumps(data, ensure_ascii=False, separators=(',', ':'))
with open(PATH, 'w', encoding='utf-8', newline='') as handle:
    handle.write(out)
print('updated 332/338')
print('332:', json.dumps(card332, ensure_ascii=False)[:220])
print('338:', json.dumps(card338, ensure_ascii=False)[:220])
