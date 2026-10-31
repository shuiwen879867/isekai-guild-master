"""Optional boards: quests, prologues, scouts, forest, dragon, festival."""
from collections import deque
from copy import deepcopy
from guild_content import CARDS,TILES,POTIONS,HEROES
from guild_new_content import QUESTS,PROLOGUES

class OptionalBoards:
    def _setup_boards(self):
        s=self.state;opt=self.rules['options'];count=len(s['players'])
        s['quests']=[None]*(6 if count<=2 else 9);s['quest_deck']=list(QUESTS)
        self._shuffle(s['quest_deck'])
        stories=list(PROLOGUES);self._shuffle(stories)
        for p in s['players']:
            p['quest_offered']=[];p['prologue_offered']=[];p['prologue']=[]
            if opt['prologue']: p['prologue_offered']=[stories.pop(),stories.pop()]
        if opt['guild_board'] and opt['solo']:
            s['quest_deck']=[q for q in s['quest_deck'] if q not in (17,19)]
            s['quests']=[dict(card=s['quest_deck'].pop(),done=False) for _ in range(6)]
        allowed=[]
        if opt['alchemy']:
            allowed=['alchemy_gem','alchemy_card']
            if opt['solo'] or count==5: allowed.append('alchemy_scout')
            if not opt['solo']: allowed.append('alchemy_draw' if count==5 else 'alchemy_build')
        s['potions_disabled'] += [k for k in POTIONS if k.startswith('alchemy_') and k not in allowed]
        if opt['all_potions']:
            s['potions_disabled']=[] if opt['alchemy'] else [k for k in POTIONS if k.startswith('alchemy_')]

    def _on_pass(self,p):
        s=self.state;opt=self.rules['options'];i=s['players'].index(p)
        if i not in s['pass_order']:s['pass_order'].append(i)
        if opt['festival_preparation'] and s['festival_slots']:
            self._enqueue(p,[dict(op='festival_pick')])
        if opt['guild_board'] and not opt['solo'] and s['round']<=3 and s['phase']=='action' and any(q is None for q in s['quests']):
            order=len(s['pass_order'])-1
            count=([4,2] if len(s['players'])==2 else [4,3,2,0,0])[order]
            p['quest_offered']=[s['quest_deck'].pop() for _ in range(min(count,len(s['quest_deck'])))]

    def _quest_met(self,p,number):
        tags=self._tags(p);active=list(self._active_cards(p));played=[c for _,c,_ in active]
        controlled=[c for c in self.state['board'] if c['owner']==p['id']]
        if number<3:
            a,b=[('gold','civ'),('gold','scrap'),('civ','scrap')][number]
            return tags[a]>=2 and tags[b]>=2
        if number<6:return tags[['gold','civ','scrap'][number-3]]>=3
        if number==6:return tags['character']>=1
        if number==7:return all(tags[k]>=1 for k in ('gold','civ','scrap'))
        if number==8:return p['affection']>=5
        if number==9:return any(c['base'] and self._region(c)==1 for c in controlled)
        if number==10:return self._bases(p)>=1 and len(p['tiles'])>=2
        if number==11:return p['strength']>=4
        if number==12:return p['pot']>=2
        if number in (13,14):return len(controlled)>=(5 if number==13 else 3)
        if number==15:return any(self._region(c)==3 for c in controlled)
        if number==16:return len(p['hand'])>=6
        if number==17:
            adjacent={n['id'] for c in controlled for n in self._neighbors(c) if n['owner'] is not None and n['owner']!=p['id']}
            return len(adjacent)>=3
        if number==18:return sum(bool(c.get('passive') or c.get('triggers') or c.get('global_passive')) for c in played)>=3
        if number==19:return True
        if number==20:return any(c.get('requirements',{}).get('civ')==5 for c in played)
        if number==21:return sum(c.get('costs',{}).get('gold_pro',0)>0 for c in played)>=2
        if number==22:return any(c.get('can_trans') for c in played)
        if number==23:return bool(p['earned_achievements'])
        if number==24:return any(TILES[t].get('star',0)>=2 for t in p['tiles'])
        if number==25:return sum(TILES[t].get('point',0)>0 for t in p['tiles'])>=2
        if number==26:return p['available']==0
        if number==27:return sum(c.get('consume_piece',0)>0 for c in played)>=1
        if number==28:return sum(c['price']>=15 for c in played)>=3
        return sum(not c.get('tags') for c in played)>=2

    def _quest_reward_list(self):
        return [{'gold': 3}, {}, {'strength': 1}, {'contribution': 1}, {'pot': 1}, {'draw': 2}] if len(self.state['quests']) == 6 else [
            {'gold': 3}, {'gold': 3}, {}, {'strength': 1}, {'strength': 1}, {'contribution': 1}, {'pot': 1}, {'pot': 1}, {'draw': 2}]

    def _quest_reward_label(self, index):
        reward = self._quest_reward_list()[index]
        names = {'gold': '金币', 'strength': '力量', 'pot': '秘药', 'draw': '抽牌', 'contribution': '贡献'}
        if not reward:
            return '无额外奖励'
        return '、'.join('%s+%s' % (names[key], amount) for key, amount in reward.items())

    def _quest_evaluate(self, round_number=None):
        rewards = self._quest_reward_list()
        report = []
        for i, q in enumerate(self.state['quests']):
            if not q or q['done']:
                continue
            eligible = [p for p in self.state['players'] if self._quest_met(p, q['card'])]
            for p in eligible:
                reward = dict(rewards[i]); p['contribution'] = min(9, p['contribution'] + 1 + reward.pop('contribution', 0))
                self._effects(p, reward)
                self._log('%s完成公会委托《%s》，贡献+1并领取格位奖励。' % (p['name'], QUESTS[q['card']]['name']), p)
                report.append(dict(player=p['name'], quest=QUESTS[q['card']]['name'],
                                   reward=self._quest_reward_label(i), slot=i + 1))
            if eligible:
                q['done'] = True
        if report:
            self.state['quest_serial'] = self.state.get('quest_serial', 0) + 1
            self.state['quest_report'] = dict(serial=self.state['quest_serial'],
                                              round=round_number if round_number else self.state.get('round', 1),
                                              items=report)

    def _quest_phase(self, round_number):
        opt = self.rules['options']
        if not opt['guild_board']:
            return
        if opt['solo']:
            if 2 <= round_number <= 4:
                self._quest_evaluate(round_number)
            if round_number == 4:
                expired = [q for q in self.state['quests'] if q and not q['done']]
                for q in expired:
                    q['expired'] = True;q['done'] = True
                if expired:
                    self._log('第4季结算：未完成的公会委托全部过期（%s份）。' % len(expired))
            return
        if round_number > 1:
            self._quest_evaluate(round_number)
        for p in sorted(self.state['players'],key=lambda p:len(p['quest_offered']),reverse=True):
            if p['quest_offered']:
                self._enqueue(p,[dict(op='quest_pick')])

    def _dragon_toward(self,p,target):
        dragon=self.state.get('dragon',{})
        if not dragon.get('active'):return
        origin=self._cell(dragon['tile']);goal=self._cell(target)
        distance=self._hex_distance(origin,goal)
        choices=[n for n in self._neighbors(origin) if n['owner'] is None and not n.get('blocked') and not n.get('forest') and self._hex_distance(n,goal)<distance]
        if choices:self._enqueue(p,[dict(op='dragon_move',targets=[n['id'] for n in choices])])

    def _variant_action(self,p,action):
        kind=action['type'];opt=self.rules['options']
        if kind=='scout' and opt['scouts']:
            if sum(s['owner']==p['id'] for s in self.state['scouts'])>=5:raise ValueError('五枚侦查队标记已用完。')
            if not self._scout_targets(p):raise ValueError('没有与自己领地相邻的可侦查板块。')
            options=['gold']+(['strength'] if len(self.state['players'])>=4 else [])
            if not any(k not in self.state['scouts_used'] and self._affordable(p,{k:3 if k=='gold' else 1}) for k in options):raise ValueError('没有可用且付得起的侦查格。')
            self._enqueue(p,[dict(op='scout_pay',payments=[k for k in options if k not in self.state['scouts_used']])])
        elif kind=='forest_purify' and opt['forest']:
            if not any(c['revealed'] and c['owner'] is None and not self._tile_locked(c) and TILES[c['loot']].get('ishole') and any(n['owner']==p['id'] for n in self._neighbors(c)) for c in self.state['board']):raise ValueError('没有与自己领地相邻的可净化洞穴。')
            payment=action.get('payment')
            if payment not in ('strength','festival') or payment in self.state.setdefault('forest_used',[]):raise ValueError('这种净化方式本轮已使用。')
            if payment=='festival':
                if p['festival_tokens']<1:raise ValueError('没有庆典碎片。')
                p['festival_tokens']-=1
            else:self._pay(p,{'strength':2})
            self.state['forest_used'].append(payment)
            self._enqueue(p,[dict(op='purify',adjacent_own=True)])
        elif kind=='dragon_hunt' and opt['dragon']:
            dragon=self.state.get('dragon',{})
            if not dragon.get('active'):raise ValueError('潜行之龙已被击败。')
            cell=self._cell(dragon['tile'])
            if not any(n['owner']==p['id'] for n in self._neighbors(cell)):raise ValueError('必须控制潜行之龙相邻的区域。')
            cost=5*(3+sum(self._visible_stars(n) for n in self._neighbors(cell)))
            if p['gold']+5*p['strength']<cost:raise ValueError('金币与力量不足以讨伐潜行之龙。')
            self._enqueue(p,[dict(op='dragon_pay',cost=cost)])
        else:raise ValueError('当前设置未开放此行动。')

    def _scout_targets(self,p):
        return [c for c in self.state['board'] if c['owner'] is None and not self._tile_locked(c) and not any(s['tile']==c['id'] and s['owner']==p['id'] for s in self.state['scouts']) and any(n['owner']==p['id'] for n in self._neighbors(c))]

    def _execute_step(self,p,task):
        step=task['step'];op=step['op'];source=task['source'];context=task['context']
        if op=='prologue_pick':
            solo=self.rules['options']['solo']
            self._prompt(task,'选择序章'+(' / 每张支付10金币，可不选' if solo else ' / 选择一张'),
                [dict(value=i,label=PROLOGUES[i]['name'],image=PROLOGUES[i]['source']) for i in p['prologue_offered']],0 if solo else 1,2 if solo else 1)
        elif op in ('draw_select','story_library'):
            cards=step.get('cards')
            if cards is None:
                cards=self._draw(2 if op=='story_library' else step.get('count',4))
                task=deepcopy(task);task['step']['cards']=cards
            self._prompt(task,'选择加入手牌'+(' / 未选卡背面打出，各获得1金币产能' if op=='story_library' else ''),
                [self._card_option(c,i) for i,c in enumerate(cards)],0 if op=='story_library' else min(step.get('keep',1),len(cards)),len(cards) if op=='story_library' else min(step.get('keep',1),len(cards)))
        elif op=='quest_pick':
            if not any(q is None for q in self.state['quests']):p['quest_offered']=[];return
            self._prompt(task,'选择一项公会委托放上公告板',[dict(value=i,label=QUESTS[i]['name'],image=QUESTS[i]['source']) for i in p['quest_offered']])
        elif op=='quest_place':
            self._prompt(task,'选择委托格位',[dict(value=i,label=self._quest_slot_label(i)) for i,q in enumerate(self.state['quests']) if q is None])
        elif op=='festival_pick':
            self._prompt(task,'休店 / 领取一枚庆典碎片',[dict(value=i,label=('查看4张保留2张' if i==0 and len(self.state['players'])>=3 else '查看3张保留1张' if i==(1 if len(self.state['players'])>=3 else 0) else '庆典碎片')) for i in self.state['festival_slots']])
        elif op=='scout_pay':
            self._prompt(task,'派遣侦查队 / 选择本轮未使用的费用',[dict(value=k,label='支付3金币' if k=='gold' else '支付1力量') for k in step['payments'] if p[k]>=(3 if k=='gold' else 1)])
        elif op=='scout_target':
            self._prompt(task,'选择与自己控制区域相邻的迷宫',[self._board_option(c) for c in self._scout_targets(p)])
        elif op=='dragon_move':
            self._prompt(task,'选择潜行之龙靠近目标的方向',[self._board_option(self._cell(cid)) for cid in step['targets'] if self._cell(cid)['owner'] is None])
        elif op=='dragon_pay':
            cost=step['cost']
            self._prompt(task,'讨伐潜行之龙 / 总费用%s金币，1力量抵5金币'%cost,[dict(value=n,label='支付%s力量＋%s金币'%(n,max(0,cost-5*n))) for n in range(min(p['strength'],(cost+4)//5)+1) if p['gold']>=max(0,cost-5*n)])
        elif op=='clear_forest':
            self._prompt(task,'据点建设 / 可移除一片相邻魔之森',[self._board_option(c) for c in self._neighbors(self._cell(step['tile'])) if c.get('forest')],optional=True)
        else:return super()._execute_step(p,task)

    def _execute_choice_step(self,p,task,values,extra):
        step=task['step'];op=step['op'];source=task['source'];context=task['context']
        if op=='prologue_pick':
            if self.rules['options']['solo']:self._pay(p,{'gold':10*len(values)})
            p['prologue']=values;p['prologue_offered']=[]
            for i in values:
                d=PROLOGUES[i];self._gain_tags(p,d['tags']);self._effects(p,d['effect'])
                self._log('%s的故事开始：《%s》。'%(p['name'],d['name']),p)
        elif op in ('draw_select','story_library'):
            cards=step['cards'];p['hand']+=[c for i,c in enumerate(cards) if i in values]
            remaining=[c for i,c in enumerate(cards) if i not in values]
            if op=='story_library':
                for c in remaining:
                    p['played'].append(c);self._card_states(p)[-1]['face_down']=True;p['gold_pro']+=1
            else:self.state['discard']+=remaining
        elif op=='quest_pick':
            p['quest_offered']=[];self._enqueue(p,[dict(op='quest_place',card=values[0])])
        elif op=='quest_place':
            self.state['quests'][values[0]]=dict(card=step['card'],done=False)
            self._log('%s发布委托《%s》。'%(p['name'],QUESTS[step['card']]['name']),p)
        elif op=='festival_pick':
            slot=values[0];self.state['festival_slots'].remove(slot);p['festival_tokens']+=1
            if slot==0 and len(self.state['players'])>=3:self._enqueue(p,[dict(op='draw_select',count=4,keep=2)])
            elif slot==(1 if len(self.state['players'])>=3 else 0):self._enqueue(p,[dict(op='draw_select',count=3,keep=1)])
        elif op=='scout_pay':
            payment=values[0];self._pay(p,{payment:3 if payment=='gold' else 1})
            self.state['scouts_used'].append(payment);self._enqueue(p,[dict(op='scout_target')])
        elif op=='scout_target':
            cell=self._cell(values[0]);self.state['scouts'].append(dict(tile=cell['id'],owner=p['id']))
            if not cell['revealed']:
                p['private_tiles'][cell['id']]=cell['loot'];self._enqueue(p,[dict(op='peek_publish',tile=cell['id'])])
        elif op=='dragon_move':self.state['dragon']['tile']=values[0]
        elif op=='dragon_pay':
            n=values[0];self._pay(p,dict(strength=n,gold=max(0,step['cost']-5*n)))
            dragon=self.state['dragon']
            if dragon['eggs']:
                dragon['eggs']-=1;p['dragon_points']+=2;dragon['tile']=dragon['home']
                self._enqueue(p,[dict(op='treasure')])
            else:dragon['active']=False;p['dragon_points']+=6
            self._log('%s成功讨伐潜行之龙。'%p['name'],p)
        elif op=='clear_forest':
            self._cell(values[0])['forest']=False;p['festival_tokens']+=1
        else:return super()._execute_choice_step(p,task,values,extra)

    def _quest_slot_label(self,i):
        labels=['金币+3','无额外奖励','力量+1','额外贡献+1','秘药+1','抽牌+2'] if len(self.state['quests'])==6 else ['金币+3','金币+3','无额外奖励','力量+1','力量+1','额外贡献+1','秘药+1','秘药+1','抽牌+2']
        return '格位%s / %s'%(i+1,labels[i])
