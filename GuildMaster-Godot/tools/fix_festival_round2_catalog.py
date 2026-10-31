# -*- coding: utf-8 -*-
"""Round-2 festival corrections: sync catalog 320-338 from engine definitions.

Player-confirmed print fixes applied to the engine first:
  323 A-121 cost 15 + can_trans (sword mark)  - already correct
  325 A-123 scaled = each scrap tag -> +3 gold - already correct (wording fix only)
  329 A-127 no reputation (point 0), reveal-2-pick-1 play, then discard
  330 A-128 cost 2 + 1 piece; req 4 pieces; gold_pro+3 civ+1; branch:
       extra action (explore discount -10)  /  pass: +10 gold, out of actions
  331 B-026 no corner tags
  333 B-028 constant: playing a card whose printed cost ones-digit is 0/5 -> +2 gold
  336 D-016 requirement 35 gold PRODUCTION (not holdings)
"""
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, 'rules')
from guild_content import CARDS
from guild_card_corrections import PRINTED_EVENT_TEXT

PATH = r'..\GuildMaster-Godot-src\data\catalog.json'
with open(PATH, encoding='utf-8') as handle:
    data = json.loads(handle.read())

FIELDS = ('price', 'kind', 'gold', 'strength', 'pot', 'gold_pro', 'str_pro',
          'pot_pro', 'civ', 'point', 'draw', 'tags', 'costs', 'consume_piece',
          'can_trans', 'requirements', 'conditional', 'scaled', 'scoring', 'steps')

UI_SUMMARY = {
    329: '規則說明：費用9金幣；條件：金標籤×3 或 商業×3（二擇一）；打出時：從牌庫頂翻開2張卡片，'
         '選擇其中1張，並使用所選卡「打出時效果」當作是此卡打出時效果；之後，將翻開的卡片丟入棄牌堆；'
         '獲得標記：生活、金',
    330: '規則說明：費用2金幣＋支付1迷宮板塊；條件：持有4個迷宮板塊；'
         '打出時：金幣生產+3、文明值+1、選擇其一：'
         '①再執行一次行動（此時若選擇「探索」，必要成本-10）／'
         '②Pass：獲得10金幣並休店，本季無法再行動；獲得標記：零件',
    331: '規則說明：費用16金幣；條件：生活標籤×2；常時：執行「據點化」時，因相鄰據點產生的追加費用-5；'
         '打出時：金幣生產+4、力量+1、抽1張事件卡',
    333: '規則說明：費用7金幣；打出時：金幣生產+2；'
         '常時：每次你打出成本個位數為「0」或「5」的事件卡，獲得2枚金幣；獲得標記：金',
    336: '規則說明：費用14金幣＋支付1迷宮板塊；條件：金幣生產≥35 或 持有2個迷宮板塊；'
         '打出時：金幣生產+5、秘藥+1、文明值+1、選擇一個「深淵洞穴」板塊淨化；'
         '終局：金幣生產≥30獲得名聲2；持有迷宮板塊≥6再獲得名聲2；獲得標記：零件',
    325: '規則說明：費用12金幣；條件：持有4個迷宮板塊；'
         '打出時：金幣生產+4、文明值+1、獲得等同持有零件標籤數×3的金幣；獲得標記：生活、零件',
}

KEY_requirements = ('tags', 'heart', 'pieces', 'civ', 'bases', 'cards')


def catalog_requirements(req):
    """Engine requirement dict -> catalog flat dict (any/all kept as-is)."""
    out = {}
    for key in ('any', 'all'):
        if key in req:
            out[key] = [catalog_requirements(x) for x in req[key]]
    tags = req.get('tags') or {}
    out['tags'] = dict(tags)
    for key in KEY_requirements:
        out[key] = dict(tags) if key == 'tags' else req.get(key, 0)
    extra = {k: v for k, v in req.items()
             if k not in ('any', 'all', 'tags') and k not in KEY_requirements}
    out.update(extra)
    return out

changes = []
for cid in range(320, 339):
    engine = CARDS.get(cid)
    entry = data['cards'].get(str(cid))
    if engine is None or entry is None:
        continue
    for field in FIELDS:
        before = entry.get(field)
        after = json.loads(json.dumps(engine.get(field, [] if field in
                           ('tags', 'conditional', 'scaled', 'scoring', 'steps')
                           else {} if field in ('costs', 'requirements')
                           else 0 if field in ('price', 'gold', 'strength', 'pot', 'gold_pro',
                                               'str_pro', 'pot_pro', 'civ', 'point', 'draw',
                                               'consume_piece')
                           else False), ensure_ascii=False))
        if field == 'point':
            after = int(engine.get('point', 0) or 0)
        if field == 'requirements':
            after = catalog_requirements(engine.get('requirements') or {})
        if field == 'can_trans':
            after = bool(engine.get('can_trans'))
        if field in ('price', 'consume_piece'):
            after = int(engine.get(field, 0))
        if after != before:
            entry[field] = after
            changes.append('%d.%s: %r -> %r' % (cid, field, before, after))
    printed = PRINTED_EVENT_TEXT.get(cid, ('', ''))
    if printed[1] and entry.get('printed_text') != printed[1]:
        entry['printed_text'] = printed[1]
        changes.append('%d.printed_text updated' % cid)
    if cid in UI_SUMMARY and entry.get('ui_summary') != UI_SUMMARY[cid]:
        entry['ui_summary'] = UI_SUMMARY[cid]
        changes.append('%d.ui_summary updated' % cid)

out = json.dumps(data, ensure_ascii=False, separators=(',', ':'))
with open(PATH, 'w', encoding='utf-8', newline='') as handle:
    handle.write(out)
print('CHANGES (%d):' % len(changes))
for line in changes:
    print(' ', line)
