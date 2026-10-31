"""Mode-printed cards: four cards shipped with different solo / multiplayer prints.

Verified against the scanned prints (圖包）： pack/6_6, 7_1, 7_7, 8_6 carry the
multiplayer prints; pack/9B_1..4 carry the solo prints.

  B-017 完美默契      multi: 每獲得1張成就卡獲得5金幣 + 打出時GG並執行1次主要行動
                      solo : 每獲得1張成就卡獲得3金幣（打出僅GG）
  D-002 老舊的放映機  multi: 遊戲結束時每打出3張事件卡獲得1點名聲（無上限）
                      solo : 同上（至多6點名聲）
  E-001 庫姬          multi: 獲得(5+文明值)金幣 → 移至左邊玩家
                      solo : 同效果 → 翻至背面
  E-007 大賢者        multi: 支付1秘藥，獲得等同「廢品」標籤數的戰力（無上限）
                      solo : 同效果（至多5）

The base definitions describe the multiplayer print. apply_mode_variants()
is called from Engine setup with the normalized options, so gameplay always
reads the active print. Tables below are static: never mutate at runtime.
"""

from copy import deepcopy

_MODE_CARD_VARIANTS = {
    # printed_code: {mode: {card fields + face fields}}
    'B-017': {
        'multi': {
            'triggers': [dict(event='achievement', effect=dict(gold=5), condition={})],
            'steps': [dict(op='extra_action')],
            'image_path': 'pack/6_6', 'source': 'pack/6_6',
        },
        'solo': {
            'triggers': [dict(event='achievement', effect=dict(gold=3), condition={})],
            'steps': [],
            'image_path': 'pack/9B_2', 'source': 'pack/9B_2',
        },
    },
    'D-002': {
        'multi': {
            'scoring': [dict(stat='played', per=3, point=1)],
            'image_path': 'pack/8_6', 'source': 'pack/8_6',
        },
        'solo': {
            'scoring': [dict(stat='played', per=3, point=1, max=6)],
            'image_path': 'pack/9B_3', 'source': 'pack/9B_3',
        },
    },
    'E-001': {
        'multi': {
            'action': dict(gold=5,
                scaled=[dict(resource='gold', stat='civ', multiplier=1)],
                steps=[dict(op='pass_left')]),
            'image_path': 'pack/7_1', 'source': 'pack/7_1',
        },
        'solo': {
            'action': dict(gold=5,
                scaled=[dict(resource='gold', stat='civ', multiplier=1)],
                steps=[dict(op='flip', self=True)]),
            'image_path': 'pack/9B_4', 'source': 'pack/9B_4',
        },
    },
    'E-007': {
        'multi': {
            'action': dict(costs=dict(pot=1),
                scaled=[dict(resource='strength', stat='tag:scrap', multiplier=1)]),
            'image_path': 'pack/7_7', 'source': 'pack/7_7',
        },
        'solo': {
            'action': dict(costs=dict(pot=1),
                scaled=[dict(resource='strength', stat='tag:scrap', multiplier=1, max=5)]),
            'image_path': 'pack/9B_1', 'source': 'pack/9B_1',
        },
    },
}


def apply_mode_variants(options):
    """Fold the mode's printed effects into CARDS (idempotent per setup)."""
    from guild_content import CARDS
    mode = 'solo' if (options or {}).get('solo') else 'multi'
    for card in CARDS.values():
        if card.get('archived_print'):
            continue
        variants = _MODE_CARD_VARIANTS.get(card.get('printed_code'))
        if variants:
            for key, value in variants[mode].items():
                card[key] = deepcopy(value)
