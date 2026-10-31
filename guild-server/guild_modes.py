"""Room options and board layouts transcribed from the supplied rulebooks.

Coordinates are axial; map regions are printed end-game VP, not tile stars.
Rules references: base pp4-6, expansion pp5-19; TTS boards 210-217.
"""
from copy import deepcopy

OPTION_LABELS = {
    'setup_draft':'开局轮抽',
    'variable_tiles':'变动板块', 'prefer_large':'四人优先大迷宫',
    'labyrinth_events':'迷宫大变动', 'city_events':'都市群像剧', 'festival_events':'冒险者庆典',
    'scouts':'侦查队', 'flags':'旗标碎片', 'forbidden':'禁止区域', 'hard_boss':'高难度魔王',
    'prologue':'故事之始', 'guild_board':'公会委托', 'rich_seasons':'丰收', 'pollution':'污染领地',
    'alchemy':'欧贝拉炼金工房', 'monster_quests':'魔兽讨伐任务', 'dragon':'潜行之龙',
    'forest':'魔之森', 'festival_preparation':'庆典准备',
    'force_large':'强制大地图','all_potions':'开放所有人数的秘药行动','action_timer':'行动倒计时',
}
DEFAULT_OPTIONS = dict({k:False for k in OPTION_LABELS}, prefer_large=True, setup_draft=True,
    map_type='normal', hero_draw=2, solo=False, solo_difficulty='beginner', start_player='auto',
    base_seconds=30, reserve_seconds=120, disconnect_seconds=30,initial_civ=None,initial_miasma=None)
MAP_LABELS = dict(normal='一般迷宫',deep='大深度迷宫',training='训练迷宫')
DIFFICULTIES = dict(beginner='初级',advanced='上级',expert='特级',super='超级')

# Printed VP rows on the large boards (TTS 211 and 214), left to right.
# Two bosses do not create two overlapping concentric scoring regions.
LARGE_MAP_REGIONS = {
    'normal': {
        -3: (1,1,1,1),
        -2: (1,2,2,2,1,1,1),
        -1: (1,2,3,3,2,2,2,1),
         0: (1,2,3,3,3,3,3,2,1),
         1: (1,2,3,3,2,2,2,1),
         2: (1,2,2,2,1,1,1),
         3: (1,1,1,1),
    },
    'deep': {
        -4: (1,1,1,1,1,1,1),
        -3: (1,2,2,2,2,2,2,1),
        -2: (1,2,3,3,3,3,3,2,1),
        -1: (1,2,3,4,4,4,3,3,2,1),
         0: (1,2,3,4,4,4,4,3,3,2,1),
         1: (1,2,3,4,4,4,3,3,2,1),
         2: (0,0,0,0,0,0,0,0,0),
    },
}

def normalize_options(raw=None, players=None):
    if raw is not None and not isinstance(raw,dict):
        raise ValueError('房间设置必须为选项对象。')
    options = deepcopy(DEFAULT_OPTIONS)
    for k,v in (raw or {}).items():
        if k not in options:
            raise ValueError('未知房间选项：'+str(k))
        if k in OPTION_LABELS or k=='solo':
            if type(v) is not bool:
                raise ValueError('开关选项必须为开启或关闭。')
        options[k] = v
    if options['map_type'] not in MAP_LABELS or options['solo_difficulty'] not in DIFFICULTIES:
        raise ValueError('地图或单人难度不正确。')
    if type(options['hero_draw']) is not int or not 1 <= options['hero_draw'] <= 5:
        raise ValueError('角色候选张数应为 1–5。')
    if options['start_player']!='auto' and (type(options['start_player']) is not int or not 0<=options['start_player']<5):
        raise ValueError('先手席位不正确。')
    if options['labyrinth_events']:
        options['variable_tiles'] = True
    for key,maximum in [('base_seconds',3600),('reserve_seconds',7200)]:
        if type(options[key]) is not int or not (1 if key=='base_seconds' else 0)<=options[key]<=maximum:
            raise ValueError('基础时间应为1–3600秒，备用时间应为0–7200秒。')
    if type(options['disconnect_seconds']) is not int or not 1 <= options['disconnect_seconds'] <= 3600:
        raise ValueError('断线等待时间应为1–3600秒。')
    for key,minimum,label in [('initial_civ',1,'初始文明'),('initial_miasma',0,'初始瘴气')]:
        value=options[key]
        if value is not None and (type(value) is not int or not minimum<=value<=1000):
            raise ValueError('%s应为%s–1000的整数，或留空使用标准规则。'%(label,minimum))
    if options['force_large'] and options['map_type']=='training':
        options['map_type']='normal'
    if options['force_large'] and options['forbidden']:
        raise ValueError('强制大地图不能与禁止区域同时开启。')
    if players is not None:
        if options['solo'] and players!=1:
            raise ValueError('单人挑战只能由一位玩家游玩。')
        if options['forbidden'] and players>3:
            raise ValueError('禁止区域仅支持 1–3 人。')
        if options['solo']:
            incompatible = ('festival_preparation','monster_quests','scouts')
            if any(options[k] for k in incompatible):
                raise ValueError('单人规则不使用庆典准备、魔兽讨伐或侦查队。')
    return options

def board_layout(options, count):
    big = options['map_type']!='training' and (options['force_large'] or count==5 or (count==4 and options['prefer_large']))
    deep = options['map_type']=='deep'
    cells=[]
    if deep:
        for r in range(-4,3):
            lo,hi = (max(-4,-4-r),4 if r<=0 else 4-r)
            for q in range(lo,hi+1+(2 if big else 0)):
                cells.append(dict(q=q,r=r,blocked=r==2))
        bosses=[(0,0),(3,0)] if big else [(0,0)]
        # The compact deep board has its two upper reveal markers at the
        # outward printed positions, not the two adjacent centre cells.
        reveals=[(0,-3),(3,-3),(-2,-2),(3,-2),(-3,0),(3,0)] if not big else [(1,-3),(4,-3),(-2,-2),(5,-2),(-3,0),(5,0)]
        variable=[(1,-2),(-1,-1),(2,-1),(-2,1),(1,1)] if not big else [(0,-2),(-2,-1),(-3,1)]
    else:
        for r in range(-3,4):
            lo,hi = max(-3,-3-r),min(3,3-r)
            if big and -2<=r<=2: hi+=2
            for q in range(lo,hi+1):
                cells.append(dict(q=q,r=r,blocked=False))
        bosses=[(0,0),(3,0)] if big else [(0,0)]
        reveals=[(0,-2),(2,-2),(-2,0),(2,0),(-2,2),(0,2)]
        if big: reveals.append((4,0))
        variable=[(-1,-1),(1,-2),(2,-1),(-2,1),(-1,2),(1,1)]
    for c in cells:
        pos=(c['q'],c['r'])
        distance=min(max(abs(c['q']-q),abs(c['r']-r),abs(c['q']-q+c['r']-r)) for q,r in bosses)
        c.update(id='%s,%s'%pos,boss=pos in bosses,
            region=0 if c['blocked'] else min(4 if deep else 3,max(1,(5 if deep else 4)-distance)),
            initially_revealed=pos in reveals,initial_variable=options['variable_tiles'] and pos in variable)
    if big:
        for r,regions in LARGE_MAP_REGIONS[options['map_type']].items():
            for c,region in zip((c for c in cells if c['r']==r),regions):
                c['region']=region
    if options['forbidden']:
        # Expansion p10: normal map's sixth row; deep map's right diagonal.
        if deep:
            cells=[c for c in cells if c['q']+c['r']<=3]
            for c in cells:
                if c['q']+c['r']==3: c.update(blocked=True,region=0)
        else:
            cells=[c for c in cells if c['r']<=2]
            for c in cells:
                if c['r']==2: c.update(blocked=True,region=0)
    if options['map_type']=='training':
        # Tutorial board 212 covers the outer corners with an impassable frame.
        cells=[c for c in cells if abs(c['q'])<=2 and abs(c['r'])<=2 and abs(c['q']+c['r'])<=2]
        for c in cells:
            c['region']=min(3,max(2,4-max(abs(c['q']),abs(c['r']),abs(c['q']+c['r']))))
    return cells, big
