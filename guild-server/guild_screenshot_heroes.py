"""Alternative character prints transcribed from the user's October screenshots.

Distinct rules stay distinct; existing character print IDs remain compatible.
"""
def install(ns):
    hero, card = ns['_hero'], ns['_card']
    def steps(*values): return dict(steps=list(values))
    def add(key, name, variant, **values):
        character=key.rsplit('_',1)[0]
        numbers=[81000+len(ns['HEROES'])*3+i for i in range(3)]
        definition=hero(name,'截图新版 / '+('白版' if variant=='white' else '黑版'),numbers,**values)
        definition.update(character=character,variant=variant,available=True,requires_dlc=[],
                          source=['supplied/%s_%s.webp'%(key,i) for i in range(1,4)],screenshot_print=True)
        ns['HEROES'][key]=ns['HERO_ARCHIVE'][key]=definition
        identity=ns['CHARACTERS'].setdefault(character,dict(id=character,name=name+'（截图新版）',variants={}))
        identity['variants'][variant]=key
        for level,number in enumerate(numbers,1):
            ns['HERO_GALLERY'][number]=dict(definition,id=number,hero=key,level=level,image_path=definition['source'][level-1])

    add('sif_revised_white','希芙','white',gold=36,gold_pro=21,draw=1,points=3,
        upgrade2=steps(dict(op='pay_effect',costs=dict(str_pro=1),effect=dict(gold_pro=6))),
        upgrade3=steps(dict(op='screenshot_sif_income')),
        description='每打出没有标记的事件，获得3金币。二级：可将力量产能降低1，使金币产能增加6。三级：每3张已打出的无标记事件，或每个人物标记，获得2金币。')
    add('sif_revised_black','希芙','black',gold=35,gold_pro=19,points=3,
        ability=steps(dict(op='consume_tiles',min=1,max=1,per=dict(strength=3)),dict(op='screenshot_recall',optional=True)),
        upgrade2=steps(dict(op='screenshot_sif_blank',optional=True)),
        upgrade3=dict(scaled=[dict(resource='strength',stat='controlled',per=2,multiplier=1)]),
        description='特别行动：支付1块迷宫板块，获得3力量；然后可收回地图上一枚自己的非据点冒险者，并在该处放置空白板块。二级：可获得地图上的空白板块并在该处放置冒险者，不受地图边缘或自己冒险者邻接限制。三级：每2个支配区域获得1力量。')
    add('frida_revised_white','芙莉达','white',gold=39,gold_pro=19,points=3,
        upgrade2=dict(gold_pro=3,tags=['gold']),upgrade3=dict(scaled=[dict(resource='gold',stat='available',multiplier=3)]),
        description='每打出印刷费用个位为3、6、9的事件，获得3金币。二级：金币产能增加3，获得商业标记。三级：冒险者酒馆每有1枚可用冒险者，获得3金币。')
    add('frida_revised_black','芙莉达','black',gold=29,gold_pro=19,strength=1,points=3,
        upgrade2=dict(gold_pro=-3,str_pro=2),upgrade3=steps(dict(op='screenshot_frida_strength')),
        description='每增加1力量产能，获得3金币；包括升级效果，不包括初始资产。二级：力量产能增加2，金币产能降低3。三级：若有至少1个名声3以上的支配区域，获得3力量，否则获得1力量。')
    add('bell_revised_white','贝露','white',gold=38,gold_pro=18,points=3,
        ability=steps(dict(op='pay_resource',resource='strength',min=1,max=2,per=dict(gold=8))),
        upgrade2=steps(dict(op='all',effect=dict(strength=1))),
        upgrade3=steps(dict(op='screenshot_bell_extra')),
        description='特别行动：支付1至2力量，每点获得8金币。二级：所有玩家（包括自己）获得1力量。三级：不放置使用标记，立刻执行一次该特别行动，再执行一次额外主要行动（也可再次执行该特别行动）。')
    add('bell_revised_black','贝露','black',gold=29,gold_pro=16,strength=1,str_pro=2,points=2,
        ability=steps(dict(op='screenshot_attach')),
        initial_steps=[dict(op='all',effect=dict(strength=1))],
        upgrade2=dict(str_pro=1,steps=[dict(op='all',effect=dict(strength=1))]),
        upgrade3=steps(dict(op='screenshot_explore',no_star=True,hole_retry=True,optional=True)),
        description='特别行动：在看板娘上放置1块非魔王迷宫板块，获得8金币；另获得与板块名声相等的秘药。保留板块名声及标记。开局及二级：所有玩家获得1力量；二级另增加1力量产能。三级：探索一次，目标板块星数按0计算，不可选魔王；若翻出深渊，可改选其他区域。')
    add('marta_revised_white','玛尔塔','white',gold=47,gold_pro=16,initial_special='懒散生活',initial_steps=[dict(op='effect',effect=dict(civ=1))],points=3,
        upgrade2=dict(gold_pro=3,tags=['civ']),
        upgrade3=dict(strength=1,pot=1,steps=[dict(op='screenshot_lazy_finish')]),
        description='开局文明增加1，将专属事件“懒散生活”加入手牌。二级：金币产能增加3，获得生活标记。三级：获得1力量和1秘药；收回“懒散生活”上的冒险者，每枚获得15金币及1张事件；将本卡翻至背面，文明后退3。')
    add('marta_revised_black','玛尔塔','black',gold=37,gold_pro=16,strength=2,points=3,
        ability=steps(dict(op='screenshot_explore',point_discount=10,hole_retry=True)),
        upgrade2=dict(str_pro=1,tags=['scrap']),
        upgrade3=steps(dict(op='screenshot_build',max=2,optional=True)),
        description='特别行动：探索一次；选择名声2以下区域的迷宫板块时，金币费用减少10，最低10。若翻出深渊，可改选其他区域。二级：力量产能增加1，获得零件标记。三级：可将至多2个名声2以下的支配区域据点化，无需追加费用。')
    for suffix,reward,draw in [('revised',8,3),('five',5,3)]:
        add('horn_%s_white'%suffix,'霍伦','white',gold=30,gold_pro=20,draw=draw,points=3,
            screenshot_sets=reward,
            upgrade2=dict(draw=4,steps=[dict(op='discard_gain',min=3,max=3,per=0)]),
            upgrade3=steps(dict(op='screenshot_tag_money')),
            description='每凑齐一组生活、商业、零件标记，获得%s金币。二级：抽4张事件，弃3张手牌。三级：获得等于生活、商业、零件标记总数的金币，最多30。'%reward)
    # These two red prints differ in their reward and are separate choices.
    ns['CHARACTERS']['horn_five']['name']='霍伦（收藏家5金币版）'
    add('horn_revised_black','霍伦','black',gold=30,gold_pro=20,points=3,
        ability=steps(dict(op='play_facedown',min=1,max=1,effect=dict(str_pro=1))),
        initial_steps=[dict(op='screenshot_horn_start')],
        upgrade2=dict(draw=2,tags=['scrap']),upgrade3=steps(dict(op='screenshot_horn_flip',optional=True)),
        description='特别行动：将1张事件手牌背面放入自己的场上，力量产能增加1。开局另从4张事件中选1张免费加入手牌（也可购买其余）。二级：抽2张事件，获得零件标记。三级：可将自己场上1张背面事件翻开并打出，金币费用减少10，额外费用及前置条件仍需支付。')
    lazy=card(303,'懒散生活',7,special=True,printed_code='Z-003',gold_pro=2,civ=1,
              image_path='supplied/lazy_life.webp',source='supplied/lazy_life.webp',
              action=steps(dict(op='screenshot_lazy_develop')),
              description='特别行动：支付5＋当前文明值的金币，解锁一个尚未解锁的发展格，把对应冒险者放在本卡上；然后文明增加1。')
    ns['CARDS'][303]=lazy;ns['CARD_GALLERY'][303]=dict(lazy,category='project')
    # Official expansion book p17: Elu reverse is replaced by Pieria reverse.
    ns['HEROES']['elu_red_b']['solo_replacement']='peria_black'
    ns['HEROES']['elu_red_b']['description']='每季起始玩家行动前，先执行一个主要行动。单人按日文扩展规则书第17页改用皮耶利亚背面（含初始资产及升级），选角时显示替换卡面。二级：力量产能1、抽1牌、零件标记1。三级：可弃手牌，每张3金币，再执行一次主要行动。'
    for key in ('shion_white','shion_red'):
        ns['HEROES'][key]['name']='紫苑'
    ns['CHARACTERS']['shion']['name']='紫苑'
