"""Stateful character abilities, using the same serialized choice queue as cards."""
from copy import deepcopy
from guild_content import HEROES,CARDS,TILES

class HeroRules:
    def _draw(self,count):
        # Character-only events leave the game when discarded.
        self.state['discard']=[c for c in self.state.get('discard',[]) if not CARDS[c].get('special')]
        return super()._draw(count)

    def _setup_heroes(self):
        for p in self.state['players']:
            hero=HEROES[p['hero']]
            p.update(hero_deck=self._draw(hero.get('private_deck',0)),hero_tiles=[],hero_milestones=[],special_adventurer=bool(hero.get('special_adventurer')),special_attached=None)
            if p['hero']=='macaron_white':
                p['gold']+=3*sum(c['revealed'] and TILES[c['loot']].get('ishole',False) for c in self.state['board'])

    def _apply(self,player_id,action):
        p=self._player(player_id)
        if action['type']=='horn_preference':
            if p['hero']!='horn_black' or self.state['phase']=='finished':raise ValueError('不能设置替代支付。')
            pending=self.state.get('pending')
            if pending and pending['player']!=player_id:raise ValueError('请等待其他玩家完成选择。')
            value=action.get('prefer_pot')
            if type(value) is not bool:raise ValueError('支付选项无效。')
            p['prefer_pot']=value;return
        if action['type'] not in ('research','choice','sell_event','discard_achievement','exchange','payment_preference'):
            hero=HEROES[p['hero']]
            if hero.get('first_steps') and not p.get('hero_first_done') and self.state['phase']=='action' and self.state['players'][self.state['turn']]['id']==player_id and not self.state.get('pending'):
                p['hero_first_done']=True
                followup = [dict(op='resume_action',action=action)] if hero.get('resume_first_action',True) else []
                if not followup:
                    self._log('%s先结算首次行动前的能力；结算后重新选择主要行动。'%p['name'],p)
                self._enqueue(p,hero['first_steps']+followup)
                self._drain_effects();return
        # Tile substitution is a payment, never a way to sell tiles for money.
        if action['type']=='exchange' and p['hero']=='horn_black' and p['pot']<action.get('amount',1):raise ValueError('兑换金币必须支付实际秘药。')
        return super()._apply(player_id,action)

    def _hero_draw(self,p,count=1):
        deck=p.get('hero_deck',[])
        p['hand'] += [deck.pop() for _ in range(min(count,len(deck)))]

    def _gain_tags(self,p,tags,store=True,origin=None):
        super()._gain_tags(p,tags,store,origin)
        if p['hero']=='horn_white':p['gold']+=len(tags)
        if p['hero']=='shuri_white':self._hero_draw(p,tags.count('gold'))

    def _effects(self,p,effects,action=None):
        gold_pro,str_pro=p['gold_pro'],p['str_pro']
        super()._effects(p,effects,action)
        if p['hero']=='frida_black' and p['str_pro']>str_pro:p['gold']+=(p['str_pro']-str_pro)*3
        if p['hero']=='olivia_white' and (action or {}).get('_context',{}).get('on_play') and p['gold_pro']>gold_pro:p['gold']+=p['gold_pro']-gold_pro

    def _emit(self,p,event,context=None):
        super()._emit(p,event,context)
        if event=='reveal' and (context or {}).get('hole'):
            for other in self.state['players']:
                if other['hero']=='macaron_white':
                    other['gold']+=3;self._log('%s的圣女能力：公开洞穴，金币+3。'%other['name'],other)

    def _play(self,p,action,free=False):
        card=CARDS.get(action.get('card'),{})
        double=action.get('double',False)
        if type(double) is not bool or (double and (p['hero']!='vee_white' or free or action.get('_source') or 'character' in card.get('tags',[]) or card.get('point',0)<0)):
            raise ValueError('此卡不能使用薇伊的双倍打出。')
        original_civ=self.state['civ']
        super()._play(p,action,free)
        if p['hero']=='melissa_white' and len(p['played'])%4==0:
            p['pot']+=1
            self._log('%s的梅莉莎：事件总数达到4的倍数，秘药+1。'%p['name'],p)
        if p['hero']=='sif_white' and any(card.get('requirements',{}).values()):p['gold']+=2
        if card.get('price',-1)>=0 and card.get('price',-1)%10 in (0,5) and p['hero']=='bell_white':
            p['gold']+=2;self._hero_draw(p)
        if any(c.get('zero_five_gold') for _,c,_ in self._active_cards(p)) and card.get('price',-1)%5==0:
            p['gold']+=2
        if p['hero']=='marta_black' and (not card.get('tags') or set(card['tags'])=={'character'}):p['gold']+=3
        if double:self._enqueue(p,[dict(op='repeat_play',card=card['id'],civ=original_civ)],self._source(p,len(p['played'])-1))

    def _pay(self,p,costs):
        costs=dict(costs)
        if p['hero']=='horn_black' and costs.get('pot',0)>p['pot']:
            needed=costs['pot']-p['pot']
            if len(p['tiles'])>=needed:
                tiles=p['tiles'][:needed];del p['tiles'][:needed];costs['pot']-=needed
                for tile in tiles:self._emit(p,'consume_tile',dict(tile=tile))
        return super()._pay(p,costs)

    def _season(self):
        bonus=[(p,p['gold_pro'],p['str_pro'],p['pot_pro']) for p in self.state['players']
               if p['hero']=='peria_black' and self.state['season']==0 and self.state['round']==2]
        super()._season()
        for p,gold,strength,pot in bonus:
            p['gold']=max(0,p['gold']+gold-20)
            p['strength']+=strength;p['pot']+=pot
            self._log('%s的妖精女王：春季产能额外结算一次，再失去20金币。'%p['name'],p)

    def _affordable(self,p,costs):
        if p['hero']=='horn_black' and costs.get('pot',0)>p['pot']:
            costs=dict(costs,pot=max(0,costs['pot']-len(p['tiles'])))
        return super()._affordable(p,costs)

    def _stat(self,p,stat):
        if stat=='permanent_cards':return sum(bool(c.get('passive') or c.get('triggers') or c.get('global_passive') or c.get('build_surcharge_discount') or c.get('zero_five_gold')) for _,c,_ in self._active_cards(p))
        count=super()._stat(p,stat)
        if stat in ('tiles','pieces'):count+=len(p.get('hero_tiles',[]))
        if stat=='holes':count+=sum(TILES[t].get('ishole',False) for t in p.get('hero_tiles',[]))
        return count

    def _tags(self,p):
        tags=super()._tags(p)
        for tile in p.get('hero_tiles',[]):tags.update(TILES[tile].get('tags',[]))
        return tags

    def can_explore(self,player_id,tile_id,allow_hole=False):
        p=self._player(player_id)
        if p['hero']=='marta_white' and p['hero_level']<3:return False
        return super().can_explore(player_id,tile_id,allow_hole=allow_hole)

    def _prepare_explore(self,p,task):
        cell=self._cell(task['step']['tile'])
        if p['hero']=='chris_black' and not cell['revealed'] and not task['step'].get('chris_checked'):
            task=deepcopy(task);task['step']['chris_checked']=True
            self._enqueue(p,[dict(op='chris_explore_swap',payment=task)])
            return False
        result=super()._prepare_explore(p,task)
        if not result and TILES[cell['loot']].get('ishole'):
            if task['step'].get('retry_hole'):
                p['extra_actions']=max(0,p['extra_actions']-int(task['step'].get('hole_extra',True)))
                retry = {k:v for k,v in task['step'].items() if k not in ('tile','op','chris_checked')}
                self._enqueue(p,[dict(retry,op='explore',optional=True,retry_hole=True)])
        return result

    def _explore(self,p,action):
        before=self.state['miasma'];result=super()._explore(p,action)
        if result=='explored':
            if p['hero']=='macaron_black':
                frame=self.state.get('action_frame') or {}
                n=min(max(0,before-self.state['miasma']),max(0,3-frame.get('macaron_gain',0)))
                frame['macaron_gain']=frame.get('macaron_gain',0)+n
                p['gold']+=2*n;p['gold_pro']+=n
            if p['hero']=='olivia_black':
                count=self._stat(p,'controlled')
                for milestone in (1,3,5,7):
                    if count>=milestone and milestone not in p['hero_milestones']:
                        p['hero_milestones'].append(milestone);p['pot']+=1
        return result

    def build_cost(self,player_id,tile_id):
        cost=super().build_cost(player_id,tile_id)
        p=self._player(player_id)
        surcharge=max(0,cost-self.rules['build_cost'])
        reduction=sum(c.get('build_surcharge_discount',0) for _,c,_ in self._active_cards(p))
        return self.rules['build_cost']-p.get('_build_discount',0)+max(0,surcharge-reduction)

    def _flip(self,source):
        found=self._source_card(source)
        if found and found[0].get('special_attached')==found[3]['uid']:
            found[0]['special_attached']=None;found[0]['special_adventurer']=True
        return super()._flip(source)

    def _execute_step(self,p,task):
        step=task['step'];op=step['op'];source=task['source'];ctx=task['context']
        if op=='resume_action':return self._apply(p['id'],step['action'])
        if op=='siren_discount':
            options=[]
            for n in range(min(5,p['gold_pro'])+1):
                payment=dict(discount=2*n,costs=dict(gold_pro=n))
                if any(self._requirements(p,CARDS[c].get('requirements',{}),True) and self._can_nested_play(p,c,payment) for c in p['hand']):
                    options.append(dict(value=n,label='产能 −%s / 打出费用 −%s'%(n,2*n)))
            self._prompt(task,'减少多少金币产能来打出事件？',options)
        elif op=='refresh_actions':
            options=[]
            if 'ability' in p['used']:options.append(dict(value='hero',label='恢复看板娘特别行动',image=HEROES[p['hero']]['source'][2]))
            options += [self._card_option(c,m['uid']) for c,m in zip(p['played'],self._card_states(p)) if not m['face_down'] and m.get('used_round')==self.state['round']]
            self._prompt(task,'移除至多两张卡上的使用完毕标记',options,0,2,optional=True)
        elif op=='ruby_explore':
            self._enqueue(p,[dict(op='explore',discount=10 if p['retreat']>0 else 0)],source,ctx)
        elif op=='melissa_reveal_play':
            cards=self._draw(2)
            self._log('%s公开牌库顶：%s。'%(p['name'],'、'.join(CARDS[c]['name'] for c in cards)),p)
            task['step']['cards']=cards
            self._prompt(task,'选择一张公开事件，无视打出费用与条件打出',[self._card_option(c,i) for i,c in enumerate(cards)])
        elif op=='pen_reveal_use':
            # 恶魔羽毛笔：翻开牌库顶2张，选1张使用其「打出时效果」，之后翻开的卡片全部弃牌。
            cards=self._draw(2)
            self._log('%s公开牌库顶：%s。'%(p['name'],'、'.join(CARDS[c]['name'] for c in cards)),p)
            task['step']['cards']=cards
            self._prompt(task,'选择一张公开事件，使用其「打出时效果」',[self._card_option(c,i) for i,c in enumerate(cards)])
        elif op=='draw_to_three':
            n=max(0,3-len(p['hand']));cards=self._draw(n);p['hand']+=cards;p['gold']+=2*len(cards)
        elif op=='all_tags_gold':p['gold']+=sum(self._tags(p).values())
        elif op=='repeat_play':
            found=self._source_card(source)
            if found and not found[3]['face_down']:
                card=CARDS[step['card']];action=dict(_source=source,_context=dict(origin='card',on_play=True))
                self._effects(p,{k:deepcopy(v) for k,v in card.items() if k not in ('costs','tags')},action)
                for rule in card.get('conditional',[]):
                    if rule.get('civ_min',1)<=step.get('civ',self.state['civ'])<=rule.get('civ_max',10**9) and self._requirements(p,rule.get('requirements',{})):
                        self._effects(p,rule.get('effect',{}),action)
        elif op in ('restore_cards','return_played','repeat_card'):
            options=[self._card_option(c,m['uid']) for c,m in zip(p['played'],self._card_states(p)) if op=='return_played' or m['face_down']==(op=='restore_cards')]
            self._prompt(task,dict(restore_cards='将背面事件翻回正面（不执行打出效果）',return_played='收回一张事件到手牌',repeat_card='再结算一张事件的打出效果')[op],options,maximum=step.get('max',1),optional=True)
        elif op=='recall_attached':
            for m in self._card_states(p):p['available']+=m['adventurers']-int(p.get('special_attached')==m['uid']);m['adventurers']=0
            p['special_adventurer']=True;p['special_attached']=None
        elif op=='hero_attach_tile':self._prompt(task,'将一块板块放在看板娘上，获得8金币',self._tile_options(p))
        elif op=='consume_tiles' and p['hero']=='horn_black':
            options=self._tile_options(p)+[dict(value='pot%s'%i,label='支付1秘药代替板块') for i in range(p['pot'])]
            self._prompt(task,'支付板块 / 秘药也可代替',options,step.get('min',1),step.get('max',1),step.get('optional',False))
        elif op=='hero_sacrifice_play':
            if p['strength']<1 or not p['tiles']:raise ValueError('需要1力量及1块可支付的迷宫板块。')
            check=deepcopy(p);check['strength']-=1;check['tiles']=check['tiles'][1:]
            if not any(CARDS[c]['price']<=14 and self._can_nested_play(check,c,dict(free=True)) for c in p['hand']):raise ValueError('没有费用14以下且能支付额外费用的手牌。')
            self._prompt(task,'先支付一个迷宫板块',self._tile_options(p))
        elif op=='hero_tile_discount_play':self._enqueue(p,[dict(op='play',discount=self._stat(p,'pieces')*3)],source)
        elif op=='play_extra_gold':self._enqueue(p,[dict(op='play',filter=dict(extra_cost=True),on_success=dict(gold=5),optional=True)],source)
        elif op=='vee_build':
            discount=min(15,3*self._tags(p)['scrap'])
            choices=[]
            for cell in self.state['board']:
                if cell['owner']==p['id'] and not cell['base']:
                    price=self.build_cost(p['id'],cell['id'])-discount
                    if self._affordable(p,dict(gold=price)):choices.append(dict(self._board_option(cell),label='建设 / %s金币'%price))
            if not choices:raise ValueError('没有可建设且付得起费用的领地。')
            self._prompt(task,'选择建设据点的位置',choices)
        elif op in ('swap_tiles','chris_explore_swap'):
            target=step.get('payment',{}).get('step',{}).get('tile')
            cells=[c for c in self.state['board'] if c['owner'] is None and not c.get('boss') and not self._tile_locked(c)
                   and c['id']!=target and not (c['revealed'] and TILES[c['loot']].get('ishole')) and (c['revealed'] or op=='swap_tiles')]
            self._prompt(task,'选择交换位置的迷宫（可选0个继续原地探索）' if target else '选择交换的两个迷宫',[self._board_option(c) for c in cells],0 if target else 2,1 if target else 2,optional=not bool(target))
        elif op=='attach_adventurer' and p.get('special_adventurer'):
            options=[dict(value=i,label='安置%s名冒险者（优先使用专用冒险者）'%i) for i in range(1,min(p['available']+1,step.get('max',1))+1)]
            self._prompt(task,'选择安置数量',options,optional=step.get('optional',False))
        else:return super()._execute_step(p,task)

    def _swap(self,a,b):
        # Move the physical tile and its facing together; coordinates/region remain.
        for k in ('loot','revealed','back_star'):a[k],b[k]=b[k],a[k]
        for p in self.state['players']:
            p['private_tiles'].pop(a['id'],None);p['private_tiles'].pop(b['id'],None)

    def _execute_choice_step(self,p,task,values,extra):
        step=task['step'];op=step['op'];source=task['source']
        if op=='siren_discount':
            n=values[0]
            self._enqueue(p,[dict(op='play',discount=2*n,costs=dict(gold_pro=n))],source)
        elif op=='refresh_actions':
            for value in values:
                if value=='hero':
                    p['used']=[u for u in p['used'] if u!='ability']
                else:
                    found=self._source_card(dict(player=p['id'],uid=value))
                    if found:
                        found[3]['used_round']=None
                        p['used']=[u for u in p['used'] if u!='card:%s'%found[2]['id']]
        elif op=='melissa_reveal_play':
            cards=step['cards'];selected=values[0]
            p['hand'].append(cards[selected])
            self.state['discard'] += [c for i,c in enumerate(cards) if i!=selected]
            self._play(p,dict(card=cards[selected],_ignore_extra=True,_ignore_requirements=True),free=True)
        elif op=='pen_reveal_use':
            # 恶魔羽毛笔：被选卡只结算「打出时效果」，不进疆域、不获得标记；两张翻开卡全部弃牌。
            cards=step['cards'];chosen=cards[values[0]]
            self.state['discard'] += list(cards)
            card=CARDS[chosen]
            action=dict(_source=source,_context=dict(origin='card',on_play=True))
            self._effects(p,{k:deepcopy(v) for k,v in card.items() if k not in ('costs','tags')},action)
            civ=self.state['civ']
            for rule in card.get('conditional',[]):
                if rule.get('civ_min',1)<=civ<=rule.get('civ_max',10**9) and self._requirements(p,rule.get('requirements',{})):
                    self._effects(p,rule.get('effect',{}),action)
        elif op in ('restore_cards','return_played','repeat_card'):
            for uid in values:
                found=self._source_card(dict(player=p['id'],uid=uid))
                if not found:continue
                owner,i,card,meta=found
                if op=='restore_cards':meta['face_down']=False;p['strength']+=step.get('strength_each',0)
                elif op=='return_played':
                    p['available']+=meta['adventurers']-int(p.get('special_attached')==meta['uid'])
                    if p.get('special_attached')==meta['uid']:p['special_attached']=None;p['special_adventurer']=True
                    p['hand'].append(p['played'].pop(i));p['card_states'].pop(i)
                else:self._enqueue(p,[dict(op='repeat_play',card=card['id'],civ=self.state['civ'])],dict(player=p['id'],uid=uid))
        elif op=='hero_attach_tile':
            tile=p['tiles'].pop(values[0]);p['hero_tiles'].append(tile);p['gold']+=8;p['strength']+=int(TILES[tile].get('point',0)>0)
        elif op=='consume_tiles' and p['hero']=='horn_black':
            real=[i for i in values if type(i) is int];pot=len(values)-len(real)
            if p['pot']<pot:raise ValueError('用于代替板块的秘药不足。')
            p['pot']-=pot
            super()._execute_choice_step(p,task,real,extra)
            for _ in range(pot):self._effects(p,step.get('per',{}),dict(_source=source))
        elif op=='hero_sacrifice_play':
            tile=p['tiles'].pop(values[0]);self._emit(p,'consume_tile',dict(tile=tile));self._pay(p,dict(strength=1))
            self._enqueue(p,[dict(op='play',free=True,filter=dict(price_max=14))],source)
        elif op=='vee_build':
            p['_build_discount']=min(15,3*self._tags(p)['scrap'])
            try:self._build(p,values[0])
            finally:p.pop('_build_discount',None)
        elif op in ('swap_tiles','chris_explore_swap'):
            if values:
                a=step['payment']['step']['tile'] if op=='chris_explore_swap' else values[1]
                self._swap(self._cell(a),self._cell(values[0]))
            if op=='chris_explore_swap':self.state['effects'].insert(0,step['payment'])
        elif op=='attach_adventurer' and p.get('special_adventurer'):
            found=self._source_card(source)
            if found and not found[3]['face_down']:
                p['available']-=values[0]-1;p['special_adventurer']=False;p['special_attached']=found[3]['uid'];found[3]['adventurers']+=values[0]
                self._effects(p,step.get('effect',{}),dict(_source=source))
        else:return super()._execute_choice_step(p,task,values,extra)

    def score_breakdown(self,player_id):
        result=super().score_breakdown(player_id);p=self._player(player_id)
        result['loot']+=sum(self._points(p,TILES[t]) for t in p.get('hero_tiles',[]))
        return result

    def view(self,player_id=None,reveal=False):
        view=super().view(player_id,reveal)
        for p in view['players']:
            p['hero_deck_count']=len(p.pop('hero_deck',[]))
        return view
