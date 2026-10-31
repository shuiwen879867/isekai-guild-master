"""Rulebook modes and optional boards layered over the authoritative engine."""
from collections import Counter
from copy import deepcopy
from guild_content import CARDS,HEROES,TILES,ACHIEVEMENTS,POTIONS
from guild_modes import board_layout
from guild_new_content import asset


from guild_optional_boards import OptionalBoards


class VariantRules(OptionalBoards):
    def _effects(self,p,effects,action=None):
        before=(self.state['civ'],self.state['miasma'])
        super()._effects(p,effects,action)
        self._collect_flags(p,before)

    def _take_loot(self,p,loot_id,action=None):
        before=(self.state['civ'],self.state['miasma'])
        super()._take_loot(p,loot_id,action)
        self._collect_flags(p,before)

    def _explore(self,p,action):
        before=(self.state['civ'],self.state['miasma'])
        result=super()._explore(p,action)
        self._collect_flags(p,before)
        if result=='explored':
            self._dragon_toward(p,action['tile'])
            cell=self._cell(action['tile']);dragon=self.state.get('dragon',{})
            if cell.get('boss') and dragon.get('active') and dragon.get('eggs'):
                dragon['eggs']=0
                self._log('魔王板块被控制，潜行之龙的龙蛋标记全部移除。',p)
        return result

    def _build(self,p,tile_id,free=False,no_surcharge=False):
        super()._build(p,tile_id,free,no_surcharge)
        if self.rules['options']['forest']:
            self._enqueue(p,[dict(op='clear_forest',tile=tile_id)])

    def _draw_achievement(self,p,count):
        if self.rules.get('options',{}).get('solo') or self.rules.get('options',{}).get('map_type')=='training':return
        return super()._draw_achievement(p,count)

    def _achievement(self,p,action,discount=0):
        card=ACHIEVEMENTS.get(action.get('id'),{})
        if not card.get('solo'):return super()._achievement(p,action,discount)
        if not self.rules['options']['solo'] or action.get('id') not in self.state['public_achievements']:
            raise ValueError('这项单人王权已经达成或未开放。')
        if not self._requirements(p,card.get('requirements',{})):raise ValueError('未满足单人王权条件。')
        cost=max(0,card['price']-discount)
        strength=max(0,(cost-p['gold']+4)//5) if card.get('can_trans') else 0
        self._pay(p,dict(gold=max(0,cost-5*strength),strength=strength))
        self.state['public_achievements'].remove(action['id']);p['earned_achievements'].append(action['id'])
        self._effects(p,card['effect']);self._emit(p,'achievement')
        self._log('%s完成单人王权《%s》。'%(p['name'],card['name']),p)

    def _develop(self,p,count,action,free=False):
        spend=action.get('festival',{})
        if not isinstance(spend,dict):raise ValueError('庆典抵扣参数不正确。')
        if spend and not (self.rules['options']['forest'] or self.rules['options']['festival_preparation']):raise ValueError('本局没有庆典碎片。')
        total=0
        for key,n in spend.items():
            if key not in action.get('slots',[]) or key not in ('gold','strength','pot') or type(n) is not int or n<0:
                raise ValueError('只能为选中的金币、力量或秘药发展条件使用庆典。')
            cap=dict(gold=4,strength=3,pot=2)[key]
            if n>cap:raise ValueError('庆典抵扣超过费用。')
            total+=n
        if total>p['festival_tokens']:raise ValueError('庆典碎片不足。')
        if free and total:raise ValueError('免费发展无需支付庆典。')
        p['festival_tokens']-=total
        for key,n in spend.items():p[key]+=n*(5 if key=='gold' else 1)
        return super()._develop(p,count,action,free)
    def _card_in_deck(self,card):
        opt=self.rules['options']
        if card.get('special') or not card.get('available',True): return False
        if card.get('requires_dlc') and not opt['labyrinth_events']: return False
        if card.get('expansion') and not opt.get(card['expansion']): return False
        return True

    def _draw_variable(self,placed=True):
        supply=self.state.get('variable_supply',[])
        if not supply: raise ValueError('变动板块供应已用尽。')
        tile=supply.pop()
        if placed and self.rules['options']['solo'] and self.state.get('action_count',0):
            self.state['miasma']+=1
        return tile

    def _make_board(self):
        opt=self.rules['options']; count=len(self.state['players'])
        cells,big=board_layout(opt,count)
        self.state['map_name']=('大深度' if opt['map_type']=='deep' else '训练' if opt['map_type']=='training' else '一般')+('大迷宫' if big else '迷宫')
        self.state['variable_supply']=[k for k,t in TILES.items() if t.get('variable')]
        self._shuffle(self.state['variable_supply'])
        ordinary=[k for k,t in TILES.items() if not t.get('boss') and not t.get('variable') and not t.get('blocked') and k not in ('tile21','tile22')]
        draws=[]
        while len(draws)<len(cells):
            batch=ordinary[:];self._shuffle(batch);draws+=batch
        for c in cells:
            c.update(owner=None,base=False,revealed=c.pop('initially_revealed'))
            variable=c.pop('initial_variable')
            if c['blocked']:
                c.update(loot='blocked',revealed=True,back_star=1)
            elif c['boss']:
                back=2 if big and c['q']==3 else 3
                if opt['map_type']=='training': back=2
                if opt['solo']: back=3 if opt['map_type']=='deep' else 4
                elif opt['hard_boss']: back+=1
                c.update(loot='boss' if back==3 else 'boss%s'%back,revealed=False,back_star=back)
            else:
                c.update(loot=self._draw_variable() if variable else draws.pop(),back_star=2 if variable else 1)
        self.state['board']=cells

    def _setup_variants(self):
        s=self.state;opt=self.rules['options'];count=len(s['players'])
        self.rules['discard_achievement_gold']=5
        s.update(mercenary_supply=7,flags=[],pass_order=[],gems_supply=9,
                 scouts_used=[],scouts=[],festival_slots=[],festival_supply=21,monster_supply=[2]*4)
        for p in s['players']:
            p.update(gems=0,festival_tokens=0,monster_tokens=0,contribution=0,dragon_points=0,mulligan_done=False)
        order=list(range(count));self._shuffle(order)
        starter=opt['start_player']
        s['start_player']=s['turn']=order[0] if starter=='auto' or starter>=count else starter
        if opt['pollution']: s['miasma']=count*12
        if opt['prologue']: s['miasma']=count*(13 if opt['pollution'] else 11)
        if opt['solo']:
            d=opt['solo_difficulty'];p=s['players'][0]
            s.update(civ=3,miasma=dict(beginner=20,advanced=25,expert=25,super=35)[d],start_player=0,turn=0)
            s['potions_disabled']=['strength','knowledge']
            if d=='super':
                p['gold']+=10;p['available']+=1;p['offered']+=self._draw(4)
            prefix='solo_hard_' if d in ('expert','super') else 'solo_normal_'
            s['public_achievements']=[prefix+str(i) for i in range(6)]
            s['achievement_deck']=[]
            p['achievements']=[]
            self.rules['solo_rounds']=6
        if opt['map_type']=='training':
            s['public_achievements']=[];s['achievement_deck']=[]
            for p in s['players']: p['gold']+=6;p['achievements']=[]
        for option,state_key in [('initial_civ','civ'),('initial_miasma','miasma')]:
            if opt[option] is not None:s[state_key]=opt[option]
        if opt['flags'] or (opt['guild_board'] and not opt['solo']):
            s['flags']=[n for n in range(5,s['miasma'],5) if n>s['civ']]
        if opt['festival_preparation']:
            s['festival_slots']=list(range(count-1))
            s['festival_supply']-=count-1
        if opt['forest']:
            coords=[(1,-2),(-1,-1),(2,-1),(-2,1),(1,1),(-1,2)]
            if opt['map_type']=='deep': coords=[(0,-2),(2,-2),(-2,-1),(3,-1),(-1,0),(1,0),(-3,1),(2,1)]
            for c in s['board']:
                if (c['q'],c['r']) in coords and not c['boss'] and not c['blocked']: c['forest']=True
        if opt['dragon']:
            home=next(c for c in s['board'] if c['boss'])['id']
            s['dragon']=dict(tile=home,home=home,eggs=0 if count<3 else 1 if count==3 else 2,active=True)
        self._setup_boards()
        self._setup_heroes()
        self._log('对局设置：%s；%s人；角色候选%s张。'%(s['map_name'],count,opt['hero_draw']))
        if opt['initial_civ'] is not None or opt['initial_miasma'] is not None:
            self._log('自定义初始数值：文明%s；瘴气%s。'%(s['civ'],s['miasma']))
        from guild_draft import setup
        setup(self)

    def _tile_locked(self,c):
        dragon=self.state.get('dragon',{})
        return bool(c.get('blocked') or c.get('forest') or (dragon.get('active') and dragon.get('tile')==c['id']))

    def _visible_stars(self,c):
        if c.get('blocked'): return 1
        if c.get('forest'): return 2
        d=self.state.get('dragon',{})
        if d.get('active') and d.get('tile')==c['id']: return 3
        if c['owner'] is not None: return 0
        return TILES[c['loot']].get('star',0) if c['revealed'] else c.get('back_star',1)

    def _apply(self,player_id,action):
        kind=action['type'];p=self._player(player_id)
        if kind=='draft_pick':
            from guild_draft import pick
            pick(self,p,action)
            return
        if self.state['phase']=='draft' and kind!='choice':
            raise ValueError('请先完成开局轮抽，再购买情报或进行其他行动。')
        if kind=='mulligan':
            if self.state['round']!=1 or self.state['phase']!='research' or p['researched'] or p['mulligan_done'] or self.state.get('pending'):
                raise ValueError('只能在开局留牌前换牌一次。')
            cards=action.get('cards',[]);self._check_cards(cards,p['offered'])
            if len(cards)>5: raise ValueError('开局最多更换5张手牌。')
            for card in cards: p['offered'].remove(card)
            p['offered']+=self._draw(len(cards));self.state['discard']+=cards;p['mulligan_done']=True
            self._log('%s更换%s张起始手牌。'%(p['name'],len(cards)),p);return
        if kind=='sell_gem':
            if self.state['phase']=='finished' or p['gems']<1: raise ValueError('没有可以售卖的宝石。')
            p['gems']-=1;p['gold']+=3;self.state['gems_supply']+=1
            self._log('%s售卖宝石，金币+3。'%p['name'],p);return
        super()._apply(player_id,action)
        if kind=='research' and self.state['phase']=='action' and self.state['round']==1 and self.rules['options']['prologue']:
            players=self.state['players'];start=self.state['start_player']
            for other in players[start:]+players[:start]:
                if other['prologue_offered']: self._enqueue(other,[dict(op='prologue_pick')])
            self._drain_effects()

    def _collect_flags(self,p,before):
        if self.state['phase'] not in ('action','final'): return
        civ,miasma=before
        claimed=[n for n in self.state['flags'] if min(civ,self.state['civ'])<=n<=max(civ,self.state['civ']) or min(miasma,self.state['miasma'])<=n<=max(miasma,self.state['miasma'])]
        if not claimed:return
        self.state['flags']=[n for n in self.state['flags'] if n not in claimed]
        if self.rules['options']['guild_board'] and not self.rules['options']['solo']: p['contribution']=min(9,p['contribution']+len(claimed))
        else:p['reputation']+=len(claimed)
        self._log('%s获得%s枚%s。'%(p['name'],len(claimed),'贡献标记' if self.rules['options']['guild_board'] else '旗标'),p)

    def _execute_step(self,p,task):
        if task['step']['op']=='all' and self.rules['options']['solo']: return
        if task['step']['op']=='gain_gem':
            if self.state['gems_supply']:
                self.state['gems_supply']-=1;p['gems']+=1
            return
        return super()._execute_step(p,task)

    def _execute_choice_step(self,p,task,values,extra):
        op=task['step']['op']
        result=super()._execute_choice_step(p,task,values,extra)
        if op=='reveal' and values:self._dragon_toward(p,values[0])
        if op=='peek_publish' and values and values[0]:self._dragon_toward(p,task['step']['tile'])
        return result

    def _season(self):
        s=self.state;opt=self.rules['options'];season=s['season'];round_number=s['round']
        if opt['solo'] and round_number>=self.rules['solo_rounds']:
            if not s.get('solo_final_bonus_started'):
                s['solo_final_bonus_started'] = True
                p = s['players'][0]
                passive = HEROES[p['hero']].get('passive',{})
                hero_extra = p['hero_level'] >= passive.get('final_extra_level',99)
                if hero_extra:
                    p['gold'] += passive.get('final_extra_gold',0)
                bonus_extra = 0
                for _,c,m in self._active_cards(p):
                    bonus = c.get('final_bonus') or {}
                    if bonus:
                        p['gold'] += bonus.get('gold',0)
                        bonus_extra += int(bonus.get('action',0))
                        self._log('%s的「%s」发动，获得%s金币并再执行一次主要行动。' % (p['name'],c['name'],bonus.get('gold',0)),p)
                if hero_extra or bonus_extra:
                    p['passed'] = False
                    s['solo_final_action'] = True
                    s['turn'] = 0
                    return
            self._finish();return
        no_bonus=opt['guild_board'] or opt['festival_preparation']
        # The base engine produces spring/summer/autumn once; remove or double
        # only the extra seasonal yield. Winter has no bonus in the base book.
        bonuses={0:('strength',1),1:('pot',1),2:('gold',5)}
        if season in bonuses:
            key,n=bonuses[season]
            for p in s['players']:
                if no_bonus: p[key]-=n
                elif opt['rich_seasons']:p[key]+=n
        super()._season()
        self._quest_phase(round_number)
        s['forest_used']=[]
        if opt['pollution'] and round_number==4:
            for p in s['players']:p['available']+=1
            self._log('污染领地：每位公会长获得额外冒险者，第五轮起可用。')
        if opt['rich_seasons'] and season==3 and not no_bonus:
            for p in s['players']:p['hand']+=self._draw(2)
        # Base p12: the start-player marker passes left each round.
        s['pass_order']=[];s['scouts_used']=[]
        if opt['festival_preparation']:
            for slot in range(len(s['players'])-1):
                if slot not in s['festival_slots'] and s['festival_supply']:
                    s['festival_slots'].append(slot);s['festival_supply']-=1
        self._drain_effects()

    def _finish(self):
        if self.rules['options']['guild_board'] and not self.rules['options']['solo'] and not self.state.get('quests_final_done'):
            self.state['quests_final_done']=True
            self._quest_evaluate()
        super()._finish()
        if self.rules['options']['solo']:
            won=self.state['civ']+1>=self.state['miasma']
            self.state['solo_result']='win' if won else 'loss'
            self.state['winners']=[self.state['players'][0]['id']] if won else []
            score=self.state['scores'][0]['score'];offset=10 if self.rules['options']['solo_difficulty']=='super' else 0
            ranks=['蛇','蜥蜴人','飞龙','龙','巴哈姆特','耶梦加得']
            self.state['solo_rank']=ranks[max(0,min(5,(score-offset)//10-3))]+'级公会' if won else '挑战未达成'
            self._log('单人挑战%s：第%s轮结束，文明%s / 瘴气%s。'%('成功' if won else '失败',self.state['round'],self.state['civ'],self.state['miasma']))

    def _variant_action(self,p,action):
        kind=action['type'];opt=self.rules['options']
        if kind=='hire' and opt['solo']:
            if not self.state['mercenary_supply']: raise ValueError('雇佣兵已全部雇用。')
            self._pay(p,{'gold':15});p['available']+=1;self.state['mercenary_supply']-=1
            self._log('%s支付15金币，雇用1名冒险者。'%p['name'],p)
        elif kind=='monster_hunt' and opt['monster_quests']:
            season=(self.state['season']+1)%4
            if not self.state['monster_supply'][season]: raise ValueError('本季魔兽已被讨伐完毕。')
            self._pay(p,{'strength':2 if season<2 else 3})
            self.state['monster_supply'][season]-=1;p['monster_tokens']+=1
            self._effects(p,[{'gold_pro':5},{'str_pro':1},{'pot':1,'draw':1},{}][season])
        else: return super()._variant_action(p,action)

    def score_breakdown(self,player_id):
        d=super().score_breakdown(player_id);p=self._player(player_id)
        d.update(gems=p.get('gems',0)*2,festival=p.get('festival_tokens',0),
                 monsters=p.get('monster_tokens',0)*p['hero_level'],dragon=p.get('dragon_points',0))
        contribution=p.get('contribution',0)
        d['contribution']=0 if contribution<2 else 1 if contribution<4 else 2 if contribution<6 else 4 if contribution<8 else 6 if contribution<9 else 8
        return d

    def view(self,player_id=None,reveal=False):
        view=super().view(player_id,reveal)
        from guild_draft import redact
        redact(view,player_id)
        view.pop('variable_supply',None)
        view.pop('quest_deck',None)
        for p in view['players']:
            if p['id']!=player_id and not reveal:
                p.pop('quest_offered',None);p.pop('prologue_offered',None)
        view['variable_remaining']=len(self.state.get('variable_supply',[]))
        for c in view['board']:
            c['point']=c['region']
            original=self._cell(c['id'])
            c['visible_star']=self._visible_stars(original)
            if not c['revealed']:
                c['image']=17 if c.get('boss') else 1083 if c.get('back_star')==2 else 2
                c['back_source']=('images/piece_png/17.png' if c.get('back_star')==3 else asset(87 if c.get('back_star')==2 else 88)) if c.get('boss') else asset(83) if c.get('back_star')==2 else 'images/piece_png/2.png'
        view['options']=deepcopy(self.rules['options'])
        return view
