# -*- coding: utf-8 -*-
"""Dump festival expansion (320-338) card definitions to UTF-8 text for player review."""
import sys
sys.path.insert(0, 'rules')
from guild_content import CARDS

out_lines = []
NOTE = {
    320: 'A-118', 321: 'A-119', 322: 'A-120', 323: 'A-121', 324: 'A-122',
    325: 'A-123', 326: 'A-124', 327: 'A-125', 328: 'A-126', 329: 'A-127',
    330: 'A-128',
    331: 'B-026', 332: 'B-027', 333: 'B-028', 334: 'D-014', 335: 'D-015',
    336: 'D-016', 337: 'E-025', 338: 'E-026',
}

def fmt_requirements(req):
    if not req: return '-'
    parts = []
    tags = req.get('tags') or {}
    for k, v in tags.items():
        parts.append('%s標籤×%s' % (k, v))
    if req.get('civ'):
        parts.append('文明值≥%s' % req['civ'])
    if req.get('pieces'):
        parts.append('持有%s個迷宮板塊' % req['pieces'])
    if req.get('cards'):
        parts.append('標記%s張事件卡' % req['cards'])
    if req.get('holes'):
        parts.append('持有%s個深淵洞穴' % req['holes'])
    if req.get('gold'):
        parts.append('持有%s金幣' % req['gold'])
    if req.get('any'):
        parts.append('「('+' 或 '.join(fmt_requirements(x) for x in req['any'])+')')
    for k in ('played', 'controlled', 'bases', 'heart'):
        if req.get(k):
            parts.append('%s×%s' % (k, req[k]))
    return '＋'.join(parts) if parts else '-'

def fmt_costs(costs):
    if not costs: return ''
    names = {'gold_pro': '金幣生產', 'str_pro': '戰力生產', 'pot_pro': '秘藥生產',
             'pot': '秘藥', 'gold': '金幣', 'strength': '戰力', 'wisdom': '睿智',
             'flash': '一閃', 'civ': '文明', 'gems': '寶石'}
    return '＋'.join(names.get(k, k)+'×'+str(v) for k, v in costs.items())

def fmt_steps(steps, indent=0):
    labels = {
        'peek': '私下情報（翻看牌庫/板塊）', 'explore': '執行探索', 'play': '免費打出事件卡',
        'downgrade_base': '將據點降為冒險者', 'all': '所有玩家生效', 'supply': '從供應堆取得板塊',
        'reveal': '公開揭示×2', 'if': '滿足條件時', 'purify': '淨化一個已公開深淵洞穴',
        'vip_customer': 'VIP顧客效果', 'pen_reveal_use': '惡魔羽毛筆揭示使用',
        'extra_action': '再執行一次行動', 'flip': '翻面', 'branch': '選擇其一',
    }
    lines = []
    for s in steps:
        op = s.get('op')
        txt = labels.get(op, op)
        extra = []
        if s.get('filter', {}).get('price_max'):
            extra.append('費用上限%s' % s['filter']['price_max'])
        if s.get('count', 1) > 1:
            extra.append('×%s' % s['count'])
        if s.get('hole_claim'):
            extra.append('可探索深淵洞穴／按普通迷宮計算成本（BOSS除外）')
        if s.get('effect'):
            eff = s['effect']
            e_parts = []
            rn = {'gold':'金幣','strength':'戰力','str_pro':'戰力生產','gold_pro':'金幣生產',
                  'pot_pro':'秘藥生產','pot':'秘藥','draw':'抽牌','civ':'文明',
                  'point':'名聲','gems':'寶石','flash':'一閃','wisdom':'睿智'}
            for k, v in eff.items():
                if k in rn: e_parts.append('%s+%s' % (rn[k], v))
                if k == 'steps': e_parts.extend(fmt_steps(v, indent+1))
            txt += '（'+'、'.join(e_parts)+'）' if e_parts else txt
        if s.get('optional'):
            headline = '（可略過）' + txt if not s.get('otherwise') else '否則'+str(s.get('otherwise'))
            txt = txt + '（可略過，否則翻面自己）' if s.get('otherwise') else txt + '（可略）'
        sfx = ('｜' + '、'.join(extra)) if extra else ''
        if op == 'all' and s.get('effect'):
            txt = '所有玩家（含自己）：strength+2' if 'strength' in s.get('effect', {}) and list(s['effect'].keys()) == ['strength'] else txt
        lines.append('    打出時：' + txt + sfx)
    return lines

for cid in range(320, 339):
    c = CARDS.get(cid, {})
    out_lines.append('=' * 70)
    out_lines.append('%s（id %d）　%s' % (NOTE.get(cid, ''), cid, c.get('name', '')))
    out_lines.append('  費用：%s%s' % (c.get('price', 0), ('＋'+fmt_costs(c.get('costs'))) if c.get('costs') else ''))
    if c.get('consume_piece'):
        out_lines.append('  追加支付：迷宮板塊×%s' % c['consume_piece'])
    out_lines.append('  前置：%s' % fmt_requirements(c.get('requirements', {})))
    out_lines.append('  打出時/常時型：%s' % {'event': '即時事件', 'passive': '常駐（被動）', 'action': '特別行動'}.get(c.get('kind', 'event'), c.get('kind', 'event')))
    gains = []
    rn = {'gold':'金幣','strength':'戰力','str_pro':'戰力生產','gold_pro':'金幣生產',
          'pot_pro':'秘藥生產','pot':'秘藥','pot': '秘藥','draw':'抽牌','civ':'文明',
          'point':'名聲','gems':'寶石','flash':'一閃'}
    for k in ('gold','strength','str_pro','gold_pro','pot_pro','pot','draw','civ','point'):
        if c.get(k): gains.append('%s+%s' % (rn[k], c[k]))
    for t in c.get('tags', []):
        gains.append('獲得標記：%s' % t)
    out_lines.append('  數值：' + ('、'.join(gains) if gains else '（無）'))
    for s in c.get('scoring', []):
        out_lines.append('  計分：%s' % s)
    if c.get('scaled'):
        out_lines.append('  浮動：%s' % c['scaled'])
    if c.get('final_bonus'):
        out_lines.append('  常時：結束階段結束時獲得%s金幣並再執行一次主要行動' % c['final_bonus'].get('gold'))
    if c.get('build_surcharge_discount'):
        out_lines.append('  常時：建造據點時減免%s金幣追加費' % c['build_surcharge_discount'])
    if c.get('zero_five_gold'):
        out_lines.append('  常時：積分卡機制（金幣計分以0.5進位累計）')
    for line in fmt_steps(c.get('steps', [])):
        out_lines.append(line)

with open(sys.argv[1], 'w', encoding='utf-8') as f:
    f.write('\n'.join(out_lines))
print('written', sys.argv[1])
