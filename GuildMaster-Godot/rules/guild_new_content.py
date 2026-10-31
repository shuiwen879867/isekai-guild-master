"""Additional physical components. Chinese text follows supplied TTS scans.

Atlas references are Ren'Py image names registered by expansion_screens.rpy;
the headless server needs only these JSON-serializable definitions.
"""
import json
from pathlib import Path

ASSETS = json.loads(Path(__file__).with_name('guild_asset_manifest.json').read_text(encoding='utf-8'))
ATLAS = {}
QUESTS = {}
PROLOGUES = {}

def asset(number):
    return ASSETS[str(number)]['path']

def atlas(number,index,cols,rows,box=None):
    name='tts_%s_%s'%(number,index)
    entry=ASSETS.get(str(number))
    if entry is None:
        return name
    w,h=entry['size']
    if box is None:
        x,y=index%cols,index//cols
        box=(int(x*w/cols),int(y*h/rows),int((x+1)*w/cols)-int(x*w/cols),int((y+1)*h/rows)-int(y*h/rows))
    ATLAS[name]=dict(path=asset(number),box=box)
    return name

def install(namespace):
    tiles=namespace['TILES']; achievements=namespace['ACHIEVEMENTS']
    namespace['POTIONS'].update({
        'alchemy_gem':dict(name='炼金宝石',cost=1,effect=dict(gold=2,steps=[dict(op='gain_gem')]),description='金币+2，获得一枚宝石；宝石值2声望，可随时售卖3金币。'),
        'alchemy_card':dict(name='炼金召唤',cost=2,effect=dict(steps=[dict(op='play',free=True,filter=dict(price_max=14))]),description='免金币打出费用不超过14的手牌；额外费用照付。'),
        'alchemy_scout':dict(name='炼金侦察',cost=2,effect=dict(strength=3,steps=[dict(op='peek')]),description='力量+3，查看一块迷宫，可选择公开。'),
        'alchemy_build':dict(name='炼金筑城',cost=3,effect=dict(steps=[dict(op='build',free=True,no_surcharge=True)]),description='免费建设一座据点，免相邻追加费用。'),
        'alchemy_draw':dict(name='炼金情报',cost=1,effect=dict(draw=2),description='抽取2张事件卡。'),
    })
    def tile(key,image,star,point=0,**kw):
        d=dict(tiles['tile8'],name=kw.pop('name','变动迷宫'),image=1000+image,
               star=star,point=point,tags=[],source=asset(image),default_star=2,
               treasure=False,ishole=False,variable=True,draw=0,pot=0,strength=0)
        d.update(kw); tiles[key]=d
    values=[(68,3,3,dict(steps=[dict(op='replace',concealed=True,variable=True)])),
        (69,2,1,dict(draw=2)),(70,2,1,dict(pot=1)),(71,3,2,dict(pot=1)),
        (72,3,2,dict(draw=2)),(73,2,1,dict(draw=1,tags=['scrap'])),
        (74,3,1,dict(treasure=True)),(75,3,2,dict(tags=['scrap','scrap'])),
        (76,2,0,dict(treasure=True)),(77,3,2,dict(tags=['scrap'],draw=1)),
        (78,2,1,dict(tags=['scrap','scrap'])),(79,0,2,dict(ishole=True)),
        (80,3,2,dict(strength=2)),(81,2,2,{}),(82,2,1,dict(strength=1))]
    for image,stars,points,kw in values: tile('variable%s'%image,image,stars,points,**kw)
    for back,front,image,points in [(2,4,258,3),(4,7,240,6)]:
        # Printed fronts: 2→4, 3→5, 4→7 stars.
        tile('boss%s'%back,image,front,points,name='魔王',variable=False,boss=True,default_star=back)
    tiles['boss'].update(boss=True)
    tiles['blocked']=dict(tiles['tile21'],name='禁止进入',star=1,source=asset(63),image=1063,blocked=True)
    solo_names=[['生活方式革命','皇室专用认证','异世界传送门建造完成','本日公会大获成功','日落时分的婚礼钟声','编撰大迷宫史'],
                ['供水及污水管道建设','大迷宫商会','无限延伸的铁路','勇者凯旋','战友之誓','讨伐宇宙外魔王']]
    # Coordinates of the six printed cards, excluding the mercenary panel.
    for hard in (False,True):
        image=217 if hard else 216; w,h=ASSETS[str(image)]['size']
        for i,name in enumerate(solo_names[int(hard)]):
            col,row=i%3,i//3
            crop=(int(w*(.054+col*.244)),int(h*(.06+row*.456)),int(w*.214),int(h*.422))
            source=atlas(image,i,3,2,crop)
            stat=['tag:civ','tag:gold','tag:scrap','controlled','affection',None][i]
            req={} if stat is None else {'stat':stat,'value':4 if hard else 5}
            effect={'gold_pro':4,'draw':2} if hard else dict(gold_pro=4)
            if not hard:
                if i<2: effect['civ']=3
                if i in (2,3): effect.update(draw=2,civ=1)
                if i==4: effect['draw']=2
            if i==5: effect={'civ':3 if hard else 2}
            aid='solo_%s_%s'%('hard' if hard else 'normal',i)
            d=dict(name=name,price=40 if i==5 else 10,point=([1,1,1,3,3,5] if hard else [3,3,3,3,4,8])[i],
                image=2000+int(hard)*6+i,source=source,verified=True,available=True,requirement={},requirements=req,
                description=('支付时可用力量折抵金币；' if hard and i==5 else '')+('需%s达到%s'%({'tag:civ':'生活标记','tag:gold':'商业标记','tag:scrap':'零件标记','controlled':'控制区域','affection':'好感度'}[stat],req.get('value')) if stat else '无前置条件'),
                effect=effect,solo=True,can_trans=hard and i==5)
            if hard and i<3: d['scoring']=[dict(stat=stat,per=2,point=1)]
            achievements[aid]=d
    quest_labels=['商业2＋生活2','商业2＋零件2','生活2＋零件2','商业3','生活3','零件3','人物1','三种标记各1','好感度5',
        '在1分区域建设据点','据点1＋持有板块2','力量4','秘药2','控制区域5','控制区域3','控制3分区域1',
        '手牌6','相邻其他公会区域3','永久效果事件3','所有公会均可达成','文明条件为5的事件1','消耗金币产能的事件2',
        '可用力量支付的事件1','完成王权1','三星以上板块1','有声望板块2','没有待命冒险者','消耗板块的事件1','费用15以上事件3','无标记事件2']
    # 委托卡面：贡献小卡.png（7×5，第5列仅2张任务卡）；格位↔条件对照（2026-10 实体卡校对）。
    QUEST_CELLS = {0: 19, 1: 13, 2: 15, 3: 18, 4: 12, 5: 14, 6: 16, 7: 17, 8: 27, 9: 21,
                   10: 23, 11: 25, 12: 20, 13: 22, 14: 24, 15: 26, 16: 5, 17: 29, 18: 2,
                   19: 3, 20: 28, 21: 0, 22: 1, 23: 4, 24: 6, 25: 8, 26: 10, 27: 7, 28: 9, 29: 11}
    for i, label in enumerate(quest_labels):
        cell = QUEST_CELLS[i]
        x, y = cell % 7, cell // 7
        box = (int(x * 8360 / 7), int(y * 3848 / 5),
               int((x + 1) * 8360 / 7) - int(x * 8360 / 7),
               int((y + 1) * 3848 / 5) - int(y * 3848 / 5))
        QUESTS[i] = dict(id=i, name=label, source=atlas(5, i, 6, 5, box=box))

    def story(i,name,effect,tags=(),image=42,index=None):
        PROLOGUES[i]=dict(id=i,name=name,effect=effect,tags=list(tags),source=atlas(image,i if index is None else index,5 if image==42 else 2,3))
    story(0,'闯入不可思议的图书馆',dict(gold=8,steps=[dict(op='story_library')]))
    story(1,'故事编织者',dict(gold=3,strength=1,draw=1,draw_achievement=1))
    story(2,'废品堆放场的居民',dict(strength=2,draw=1),['scrap'])
    story(3,'捡到弃猫的少女',dict(gold=5,steps=[dict(op='develop',exclude=['gold'])]))
    story(4,'女王的奇思妙想',dict(str_pro=1,strength=2,steps=[dict(op='all',effect=dict(strength=1))]))
    story(5,'莫名其妙地开始',dict(gold=5,steps=[dict(op='play',ignore_non_tag_requirements=True)]))
    story(6,'降落于森林妖精村庄',dict(gold=8,steps=[dict(op='draw_select',count=5,keep=1)]),['civ'])
    story(8,'行商人的得意门生',dict(gold_pro=2,gold=8),['gold'])
    story(9,'公会的继任者',dict(gold_pro=4,gold=5),['civ'])
    story(10,'与勇者相遇',dict(str_pro=1,gold=8,steps=[dict(op='peek',count=2,optional=True)]))
    story(12,'冒险家公会的优惠政策',dict(gold_pro=2,gold=10,steps=[dict(op='all',effect=dict(gold=5))]))
    story(13,'佣兵团杂工',dict(str_pro=2,gold=6,gold_pro=-2))
    story(15,'药师的侍从',dict(pot_pro=1,gold=7),image=44,index=0)
    story(16,'有勇无谋的迷宫之行',dict(strength=2,steps=[dict(op='reveal',count=2,optional=True),dict(op='explore',discount=5,optional=True)]),image=44,index=1)
    story(17,'锻造屋的见习生',dict(strength=1,gold=7),['civ','gold'],44,2)
    story(18,'把锄头换成剑',dict(gold=5,draw=1,steps=[dict(op='discard_gain',min=0,max=2,resource='strength',per=1,optional=True)]),image=44,index=3)
    story(19,'抢先召唤',dict(steps=[dict(op='play',free=True,filter=dict(price_max=14))]),image=44,index=4)
    story(20,'口袋里的计算机',dict(gold=7),['gold','scrap'],44,5)
