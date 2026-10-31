"""Optional event packs, keyed by their physical sheet rather than titles."""
from guild_new_content import atlas

CITY_CARDS=[76,74,75,204,202,72,73,205,203,196,195,194,97,95,197,99,100,98,
            211,213,209,210,207,208,212,214,193,206,189,190,186,188,187,185,183,184,182,180,181]

def install(ns):
    for cid in CITY_CARDS:ns['CARDS'][cid]['expansion']='city_events'
    card=ns['_card']
    def E(i,name,price,**kw):
        source=atlas(128,i,7,3)
        data=card(320+i,name,price,expansion='festival_events',image_path=source,source=source,**kw)
        ns['CARDS'][320+i]=data;ns['CARD_GALLERY'][320+i]=dict(data,category='project')
    E(0,'S级冒险者队伍·勇敢行者',19,costs=dict(gold_pro=5),str_pro=3,strength=3,
      steps=[dict(op='peek',count=2),dict(op='explore',optional=True)])
    E(1,'与运输公会的合作',14,costs=dict(gold_pro=3),requirements=dict(tags=dict(gold=2)),tags=['civ','gold'],
      steps=[dict(op='play',free=True,filter=dict(price_max=14)),dict(op='play',free=True,filter=dict(price_max=14))])
    E(2,'巨兽贝希摩斯的觉醒',20,requirements=dict(civ=5),tags=['civ'],can_trans=True,str_pro=2,strength=3,point=4,
      steps=[dict(op='all',effect=dict(strength=2)),dict(op='downgrade_base',optional=True,otherwise=dict(steps=[dict(op='flip',self=True)]))])
    E(3,'讨伐矿石兽',15,tags=['gold','scrap'],can_trans=True,gold_pro=5,point=1,steps=[dict(op='all',effect=dict(gold=5))])
    E(4,'侵占救援物资',1,pot=1,point=-3,steps=[dict(op='supply')])
    E(5,'方舟遗迹',12,requirements=dict(pieces=4),tags=['civ','scrap'],gold_pro=4,civ=1,point=2,
      scaled=[dict(resource='gold',stat='tag:scrap',multiplier=3)])
    E(6,'意外邂逅',5,requirements=dict(tags=dict(character=1)),tags=['civ'],draw=2,
      steps=[dict(op='if',condition=dict(stat='tag:character',min=2),effect=dict(strength=2))])
    E(7,'魔兽的生态调查',20,can_trans=True,str_pro=1,point=2,
      steps=[dict(op='reveal',count=2),dict(op='all',effect=dict(strength=1,draw=1))])
    E(8,'开发魔法炉',4,consume_piece=1,tags=['civ','scrap'],gold_pro=3,civ=1)
    E(11,'加蕾特建筑公司',16,requirements=dict(tags=dict(civ=2)),gold_pro=4,strength=1,draw=1,point=1,
      kind='passive',build_surcharge_discount=5)
    E(13,'积分卡',7,tags=['gold'],gold_pro=2,kind='passive',zero_five_gold=True)
    E(15,'精灵的居住园地',5,requirements=dict(any=[dict(tags=dict(civ=2)),dict(holes=1)]),costs=dict(pot=2),tags=['civ'],
      gold_pro=3,str_pro=1,strength=2,point=3,scoring=[dict(stat='holes',per=1,point=1)])
    E(16,'魔力工业联合体',14,requirements=dict(any=[dict(gold_pro=35),dict(pieces=2)]),consume_piece=1,tags=['scrap'],
      gold_pro=5,pot=1,civ=1,point=1,scoring=[dict(stat='gold_pro',threshold=30,point=2),dict(stat='pieces',threshold=6,point=2)],steps=[dict(op='purify')])
    E(17,'情报贩子琪修',16,requirements=dict(cards=4),tags=['gold','character'],gold_pro=4,draw=1,point=1,
      scoring=[dict(stat='permanent_cards',per=2,point=1)])


    E(9,'恶魔羽毛笔',9,requirements=dict(any=[dict(tags=dict(civ=3)),dict(tags=dict(gold=3))]),tags=['civ','gold'],
      steps=[dict(op='pen_reveal_use')])
    E(10,'迷宫时钟',2,consume_piece=1,requirements=dict(pieces=4),tags=['scrap'],gold_pro=3,civ=1,point=2,
      steps=[dict(op='branch',options=[
        dict(label='再执行一次行动（选择探索时必要成本-10）',
             effect=dict(steps=[dict(op='extra_action',explore_discount=10)])),
        dict(label='Pass：获得10金币，本季无法再行动',
             effect=dict(gold=10,steps=[dict(op='pass_out')]))])])
    E(12,'能量饮料 Bring Feather',9,kind='passive',costs=dict(pot=1),str_pro=1,strength=1,tags=['civ'],
      point=0,final_bonus=dict(gold=10,action=1),steps=[])
    E(14,'Phrase百货',25,requirements=dict(tags=dict(gold=2,civ=2,scrap=2)),consume_piece=1,tags=['gold'],
      gold_pro=7,str_pro=1,draw=1,civ=1,point=0,scoring=[dict(stat='best_event_point',per=1,point=1)])
    E(18,'剑圣阿兹姬',11,costs=dict(gold_pro=3),requirements=dict(pieces=2),tags=['character'],str_pro=2,
      point=2,steps=[dict(op='explore',hole_claim=True)])
