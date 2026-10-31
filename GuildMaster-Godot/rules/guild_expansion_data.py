"""Full-scan expansion transcriptions for the ordered resolution engine.

Each entry is keyed by the original art file, not an invented card number.
Interactive effects use ordered steps so draws and hidden information can be
resolved before the next choice, rather than asking for blind pre-selections.
"""

HERO_SPECS = [
    dict(key="misha_white", name="米夏", subtitle="不请自来的少女 / 白版", images=[9,8,7],
         gold=34, gold_pro=20, points=2,
         triggers=[dict(event="play", condition={"price_min":15}, effect={"gold":2,"gold_pro":2})],
         upgrade2={"gold_pro":1,"pot":1},
         upgrade3={"steps":[{"op":"branch","options":[{"label":"取得一个宝物","effect":{"steps":[{"op":"treasure"}]}},{"label":"抽取三张事件卡","effect":{"draw":3}}]}]},
         description="打出印刷成本至少15的事件卡时，获得2金币、金币产能+2。二级：金币产能+1、秘药+1。三级：选择获得一个宝物或抽3张牌。"),
    dict(key="sofia_white", name="索菲亚", subtitle="无主的女仆 / 白版", images=[12,11,10],
         gold=36, gold_pro=21, draw=1, points=3,
         triggers=[dict(event="tag", condition={"tag":"civ"}, effect={"gold":3})],
         upgrade2={"gold_pro":3,"tags":["civ"]},
         upgrade3={"steps":[{"op":"play","discount":10,"optional":True}]},
         description="每获得一个生活标记，获得3金币。二级：金币产能+3、生活标记+1（触发奖励）。三级：立即打出一张事件卡，减免10金币。"),
    dict(key="shion_white", name="诗音", subtitle="异世界研究者 / 白版", images=[15,14,13],
         gold=30, gold_pro=15, pot=1, pot_pro=1, points=3,
         ability={"steps":[{"op":"potion","ignore_slot":True}]},
         upgrade2={"gold_pro":3,"tags":["gold"]}, upgrade3={"pot":2},
         description="每季特别行动：支付正常费用使用一次秘药格，允许选择已使用或被人数限制的格子。二级：金币产能+3、商业标记+1。三级：秘药+2。"),
    dict(key="alicia_white", name="艾莉西亚", subtitle="商人学徒 / 白版", images=[18,17,16],
         gold=38, gold_pro=21, points=3,
         triggers=[dict(event="tag", condition={"tag":"gold"}, effect={"gold":3})],
         upgrade2={"gold_pro":3,"tags":["gold"]},
         upgrade3={"gold":5,"scaled":[{"resource":"gold","stat":"civ","multiplier":1}]},
         description="每获得一个商业标记，获得3金币。二级：金币产能+3、商业标记+1（触发奖励）。三级：获得文明值+5的金币。"),
    dict(key="ayaka_white", name="绫香", subtitle="纠缠不清的青梅竹马 / 白版", images=[21,20,19],
         gold=30, gold_pro=21, wisdom=1, points=3,
         ability={"steps":[{"op":"play","discount":5,"ignore_extra":True,"costs":{"wisdom":1}}]},
         upgrade2={"gold_pro":3,"wisdom":1,"tags":["civ"]},
         upgrade3={"draw":1,"wisdom":1,"draw_achievement":1},
         description="每季特别行动：支付1睿智，打出一张事件卡，金币费用-5并免除其他额外成本。仍须满足出牌条件。二级：金币产能+3、睿智+1、生活标记+1。三级：抽1牌、睿智+1、抽1王权。"),
]

HERO_SPECS.extend([
    dict(key="elu_white",name="艾露",subtitle="无家可归系女子 / 初版",images=[24,23,22],
         gold=40,gold_pro=18,draw=1,points=3,
         triggers=[dict(event="play",condition={"has_point":True},effect={"gold":2})],
         upgrade2={"gold_pro":3},upgrade3={"steps":[{"op":"reveal_draw","count":5,"keep_filter":{"has_point":True}}]},
         description="打出带有声望标记的事件卡时获得2金币。二级：金币产能+3。三级：公开牌库顶5张，带声望标记的加入手牌，其余弃置。"),
    dict(key="skadi_white",name="丝卡迪",subtitle="威武的佣兵团女团长 / 白版",images=[27,26,25],
         gold=0,gold_pro=4,strength=5,str_pro=3,points=3,
         passive={"strength_as_gold":True,"initial_research_free":True,"initial_research_limit":4},
         upgrade2={"str_pro":1},upgrade3={"strength":3},
         description="支付金币时随时可用1力量抵5金币，多余部分不找零。开局最多免费保留4张情报，不能另购。二级：力量产能+1。三级：力量+3。"),
    dict(key="ruby_white",name="露比",subtitle="双胞胎之一 / 白版",images=[30,29,28],
         gold=50,gold_pro=17,points=3,
         ability={"steps":[{"op":"play","discount_stats":["affection","tag:character"]}]},
         upgrade2={"gold_pro":3,"tags":["character"]},
         upgrade3={"scaled":[{"resource":"pot","stat":"tag:character","multiplier":1}]},
         description="每季特别行动：打出一张事件卡，减免好感度与人物标记合计数量的金币。二级：金币产能+3、人物标记+1。三级：每个人物标记获得1秘药。"),
    # P-037a: the printed 30G tutorial grant is reduced by 10G in normal play.
    dict(key="peria_white",name="皮耶利亚",subtitle="教学妖精 / 白版",images=[33,32,31],
         gold=20,gold_pro=18,str_pro=1,pot_pro=1,points=3,
         passive={"initial_research_free":True},upgrade2={"gold_pro":3},
         upgrade3={"gold":10,"steps":[{"op":"discard_draw","max":5,"optional":True}]},
         description="普通对局初始20金币（按卡面30金币减10），金币产能18、力量产能1、秘药产能1；起始8张情报全部免费。后续情报按正常费用购买。二级：金币产能+3。三级：获得10金币，可弃1至5张手牌并补抽等量牌，声望3。"),
    dict(key="peria_ex",name="皮耶利亚 EX",subtitle="教学妖精 / EX版",images=[36,35,34],
         gold=40,gold_pro=15,points=3,
         passive={"initial_research_free":True,"research_free":1},upgrade2={"gold_pro":3},
         upgrade3={"gold":10,"steps":[{"op":"discard_draw","max":5,"optional":True}]},
         description="初始8张情报全部免费；之后每季第一张保留情报免购买费。二级：金币产能+3。三级：获得10金币，可弃1至5张手牌并补抽等量牌。"),
])

def _hero_variant(source,key,images,subtitle,**changes):
    from copy import deepcopy
    result=deepcopy(next(h for h in HERO_SPECS if h['key']==source))
    result.update(key=key,images=images,subtitle=subtitle,**changes)
    HERO_SPECS.append(result)

_hero_variant("ayaka_white","ayaka_revised",[39,38,37],"青梅竹马 / 修订版",
              upgrade3={"draw":3,"wisdom":1,"draw_achievement":1},
              description="每季特别行动：支付1睿智，打出一张事件卡，金币费用-5并免除其他额外成本。二级：金币产能+3、睿智+1、生活标记+1。三级：抽3牌、睿智+1、抽1王权。")
_hero_variant("elu_white","elu_reprint",[42,41,40],"无家可归系女子 / 再版")

HERO_SPECS.extend([
    dict(key="ayaka_red",name="绫香",subtitle="长伴左右 / 红版初版",images=[46,47,48],
         gold=38,gold_pro=18,strength=1,str_pro=1,flash=1,points=3,
         passive={"flash_explore":True},upgrade2={"str_pro":1,"strength":1,"flash":1},
         upgrade3={"strength":1,"flash":1,"draw_achievement":1},
         description="探索付费前可支付1一闪，无视普通迷宫的星数（不包括BOSS）。二级：力量产能+1、力量+1、一闪+1。三级：力量+1、一闪+1、抽1王权。"),
    dict(key="elu_red",name="艾露",subtitle="终身职新娘 / 红版初版",images=[49,50,51],
         gold=38,gold_pro=17,strength=3,str_pro=1,points=3,
         passive={"season_first_extra":True},upgrade2={"str_pro":1,"tags":["scrap"]},
         upgrade3={"steps":[{"op":"discard_gain","max":5,"resource":"gold","per":3,"optional":True},{"op":"extra_action"}]},
         description="每季自己的第一个行动结束后，执行一个额外行动。二级：力量产能+1、零件标记+1。三级：可弃1至5牌，每张获得3金币，然后执行额外行动。"),
    dict(key="skadi_red",name="丝卡迪",subtitle="公会的冲锋队长 / 红版",images=[52,53,54],
         gold=34,gold_pro=20,strength=1,points=2,initial_special="丝卡迪的佣兵团",
         upgrade2={"tags":["gold"],"steps":[{"op":"return_special","name":"丝卡迪的佣兵团"}]},
         upgrade3={"steps":[{"op":"return_special","name":"丝卡迪的佣兵团"},{"op":"extra_action"}]},
         description="开局获得专属事件卡「丝卡迪的佣兵团」。二级：商业标记+1，已打出的专属卡回手。三级：已打出的专属卡回手，再执行一个额外行动。"),
])
_hero_variant("ayaka_red","ayaka_red_b",[55,56,57],"长伴左右 / 红版B",points=4,
              upgrade3={"strength":1,"flash":1},
              description="探索付费前可支付1一闪，无视非BOSS迷宫星数。二级：力量产能+1、力量+1、一闪+1。三级：力量+1、一闪+1，声望4。")
_hero_variant("elu_red","elu_red_b",[58,59,60],"终身职新娘 / 红版B",
              strength=2,passive={},triggers=[dict(event="explore",effect={"draw":1})],
              upgrade3={"steps":[{"op":"discard_gain","max":5,"resource":"gold","per":3,"optional":True}]},
              description="每次探索成功抽1事件卡。二级：力量产能+1、零件标记+1。三级：可弃1至5张手牌，每张获得3金币。")

HERO_SPECS.extend([
    dict(key="melissa_red",name="梅莉莎",subtitle="订下契约的恶魔 / 红版",images=[64,65,66],
         gold=30,gold_pro=20,strength=2,str_pro=1,points=3,
         passive={"claim_holes":True},initial_steps=[{"op":"replace_hole","region":1}],
         upgrade2={"str_pro":1,"draw":1,"steps":[{"op":"supply","tile":"tile14"}]},
         upgrade3={"steps":[{"op":"supply","variable":True}]},
         description="可将深渊洞穴视为普通迷宫付费探索并获得。首次行动前将声望1区域的一格替换为供应堆洞穴。二级：力量产能+1、抽1牌、获得供应堆洞穴。三级：随机获得一个变动板块及资源，不减瘴气。"),
    dict(key="siren_red",name="赛莲",subtitle="不再流浪的贤者 / 红版",images=[67,68,69],
         gold=32,gold_pro=20,strength=1,points=2,initial_steps=[{"op":"lab_move"}],
         ability={"steps":[{"op":"lab_move"}],"max_level":2},
         passive={"lab":True},upgrade2={"str_pro":1,"tags":["civ"]},
         upgrade3={"steps":[{"op":"lab_recall"}]},
         description="开局把浮空实验室放在地图外缘外侧，视为据点；一二级每季可移动它一次。二级：力量产能+1、生活标记+1。三级：实验室收回角色卡，之后探索成功可用它代替冒险者，直接成为据点，不需额外费用或冒险者。"),
    dict(key="misha_red",name="米夏",subtitle="世界第一可爱美少女 / 红版",images=[79,80,81],
         gold=42,gold_pro=20,strength=1,points=3,initial_steps=[{"op":"supply"}],
         upgrade2={"str_pro":2,"gold_pro":-2,"tags":["civ"]},upgrade3={},
         passive={"final_extra_level":3},
         description="开局获得一个普通迷宫板块。二级：力量产能+2、金币产能-2、生活标记+1。三级：结束阶段终了时执行一个额外行动。"),
    dict(key="sofia_red",name="索菲亚",subtitle="忠诚的追随者 / 红版",images=[82,83,84],
         gold=34,gold_pro=20,strength=2,points=3,passive={"own_base_no_surcharge":True},
         triggers=[dict(event="build",effect={"gold":5})],upgrade2={"str_pro":1},
         upgrade3={"strength":1,"scaled":[{"resource":"gold","stat":"bases","multiplier":5}]},
         description="每次据点化后获得5金币；自己的相邻据点不增加建设费用。二级：力量产能+1。三级：力量+1，每个自己的据点获得5金币。"),
])

EVENT_SPECS = {
    6: dict(name="地精洞穴", price=15, can_trans=True, gold_pro=3, point=1,
            steps=[{"op":"supply"},{"op":"all","effect":{"gold_pro":2}}]),
}

def E(number, name, price, **values):
    EVENT_SPECS[number] = dict(name=name, price=price, **values)

E(11,"负离子产生器",13,tags=["civ","scrap"],requirements={"tags":{"scrap":1}},pot=2,civ=1,steps=[{"op":"purify"}])
E(15,"异世界杂货铺",15,tags=["gold","scrap"],requirements={"pieces":1},gold_pro=5,civ=1,
  steps=[{"op":"attach_adventurer","optional":True,"effect":{"gold":10,"scaled":[{"resource":"gold","stat":"tag:gold","multiplier":1}]}}])
E(16,"异世界时尚表演",18,requirements={"tags":{"scrap":2}},gold_pro=5,affection=1,civ=1,point=1)
E(18,"八卦欧巴桑协会",5,tags=["civ"],gold_pro=2,steps=[{"op":"discard_draw","max":5,"optional":True}])
E(19,"最前线魔物研究所",13,costs={"pot":1},pot_pro=1,civ=1,steps=[{"op":"build","free":True}])
E(20,"死灵王的大军势",30,can_trans=True,pot=3,point=2,steps=[{"op":"all","effect":{"pot":1}}])
E(23,"悬赏怪物通缉令",9,tags=["gold"],gold_pro=2,pot=1,steps=[{"op":"reveal","count":2}])
E(25,"新型马车开发",16,tags=["civ","gold"],requirements={"tags":{"scrap":2}},civ=1,point=2,
  scaled=[{"resource":"gold","stat":"tag:civ","multiplier":2},{"resource":"gold","stat":"tag:gold","multiplier":2}])
E(26,"新人训练制度",7,str_pro=1,steps=[{"op":"attach_adventurer","optional":True,"effect":{"strength":3}}])
E(27,"深红甲壳城堡",8,consume_piece=1,gold_pro=2,steps=[{"op":"build","free":True,"reveal_neighbors":True}])
E(29,"王室女仆部队",17,tags=["civ"],requirements={"any":[{"tags":{"civ":2}},{"tags":{"character":1}}]},gold_pro=3,point=1,
  steps=[{"op":"branch","options":[{"label":"据点化","effect":{"steps":[{"op":"build","free":True}]}},{"label":"普通迷宫板块与力量产能","effect":{"str_pro":1,"steps":[{"op":"supply"}]}}]}])
E(30,"机械大门",9,tags=["scrap"],requirements={"any":[{"tags":{"scrap":3}},{"pieces":4}]},civ=1,steps=[{"op":"treasure"}])
E(31,"宫殿舞会",22,tags=["gold"],requirements={"cards":4},gold_pro=4,point=1,
  steps=[{"op":"branch","options":[{"label":"解放好感度","effect":{"affection":1}},{"label":"人物卡费用减20","effect":{"steps":[{"op":"play","discount":20,"filter":{"tag":"character"}}]}}]}])
E(32,"极彩爆裂炮弹",8,tags=["scrap"],requirements={"tags":{"scrap":2}},point=1,
  steps=[{"op":"branch","options":[{"label":"替换支配区域相邻迷宫，可再探索一次","effect":{"steps":[{"op":"replace","adjacent_own":True},{"op":"explore","optional":True}]}},{"label":"按已出事件卡获得金币","effect":{"scaled":[{"resource":"gold","stat":"played","multiplier":1}]}}]}])
E(34,"富商的邀请函",15,tags=["gold"],requirements={"cards":4},gold_pro=5,point=2,
  steps=[{"op":"if","condition":{"stat":"tag:gold","max":3},"effect":{"gold":5,"pot":1,"steps":[{"op":"flip","self":True}]}}])
E(35,"连接朱红色大门之路",10,requirements={"pieces":2},gold_pro=3,pot=1,
  steps=[{"op":"purify"},{"op":"consume_tiles","min":1,"max":3,"per":{"gold":5,"draw":1}}])
E(36,"精灵栖息之泉",10,gold_pro=2,pot=1,
  steps=[{"op":"consume_tiles","min":1,"max":1,"optional":True,"per":{"pot":1}},{"op":"discard_gain","min":2,"max":2,"optional":True,"effect":{"pot":1}}])
E(38,"研究人造深渊",13,requirements={"pieces":1},costs={"gold_pro":2},pot_pro=1,civ=1,point=-1,
  steps=[{"op":"supply","tile":"tile14"}])
E(41,"占卜师的帐篷",15,tags=["gold"],gold_pro=3,steps=[{"op":"reveal_draw","count":1,"tag_potions":True}])

def trigger(event, effect, **condition):
    return dict(event=event, effect=effect, condition=condition)

E(46,"简易式露天澡堂",14,kind="passive",tags=["civ"],gold_pro=2,point=1,triggers=[trigger("affection",{"gold":3})])
E(47,"迷宫攻略RTA",3,kind="passive",tags=["gold"],costs={"gold_pro":2},
  passive={"explore_revealed_discount":5},steps=[{"op":"reveal","count":2},{"op":"explore","optional":True,"hole_extra":False}])
E(48,"有效活用迷宫瘴气",16,kind="passive",gold_pro=4,civ=1,point=1,
  triggers=[trigger("gain_tile",{"gold":5},hole=True)],steps=[{"op":"purify"}])
E(49,"A级冒险者队伍－龙坠少女",23,kind="passive",costs={"gold_pro":2},str_pro=2,strength=2,
  passive={"explore_stars_discount":{"min":3,"discount":10}})
E(50,"B级冒险者队伍－狼群军团",15,kind="passive",costs={"gold_pro":3},str_pro=1,strength=2,
  passive={"explore_region_discount":{"region":1,"discount":5}})
E(51,"公会的不协调搭档",24,kind="passive",tags=["civ"],gold_pro=3,str_pro=1,triggers=[trigger("upgrade",{"strength":2})])
E(52,"A级冒险者队伍－暗影中的人们",14,kind="passive",costs={"gold_pro":6},str_pro=2,strength=4,
  passive={"discard_explore_loot_strength":2})
E(53,"完美默契",8,kind="passive",requirements={"heart":3},gold_pro=2,point=1,
  triggers=[trigger("achievement",{"gold":5})],steps=[{"op":"extra_action"}])
E(54,"马宿的聚会",9,kind="passive",gold_pro=2,triggers=[trigger("tag",{"gold":2},tag="gold")],
  steps=[{"op":"pay_effect","costs":{"gold":10},"effect":{"steps":[{"op":"supply"}]}}])
E(57,"水晶墓碑",13,kind="action",requirements={"bases":1},point=1,steps=[{"op":"supply"}],
  action={"costs":{"strength":1},"pot":1})
E(58,"异世界技术",13,kind="action",gold_pro=3,draw=1,
  action={"steps":[{"op":"consume_tiles","min":1,"max":1,"scrap_bonus":{"gold":5},"per":{"gold":5,"scaled":[{"resource":"gold","stat":"tag:gold","multiplier":1}]}}]})
E(59,"异世界电台",5,kind="action",tags=["scrap"],requirements={"pieces":1},draw=1,civ=1,
  action={"steps":[{"op":"discard_draw","min":1,"max":5,"bonus":1},{"op":"flip","self":True}]})
E(61,"古代魔像墓地",25,kind="action",tags=["scrap"],can_trans=True,str_pro=2,civ=1,point=2,
  steps=[{"op":"all","effect":{"strength":1}}],action={"steps":[{"op":"peek","count":1}]})
E(62,"与矿山精灵斗酒",12,kind="action",tags=["civ"],gold_pro=2,
  action={"costs":{"gold":5},"steps":[{"op":"build","free":True},{"op":"flip","self":True}]})
E(63,"蒸馏酒",18,kind="action",tags=["civ","gold"],requirements={"tags":{"scrap":2}},civ=1,point=2,
  action={"costs":{"pot":1},"gold":8,"scaled":[{"resource":"gold","stat":"tag:gold","multiplier":1}]})
E(64,"异世界食堂",14,kind="passive",tags=["gold"],requirements={"tags":{"scrap":1}},gold_pro=2,pot=1,point=1,
  scoring=[{"stat":"attached:self","per":1,"point":2}],steps=[{"op":"attach_adventurer","optional":True}])
E(66,"圣女亲卫队",7,kind="passive",tags=["gold"],costs={"gold_pro":2},str_pro=1,
  scoring=[{"stat":"holes","per":1,"point":1}],steps=[{"op":"purify"}])
E(67,"迷宫开拓村",25,kind="passive",tags=["civ"],requirements={"tags":{"civ":4}},can_trans=True,point=2,
  scoring=[{"stat":"attached:self","per":1,"point":2}],steps=[{"op":"attach_adventurer","max":2,"optional":True},{"op":"all","effect":{"gold":10}}])
E(68,"吟游诗人的叙事歌",2,kind="passive",draw=2,scoring=[{"stat":"minimum_tags","per":1,"point":1}],
  steps=[{"op":"pay_effect","costs":{"gold":10},"otherwise":{"steps":[{"op":"flip","self":True}]}}])
E(69,"设立冒险者学校",16,kind="passive",costs={"gold_pro":3},requirements={"any":[{"civ":5},{"heart":3}]},str_pro=2,draw=1,civ=1,
  scoring=[{"stat":"tiles","per":2,"point":1}],scaled=[{"resource":"gold","stat":"untagged","multiplier":3}])
E(70,"迷宫祕宝馆",11,kind="passive",tags=["gold"],requirements={"any":[{"tags":{"scrap":3}},{"cards":8}]},gold_pro=6,civ=1,point=1,
  scoring=[{"stat":"tag:scrap","threshold":5,"point":2},{"stat":"played","threshold":15,"point":2}])
E(71,"流浪商队",12,kind="passive",tags=["gold"],requirements={"any":[{"tags":{"gold":3}},{"tags":{"character":1}}]},gold_pro=3,pot=1,draw=1,point=1,
  scoring=[{"stat":"tag:character","threshold":5,"point":2},{"stat":"tag:gold","threshold":5,"point":2}])
E(73,"骑士公主的进击",12,kind="passive",tags=["civ"],requirements={"bases":1},gold_pro=2,draw=1,
  scoring=[{"stat":"bases","per":1,"point":1}],steps=[{"op":"build","free":True,"adjacent_base":True}])
E(74,"圣女的宠爱",10,kind="passive",tags=["gold"],requirements={"tags":{"gold":1}},gold_pro=2,draw=1,
  scoring=[{"stat":"holes","per":1,"point":1}],steps=[{"op":"purify"}])
E(77,"异世界来的饼干",14,kind="action",tags=["character"],gold_pro=3,pot=1,point=1,
  action={"gold":5,"scaled":[{"resource":"gold","stat":"civ","multiplier":1}],"steps":[{"op":"pass_left"}]})
E(79,"骑士公主加娜玖",18,kind="passive",tags=["character"],consume_piece=1,costs={"pot":1},gold_pro=2,str_pro=2,point=1,scoring=[{"stat":"bases","per":1,"point":1}])
E(80,"球体关节少女",10,kind="passive",tags=["scrap","scrap","character"],requirements={"bases":1},str_pro=1,
  scoring=[{"stat":"tag:scrap","per":2,"point":1}],steps=[{"op":"discard_draw","max":5,"optional":True}])
E(81,"人狼女王",30,kind="passive",tags=["character"],can_trans=True,str_pro=3,point=2,
  scoring=[{"stat":"strength","per":3,"point":1,"max":5}],steps=[{"op":"all","effect":{"strength":1}}])
E(82,"圣女玛卡洛吉",25,kind="passive",tags=["gold","character"],requirements={"civ":5},costs={"gold_pro":8},pot=5,point=1,
  scoring=[{"stat":"holes","per":1,"point":2}],steps=[{"op":"purify"}])
E(84,"大法师赛尔泽",22,tags=["character"],consume_piece=3,steps=[{"op":"build","free":True,"no_surcharge":True},{"op":"build","free":True,"no_surcharge":True}])
E(85,"传说商人芙蕾兹",18,kind="passive",tags=["gold","character"],requirements={"tags":{"gold":3}},gold_pro=7,point=1,
  scoring=[{"stat":"tag:gold","per":2,"point":1}],steps=[{"op":"discard_gain","max":5,"resource":"gold","per":3,"optional":True}])
E(86,"勇者罗萨特",18,kind="passive",tags=["character"],requirements={"pieces":2},costs={"gold_pro":4},str_pro=2,strength=2,point=1,
  scoring=[{"stat":"tiles","per":2,"point":1}])
E(87,"流浪魔女欧佩拉",20,kind="passive",tags=["character"],requirements={"tags":{"gold":2,"civ":2}},costs={"gold_pro":3},pot_pro=2,pot=2,point=1,
  scoring=[{"stat":"pot","per":2,"point":1,"max":5}])
E(88,"鬼神盖拉妮",20,tags=["character"],can_trans=True,str_pro=2,point=3,
  steps=[{"op":"all","effect":{"str_pro":1}},{"op":"pay_effect","costs":{"pot":1},"otherwise":{"steps":[{"op":"flip","self":True}]}}])
E(89,"见习召唤师杏美",10,tags=["civ","character"],consume_piece=1,str_pro=1,pot=1,
  steps=[{"op":"consumed_bonus","stars_resource":"strength","hole_bonus":{"gold":10}}])
E(90,"图书馆员普拉莉涅",9,kind="action",tags=["scrap","character"],requirements={"pieces":3},pot=1,draw=1,point=2,
  action={"steps":[{"op":"play_facedown","count":1,"effect":{"gold_pro":1}}]})
E(91,"精灵巫女阿梅蕾塔",19,kind="passive",tags=["character"],requirements={"any":[{"tags":{"scrap":2}},{"holes":1}]},str_pro=2,pot=1,point=2,
  scoring=[{"stat":"holes","per":1,"point":1}])
E(92,"大栋梁加蕾特",18,kind="passive",tags=["civ","character"],requirements={"any":[{"tags":{"civ":3}},{"bases":1}]},str_pro=1,point=1,
  scoring=[{"stat":"bases","threshold":3,"point":2},{"stat":"tag:civ","threshold":5,"point":2}],steps=[{"op":"build","free":True}])
E(93,"天眼的玛德莲",20,kind="passive",tags=["scrap","character"],requirements={"tags":{"gold":1,"scrap":1},"pieces":1},str_pro=1,strength=1,pot=1,point=2,
  passive={"explore_point_discount":5})
E(94,"伟大治疗师希芬",16,tags=["civ","gold","character"],requirements={"tags":{"gold":3}},gold_pro=3,pot_pro=1,point=2,
  steps=[{"op":"flip","min":1,"max":2}])
E(95,"史莱姆女王的强袭",25,tags=["gold","character"],requirements={"pieces":2},can_trans=True,pot_pro=1,pot=1,point=2,
  steps=[{"op":"all","effect":{"pot":1}},{"op":"potion","preserve_slot":True}])
E(96,"毛绒绒乐园开放",40,tags=["gold","gold","character"],consume_piece=2,point=6,
  scaled=[{"resource":"gold","stat":"gold_pro","multiplier":1,"offset":-20,"min":0}],
  steps=[{"op":"if","condition":{"discounted":True},"effect":{"steps":[{"op":"flip","self":True}]}}])
E(97,"花之妖精爱克莉亚",15,kind="passive",tags=["civ","character"],costs={"gold_pro":2},affection=1,
  scoring=[{"stat":"controlled","per":2,"point":1}])
E(98,"吸血皇女古蕾伊兹",17,kind="passive",tags=["character"],requirements={"tags":{"civ":1,"gold":1},"pieces":1},costs={"gold_pro":2},str_pro=2,strength=1,point=2,
  passive={"tiles_as_strength":True})
E(99,"诅咒的狐妖封印",18,kind="passive",tags=["character"],requirements={"pieces":1},gold_pro=4,point=6,
  scoring=[{"stat":"tiles","per":1,"point":-1}],steps=[{"op":"supply"}])
E(100,"真・龙坠少女",23,kind="passive",tags=["character","character"],requirements={"untagged":3},costs={"gold_pro":4},str_pro=5,point=1,
  scoring=[{"stat":"strong_tiles","per":1,"point":1},{"stat":"boss_tiles","per":1,"point":3}])
E(101,"丝卡迪的佣兵团",7,kind="passive",special=True,costs={"gold_pro":2},str_pro=1,strength=1,
  scaled=[{"resource":"strength","stat":"controlled","multiplier":1}],scoring=[{"stat":"controlled","per":2,"point":1}],
  steps=[{"op":"explore","optional":True}])
E(102,"苍银大要塞",22,civ=1,point=1,scaled=[{"resource":"gold","stat":"tag:scrap","multiplier":5,"max":25}],
  steps=[{"op":"build","free":True}])
E(103,"完美默契",8,kind="passive",requirements={"heart":3},gold_pro=2,point=1,triggers=[trigger("achievement",{"gold":3})])
E(104,"老旧投影机",16,kind="passive",tags=["gold","scrap"],requirements={"tags":{"gold":4}},consume_piece=2,gold_pro=4,draw=2,civ=1,
  scoring=[{"stat":"played","per":3,"point":1,"max":6}])
E(105,"异世界来的饼干",14,kind="action",tags=["character"],gold_pro=3,pot=1,point=1,
  action={"gold":5,"scaled":[{"resource":"gold","stat":"civ","multiplier":1}],"steps":[{"op":"flip","self":True}]})
E(106,"大贤者椒盐脆饼",13,kind="action",tags=["scrap","character"],requirements={"tags":{"scrap":3}},costs={"gold_pro":5},point=3,
  action={"costs":{"pot":1},"scaled":[{"resource":"strength","stat":"tag:scrap","multiplier":1,"max":5}]})
E(107,"恶魔的低语",0,requirements={"pieces":3},point=5,
  steps=[{"op":"replace","concealed":True,"variable":True},{"op":"supply","tile":"tile14"},{"op":"pay_effect","costs":{"gold":40},"can_trans":True,"otherwise":{"steps":[{"op":"flip","self":True}]}}])
E(108,"连接朱红色大门之路",10,requirements={"pieces":2},gold_pro=3,pot=1,
  steps=[{"op":"purify","variable":True},{"op":"consume_tiles","min":1,"max":3,"per":{"gold":5,"draw":1}}])
E(109,"研究人造深渊",13,requirements={"pieces":1},costs={"gold_pro":2},pot_pro=1,civ=1,point=-1,
  steps=[{"op":"replace","concealed":True,"variable":True},{"op":"supply","tile":"tile14"}])
E(110,"深渊炮",15,tags=["scrap"],requirements={"bases":1},consume_piece=1,strength=5,pot=1,point=-1,
  steps=[{"op":"replace","adjacent_base":True,"tile":"tile14"}])
E(111,"迷宫核试验场",11,requirements={"tags":{"civ":1,"gold":1,"scrap":1}},gold_pro=4,str_pro=1,draw=1,civ=1,
  steps=[{"op":"purify","variable":True}])
E(112,"迷宫大变动",10,requirements={"pieces":1},can_trans=True,draw=2,point=1,
  steps=[{"op":"replace","concealed":True,"variable":True},{"op":"reveal","count":3},{"op":"all","effect":{"strength":1}}])
E(113,"鬼神盖拉妮",20,tags=["character"],can_trans=True,str_pro=2,point=3,
  steps=[{"op":"replace","concealed":True,"variable":True},{"op":"all","effect":{"str_pro":1}},{"op":"pay_effect","costs":{"pot":1},"otherwise":{"steps":[{"op":"flip","self":True}]}}])
E(114,"精灵巫女阿梅蕾塔",19,kind="passive",tags=["character"],requirements={"any":[{"tags":{"scrap":2}},{"holes":1}]},str_pro=2,pot=1,point=1,
  scoring=[{"stat":"holes_or_variable","per":1,"point":1}],steps=[{"op":"replace","concealed":True,"variable":True}])
E(115,"盗贼工会合作社",11,kind="action",tags=["gold"],gold_pro=3,strength=1,
  action={"costs":{"gold":2},"steps":[{"op":"peek","count":2}]})
E(116,"飞龙快递",16,kind="action",tags=["civ","gold"],requirements={"tags":{"civ":3}},gold_pro=5,strength=1,civ=1,point=1,
  action={"costs":{"gold":5},"min_players":2,"steps":[{"op":"extra_action","count":2}]})
E(117,"绝症",0,kind="action",costs={"gold_pro":1},affection=1,point=-3,
  action={"costs":{"pot":3},"steps":[{"op":"flip","self":True}]})
E(119,"迷宫要塞三勇士",8,kind="action",requirements={"bases":1},str_pro=1,strength=1,
  action={"steps":[{"op":"downgrade_base","effect":{"strength":3}},{"op":"flip","self":True}]})
E(120,"老练的拆解工匠",16,kind="action",tags=["gold"],gold_pro=2,pot=1,
  action={"steps":[{"op":"consume_tiles","min":1,"max":1,"per":{"gold":5,"scaled":[{"resource":"gold","stat":"tag:gold","multiplier":1}]}}]})
E(121,"惊喜派对",11,kind="action",tags=["civ"],gold_pro=3,
  action={"steps":[{"op":"consume_tiles","min":2,"max":2,"effect":{"affection":1}},{"op":"flip","self":True}]})
E(122,"死亡界线的阅兵式",15,kind="action",requirements={"any":[{"pieces":3},{"holes":1}]},costs={"gold_pro":4},pot_pro=1,pot=1,
  steps=[{"op":"reveal","count":2}],action={"steps":[{"op":"explore","potion_strength":2}]})
E(123,"裂隙图书馆",20,kind="action",tags=["civ","gold","scrap"],requirements={"pieces":2},gold_pro=5,draw=1,civ=1,point=2,
  action={"steps":[{"op":"play_facedown","count":1,"effect":{"gold_pro":1}}]})
E(124,"那一天的誓言",12,kind="passive",tags=["civ"],gold_pro=5,draw=2,point=-2,
  triggers=[trigger("achievement",{"steps":[{"op":"flip","self":True}]},achievement_total=2)])
E(125,"公会仓库大扫除",2,kind="passive",tags=["civ","gold","scrap"],
  triggers=[trigger("play",{"steps":[{"op":"flip","self":True}]},not_self=True)])
E(126,"眼镜探寻者",10,kind="passive",costs={"gold_pro":2},str_pro=1,pot=1,
  conditional_tags={"condition":{"stat":"tiles","min":2},"tags":["gold","scrap"]})
E(127,"A级冒险者队伍－毛茸茸天堂",18,kind="passive",costs={"gold_pro":2},str_pro=1,strength=2,pot=1,
  triggers=[trigger("gain_tile",{"gold":2})])
E(128,"异世界甜点开发",10,kind="passive",tags=["gold"],gold_pro=2,civ=1,point=1,triggers=[trigger("tag",{"gold":5},tag="character")])
E(129,"异世界技术分析团队",10,kind="passive",pot=1,point=1,triggers=[trigger("tag",{"gold":2},tag="scrap")])
E(130,"命中注定的相遇",4,kind="passive",draw=3,point=-2,triggers=[trigger("tag",{"steps":[{"op":"flip","self":True}]},tag="character")])
E(131,"A级冒险者队伍－飞天三傻",12,kind="passive",costs={"gold_pro":3},str_pro=1,strength=2,passive={"claim_holes":True})
E(132,"消费合作社",13,kind="passive",tags=["gold"],gold_pro=2,point=1,triggers=[trigger("tag",{"gold":2},tag="civ")])

ROYAL_SPECS = {
    150: dict(name="圣女的信赖",point=3,stat="holes",value=1,description="持有至少一个深渊洞穴板块。"),
    152: dict(name="编撰大迷宫史",point=3,stat="controlled",value=5,description="控制区域至少5。"),
    153: dict(name="搜寻技术系统化",point=4,stat="untagged",value=4,description="打出至少4张没有任何标记的事件卡，背面卡不计。"),
    154: dict(name="日落时分的婚礼钟声",point=4,stat="earned_achievements",value=1,requirements={"heart":5},
              description="好感度至少5，且已完成至少1张其他王权卡。"),
}

E(157,"被遗忘的女神像",11,tags=["character"],gold_pro=2,pot=1,draw=1,point=3,
  steps=[{"op":"if","condition":{"not":{"any":[{"stat":"tiles","min":6},{"stat":"holes","min":2}]}},"effect":{"steps":[{"op":"flip","self":True}]}}])
E(158,"与法师公会的合作",19,tags=["civ"],str_pro=1,pot=1,point=1,steps=[{"op":"supply"}])
E(159,"魔法石进口",5,requirements={"tags":{"gold":2}},gold_pro=3,steps=[{"op":"supply"}])
E(160,"法师城堡极光",9,consume_piece=1,steps=[{"op":"build","free":True},{"op":"explore","optional":True,"hole_extra":False}])
E(161,"魔法通信网路",16,tags=["scrap"],requirements={"civ":5},consume_piece=1,gold_pro=2,civ=1,point=1,
  steps=[{"op":"play","free":True}])
E(162,"魅惑的美乃滋",16,tags=["civ","gold"],requirements={"heart":1},gold_pro=4,pot=1,civ=1,point=1,
  steps=[{"op":"branch","optional":True,"options":[{"label":"翻面并获得1秘药","effect":{"pot":1,"steps":[{"op":"flip","self":True}]}}]}])
E(163,"研究无咏唱魔法",13,consume_piece=1,str_pro=1,strength=3,steps=[{"op":"consumed_bonus","star_min":2,"effect":{"strength":1}}])
E(164,"史莱姆的过度增生",20,can_trans=True,gold_pro=2,pot=1,draw=1,point=2,
  steps=[{"op":"supply"},{"op":"all","effect":{"pot":1}}])
E(165,"史莱姆化妆品工作坊",13,tags=["gold"],costs={"gold_pro":3},pot_pro=1,civ=1,
  steps=[{"op":"consume_tiles","min":1,"max":1,"per":{"gold_pro":3}}])
E(166,"和平缔造者",11,tags=["scrap"],costs={"pot":1},str_pro=1,strength=2,point=1,steps=[{"op":"purify"},{"op":"extra_action"}])
E(167,"格洛利亚娜旅馆",25,tags=["civ","gold"],requirements={"any":[{"tags":{"civ":4}},{"tags":{"gold":4}}]},gold_pro=10,civ=1,point=4,
  steps=[{"op":"reveal_draw","count":5,"keep_filter":{"any_tag":["civ","gold"]}}])
E(169,"看门人米陶诺",15,requirements={"pieces":2},can_trans=True,point=1,steps=[{"op":"build","free":True},{"op":"all","effect":{"draw":1}}])
E(171,"恶魔的低语",0,requirements={"pieces":3},point=5,
  steps=[{"op":"supply","tile":"tile14"},{"op":"pay_effect","costs":{"gold":40},"can_trans":True,"otherwise":{"steps":[{"op":"flip","self":True}]}}])
E(172,"异世界人的踪迹",16,requirements={"cards":8},pot=2,point=2,scaled=[{"resource":"gold","stat":"maximum_tags","multiplier":2}])
E(174,"迷宫核试验场",11,requirements={"tags":{"civ":1,"gold":1,"scrap":1}},gold_pro=4,str_pro=1,draw=1,civ=1,steps=[{"op":"purify"}])
E(175,"迷宫清洁机器人",12,tags=["scrap"],requirements={"pieces":1},str_pro=1,point=1,steps=[{"op":"reveal","count":2},{"op":"purify"}])
E(176,"迷宫横町",4,tags=["civ"],costs={"gold_pro":1},draw=1,point=-2,steps=[{"op":"build","free":True,"no_surcharge":True}])
E(177,"迷宫大变动",10,requirements={"pieces":1},can_trans=True,draw=2,point=1,steps=[{"op":"reveal","count":3},{"op":"all","effect":{"strength":1}}])
E(179,"B级冒险者队伍－猫头鹰之眼",12,costs={"gold_pro":2},str_pro=1,strength=2,steps=[{"op":"peek","count":2}])
E(180,"那女孩的亲手料理",14,tags=["civ"],requirements={"heart":1},point=1,steps=[{"op":"reveal_draw","count":1,"tag_affection":True}])
E(181,"公会总部的大改造",22,tags=["civ"],requirements={"tags":{"civ":3}},gold_pro=4,point=2,
  scaled=[{"resource":"gold","stat":"played","multiplier":1},{"resource":"strength","stat":"tag:character","multiplier":1}])
E(182,"炸药派对",11,costs={"gold_pro":1},str_pro=1,strength=2,
  steps=[{"op":"branch","optional":True,"options":[{"label":"复活祭坛增加2，获得3力量","effect":{"retreat":2,"strength":3}}]}])
E(183,"制服芬里尔",30,can_trans=True,str_pro=2,point=4,steps=[{"op":"all","effect":{"gold":10}}])
E(184,"异世界图片故事工作坊",8,tags=["civ","gold","scrap"],gold_pro=3,civ=1,point=1,
  steps=[{"op":"attach_adventurer","optional":True,"otherwise":{"steps":[{"op":"flip","self":True}]}}])
E(186,"终极净化魔法仪式",5,requirements={"civ":5},consume_piece=1,costs={"pot":1},point=1,
  steps=[{"op":"claim_replace","hole_bonus":{"gold":10},"variable_flip":True}])
E(188,"拿到了被诅咒的武器",13,tags=["scrap"],gold_pro=3,strength=2,point=-1,steps=[{"op":"flip","self":True,"optional":True}])
E(191,"白墙之城与狭路天空",10,kind="passive",tags=["gold"],gold_pro=2,strength=1,
  triggers=[trigger("civ",{"gold":3},origin="card")])
E(192,"迷宫监视塔",13,kind="passive",requirements={"bases":1},gold_pro=2,strength=2,passive={"explore_adjacent_base_discount":5})
E(193,"弹力伸缩桌",15,kind="passive",costs={"gold_pro":2},scoring=[{"stat":"counters:self","per":1,"point":1,"max":10}],
  triggers=[trigger("tag",{"steps":[{"op":"counter","count":1}]},any_tag=["civ","character"],origin="card")],
  steps=[{"op":"if","condition":{"round":1},"effect":{"gold":5}}])
E(194,"贵族赞助者",14,kind="passive",tags=["gold"],gold_pro=2,point=1,triggers=[trigger("play",{"gold":3},price_min=15)])
E(195,"大法师的奇思妙想",15,kind="passive",gold_pro=2,draw=1,triggers=[trigger("consume_tile",{"gold":3})],steps=[{"op":"supply"}])
E(196,"迷宫的七大不可思议",14,kind="passive",gold_pro=2,str_pro=1,draw=1,point=-2,
  steps=[{"op":"if","condition":{"stat":"controlled","min":7},"effect":{"steps":[{"op":"flip","self":True}]}}],
  triggers=[trigger("explore",{"gold":2,"steps":[{"op":"if","condition":{"stat":"controlled","min":7},"effect":{"steps":[{"op":"flip","self":True}]}}]})])
E(197,"发现迷宫电梯",9,kind="passive",tags=["scrap"],requirements={"pieces":1},gold_pro=2,global_passive={"remote_region":2,"remote_discount":10})
E(198,"迷宫珠宝商",24,kind="action",tags=["gold"],requirements={"tags":{"gold":2,"scrap":2}},pot=1,civ=1,point=3,
  action={"steps":[{"op":"consume_tiles","min":1,"max":1,"costs":{"pot":1},"per":{"gold":12,"scaled":[{"resource":"gold","stat":"tag:gold","multiplier":1}]}}]})
E(199,"与隐密的一族交流",9,kind="action",tags=["civ"],costs={"pot":1},str_pro=1,strength=1,draw=1,
  action={"steps":[{"op":"peek","count":1},{"op":"extra_action"}]})
E(200,"捡到幻兽的幼崽",13,kind="action",scoring=[{"stat":"attached_tiles:self","per":1,"point":1}],
  action={"steps":[{"op":"attach_tile","effect":{"strength":1}}]})
E(201,"借钱度日",0,kind="action",tags=["civ"],gold=10,point=-3,action={"costs":{"gold":20},"steps":[{"op":"flip","self":True}]})
E(202,"伪装结婚",14,kind="action",tags=["civ"],gold_pro=2,affection=1,point=-2,
  action={"requirements":{"heart":5},"steps":[{"op":"flip","self":True}]})
E(203,"东方的锻刀匠",16,kind="action",tags=["gold"],str_pro=1,civ=1,
  action={"steps":[{"op":"consume_tiles","min":1,"max":1,"per":{"strength":2},"star_min":2,"star_bonus":{"strength":1}}]})
E(204,"迷宫导游",19,kind="action",tags=["gold"],civ=1,
  action={"steps":[{"op":"explore","on_success":{"gold":5,"scaled":[{"resource":"gold","stat":"tag:gold","multiplier":1}]}}]})
E(205,"迷宫地图制图师",11,kind="action",tags=["gold"],costs={"gold_pro":2},str_pro=1,strength=1,point=1,action={"steps":[{"op":"reveal","count":1}]})
E(207,"超合金刀刃",9,tags=["scrap"],requirements={"tags":{"scrap":2}},str_pro=1,
  scaled=[{"resource":"strength","stat":"str_pro","multiplier":1,"per":2,"max":5}])
E(208,"深渊兽大爆发",20,can_trans=True,gold_pro=2,str_pro=1,point=1,steps=[{"op":"purify"},{"op":"all","effect":{"strength":1}}])
E(209,"研究发酵魔法",22,tags=["civ","gold"],requirements={"tags":{"civ":2}},gold_pro=3,pot=1,civ=1,point=1,
  scaled=[{"resource":"gold","stat":"tag:civ","multiplier":3}])
E(211,"无名冒险者的墓地",10,tags=["civ"],gold_pro=2,point=1,steps=[{"op":"if","condition":{"stat":"available","max":0},"effect":{"gold":10}}])
E(212,"迷宫露天开采",16,requirements={"tags":{"gold":3}},gold_pro=5,pot=1,civ=1,point=1,steps=[{"op":"build","free":True},{"op":"supply"}])
E(213,"龙之血",8,requirements={"any":[{"tags":{"gold":4}},{"pieces":5}]},strength=3,point=3,steps=[{"op":"flip","min":1,"max":1}])
E(214,"徬徨亡灵战车",20,tags=["scrap"],can_trans=True,str_pro=1,strength=1,civ=1,point=2,steps=[{"op":"supply"},{"op":"all","effect":{"strength":1}}])
E(217,"创立迷宫品牌",20,tags=["gold","gold"],gold_pro=4,point=2,steps=[{"op":"discard_gain","min":1,"max":5,"optional":True,"resource":"gold","per":3}])
E(218,"欢迎来到迷宫酒馆！",13,tags=["gold"],requirements={"tags":{"gold":2}},gold_pro=4,steps=[{"op":"build","free":True}])
E(219,"迷宫魔草园开幕",9,tags=["gold"],requirements={"bases":1},pot_pro=1,civ=1,point=1)
E(220,"迷宫魔物的过度增生",10,can_trans=True,strength=1,steps=[{"op":"supply"},{"op":"all","effect":{"draw":1}}])
E(222,"瘴气温泉",19,tags=["gold"],requirements={"tags":{"scrap":1}},consume_piece=1,gold_pro=2,str_pro=1,steps=[{"op":"build","free":True},{"op":"purify"}])
E(223,"海妖巴尼克",9,str_pro=1,pot=1,steps=[{"op":"replace_hole","region":1}])
E(226,"圣女驾到",7,tags=["gold"],gold_pro=2,steps=[{"op":"purify"}])
E(227,"圣水的剩余库存",13,requirements={"tags":{"gold":2}},pot=2,steps=[{"op":"purify"}])
E(228,"苍银大要塞",22,civ=1,point=1,scaled=[{"resource":"gold","stat":"tag:scrap","multiplier":5,"max":25}],steps=[{"op":"build","free":True}])
E(233,"一夜城",3,requirements={"civ":5},point=-1,steps=[{"op":"build","free":True}])
E(234,"C级冒险者队伍－荣耀的黎明",4,tags=["civ"],costs={"gold_pro":2},str_pro=1,steps=[{"op":"peek","count":1},{"op":"explore","optional":True,"hole_extra":False}])
E(235,"开发永动装置",15,tags=["scrap"],requirements={"tags":{"scrap":4}},gold_pro=5,pot_pro=1,pot=1,civ=1,point=3,
  steps=[{"op":"purify"},{"op":"effect","effect":{"scaled":[{"resource":"gold","stat":"holes","multiplier":5}]}}])
E(236,"王族迷宫视察",15,gold_pro=3,strength=2,point=1,steps=[{"op":"reveal","count":2}])
E(238,"挖掘奇妙巨石",15,requirements={"pieces":2},gold_pro=4,pot=2,civ=1,steps=[{"op":"supply"}])
E(239,"强行探索",5,requirements={"civ":5},consume_piece=1,costs={"pot":1},steps=[{"op":"explore","discount":20,"optional":True,"hole_extra":False}])

HERO_SPECS.extend([
    dict(key="shion_red",name="诗音",subtitle="稀有的大学者 / 红版",images=[85,86,87],
         gold=27,gold_pro=17,strength=1,str_pro=1,points=3,
         triggers=[dict(event="gain_tile",effect={"gold":5})],upgrade2={"str_pro":1},
         upgrade3={"strength":2,"steps":[{"op":"supply"}]},
         description="每获得一个迷宫板块，获得5金币。二级：力量产能+1。三级：力量+2，从供应堆获得一个普通迷宫板块（也触发5金币）。"),
    dict(key="alicia_red",name="艾莉西亚",subtitle="迷宫商人 / 红版",images=[88,89,90],
         gold=40,gold_pro=18,strength=2,str_pro=1,points=3,
         passive={"explore_revealed_discount":5},
         ability={"steps":[{"op":"peek","count":1},{"op":"extra_action"}]},
         upgrade2={"str_pro":1,"tags":["scrap"]},upgrade3={"strength":2,"steps":[{"op":"extra_action"}]},
         description="探索此前已公开的迷宫时，金币费用减5。每季特别行动：查看一块非BOSS迷宫，可选择是否公开，然后执行额外行动。二级：力量产能+1、零件标记+1。三级：力量+2，再执行额外行动。"),
])
