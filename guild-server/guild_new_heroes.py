"""Chinese transcriptions of TTS character sheets 143/144, ten paired heroes."""
from guild_new_content import atlas, asset

def install(ns):
    # The supplied revised Chinese scans replace the older base-game art.
    positions = {
        'elu_reprint':(186,1),'elu_red_b':(185,1),'ayaka_revised':(186,2),'ayaka_red_b':(185,2),
        'skadi_white':(186,3),'skadi_red':(185,3),'siren_red':(185,4),'melissa_red':(185,5),
        'peria_white':(186,6),'ruby_white':(188,0),'shion_white':(188,1),'shion_red':(187,1),
        'alicia_white':(188,2),'alicia_red':(187,2),'hainie_white':(188,3),'hainie_red':(187,3),
        'sofia_white':(188,4),'sofia_red':(187,4),'bai_white':(188,5),'bai_red':(187,5),
        'misha_white':(188,6),'misha_red':(187,6),
    }
    for key,(sheet,row) in positions.items():
        definition=ns['HEROES'][key]
        order=(2,1,0) if definition['variant']=='black' else (0,1,2)
        sources=[atlas(sheet,row*3+col,3,7) for col in order]
        definition['source']=sources
        for number,source in zip(definition['images'],sources):
            ns['HERO_GALLERY'][number]['image_path']=source
    hero,card=ns['_hero'],ns['_card']
    def paired(key,character,name,sheet,row,variant,**values):
        indices=[row*3+i for i in ((2,1,0) if variant=='black' else (0,1,2))]
        sources=[atlas(sheet,i,3,7) for i in indices]
        numbers=[9000+sheet*30+i for i in indices]
        d=hero(name,'新版 / '+('黑版' if variant=='black' else '白版'),numbers,**values)
        d.update(source=sources,character=character,variant=variant,available=True,requires_dlc=[])
        ns['HEROES'][key]=ns['HERO_ARCHIVE'][key]=d
        ns['CHARACTERS'][character]['variants'][variant]=key
        for level,(number,source) in enumerate(zip(numbers,sources),1):
            ns['HERO_GALLERY'][number]=dict(d,id=number,hero=key,level=level,image_path=source)
    paired('siren_white','siren','赛莲',186,4,'white',gold=28,gold_pro=22,points=4,
        first_steps=[dict(op='play',discount=20,optional=True)],
        ability=dict(steps=[dict(op='siren_discount')]),
        upgrade2=dict(gold_pro=3,tags=['scrap']),upgrade3=dict(steps=[dict(op='refresh_actions')]),
        description='首次行动前，可满足条件打出一张事件卡，金币费用减20。特别行动：打出一张事件，可减少0至5金币产能，每减少1产能抵2金币。二级：金币产能+3、零件标记+1。三级：可移除至多两张卡（含本角色）的已使用标记。')
    paired('melissa_white','melissa','梅莉莎',186,5,'white',gold=33,gold_pro=20,draw=4,points=3,
        upgrade2=dict(gold_pro=3,strength=1,draw=1,tags=['gold']),upgrade3=dict(steps=[dict(op='melissa_reveal_play')]),
        description='每当已打出的事件总数达到4的倍数，获得1秘药。二级：金币产能+3、力量+1、抽1牌、商业标记+1。三级：公开牌库顶两张事件，选择一张无视全部打出费用与条件打出，另一张弃置。')
    paired('ruby_black','ruby','莎菲亚',187,0,'black',gold=33,gold_pro=20,strength=3,points=4,
        ability=dict(steps=[dict(op='ruby_explore')]),upgrade2=dict(gold_pro=2,str_pro=1,tags=['character']),
        upgrade3=dict(steps=[dict(op='replace',concealed=True,optional=True),dict(op='replace',concealed=True,optional=True)]),
        description='特别行动：探索一次；复活祭坛上有数字标记（撤退计数大于0）时，金币费用减10，最低10；遇到洞穴可额外行动。二级：金币产能+2、力量产能+1、人物标记+1。三级：可将至多两个未公开的非魔王板块替换为空白板块。')
    paired('peria_black','peria','皮耶利亚',185,6,'black',gold=34,gold_pro=20,draw=2,points=6,
        upgrade2=dict(str_pro=1),description='第一年春季生产时，金币、力量、秘药的产能按两倍结算，然后失去20金币。二级：力量产能+1。')
    # The white print is the tutorial fairy. Keep the character ID stable for
    # existing rooms, but expose its familiar name in every selection pool.
    ns['CHARACTERS']['peria']['pool_name']='教学妖精 / 皮耶利亚'
    ns['CHARACTERS']['ruby']['name']='露比 / 莎菲亚'
    special=card(302,'圣女的遗痕',8,kind='action',str_pro=1,pot=1,point=1,special=True,
        action=dict(steps=[dict(op='purify',optional=True),dict(op='flip',self=True)]),
        image_path=atlas(27,28,7,5),source=atlas(27,28,7,5),printed_code='Z-002')
    ns['CARDS'][302]=special;ns['CARD_GALLERY'][302]=dict(special,category='project')
    def H(key,name,index,portrait,**kw):
        black=key.endswith('_black'); sheet=144 if black else 143
        indices=[index+10,index+5,index] if black else [index,index+5,index+10]
        sources=[atlas(sheet,i,5,6) for i in indices]
        d=hero(name,'新版 / '+('黑版' if black else '白版'),[3000+sheet*30+i for i in indices],**kw)
        character=key.split('_')[0]
        d.update(source=sources,portrait=asset(portrait),available=True,character=character,variant='black' if black else 'white',requires_dlc=[])
        ns['HEROES'][key]=d;ns['HERO_ARCHIVE'][key]=d
        ns['CHARACTERS'].setdefault(character,dict(id=character,name=name,variants={}))['variants'][d['variant']]=key
        for level,num in enumerate(d['images'],1):
            ns['HERO_GALLERY'][num]=dict(d,id=num,hero=key,level=level,image_path=sources[level-1])
    def steps(*ops):return dict(steps=list(ops))
    def scaled(resource,stat,multiplier=1,per=1,cap=1000):return dict(scaled=[dict(resource=resource,stat=stat,multiplier=multiplier,per=per,max=cap)])
    H('vee_white','薇伊',0,165,gold=46,gold_pro=20,draw=2,tags=['civ'],points=4,
      upgrade2=dict(gold_pro=3,draw=1),upgrade3=dict(gold=10,draw=2),
      description='正常打出非人物、声望非负的事件卡时，可支付双倍金币及额外费用，将打出效果结算两次；标记与永久能力只触发一次，翻面则不再结算第二次。')
    H('olivia_white','奥莉维亚',1,163,gold=30,gold_pro=18,points=3,upgrade2=dict(gold_pro=3),
      upgrade3=scaled('gold','gold_pro',per=3),description='事件卡的打出效果每增加1金币产能，同时获得1金币。')
    H('chris_white','克莉丝',2,161,gold=32,gold_pro=20,points=3,
      ability=scaled('gold','tag:civ',2,cap=12),upgrade2=dict(gold_pro=3),upgrade3=scaled('strength','tag:civ',per=2,cap=6),
      description='特别行动：每个生活标记获得2金币，最多12金币。三级：每两个生活标记获得1力量，最多6力量。')
    H('shuri_white','舒莉',3,159,gold=40,gold_pro=20,private_deck=10,points=3,
      upgrade2=dict(gold_pro=3,tags=['gold']),upgrade3=scaled('strength','tag:gold',per=2,cap=6),
      description='初始暗置10张专用牌；每获得一个商业标记，从专用牌组抽1张。三级：每两个商业标记获得1力量，最多6力量。')
    H('macaron_white','玛卡洛吉',4,157,gold=48,gold_pro=20,points=4,initial_special='圣女的遗痕',
      upgrade2=dict(gold_pro=3,tags=['gold'],steps=[dict(op='reveal',count=2)]),upgrade3=steps(dict(op='restore_cards',max=2)),
      description='任何公会公开深渊洞穴时，获得3金币，包含开局公开。三级：可将自己最多两张背面事件翻回正面，不结算打出效果。')
    H('sif_white','希芙',15,155,gold=38,gold_pro=20,draw=1,points=3,upgrade2=dict(gold_pro=3),upgrade3=steps(dict(op='repeat_card')),
      description='每打出一张有前置条件的事件卡，获得2金币。三级：选择自己的一张正面事件，再结算一次打出效果。')
    H('frida_white','芙莉达',16,153,gold=39,gold_pro=23,points=4,ability=steps(dict(op='draw_to_three')),
      upgrade2=dict(gold_pro=2,pot=1,tags=['gold']),upgrade3=dict(pot=1,draw=3),
      description='特别行动：将手牌补至3张，每补1张获得2金币。')
    H('bell_white','蓓儿',17,151,gold=35,gold_pro=18,strength=1,private_deck=5,points=4,
      upgrade2=dict(gold_pro=3,steps=[dict(op='all',effect=dict(strength=1))]),upgrade3=dict(gold=5,steps=[dict(op='extra_action')]),
      description='初始暗置5张专用牌；每打出印刷费用个位数为0或5的事件（含10、15、20等），获得2金币并从专用牌抽1张。')
    H('horn_white','霍伦',18,149,gold=37,gold_pro=22,draw=2,points=4,upgrade2=dict(gold_pro=3,draw=1),
      upgrade3=steps(dict(op='all_tags_gold')),description='每获得任意一个标记，获得1金币。三级：每个标记获得1金币。')
    H('marta_white','玛尔塔',19,147,gold=48,gold_pro=20,draw=2,points=3,initial_development='territory',
      upgrade2=dict(gold=5,tags=['civ']),upgrade3=dict(strength=1,scaled=[dict(resource='strength',stat='played',per=3,multiplier=1,max=6)]),
      description='初始免费解锁领地发展格；升至三级以前不能探索。三级获得1力量，另每三张已打出事件获得1力量，最多额外6力量。')
    H('vee_black','薇伊',0,166,gold=33,gold_pro=18,str_pro=1,strength=2,tags=['scrap'],points=4,
      ability=steps(dict(op='vee_build')),upgrade2=dict(str_pro=1,strength=1),upgrade3=steps(dict(op='restore_cards',max=2,strength_each=1)),
      description='特别行动：据点基础费用15金币，每个零件标记减3，最低0；相邻追加费照付。三级：翻回最多两张背面事件，每张获得1力量。')
    H('olivia_black','奥莉维亚',1,164,gold=33,gold_pro=18,str_pro=1,strength=2,points=3,special_adventurer=True,
      upgrade2=dict(str_pro=1,steps=[dict(op='recall_attached')]),upgrade3=dict(strength=2,steps=[dict(op='explore',retry_hole=True,optional=True)]),
      description='控制区域首次达到1、3、5、7时各获得1秘药。拥有一名专用冒险者供卡牌安置。二级收回卡牌上的冒险者；三级力量+2并可探索，遇洞穴可换目标。')
    H('chris_black','克莉丝',2,162,gold=38,gold_pro=20,str_pro=1,strength=2,points=3,
      upgrade2=dict(str_pro=1,steps=[dict(op='peek',count=2)]),upgrade3=dict(strength=2,steps=[dict(op='swap_tiles')]),
      description='探索背面板块前，可与一块已公开的非洞穴、非魔王板块交换。三级：力量+2，可交换两个非洞穴、非魔王板块的位置。')
    H('shuri_black','舒莉',3,160,gold=34,gold_pro=17,str_pro=1,strength=1,draw=1,points=3,
      ability=steps(dict(op='hero_sacrifice_play')),upgrade2=dict(str_pro=1,draw=1,tags=['scrap']),upgrade3=dict(strength=2,draw=1,steps=[dict(op='supply')]),
      description='特别行动：支付1力量与1迷宫板块，免金币打出费用不超过14的事件，额外费用照付。')
    H('macaron_black','玛卡洛吉',4,158,gold=32,gold_pro=17,str_pro=1,strength=1,points=3,first_steps=[dict(op='reveal',count=2)],
      upgrade2=dict(str_pro=1,steps=[dict(op='reveal',count=2)]),upgrade3=steps(dict(op='consume_tiles',min=0,max=2,per=dict(gold=5)),dict(op='effect',effect=dict(draw=1))),
      description='首次行动前公开两块迷宫。每次探索每降低1瘴气，金币与金币产能各+1（每个行动上限3）。三级：可支付最多两块迷宫，各获5金币，然后抽1张牌。')
    H('sif_black','希芙',15,156,gold=26,gold_pro=15,str_pro=2,strength=3,points=3,
      ability=steps(dict(op='hero_tile_discount_play')),upgrade2=dict(str_pro=1,draw=1,tags=['civ']),
      upgrade3=steps(dict(op='branch',options=[dict(label='免费建设据点（追加费照付）',effect=steps(dict(op='build',free=True))),dict(label='力量+3',effect=dict(strength=3))])),
      description='特别行动：打出一张事件，每个持有板块减3金币，最多减15。')
    H('frida_black','芙莉达',16,154,gold=33,gold_pro=20,strength=1,points=3,
      upgrade2=dict(str_pro=2,gold_pro=-4),upgrade3=scaled('gold','str_pro',2),
      description='每增加1力量产能，获得3金币（含升级）。三级：获得力量产能两倍的金币。')
    H('bell_black','蓓儿',17,152,gold=28,gold_pro=18,str_pro=1,strength=2,points=3,
      ability=steps(dict(op='hero_attach_tile')),upgrade2=dict(str_pro=1,steps=[dict(op='all',effect=dict(strength=1))]),upgrade3=scaled('gold','controlled',3),
      description='特别行动：将一块持有板块放在本角色上，获得8金币；若是洞穴，再获1力量。放置后仍计入持有数量，但不能再支付。')
    H('horn_black','霍伦',18,150,gold=34,gold_pro=20,str_pro=1,strength=2,points=4,
      upgrade2=dict(str_pro=1,pot=1,tags=['scrap']),upgrade3=steps(dict(op='play_extra_gold')),
      description='支付费用时，秘药与持有迷宫板块可等量互相替代。三级：打出一张有额外费用的事件，再获得5金币。')
    H('marta_black','玛尔塔',19,148,gold=34,gold_pro=18,str_pro=1,strength=1,points=4,
      upgrade2=dict(str_pro=1),upgrade3=dict(strength=1,steps=[dict(op='return_played')]),
      description='每打出只有人物标记或没有标记的事件，获得3金币。三级：力量+1，可收回自己一张事件到手牌，包含背面事件。')
