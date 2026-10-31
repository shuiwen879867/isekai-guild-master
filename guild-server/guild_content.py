"""Manually transcribed scan content. No dependency on legacy/generated cards.

CARDS is the audited project deck; CARD_GALLERY preserves every scan, including
royal objectives and projects whose complete effects are not implemented.
Extra effect keys are contracts with guild_engine, documented in CONTENT_AUDIT.
"""

RESOURCE_NAMES = {
    'gold': '金币', 'strength': '力量', 'pot': '药水',
    'gold_pro': '金币产能', 'str_pro': '力量产能', 'pot_pro': '药水产能',
    'civ': '文明', 'point': '声望', 'draw': '抽牌', 'affection': '好感度',
    'wisdom': '睿智', 'flash': '一闪',
}
STARTING_RESOURCE_KEYS = ('gold', 'strength', 'pot', 'gold_pro', 'str_pro', 'pot_pro')


def starting_resources(hero_id):
    """One audited source for local, solo and network starting allocations."""
    hero = HEROES[hero_id]
    values = {key: hero.get(key, 0) for key in STARTING_RESOURCE_KEYS}
    if any(type(value) is not int or value < 0 for value in values.values()):
        raise ValueError('看板娘的开局资源数据不正确：%s' % hero_id)
    return values
TAG_NAMES = {'civ': '生活', 'scrap': '零件', 'gold': '商业', 'character': '人物'}


def _requirements(**values):
    result = dict(tags={}, heart=0, pieces=0, civ=0, bases=0, cards=0)
    result.update(values)
    return result


def _card(number, name, price, **values):
    result = dict(id=number, name=name, price=price, kind='event', image=number,
                  image_path='images/cards/%s.jpg' % number,
                  gold=0, strength=0, pot=0, gold_pro=0, str_pro=0, pot_pro=0,
                  civ=0, point=0, draw=0, affection=0, tags=[],
                  requirements=_requirements(), consume_piece=0, can_trans=False,
                  action={}, costs={}, conditional=[], scaled=[], scoring=[], available=True, verified=True,
                  subtitle='', printed_code='', required_effects=[], price_verified=True,
                  unavailable_reason='', source='images/cards/%s.jpg' % number)
    result.update(values)
    return result


# Printed CON is a prerequisite; a RED hexagon below the price is a cost.
# Top-right icons are gained tags, never inferred from the card title.
CARDS = {card['id']: card for card in [
    _card(1, '四吨重卡车残骸', 12, gold_pro=4, draw=3, consume_piece=1, tags=['scrap'],
          requirements=_requirements(pieces=1),
          description='抽牌图标1；另支付一块迷宫板块抽2张事件卡，总计抽3张。'),
    _card(2, '偶像出道', 10, gold_pro=2, civ=1, point=2, tags=['gold'],
          requirements=_requirements(tags={'character': 1})),
    _card(3, '公会偶像', 10, gold_pro=2, civ=1, point=2, tags=['civ'],
          requirements=_requirements(heart=3)),
    _card(4, '迷宫入口公会门市', 6, gold_pro=4, point=1, consume_piece=1, tags=['gold']),
    _card(5, '公会通讯录', 7, draw=2, point=1, tags=['civ']),
    _card(7, 'C级冒险者队伍－暴力团支援', 5, strength=2, costs={'gold_pro': 1}, tags=['civ'],
          conditional=[{'civ_max': 4, 'effect': {'draw': 1}}]),
    _card(8, '蝾螈浴场', 16, gold_pro=5, pot=1, civ=1, point=1,
          consume_piece=1, tags=['civ', 'gold']),
    _card(9, '导入轮班制度', 19, gold_pro=2, str_pro=1, tags=['civ'],
          scaled=[{'resource': 'gold', 'stat': 'available', 'multiplier': 3}]),
    _card(10, '废品区域管理', 6, draw=2, tags=['scrap'],
          requirements=_requirements(tags={'gold': 1})),
    _card(12, 'B级冒险者队伍－金属破坏者', 10, strength=3, costs={'gold_pro': 2},
          conditional=[{'civ_max': 4, 'effect': {'strength': 1}}]),
    _card(13, '恶魔果实', 12, gold_pro=4, civ=1, point=2, tags=['civ', 'gold'],
          requirements=_requirements(civ=5)),
    _card(14, '异世界桌游', 5, gold_pro=3, tags=['civ', 'gold'],
          requirements=_requirements(heart=2)),
    _card(17, '异世界魔王的讨伐纪录', 11, strength=1, str_pro=1, tags=['scrap'],
          requirements=_requirements(pieces=1)),
    _card(21, '手动帮浦开发', 18, gold_pro=6, civ=1, point=2, tags=['civ'],
          requirements=_requirements(tags={'civ': 2})),
    _card(22, '接待小姐的目光', 10, strength=3, draw=1,
          requirements=_requirements(heart=3)),
    _card(24, '诚心的礼物', 15, affection=1, point=1,
          requirements=_requirements(tags={'civ': 2})),
    _card(28, '异世界料理教室', 3, tags=['civ', 'gold'],
          requirements=_requirements(any=[{'tags': {'civ': 1}}, {'tags': {'gold': 1}}])),
    _card(33, '远古食谱', 12, pot=3, civ=1, tags=['civ', 'gold'],
          requirements=_requirements(pieces=3)),
    _card(37, '神秘水瓶', 11, gold_pro=3, pot=1, tags=['scrap'],
          requirements=_requirements(pieces=1)),
    _card(39, '水灵的小房间', 10, gold_pro=2, pot=2, civ=1, consume_piece=1, tags=['civ']),
    _card(40, '仰望星空', 5, gold_pro=2, draw=1, tags=['civ'],
          requirements=_requirements(heart=1)),
    _card(42, '穿越纪念日', 14, gold_pro=2, draw=1, affection=1, civ=1, tags=['civ'],
          requirements=_requirements(civ=5)),
    _card(43, '深渊炮', 15, strength=5, pot=1, point=-1, consume_piece=1,
          tags=['scrap'], requirements=_requirements(bases=1)),
    _card(44, '开拓边境贸易路线', 15, gold_pro=5, draw=1, civ=1, point=2, tags=['gold'],
          requirements=_requirements(tags={'gold': 2})),
    _card(45, '冒险者咨询柜台', 16, gold_pro=2, draw=1, tags=['civ', 'gold'],
          conditional=[{'civ_max': 4, 'effect': {'gold_pro': 2}},
                       {'civ_min': 5, 'effect': {'gold': 5, 'scaled': [
                           {'resource': 'gold', 'stat': 'tag:gold', 'multiplier': 1}]}}]),
    _card(55, '绿色果汁制造机', 3, kind='action', point=-1,
          action={'costs': {'gold': 5}, 'pot': 1}),
    _card(56, '奶奶的药房', 16, kind='action', gold_pro=3, tags=['civ', 'gold'],
          action={'costs': {'gold': 5}, 'pot': 1}),
    _card(60, '特价购买稀有材料', 6, kind='action', gold_pro=2, consume_piece=1,
          tags=['gold'], action={'costs': {'gold': 5}, 'pot': 1}),
    _card(65, '老旧投影机', 16, kind='passive', consume_piece=2, gold_pro=4, draw=2,
          civ=1, tags=['gold', 'scrap'], requirements=_requirements(tags={'gold': 4}),
          scoring=[{'stat': 'played', 'per': 3, 'point': 1}]),
    _card(72, '隐藏的公主守护者', 16, kind='passive', gold_pro=2, str_pro=1, draw=1,
          tags=['civ'], requirements=_requirements(tags={'civ': 1}),
          scoring=[{'stat': 'tag:civ', 'per': 2, 'point': 1}]),
    _card(75, '与大贤者的誓约', 15, kind='passive', str_pro=1, pot=1, draw=1, civ=1,
          tags=['scrap'], requirements=_requirements(tags={'scrap': 1}),
          scoring=[{'stat': 'tag:scrap', 'per': 2, 'point': 1}]),
    _card(76, '缜密的行商网路', 16, kind='passive', gold_pro=4, draw=1, civ=1,
          tags=['gold'], requirements=_requirements(tags={'gold': 1}),
          scoring=[{'stat': 'tag:gold', 'per': 2, 'point': 1}]),
    _card(78, '王国公主夏洛特', 17, kind='passive', gold_pro=4, str_pro=1, point=1,
          tags=['character'], requirements=_requirements(tags={'civ': 3}),
          scoring=[{'stat': 'tag:civ', 'per': 2, 'point': 1}]),
    _card(83, 'S级冒险者－大贤者椒盐脆饼', 13, kind='action', costs={'gold_pro': 5},
          point=3, tags=['scrap', 'character'], requirements=_requirements(tags={'scrap': 3}),
          action={'costs': {'pot': 1}, 'scaled': [
              {'resource': 'strength', 'stat': 'tag:scrap', 'multiplier': 1}]}),
    _card(118, '魔物料理', 13, kind='action', civ=1, point=2, tags=['civ', 'gold'],
          requirements=_requirements(bases=1), action={'costs': {'strength': 1}, 'gold': 5,
          'scaled': [{'resource': 'gold', 'stat': 'tag:gold', 'multiplier': 1}]}),
    _card(155, '双人出游', 20, gold_pro=2, pot=1, affection=1, tags=['civ'],
          requirements=_requirements(heart=2)),
    _card(156, '武器工房的专属合约', 20, str_pro=2, point=1, tags=['gold']),
    _card(168, '魔女的锡杖', 10, str_pro=2, tags=['scrap'],
          requirements=_requirements(tags={'character': 1})),
    _card(170, '钓饵', 8, gold_pro=2, point=1, tags=['civ'],
          scaled=[{'resource': 'gold', 'stat': 'controlled', 'multiplier': 2}]),
    _card(173, '魔物咖啡馆', 0, gold_pro=4, civ=1, point=2, consume_piece=2, tags=['gold']),
    _card(178, '勇者之剑的传说', 9, gold_pro=2, draw=2, tags=['gold']),
    _card(185, '家庭妖精的祝福', 17, gold_pro=3, point=1, tags=['civ', 'civ'],
          scaled=[{'resource': 'gold', 'stat': 'affection', 'multiplier': 3}]),
    _card(187, '剑术道场的赞助', 10, str_pro=1, point=1, tags=['gold']),
    _card(189, '开发精灵蒸气装置', 16, consume_piece=1, gold_pro=5, civ=1,
          point=2, tags=['gold', 'scrap'], requirements=_requirements(tags={'scrap': 3}),
          scaled=[{'resource': 'gold', 'stat': 'civ', 'multiplier': 1}]),
    _card(190, '青空教室', 8, draw=1, point=1, tags=['civ'],
          conditional=[{'civ_max': 4, 'effect': {'gold_pro': 2}}]),
    _card(206, '探索技术竞技大赛', 16, civ=1, point=2, tags=['gold'],
          requirements=_requirements(civ=5),
          scaled=[{'resource': 'strength', 'stat': 'controlled', 'multiplier': 1}]),
    _card(210, '冒险者的敬酒', 5, str_pro=1,
          conditional=[{'requirements': {'stat': 'controlled', 'value': 3}, 'effect': {'draw': 2}}]),
    _card(215, '无言的要求', 14, gold_pro=2, affection=1,
          requirements=_requirements(tags={'gold': 2})),
    _card(216, '迷宫美食大赛', 12, civ=1, point=2, requirements=_requirements(tags={'gold': 3}),
          scaled=[{'resource': 'gold', 'stat': 'tiles', 'multiplier': 2}]),
    _card(221, '投资炼金术师公会', 20, pot_pro=1, pot=1, point=1,
          requirements=_requirements(tags={'civ': 1})),
    _card(224, '让人变傻的靠垫', 13, pot=2, point=1, tags=['civ', 'civ'],
          requirements=_requirements(pieces=2)),
    _card(225, '改善睡眠环境', 13, gold_pro=3, strength=1, draw=1, civ=1, tags=['civ']),
    _card(229, '地底湖度假', 12, pot=1, affection=1,
          requirements=_requirements(bases=1)),
    _card(230, '灯火通信', 15, gold_pro=2, str_pro=1, draw=1, civ=1, point=1, tags=['gold'],
          requirements=_requirements(tags={'scrap': 1, 'gold': 1})),
    _card(231, '我梦想中的家', 12, affection=1, point=2, tags=['civ'],
          requirements=_requirements(tags={'civ': 4})),
    _card(232, '神秘SF枪', 6, str_pro=2,
          requirements=_requirements(tags={'scrap': 2})),
    _card(237, '坏掉的智慧型手机', 3, tags=['scrap'], requirements=_requirements(pieces=1),
          conditional=[{'requirements': {'pieces': 3}, 'effect': {'draw': 2}}]),
    _card(240, '银色光盘', 5, draw=2, civ=1, point=2, tags=['civ', 'scrap'],
          requirements=_requirements(pieces=4)),
    _card(241, '高效率魔力养成', 10, costs={'pot': 1}, str_pro=2),
]}

# Kept as a public catalog partition for future fully audited exclusions.
UNAVAILABLE_AUDITED_CARDS = {}

_PRINTED_CODES = {
    1:'A-001', 2:'A-002', 3:'A-003', 4:'A-004', 5:'A-005', 7:'A-007', 8:'A-008', 9:'A-009',
    10:'A-010', 12:'A-012', 13:'A-013', 14:'A-014', 17:'A-017',
    21:'A-030', 22:'A-031', 24:'A-033', 28:'A-073', 33:'A-078',
    37:'A-082', 39:'A-084', 40:'A-085', 42:'A-087', 43:'A-088',
    44:'A-089', 45:'A-090', 55:'C-001', 56:'C-002', 60:'C-006', 65:'D-002',
    72:'D-009', 75:'D-012', 76:'D-013', 78:'E-002', 83:'E-007', 118:'C-013', 155:'A-046',
    156:'A-047', 168:'A-068', 170:'A-070', 173:'A-091', 178:'A-096', 185:'A-103', 187:'A-105',
    189:'A-107', 206:'A-109', 210:'A-113', 216:'A-056', 237:'A-023',
    190:'A-108', 215:'A-055', 221:'A-061', 224:'A-037', 225:'A-038',
    229:'A-042', 230:'A-043', 231:'A-044', 232:'A-045', 240:'A-026', 241:'A-027',
}
for _number, _card_data in CARDS.items():
    _card_data['printed_code'] = _PRINTED_CODES[_number]
    if _card_data['conditional']:
        _card_data['required_effects'].append('conditional')
    if _card_data['action']:
        _card_data['required_effects'].append('action_costs')
    if _card_data['affection']:
        _card_data['required_effects'].append('release_affection')
    if _card_data['scaled'] or _card_data['action'].get('scaled'):
        _card_data['required_effects'].append('scaled')
    if _card_data['scoring']:
        _card_data['required_effects'].append('scoring')
for _number, _card_data in UNAVAILABLE_AUDITED_CARDS.items():
    _card_data['printed_code'] = _PRINTED_CODES[_number]


def _hero(name, subtitle, images, **values):
    result = dict(name=name, subtitle=subtitle, image=images[0], images=list(images),
                  gold=0, strength=0, pot=0, gold_pro=0, str_pro=0, pot_pro=0,
                  draw=0, draw_achievement=0, tags=[], ability={}, passive={}, upgrade2={}, upgrade3={}, points=0,
                  description='', upgrade_choices={}, verified=True,
                  source=['images/hero/%s.jpg' % i for i in images])
    result.update(values)
    return result


HEROES = {
    'bai_white': _hero('白', '破落的少女 / 白版', [6, 5, 4], gold=32, gold_pro=20, draw=2,
        ability={'discard_min': 1, 'discard_max': 2, 'gold_per_discard': 4},
        upgrade2={'gold_pro': 4}, upgrade3={'choices': [{'civ': -2}, {'civ': 2}]}, points=4,
        upgrade_choices={'3': [{'value': 0, 'label': '文明减少2'}, {'value': 1, 'label': '文明增加2'}]},
        description='特别行动：弃1至2张手牌，每张获得4金币。二级金币产能加4；三级可令文明加2或减2。'),
    'bai_red': _hero('白', '破落的少女 / 黑版', [76, 77, 78], gold=30, gold_pro=18,
        strength=2, str_pro=1, passive={'on_tag_strength': {'scrap': 1}},
        upgrade2={'str_pro': 1, 'tags': ['scrap']},
        upgrade3={'claim_hidden_star': 1}, points=3,
        description='每获得一个零件标记，获得1力量。二级力量产能加1并获得零件标记（触发被动）。三级公开并获得一块背面一星的板块，再由供应堆补上普通板块；获得资源并减少瘴气。'),
    'hainie_white': _hero('海涅', '落魄的大小姐 / 白版', [3, 2, 1], gold=35, gold_pro=21, draw=2,
        passive={'tag_discount': {'tags': ['civ', 'gold', 'scrap'], 'amount': 1}},
        upgrade2={'gold_pro': 3, 'draw': 1},
        upgrade3={'tags': ['civ', 'gold', 'scrap'], 'gold_per_played': 1}, points=3,
        description='打出事件卡时，生活、商业、零件需求中任选一种减1。二级金币产能加3、抽1牌；三级各获一个生活、商业、零件标记，并获得等于已打出事件卡数（含背面）的金币。'),
    'hainie_red': _hero('海涅', '落魄的大小姐 / 黑版', [73, 74, 75], gold=35, gold_pro=19,
        str_pro=1, initial_development='cards', passive={'on_affection_strength': 2},
        upgrade2={'str_pro': 1}, upgrade3={'claim_achievement_discount': 10}, points=3,
        description='开局解锁“打出至少8张事件卡”的好感度格，无需满足事件卡数量条件。每获得一个好感度标记，获得2力量。二级力量产能加1；三级可立即完成一次私人或公开王权卡，金币费用减10（最低0）。'),
}

# A character is an identity; white/black are rule variants, not extra seats.
# Keep legacy IDs stable for running rooms. Display names never use "red".
HERO_VARIANT_LABELS = {'white': '白版', 'black': '黑版'}
CHARACTERS = {}
for _hero_key, _hero_data in HEROES.items():
    _character = _hero_key.split('_')[0]
    _variant = 'black' if '_red' in _hero_key else 'white'
    _hero_data.update(character=_character, variant=_variant, available=True)
    CHARACTERS.setdefault(_character, dict(id=_character, name=_hero_data['name'], variants={}))['variants'][_variant] = _hero_key


def hero_selection(character, variant):
    """Resolve a two-stage selection on the server, never trust a UI label."""
    if not isinstance(character, str) or not isinstance(variant, str):
        raise ValueError('请选择有效的角色与黑白版本。')
    hero = CHARACTERS.get(character, {}).get('variants', {}).get(variant)
    if hero not in HEROES or not HEROES[hero].get('available', False):
        raise ValueError('这个角色版本尚不可选择。')
    return hero


def selectable_hero(hero):
    if not isinstance(hero, str) or hero not in HEROES or not HEROES[hero].get('available', False):
        raise ValueError('请选择有效的角色版本。')
    return hero

HERO_GALLERY = {
    number: dict(id=number, image=number, image_path='images/hero/%s.jpg' % number,
                 name='看板娘扫描 %s' % number, available=False, verified=False,
                 unavailable_reason='该角色/版本尚未完整转录，暂不可选择。')
    for number in list(range(1, 43)) + list(range(46, 61)) + list(range(64, 70)) + list(range(73, 91))
}
for _hero_key, _hero_data in HEROES.items():
    for _level, _number in enumerate(_hero_data['images'], 1):
        HERO_GALLERY[_number].update(name=_hero_data['name'], hero=_hero_key,
            level=_level, available=True, verified=True, unavailable_reason='',
            description=_hero_data['description'])


def _tile(number, star=0, **values):
    result = dict(name='迷宫板块%s' % number, image=number, star=star, point=0,
                  gold=0, pot=0, strength=0, gold_pro=0, str_pro=0, pot_pro=0,
                  draw=0, tags=[], treasure=False, ishole=False,
                  source='images/piece_png/%s.png' % number, verified=True)
    result.update(values)
    return result


TILES = {
    'tile1': _tile(1, 3, point=2, pot=1),
    'tile3': _tile(3, 2, str_pro=1, draw=1),
    'tile4': _tile(4, 2, point=2),
    'tile5': _tile(5, 2, treasure=True),
    'tile6': _tile(6, 2, point=1, tags=['scrap', 'scrap']),
    'tile7': _tile(7, 3, gold_pro=2, treasure=True),
    'tile8': _tile(8, 1, point=1, tags=['scrap']),
    'tile9': _tile(9, 1, pot=1),
    'tile10': _tile(10, 2, point=1, pot=1),
    'tile11': _tile(11, tags=['scrap']),
    'tile12': _tile(12, 1, gold_pro=2, tags=['scrap']),
    'tile13': _tile(13, 2, gold_pro=4, tags=['scrap']),
    'tile14': _tile(14, name='深渊洞穴', ishole=True),
    'tile21': _tile(21, name='空白迷宫'),
    'tile22': _tile(22, 1, draw=2),
    'boss': _tile(18, 5, point=4, name='迷宫首领', back_image=17, default_star=3),
}

TILE_GALLERY = {
    number: dict(id=number, image=number, image_path='images/piece_png/%s.png' % number,
                 name='板块扫描 %s' % number, available=False,
                 unavailable_reason='背面或其他首领难度图，不加入当前奖励表。')
    for number in range(1, 23)
}
for _tile_key, _tile_data in TILES.items():
    TILE_GALLERY[_tile_data['image']].update(_tile_data, available=True,
        tile=_tile_key, unavailable_reason='')


def _achievement(number, name, point, stat, value, **values):
    result = dict(name=name, description='', requirement={'stat': stat, 'value': value},
                  requirements=_requirements(), price=10, point=point, image=number,
                  available=True, verified=True, can_trans=False, costs={}, effect={},
                  discard_gold=5, tags=[], scoring=[], printed_code='R-%03d' % (number - 132),
                  source='images/cards/%s.jpg' % number)
    result.update(values)
    return result


# All real royal cards. Compound requirements are AND, not optional UI hints.
ACHIEVEMENTS = {
    'royal133': _achievement(133, '如果是这个，就交给我吧！', 3, 'gold', 0,
        requirement={'any': [{'tags': {'civ': 5}}, {'tags': {'gold': 5}}, {'tags': {'scrap': 5}}]},
        description='生活、商业、零件标记任选一种至少5。'),
    'royal134': _achievement(134, '奥利哈钢戒指', 4, 'affection', 5,
        requirements=_requirements(heart=5, tags={'scrap': 4}), description='好感度至少5，零件标记至少4。'),
    'royal135': _achievement(135, '地产保险', 1, 'tag:gold', 3,
        requirements=_requirements(tags={'gold': 3}), scoring=[{'stat': 'tag:gold', 'per': 2, 'point': 1}],
        description='商业标记至少3；终局每2个商业标记额外获得1声望。'),
    'royal136': _achievement(136, '昨晚非常开心！', 4, 'affection', 5,
        requirements=_requirements(heart=5, tags={'civ': 4}), description='好感度至少5，生活标记至少4。'),
    'royal137': _achievement(137, '异世界的神像', 5, 'tiles', 6,
        requirements=_requirements(pieces=6), description='持有至少6块迷宫板块。'),
    'royal138': _achievement(138, '异世界的变革者', 3, 'played', 12,
        requirements=_requirements(cards=12), description='已打出至少12张事件卡。'),
    'royal139': _achievement(139, '异世界传送门建造完成', 4, 'tag:scrap', 5,
        requirements=_requirements(tags={'scrap': 5}), description='零件标记至少5。'),
    'royal140': _achievement(140, '一生一世的告白', 5, 'affection', 5,
        requirements=_requirements(heart=5, pieces=4), description='好感度至少5，持有至少4块迷宫板块。'),
    'royal141': _achievement(141, '个人收藏室', 3, 'tag:civ', 2,
        requirements=_requirements(tags={'civ': 2, 'gold': 2, 'scrap': 2}), description='生活、商业、零件标记各至少2。'),
    'royal142': _achievement(142, '喷火山之龙', 5, 'gold', 0, price=35, can_trans=True,
        description='无前置条件；可使用力量折抵金币费用。'),
    'royal143': _achievement(143, '本日公会大获成功！', 1, 'tiles', 3,
        requirements=_requirements(pieces=3), scoring=[{'stat': 'tiles', 'per': 2, 'point': 1}],
        description='持有至少3块迷宫板块；终局每2块持有迷宫板块额外获得1声望。'),
    'royal144': _achievement(144, '超越世界的牵绊', 4, 'affection', 5,
        requirements=_requirements(heart=5, tags={'gold': 4}), description='好感度至少5，商业标记至少4。'),
    'royal145': _achievement(145, '圣艾尔摩之火', 1, 'tag:civ', 3,
        requirements=_requirements(tags={'civ': 3}), scoring=[{'stat': 'tag:civ', 'per': 2, 'point': 1}],
        description='生活标记至少3；终局每2个生活标记额外获得1声望。'),
    'royal146': _achievement(146, '空白百科全书', 1, 'tag:scrap', 3,
        requirements=_requirements(tags={'scrap': 3}), scoring=[{'stat': 'tag:scrap', 'per': 2, 'point': 1}],
        description='零件标记至少3；终局每2个零件标记额外获得1声望。'),
    'royal147': _achievement(147, '天天和她在一起', 3, 'tag:character', 1,
        requirements=_requirements(tags={'character': 1}), description='人物标记至少1。'),
    'royal148': _achievement(148, '迷宫伯爵', 5, 'bases', 3,
        requirements=_requirements(bases=3), description='持有至少3个据点。'),
    'royal149': _achievement(149, '王国第一战士公会', 3, 'str_pro', 5, can_trans=True,
        description='力量产能至少5；可使用力量折抵金币费用。'),
    'royal151': _achievement(151, '建造大剧院', 4, 'gold_pro', 35,
        description='金币产能至少35。'),
}

POTIONS = {
    'gold': {'name': '黄金药水', 'cost': 1, 'effect': {'gold': 8}},
    'strength': {'name': '力量药水', 'cost': 1, 'effect': {'strength': 2}},
    'knowledge': {'name': '知识药水', 'cost': 1, 'effect': {'civ': 1, 'draw': 2}},
    'build': {'name': '建设药水', 'cost': 2, 'effect': {'free_build': True}},
    'free_card': {'name': '灵感药水', 'cost': 3, 'effect': {'free_card': True}},
    'power': {'name': '强力药水', 'cost': 3, 'effect': {'strength': 5}},
}

# Labels for untranscribed scans are explicit placeholders, not invented names.
CARD_GALLERY = {
    number: _card(number, '扫描卡牌 %s（待转录）' % number, 0,
                 available=False, verified=False, price_verified=False,
                 category='achievement' if 133 <= number <= 154 else 'project',
                 unavailable_reason='完整效果尚未转录；不加入对局牌库。')
    for number in range(1, 242)
}
for _number, _definition in CARDS.items():
    CARD_GALLERY[_number] = dict(_definition, category='project')
for _number, _definition in UNAVAILABLE_AUDITED_CARDS.items():
    CARD_GALLERY[_number] = dict(_definition, category='project')

# Specific unsupported semantics observed in the scans/contact sheets. These
# are catalog notes, not executable or supposedly fully verified transcriptions.
_GALLERY_NOTES = {
    1: ('四吨重卡车残骸', '需选择并支付一块持有迷宫板块、随机取得事件卡；完整结算尚未实现。'),
    6: ('地精洞穴', '需从供应堆取得板块，且所有玩家均获得金币产能；未实现跨玩家结算。'),
    9: ('导入轮班制度', '按文明判断额外抽牌及金币费用，不能只保留产能图标。'),
    11: ('负离子产生器', '需选择一块深渊洞穴并净化。'),
    15: ('异世界杂货铺', '需处理可选翻面事件卡及按标记计算的收益。'),
    16: ('异世界时尚表演', '需解放好感度标记；该牌完整成本与条件尚未逐字复核。'),
    18: ('八卦欧巴桑协会', '需选择弃1至5张手牌并按数量抽取、挑选事件卡。'),
    19: ('最前线魔物研究所', '打出时执行据点化，需要地图目标选择。'),
    20: ('死灵王的大军势', '所有玩家获得药水，需要跨玩家效果。'),
    23: ('悬赏怪物通缉令', '需选择并公开两块背面普通板块，不能选择首领。'),
    25: ('新型马车开发', '获得生活与商业标记总数乘2的金币（包括此卡）；自身标记计数时机尚未接入此牌。'),
    26: ('新人训练制度', '需选择手牌翻面，再按是否翻面结算力量。'),
    27: ('深红甲壳城堡', '需执行据点化并选择、交换邻接地图板块。'),
    29: ('王室女仆部队', '需在据点化与公开并取得板块之间选择。'),
    30: ('机械大门', '需取得特定一星板块；供应堆选择尚未实现。'),
    31: ('宫殿舞会', '需在解放好感度与折价20金币打出人物牌之间选择。'),
    32: ('极彩爆裂炮弹', '选择替换自己支配区域相邻的非魔王迷宫（不需冒险者），之后可再探索一次；或按已打出事件卡数获得金币。'),
    34: ('富商的邀请函', '商业标记含自身不超过3时得5金币与1药水并强制翻面，否则不触发。'),
    35: ('连接朱红色太阳之路', '需净化、支付可选数量板块并结算额外收益。'),
    36: ('精灵栖息之泉', '打出后另支付1板块得1药水，再弃2张手牌得1药水；需分步骤支付。'),
    38: ('研究人造深渊', '需从供应堆取得指定类型深渊洞穴。'),
    41: ('占卜师的帐篷', '需公开抽牌，按牌类/标记结算，再加入手牌。'),
    45: ('冒险者咨询柜台', '按文明区间给予不同的产能或标记计数收益。'),
    46: ('简易式露天澡堂', '永久效果：获得好感度标记时获得金币。'),
    47: ('迷宫攻略RTA', '探索相邻深渊的永久效果，并有交换板块的打出效果。'),
    48: ('有效活用迷宫瘴气', '获得深渊洞穴时触发金币，并有净化操作。'),
    49: ('龙壁少女', '探索成本受地形条件影响，永久修正尚未实现。'),
    50: ('狼群军团', '按自己板块的邻接关系修正探索成本。'),
    51: ('公会的不协调搭档', '角色每次升级触发获得2力量。'),
    52: ('暗影中的人们', '探索成功时变更板块类型并触发额外效果。'),
    53: ('完美默契', '完成王权卡时触发金币，另含额外行动。'),
    54: ('马车的聚会', '获得商业标记时触发金币，另含取得板块操作。'),
    57: ('水晶蔷薇', '特别行动支付力量换药水，另含供应堆板块选择。'),
    58: ('异世界技艺', '特别行动支付板块，收益依商业标记数计算。'),
    59: ('异世界电台', '需选择弃牌、计算文明再抽牌，属于多步特别行动。'),
    61: ('古代魔像基地', '特别行动取得指定板块，且打出时有全体效果。'),
    62: ('与矿山精灵斗酒', '特别行动支付5金币执行据点化，然后将此卡翻面。'),
    63: ('蒸馏酒', '药水换取的金币数取决于商业标记数。'),
    64: ('异世界食堂', '结算声望依赖放置在该卡上的手牌。'),
    65: ('老旧投影机', '结算声望依赖已打出事件卡数。'),
    66: ('圣女裁缝队', '结算声望依赖深渊洞穴数量。'),
    67: ('迷宫开拓村', '结算声望依赖该牌上的背面事件卡。'),
    68: ('吟游诗人的叙事歌', '需比较标记数量并动态结算声望。'),
    69: ('设立冒险者学校', '动态声望与无标记事件卡触发金币。'),
    70: ('迷宫物资馆', '动态声望按标记和已打出牌数判断。'),
    71: ('流浪商队', '动态声望按人物和商业标记判断。'),
    72: ('隐蔽的公主守护者', '按生活标记动态结算声望。'),
    73: ('骑士公主的神像', '需免费据点化，且按据点数动态结算声望。'),
    74: ('圣女的宠爱', '需净化，并按深渊洞穴数动态结算声望。'),
    75: ('与大贤者的誓约', '按零件标记动态结算声望。'),
    76: ('缜密的行商网路', '按商业标记动态结算声望。'),
    117: ('绝症', '特别行动支付药水并弃置自身；不支持事件牌翻面/移出后的重算。'),
    118: ('魔物料理', '力量换金币的数量依商业标记计算。'),
    119: ('迷宫爱慕三勇士', '将持有板块/事件牌背面化换力量，再弃置自身。'),
    120: ('老练的拆解工匠', '支付板块后按商业标记数取得金币。'),
    121: ('惊喜派对', '支付板块、解放好感度并弃置自身。'),
    122: ('死亡界线的阅兵式', '特别行动额外移动/探索并支付药水。'),
    123: ('裂隙图书馆', '需选择手牌并按原价判断额外产能。'),
    124: ('那一天的誓言', '完成王权卡时触发返还/移除事件牌。'),
    125: ('公会仓库大扫除', '永久效果修正下一张事件卡的打出方式。'),
    128: ('异世界前哨开发', '获得人物标记时触发金币。'),
    129: ('异世界技艺分析团队', '获得零件标记时触发金币。'),
    130: ('命中注定的相遇', '获得人物标记时弃置自身。'),
    132: ('消费合作社', '获得生活标记时触发金币。'),
    133: ('如果是这个，就交给我吧！', '真实王权卡，条件为三种标记之一至少5。'),
    135: ('地产保险', '真实王权卡：需商业标记3；按商业标记动态计分。'),
    143: ('本日公会大获成功！', '真实王权卡：需持有板块3；按持有板块数动态计分。'),
    145: ('圣女费摩之火', '真实王权卡：需生活标记3；按生活标记动态计分。'),
    146: ('空白百科全书', '真实王权卡：需零件标记3；按零件标记动态计分。'),
    147: ('天天和她在一起', '真实王权卡：需人物标记1；当前牌库缺少人物标记来源，不发放。'),
    150: ('圣女的信赖', '真实王权卡：特殊六角形条件，需要净化/板块类别语义。'),
    152: ('编撰大迷宫史', '真实王权卡：特殊数量条件尚未逐字核验。'),
    153: ('搜寻技术系统化', '真实王权卡：含特殊探索/板块状态条件，尚未实现。'),
    154: ('日落时分的婚礼钟声', '真实王权卡：除好感度5外另有附加条件，尚未实现。'),
    161: ('魔法通信网路', '额外免费打出手牌，需嵌套出牌与选牌。'),
    170: ('钓饵', '金币收益依控制区域数计算。'),
    175: ('迷宫清洁机器人', '需交换地图板块及净化。'),
    176: ('迷宫横町', '需选择目标并执行特殊免费据点化。'),
    180: ('那女孩的亲手料理', '需检索弃牌堆并依牌/标记内容结算。'),
    181: ('公会总部的大改造', '金币收益依已打出牌数及人物标记数计算。'),
    184: ('异世界贴片故事工作坊', '需放置背面事件牌，并重算被移除的标记。'),
    185: ('家庭妖精的祝福', '金币收益依好感度标记数计算。'),
    188: ('拿到了被诅咒的武器', '含可选翻面自身，需要重算标记及声望。'),
    189: ('开发精灵蒸气装置', '即时金币收益依当前文明数计算。'),
    191: ('白昼之城与狭隘天空', '事件卡引起文明上升时触发金币。'),
    192: ('迷宫监视塔', '探索金币费用受相邻据点影响。'),
    193: ('弹力伸缩桌', '自带计数器、特殊标记及动态声望。'),
    194: ('贵族赞助者', '打出价格15以上事件卡时触发金币。'),
    195: ('大法师的奇思妙想', '支付持有迷宫板块时触发金币。'),
    196: ('迷宫的七大不可思议', '探索成功时触发金币，并按控制区数移除自身。'),
    197: ('发现迷宫电梯', '改变所有玩家的探索行动规则。'),
    198: ('迷宫珍宝商', '需同时支付药水与板块，再按商业标记数获得金币。'),
    199: ('与恩爱的另一半交流', '特殊免费取得地图板块及额外行动。'),
    200: ('捡到幻兽的幼崽', '板块放在卡面上换取金币产能，并有动态结算声望。'),
    201: ('借钱度日', '特别行动还款后移除自身，需要重算负声望。'),
    202: ('伪装结婚', '特别行动按好感度条件移除自身。'),
    203: ('东方的锻刀匠', '需支付持有板块，按板块星级判断力量收益。'),
    204: ('迷宫导游', '特别行动执行探索并按成功结果奖励金币。'),
    205: ('迷宫地图制图师', '需选择相邻板块公开，含特别行动。'),
    206: ('探索技术竞技大赛', '力量收益按控制区域数计算。'),
    207: ('超合金刀刃', '先获得力量产能1，再按力量产能一半向下取整获得力量，最多5。'),
    208: ('深渊兽大爆发', '需净化并给全体玩家力量。'),
    209: ('研究发酵魔法', '金币收益按生活标记数计算。'),
    210: ('冒险者的敬酒', '达到控制区域门槛时额外抽牌。'),
    211: ('无名冒险者的墓地', '无背面事件卡时有条件获得金币。'),
    212: ('迷宫露天开采', '需执行据点化并从供应堆取得板块。'),
    213: ('龙之血', '效果强制把另一张已打出事件卡翻面。'),
    214: ('徘徊亡灵战车', '需取得供应堆板块并给所有玩家力量。'),
    216: ('迷宫美食大赛', '金币收益按持有板块数计算。'),
    217: ('创立迷宫品牌', '需选择弃牌并逐张换金币。'),
    218: ('欢迎来到迷宫酒馆！', '打出时执行据点化，需要地图目标。'),
    219: ('迷宫魔兽园开幕', '需持有据点；完整产能效果未逐字复核。'),
    220: ('迷宫魔物的过度增生', '需取得板块，且所有玩家额外抽牌。'),
    222: ('瘴气温泉', '需据点化和净化两个目标操作。'),
    223: ('海妖尼尼克', '需弃置已控制区域的板块，并替换为深渊洞穴。'),
    226: ('圣女驾到', '需选择并净化深渊洞穴。'),
    227: ('圣水的剩余库存', '需选择并净化深渊洞穴。'),
    228: ('苍银大要塞', '需据点化，收益依零件标记数计算。'),
    233: ('一夜城', '打出时执行据点化，需要目标选择。'),
    234: ('荣耀的黎明', '选择并取得地图板块后执行额外探索。'),
    235: ('开发永动装置', '需净化并按所有玩家持有的深渊洞穴计数。'),
    236: ('王族迷宫视察', '需交换两个已公开普通地图板块。'),
    237: ('坏掉的智慧型手机', '抽牌数量按持有板块门槛判断。'),
    238: ('挖掘奇妙巨石', '需从供应堆取得普通迷宫板块。'),
    239: ('强行探索', '立即执行折价探索，含失败后的特殊处理。'),
}
for _number, (_name, _reason) in _GALLERY_NOTES.items():
    if _number not in CARDS:
        CARD_GALLERY[_number].update(name=_name, unavailable_reason=_reason,
                                     catalog_reviewed=True)

# Preserve the completely read but currently unreachable royal character goal.
CARD_GALLERY[147].update(price=10, price_verified=True, point=3, verified=True,
    printed_code='R-015', requirements=_requirements(tags={'character': 1}),
    requirement={'stat': 'tag:character', 'value': 1}, description='人物标记至少1。')
for _key, _definition in ACHIEVEMENTS.items():
    _number = _definition['image']
    CARD_GALLERY[_number] = dict(_definition, id=_number, category='achievement',
                                achievement_id=_key, image_path='images/cards/%s.jpg' % _number,
                                unavailable_reason='王权卡独立牌堆，不加入事件卡牌库。')

ALL_CARDS = CARD_GALLERY
GALLERY = CARD_GALLERY
CARD_COUNT = len(CARD_GALLERY)
PLAYABLE_CARD_IDS = tuple(sorted(CARDS))


def _resolve(card_or_id):
    if isinstance(card_or_id, dict):
        return card_or_id
    try:
        number = int(card_or_id)
        # Playable event rules are authoritative; the gallery also contains
        # separate achievement scans whose ids must retain their own entries.
        return CARDS.get(number, CARD_GALLERY.get(number, {}))
    except (TypeError, ValueError):
        return {}


def requirement_summary(card_or_id):
    """Chinese prerequisite/cost text, with no Ren'Py or HTML markup."""
    card = _resolve(card_or_id)
    if not card:
        return '未知卡牌'
    if not card.get('verified', False):
        return '条件尚未核验；请查看原始扫描'
    req = card.get('requirements', {})
    parts = ['%s标记至少%s' % (TAG_NAMES.get(tag, tag), count)
             for tag, count in req.get('tags', {}).items() if count]
    for key, label in [('heart', '好感度'), ('pieces', '持有迷宫板块'),
                       ('civ', '文明'), ('bases', '据点'), ('cards', '已打出事件卡'),
                       ('holes','深渊洞穴'), ('untagged','无标记正面事件'), ('controlled','控制区域')]:
        if req.get(key):
            parts.append('%s至少%s' % (label, req[key]))
    if req.get('any'):
        options = []
        for option in req['any']:
            options.append(requirement_summary(dict(verified=True,requirements=option)))
        parts.append('满足其一：' + '或'.join(options))
    for key, amount in card.get('costs', {}).items():
        parts.append('另须支付%s%s' % (amount, RESOURCE_NAMES.get(key, key)))
    if card.get('consume_piece'):
        parts.append('另须支付%s块迷宫板块' % card['consume_piece'])
    if card.get('gold_pro', 0) < 0:
        parts.append('金币产能减少%s' % -card['gold_pro'])
    if not parts and card.get('requirement'):
        return card.get('description', '见扫描原卡')
    return '；'.join(parts) or '无前置条件'


def _effect_summary(effect):
    parts = []
    for key, label in RESOURCE_NAMES.items():
        value = effect.get(key, 0)
        if value:
            parts.append('%s%+d' % (label, value))
    for rule in effect.get('scaled', []):
        text = '每%s%s获得%s%s' % (rule.get('per',1), _stat_label(rule['stat']), rule.get('multiplier', 1),
                                    RESOURCE_NAMES.get(rule['resource'], rule['resource']))
        if 'cap' in rule or 'max' in rule:
            text += '（最多%s）' % rule.get('max',rule.get('cap'))
        if 'solo_max' in rule:
            text += '（单人最多%s）' % rule['solo_max']
        if rule.get('offset'):
            text += '，再%+d'%rule['offset']
        parts.append(text)
    return '、'.join(parts)


def _stat_label(stat):
    if stat.startswith('tag:'):
        return TAG_NAMES.get(stat[4:], stat[4:]) + '标记'
    return {'extra_cost_cards':'已打出且有额外费用的正面事件', 'tiles': '持有迷宫板块', 'pieces': '持有迷宫板块',
            'controlled': '控制区域', 'played': '已打出事件卡', 'cards': '已打出事件卡',
            'available': '未使用冒险者', 'bases': '据点', 'holes':'深渊洞穴', 'holes_or_variable':'洞穴或变动板块',
            'untagged':'无标记正面事件', 'permanent_cards':'有永久效果的事件', 'minimum_tags':'三种基础标记的最少数量', 'maximum_tags':'三种基础标记的最多数量',
            'strong_tiles':'两星以上非首领板块', 'boss_tiles':'首领板块', 'attached:self':'本卡上的冒险者',
            'attached_tiles:self':'本卡上的板块', 'counters:self':'本卡计数', 'earned_achievements':'已完成王权',
            'best_event_point':'指定事件的当前名声'}.get(stat, RESOURCE_NAMES.get(stat, stat))


def _scoring_summary(card):
    parts = []
    for rule in card.get('scoring', []):
        if rule.get('stat') == 'best_event_point':
            parts.append('终局指定一张已打出的正面事件，获得与该卡当前名声相同的名声')
            continue
        clause = ('终局%s至少%s时获得%s声望' % (_stat_label(rule['stat']),rule['threshold'],rule.get('point',1))
                  if 'threshold' in rule else '终局每%s%s获得%s声望' % (rule.get('per',1),_stat_label(rule['stat']),rule.get('point',1)))
        parts.append(clause + ('（最多%s分）' % rule['max'] if 'max' in rule else ''))
    return '；'.join(parts)


def _steps_summary(steps):
    labels = {'build':'执行据点化', 'explore':'执行探索', 'play':'打出一张事件卡', 'potion':'执行秘药行动',
              'purify':'净化一块已公开洞穴', 'reveal':'公开迷宫板块', 'peek':'私下查看迷宫并决定是否公开',
              'flip':'将事件卡翻至背面', 'supply':'从供应堆获得板块', 'consume_tiles':'支付持有的迷宫板块并结算收益',
              'attach_adventurer':'将未使用冒险者放在卡上', 'attach_tile':'将迷宫板块放在卡上',
              'discard_draw':'弃手牌并补抽', 'discard_gain':'弃手牌获得资源', 'treasure':'选择一个宝物',
              'extra_action':'执行额外行动', 'reveal_draw':'公开牌库顶卡并按原卡结算', 'play_facedown':'将手牌背面打出',
              'pass_left':'将此卡交给左手边玩家', 'downgrade_base':'将据点降为冒险者', 'replace':'替换地图板块',
              'pass_out':'休店：本季不再行动',
              'replace_hole':'将目标替换为洞穴', 'claim_replace':'获得目标板块并补充供应板块', 'counter':'在本卡上增加计数',
              'consumed_bonus':'按本次支付板块的星数或洞穴结算奖励',
              'siren_discount':'打出一张事件，可减少至多5金币产能，每点产能抵2金币',
              'refresh_actions':'移除至多两张卡（含本角色）的使用完毕标记',
              'ruby_explore':'探索一次，复活祭坛有数字标记时减10金币（最低10）',
              'melissa_reveal_play':'公开牌库顶两张，选择一张无视打出费用和条件打出，另一张弃置'}
    parts = []
    for step in steps:
        op = step['op']
        if op=='branch':
            text = '选择其一：'+' / '.join(x['label'] for x in step['options'])
        elif op=='all':
            text = '所有玩家（含自己）：'+_effect_summary(step['effect'])
        elif op=='if':
            text = '满足原卡条件时：'+_effect_summary(step.get('effect',{}))+' '+_steps_summary(step.get('effect',{}).get('steps',[]))
        elif op=='pay_effect':
            text = '可追加支付'+'、'.join('%s%s'%(v,RESOURCE_NAMES.get(k,k)) for k,v in step.get('costs',{}).items())+'，按原卡结算'
        elif op=='pay_resource':
            text = '支付%s～%s%s，每点%s' % (step.get('min',1),step.get('max',1),RESOURCE_NAMES.get(step['resource'],step['resource']),_effect_summary(step.get('per',{})))
        elif op=='draw_achievement_select':
            text = '抽%s张未使用成就，保留%s张' % (step['count'],step.get('keep',1))
        elif op=='effect':
            text = _effect_summary(step.get('effect',{}))
        else:
            text = labels.get(op,'按原卡执行后续选择')
            if step.get('count',1)>1:
                text += ' ×%s'%step['count']
            if step.get('discount'):
                text += '（减免%s金币）'%step['discount']
            if step.get('free'):
                text += '（免基础金币费用）'
            if op=='explore' and step.get('hole_claim'):
                text += '（可探索深渊洞穴，按普通迷宫板块计算成本；BOSS除外）'
            if op=='extra_action' and step.get('explore_discount'):
                text += '（此时选择「探索」，必要成本-%s）'%step['explore_discount']
        parts.append(('可选：' if step.get('optional') else '')+text)
    return ' → '.join(parts)


def card_summary(card_or_id, steps_formatter=None):
    """Chinese complete supported effect text, plain text only."""
    card = _resolve(card_or_id)
    summarize_steps = steps_formatter or _steps_summary
    if not card:
        return '未知卡牌'
    if not card.get('available', False):
        return card.get('unavailable_reason', '尚未开放')
    if card.get('category') == 'achievement' or 'requirement' in card:
        return '%s；支付%s金币；%s声望%s' % (card.get('description', ''), card.get('price', 0),
            '基础' if card.get('scoring') else '', card.get('point', 0))
    parts = (['卡面原文摘录：'+card['printed_text']] if card.get('printed_text') else [])
    parts.append('规则说明：费用%s金币' % card.get('price', 0))
    effect = _effect_summary(card)
    if effect:
        parts.append(effect)
    if card.get('tags'):
        parts.append('获得标记：' + '、'.join(TAG_NAMES.get(t, t) for t in card['tags']))
    for condition in card.get('conditional', []):
        clauses = []
        if 'civ_max' in condition:
            clauses.append('文明不高于%s' % condition['civ_max'])
        if 'civ_min' in condition:
            clauses.append('文明至少%s' % condition['civ_min'])
        req = condition.get('requirements', {})
        if req.get('stat'):
            clauses.append('%s至少%s' % (_stat_label(req['stat']), req.get('value', 0)))
        elif req:
            clauses.append(requirement_summary({'verified': True, 'requirements': req}))
        parts.append('%s时：%s' % ('且'.join(clauses), _effect_summary(condition['effect'])))
    action = card.get('action', {})
    if action:
        cost = '、'.join('%s%s' % (v, RESOURCE_NAMES.get(k, k)) for k, v in action.get('costs', {}).items())
        gain = _effect_summary(action)
        action_parts = (['支付%s' % cost] if cost else []) + ([gain] if gain else [])
        if action.get('steps'):
            action_parts.append(summarize_steps(action['steps']))
        parts.append('每季特别行动：' + ('，'.join(action_parts) or '按原卡执行'))
    if card.get('consume_piece'):
        parts.append('另支付%s块迷宫板块' % card['consume_piece'])
    for key, amount in card.get('costs', {}).items():
        parts.append('另支付%s%s' % (amount, RESOURCE_NAMES.get(key, key)))
    if card.get('can_trans'):
        parts.append('可用力量折抵金币费用')
    if card.get('scoring'):
        parts.append(_scoring_summary(card))
    if card.get('steps'):
        parts.append(summarize_steps(card['steps']))
    events = {'card_tags':'获得带生活或人物标记的事件卡（每张一次）','play':'打出事件卡','tag':'获得对应标记','affection':'提升好感度','upgrade':'角色升级',
              'achievement':'完成王权','gain_tile':'获得迷宫板块','consume_tile':'支付迷宫板块','explore':'探索成功','civ':'因事件改变文明'}
    for rule in card.get('triggers',[]):
        parts.append('永久效果 · '+events.get(rule['event'],rule['event'])+'时：'+_effect_summary(rule['effect'])+' '+summarize_steps(rule['effect'].get('steps',[])))
    threshold=card.get('passive',{}).get('explore_stars_discount')
    if threshold:
        parts.append('永久效果 · 探索目标≥%s星（含魔王）时，费用减少%s金币；探索费用最低10，可再用力量支付'%(threshold['min'],threshold['discount']))
    elif card.get('passive') or card.get('conditional_tags') or card.get('global_passive'):
        parts.append('其他永久条件以左侧原卡为准，游戏会自动计算')
    return '；'.join(parts)


DLC_FEATURES = {
    'variable_labyrinth': dict(name='变幻迷宫', enabled=True),
}


def _requires_variable_tiles(value):
    """Detect rule dependencies, including optional bonuses and scoring.

    Titles are deliberately ignored: an ordinary print can share the name of
    a DLC print without using any variable labyrinth tiles.
    """
    if isinstance(value, dict):
        return (value.get('variable') is True or value.get('variable_flip') is True
                or value.get('stat') in ('variable_tiles', 'holes_or_variable')
                or any(_requires_variable_tiles(v) for v in value.values()))
    if isinstance(value, (list, tuple)):
        return any(_requires_variable_tiles(v) for v in value)
    return False


def _set_dlc_availability(definition):
    required = ['variable_labyrinth'] if _requires_variable_tiles(definition) else []
    definition['requires_dlc'] = required
    disabled = [DLC_FEATURES[key]['name'] for key in required if not DLC_FEATURES[key]['enabled']]
    if disabled:
        definition.update(available=False, unavailable_reason='DLC 暂未开放：%s。规则与素材保留，不参与当前对局。' % '、'.join(disabled))
    return not disabled


# Original print scans are retained independently of the playable edition.
# Variable labyrinth cards are available, and enter decks through room options.
from guild_expansion_data import EVENT_SPECS, HERO_SPECS, ROYAL_SPECS

for _number, _spec in EVENT_SPECS.items():
    _definition = _card(_number, **_spec)
    _definition['printed_code'] = _PRINTED_CODES.get(_number, '')
    _set_dlc_availability(_definition)
    CARDS[_number] = _definition
    CARD_GALLERY[_number] = dict(_definition, category='project')
    UNAVAILABLE_AUDITED_CARDS.pop(_number, None)
for _number, _spec in ROYAL_SPECS.items():
    _definition = _achievement(_number, **_spec)
    ACHIEVEMENTS['royal%s' % _number] = _definition
    CARD_GALLERY[_number] = dict(_definition, id=_number, category='achievement', achievement_id='royal%s' % _number,
                                image_path='images/cards/%s.jpg' % _number, unavailable_reason='')

HERO_ARCHIVE = dict(HEROES)
for _spec in HERO_SPECS:
    _values = dict(_spec)
    _key = _values.pop('key')
    _values['subtitle'] = _values['subtitle'].replace('红版', '黑版')
    _values['name'] = _values['name'].replace(' EX', '')
    HERO_ARCHIVE[_key] = _hero(**_values)

_ARCHIVED_HERO_PRINTS = {'ayaka_white', 'elu_white', 'ayaka_red', 'elu_red', 'peria_ex'}
HEROES = {key: value for key, value in HERO_ARCHIVE.items() if key not in _ARCHIVED_HERO_PRINTS}
CHARACTERS = {}
for _key, _data in HERO_ARCHIVE.items():
    _character = _key.split('_')[0]
    _variant = 'black' if '_red' in _key else 'white'
    _dlc_available = _set_dlc_availability(_data)
    _active = _key in HEROES and _dlc_available
    _data.update(character=_character, variant=_variant, available=_active)
    if _key in HEROES:
        CHARACTERS.setdefault(_character, dict(id=_character, name=_data['name'], variants={}))['variants'][_variant] = _key
    for _level, _number in enumerate(_data['images'], 1):
        HERO_GALLERY[_number].update(name=_data['name'], hero=_key, level=_level, available=_active, verified=True,
            character=_character, variant=_variant, description=_data['description'],
            unavailable_reason=('旧印刷版本归档，不与黑白版本重复列为角色。' if _key in _ARCHIVED_HERO_PRINTS else
                                _data.get('unavailable_reason', '此版本暂不可选。') if not _active else ''))

DLC_CARD_IDS = {key: tuple(sorted(cid for cid, card in CARDS.items() if key in card.get('requires_dlc', [])))
                for key in DLC_FEATURES}
PLAYABLE_CARD_IDS = tuple(sorted(k for k,v in CARDS.items() if v['available'] and not v.get('special')))

from guild_new_content import install as _install_new_content
_install_new_content(globals())
from guild_new_heroes import install as _install_new_heroes
_install_new_heroes(globals())
from guild_new_events import install as _install_new_events
_install_new_events(globals())
from guild_new_art import install as _install_new_art
_install_new_art(globals())
from guild_card_corrections import install as _install_card_corrections
_install_card_corrections(globals())
from guild_screenshot_heroes import install as _install_screenshot_heroes
_install_screenshot_heroes(globals())
# Several artwork and correction layers change CARDS after CARD_GALLERY was
# populated. Keep every retained event preview aligned with the same rules
# used by the solo engine and the authoritative network server.
for _number, _definition in CARDS.items():
    if _number in CARD_GALLERY and CARD_GALLERY[_number].get('category') == 'project':
        CARD_GALLERY[_number].update(_definition)
PLAYABLE_CARD_IDS = tuple(sorted(k for k,v in CARDS.items() if v['available'] and not v.get('special')))
