"""Full-deck rules layered over the shared board/season primitives."""
from collections import Counter
from copy import deepcopy

from guild_content import CARDS, HEROES, TILES, POTIONS, ACHIEVEMENTS
from guild_resolution import ResolutionRules, RESOURCES


class FullRules(ResolutionRules):
    def _feedback(self, kind, message, p):
        serial = self.state.get('feedback', {}).get('id', 0) + 1
        self.state['feedback'] = dict(id=serial, kind=kind, message=message, player=p['id'])

    def _sell(self, p, action):
        pending = self.state.get('pending')
        if action['type'] == 'sell_event':
            card = action.get('card')
            if type(card) is not int or card not in p['hand']:
                raise ValueError('只能售卖自己手中的事件卡。')
            task = pending['task'] if pending and pending['player'] == p['id'] else {}
            step = task.get('step', {})
            if step.get('op') == 'play_payment' and step.get('card') == card and p['hand'].count(card) == 1:
                raise ValueError('这张卡已进入出牌结算，不能同时售卖；可以卖其他手牌。')
            p['hand'].remove(card)
            if not CARDS[card].get('special'):self.state['discard'].append(card)
            p['gold'] += 1
            message = '%s售卖一张事件卡，获得1金币（不消耗行动）。' % p['name']
            self._log(message, p)
        else:
            super()._apply(p['id'], action)
            message = '%s售卖一张王权卡，获得%s金币（不消耗行动）。' % (p['name'],self.rules['discard_achievement_gold'])
        self._feedback('coin', message, p)
        # Hand-index prompts must be regenerated after a sale. Never replay
        # reveal/payment steps: that could change the hidden-board context.
        if pending and pending['player'] == p['id'] and pending['task']['step']['op'] in (
                'discard_draw', 'discard_gain', 'play_facedown', 'play', 'achievement'):
            self.state['pending'] = None
            self.state['effects'].insert(0, pending['task'])
            self._drain_effects()
            self._complete_action_frame()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._resolution_init()
        for p in self.state['players']:
            hero = HEROES[p['hero']]
            # Initial unlocks use normal affection rewards after the effect
            # queue is ready. Their bonus cards never enter the setup draft.
            if hero.get('initial_development'):
                self._develop(p,1,dict(slots=[hero['initial_development']]),free=True)
            if hero.get('initial_special'):
                cards = [c for c,d in CARDS.items() if d['name']==hero['initial_special'] and d.get('special')]
                if not cards:
                    raise ValueError('缺少角色专属事件卡。')
                p['hand'].append(cards[0])
            self._enqueue(p,hero.get('initial_steps',[]),dict(player=p['id'],hero=p['hero']))
        self._drain_effects()

    def research_price(self, player_id, count):
        p = self._player(player_id)
        passive = HEROES[p['hero']].get('passive',{})
        if self.state['round']==1 and passive.get('initial_research_free'):
            return 0
        return max(0,count-passive.get('research_free',0))*self.rules['research_cost']

    def _apply(self, player_id, action):
        p = self._player(player_id)
        kind = action['type']
        if any(str(k).startswith('_') for k in action):
            raise ValueError('不能提交内部规则参数。')
        if self.state['phase']=='finished':
            raise ValueError('对局已经结束。')
        if kind in ('sell_event', 'discard_achievement'):
            self._sell(p, action)
            return
        if kind=='payment_preference':
            amount = action.get('strength',0)
            if not self._has_passive(p,'strength_as_gold') or type(amount) is not int or not 0<=amount<=p['strength']:
                raise ValueError('力量折抵数量无效。')
            if self.state.get('pending') and self.state['pending']['player']!=player_id:
                raise ValueError('请等待当前效果结算。')
            p['gold_payment_strength'] = amount
            return
        if kind=='choice':
            self._resolve_choice(p,action)
            self._complete_action_frame()
            return
        if kind == 'exchange':
            amount=action.get('amount',1)
            if type(amount) is not int or amount<1 or amount>p['pot']:
                raise ValueError('没有足够的实际秘药可供售卖。')
            # Selling potions is a free operation, including exploration payment.
            super()._apply(player_id,action)
            return
        if self.state.get('pending'):
            raise ValueError('请先完成当前卡牌效果。')
        if kind == 'exchange':
            super()._apply(player_id,action)
            return
        if kind=='research':
            if self.state['phase']!='research' or p['researched']:
                raise ValueError('现在不能进行情报收集。')
            cards = action.get('cards',[])
            self._check_cards(cards,p['offered'])
            passive = HEROES[p['hero']].get('passive',{})
            if self.state['round']==1 and len(cards)>passive.get('initial_research_limit',12 if self.rules['options'].get('solo_difficulty')=='super' else 8):
                raise ValueError('超过该角色开局可保留的情报数量。')
            self._pay(p,{'gold':self.research_price(player_id,len(cards))})
            p['hand'].extend(cards)
            self.state['discard'].extend((Counter(p['offered'])-Counter(cards)).elements())
            p.update(offered=[],researched=True)
            self._log('%s保留%s张情报卡。' % (p['name'],len(cards)),p)
            if all(x['researched'] for x in self.state['players']):
                self.state.update(phase='action',turn=self.state['start_player'])
                if not self.rules['options'].get('solo'):
                    order = [(self.state['start_player']+i)%len(self.state['players']) for i in range(len(self.state['players']))]
                    pre = [i for i in order if self._has_passive(self.state['players'][i],'season_pre_action')
                           and not self.state['players'][i].get('withdrawn')
                           and self.state['players'][i].get('timeout_round') != self.state['round']]
                    if pre:
                        self.state['season_pre_actions'] = pre
                        self.state['turn'] = pre[0]
            return
        phase = self.state['phase']
        index = self.state['turn']
        if phase not in ('action','final') or self.state['players'][index]['id'] != player_id or p['passed']:
            raise ValueError('现在不是你的行动回合。')
        self.state['action_frame'] = self.state.pop('sequence_origin', None) or dict(player=player_id,index=index,phase=phase)
        outcome = 'ok'
        if kind=='play':
            self._play(p,action)
        elif kind=='explore':
            # All explorations use the same payment choice, including those
            # granted by cards. The target is public; its face is not leaked.
            cell = self._cell(action.get('tile'))
            if not self.can_explore(player_id,cell['id']):
                raise ValueError('不能探索这个位置。')
            self._enqueue(p,[dict(op='explore_payment',tile=cell['id'],
                                  discount=action.get('_discount',0)+p.pop('next_explore_discount',0))])
        elif kind=='build':
            self._build(p,action.get('tile'))
        elif kind=='develop':
            self._develop(p,action.get('count',len(action.get('slots',[]))),action)
        elif kind=='potion':
            self._potion(p,action)
        elif kind=='ability':
            hero = HEROES[p['hero']]
            ability = hero.get('ability',{})
            if not ability or 'ability' in p['used'] or p['hero_level']>ability.get('max_level',3):
                raise ValueError('看板娘能力当前不可用。')
            self._effects(p,ability,dict(action,_source=dict(player=p['id'],hero=p['hero'])))
            p['used'].append('ability')
        elif kind=='card_action':
            card_id = action.get('card')
            copies = [(i,c,m) for i,c,m in self._active_cards(p) if c['id']==card_id and c.get('available',False) and c.get('action') and m.get('used_round')!=self.state['round']]
            if not copies:
                raise ValueError('没有可用的卡牌特别行动。')
            i, card, meta = copies[0]
            effect = card['action']
            if not self._requirements(p,effect.get('requirements',{})) or len(self.state['players'])<effect.get('min_players',1):
                raise ValueError('尚未满足该特别行动的条件。')
            self._effects(p,effect,dict(action,_source=self._source(p,i),_context=dict(origin='card')))
            meta['used_round'] = self.state['round']
            p['used'].append('card:%s'%card_id)
        elif kind=='achievement':
            self._achievement(p,action)
        elif kind=='pass':
            if not self.state.get('season_pre_actions'):
                self._on_pass(p)
            p.update(passed=True,extra_actions=0)
        else:
            self._variant_action(p,action)
        if p['first_action_round'] != self.state['round'] and phase=='action':
            p['first_action_round'] = self.state['round']
            if kind!='pass' and self._has_passive(p,'season_first_extra'):
                p['extra_actions'] += 1
        self.state['action_count'] += 1
        self.state['last_action'] = dict(player=player_id,type=kind,outcome=outcome)
        names = dict(play='打出事件卡',explore='开始探索',build='建设据点',develop='发展公会',potion='使用秘药',ability='使用看板娘能力',card_action='使用特别行动',achievement='完成王权',hire='雇用冒险者',scout='派遣侦查队',monster_hunt='讨伐魔兽',dragon_hunt='讨伐潜行之龙',forest_purify='净化洞穴')
        if kind != 'play':
            self._log('%s：%s。' % (p['name'],names.get(kind,'休店')),p)
        self._drain_effects()
        self._complete_action_frame()

    def _complete_action_frame(self):
        if self.state.get('pending') or self.state.get('effects'):
            return
        frame = self.state.get('action_frame')
        if not frame:
            return
        p = self._player(frame['player'])
        index = frame['index']
        if (p.get('withdrawn') or p.get('timeout_round') == self.state['round']) and not p['passed']:
            self._on_pass(p)
            p.update(passed=True,extra_actions=0)
            self._drain_effects()
            if self.state.get('pending') or self.state.get('effects'):
                return
        self.state['action_frame'] = None
        if not p['passed'] and p['extra_actions']:
            p['extra_actions'] -= 1
            self.state['sequence_origin'] = frame
            self._log('%s执行额外行动。' % p['name'],p)
            return
        if self.state.pop('solo_final_action',False):
            self._finish()
            return
        if self.state.get('season_pre_actions'):
            self.state['season_pre_actions'].pop(0)
            # Declining the preliminary action does not close the normal turn.
            p['passed'] = bool(p.get('withdrawn') or p.get('timeout_round') == self.state['round'])
            if self.state['season_pre_actions']:
                self.state['turn'] = self.state['season_pre_actions'][0]
            elif all(other['passed'] for other in self.state['players']):
                self._season()
            else:
                self._next_turn(self.state['start_player']-1)
            return
        if frame['phase']=='final':
            self.state['final_remaining'][index] = 0 if p['passed'] else max(0,self.state['final_remaining'][index]-1)
            self.state['final_actions_taken'] += 1
            if any(self.state['final_remaining']):
                self._next_turn(index,final=True)
            elif not self.state.get('final_bonus_started'):
                self.state['final_bonus_started'] = True
                for i,other in enumerate(self.state['players']):
                    level = HEROES[other['hero']].get('passive',{}).get('final_extra_level',99)
                    hero_extra = other['hero_level'] >= level
                    if hero_extra:
                        other['gold'] += HEROES[other['hero']].get('passive',{}).get('final_extra_gold',0)
                    bonus_extra = 0
                    for _,c,m in self._active_cards(other):
                        bonus = c.get('final_bonus') or {}
                        if bonus:
                            other['gold'] += bonus.get('gold',0)
                            bonus_extra += int(bonus.get('action',0))
                            self._log('%s的「%s」发动，获得%s金币并再执行一次主要行动。' % (other['name'],c['name'],bonus.get('gold',0)),other)
                    if hero_extra or bonus_extra:
                        other['passed'] = False
                        self.state['final_remaining'][i] = (1 if hero_extra else 0) + bonus_extra
                if any(self.state['final_remaining']):
                    self._next_turn(index,final=True)
                else:
                    self._finish()
            else:
                self._finish()
        elif self.state['miasma'] <= self.state['civ']+1 and not self.rules.get('options',{}).get('solo'):
            self._begin_final(index,'tracks')
        elif all(other['passed'] for other in self.state['players']):
            if self.state['max_rounds'] and self.state['round']>=self.state['max_rounds']:
                self._begin_final(index,'round_limit')
            else:
                self._season()
        else:
            self._next_turn(index)

    def _play(self,p,action,free=False):
        card_id = action.get('card')
        if type(card_id) is not int or card_id not in CARDS or card_id not in p['hand']:
            raise ValueError('手中没有这张事件卡。')
        card = CARDS[card_id]
        if not card.get('available',False):
            raise ValueError(card.get('unavailable_reason') or '该事件卡暂未开放。')
        req={} if action.get('_ignore_requirements') else {'tags':card.get('requirements',{}).get('tags',{})} if action.get('_ignore_non_tag_requirements') else card.get('requirements',{})
        if not self._requirements(p,req,True):
            raise ValueError('尚未满足事件卡的前置条件。')
        strength = action.get('strength',0)
        if type(strength) is not int or strength<0 or (strength and (free or not (card.get('can_trans') or self._has_passive(p,'strength_as_gold')))):
            raise ValueError('此卡不能使用所选力量折抵。')
        ignore = action.get('_ignore_extra',False)
        multiplier = 2 if action.get('double') else 1
        count = 0 if ignore else card.get('consume_piece',0)*multiplier
        tile_pot = min(count,p['pot']) if p['hero']=='horn_black' and p.get('prefer_pot') else max(0,count-len(p['tiles'])) if p['hero']=='horn_black' else 0
        count -= tile_pot
        pieces = action.get('pieces',p['tiles'][:count])
        if not isinstance(pieces,list) or len(pieces)!=count or Counter(pieces)-Counter(p['tiles']):
            raise ValueError('请选择所需数量的持有迷宫板块。')
        costs = Counter(action.get('_ability_costs',{}))
        if not ignore:
            costs.update({k:v*multiplier for k,v in card.get('costs',{}).items()})
        costs.update(pot=tile_pot)
        discount = action.get('_discount',0)
        maximum = 0 if free else (max(0,card['price']*multiplier-discount)+4)//5
        if strength > maximum:
            raise ValueError('力量折抵超过费用上限，本次最多使用%s点力量。' % maximum)
        costs.update(gold=0 if free else max(0,card['price']*multiplier-discount-5*strength),strength=strength)
        for tile in pieces:
            p['tiles'].remove(tile)
            self._emit(p,'consume_tile',dict(tile=tile))
        self._pay(p,costs)
        p['hand'].remove(card_id)
        p['played'].append(card_id)
        source = self._source(p,len(p['played'])-1)
        context = dict(origin='card',uid=source['uid'],consumed=pieces,discounted=bool(free or discount),
                       price=card['price'],has_point=bool(card.get('point') or card.get('scoring')))
        original_civ = self.state['civ']
        self._log('%s打出事件卡《%s》。' % (p['name'],card['name']),p)
        self._gain_tags(p,card.get('tags',[]),store=False,origin='card')
        self._emit(p,'play',context)
        context['on_play']=True
        effects = {k:deepcopy(v) for k,v in card.items() if k not in ('costs','tags')}
        self._effects(p,effects,dict(action,_source=source,_context=context))
        for cond in card.get('conditional',[]):
            if cond.get('civ_min',1)<=original_civ<=cond.get('civ_max',original_civ) and self._requirements(p,cond.get('requirements',{})):
                self._effects(p,cond.get('effect',{}),dict(action,_source=source,_context=context))

    def _develop(self,p,count,action,free=False):
        if type(count) is not int or count<1 or p['affection']+count>5:
            raise ValueError('发展次数超出可解锁的好感度。')
        selected = action.get('slots',[])
        slots = self.rules['development_slots']
        if not isinstance(selected,list) or len(selected)!=count or any(type(s) is not str for s in selected) or len(set(selected))!=count or any(s not in slots or s in p['developed'] for s in selected):
            raise ValueError('请选择尚未解锁且不重复的发展条件。')
        costs = Counter()
        if not free:
            for slot in selected:
                if not self._requirements(p,slots[slot].get('requirements',{})):
                    raise ValueError('尚未满足发展条件。')
                costs.update(slots[slot].get('costs',{}))
        self._pay(p,costs)
        p['hand'].extend(self._draw(count))
        hero = HEROES[p['hero']]
        for slot in selected:
            p['developed'].append(slot)
            p['affection'] += 1
            p['available'] += 1
            p['strength'] += hero.get('passive',{}).get('on_affection_strength',0)
            self._emit(p,'affection')
            level = {2:2,5:3}.get(p['affection'])
            if level:
                p['hero_level'] = level
                upgrade = deepcopy(hero.get('upgrade%s'%level,{}))
                special = []
                if 'claim_hidden_star' in upgrade or upgrade.get('claim_hidden_tile'):
                    special.append(dict(op='claim_replace',concealed=True,reduce_miasma=True))
                if 'claim_achievement_discount' in upgrade:
                    special.append(dict(op='achievement',discount=upgrade['claim_achievement_discount']))
                self._enqueue(p,[dict(op='effect',effect=upgrade)]+special,dict(player=p['id'],hero=p['hero']))
                self._emit(p,'upgrade',dict(level=level))

    def _potion(self,p,action):
        option = action.get('option')
        if option not in POTIONS or (not action.get('_ignore_slot') and option in self.state['potions_used']+self.state['potions_disabled']):
            raise ValueError('该秘药格目前不可用。')
        potion = POTIONS[option]
        if option=='build':
            # 2026-10-26 修复：只看「有营地」放行不够——若所有营地都支付不起邻接追加费用，
            # 接下来的据点选择将没有任何可选目标（选择界面会过滤付不起的格子），秘药会被扣掉却毫无效果。
            # 这里把「付得起追加费用」一并纳入前置判断，不满足直接拒绝：秘药不消耗、弹窗提示后玩家继续选择其他行动。
            camps=[cell for cell in self.state['board'] if cell['owner']==p['id'] and not cell['base']]
            if not camps:
                raise ValueError('没有可以据点化的营地，秘药未消耗。')
            if not any(self._affordable(p,{'gold':max(0,self.build_cost(p['id'],cell['id'])-self.rules['build_cost'])}) for cell in camps):
                raise ValueError('据点化追加费用全部无法支付，秘药未消耗。')
        if option=='free_card' and not any(self._card_filter(CARDS[c],{}) and self._requirements(p,CARDS[c].get('requirements',{}),True) and self._can_nested_play(p,c,{}) for c in set(p['hand'])):
            raise ValueError('没有可以免费打出的事件卡，秘药未消耗。')
        self._pay(p,{'pot':potion['cost']})
        if not action.get('_preserve_slot') and option not in self.state['potions_used']:
            self.state['potions_used'].append(option)
        if option=='free_card':
            self._enqueue(p,[dict(op='play',free=True)],action.get('_source'))
        elif option=='build':
            # 秘药据点化必须完成一次建设：前置检查已保证至少有一个付得起的目标，
            # 不再允许略过（旧版可选略过会被白扣秘药）。
            self._enqueue(p,[dict(op='build',free=True,optional=False)],action.get('_source'))
        else:
            self._effects(p,potion.get('effect',{}),action)

    def _achievement(self,p,action,discount=0):
        super()._achievement(p,action,discount)
        self._emit(p,'achievement')

    def _take_loot(self,p,loot_id,action=None):
        action = action or {}
        loot = TILES[loot_id]
        p['tiles'].append(loot_id)
        effects = {k:v for k,v in loot.items() if k!='tags'}
        self._gain_tags(p,loot.get('tags',[]),store=False,origin='tile')
        self._effects(p,effects,action)
        if self.state['phase']!='final' and not action.get('no_miasma'):
            self.state['miasma'] = max(0,self.state['miasma']-loot.get('star',0))
        self._emit(p,'gain_tile',dict(hole=bool(loot.get('ishole')),tile=loot_id))
        if loot.get('treasure'):
            self._enqueue(p,[dict(op='treasure')],action.get('_source'))

    def _bases(self,p):
        return super()._bases(p)+int(bool(p.get('lab')))

    def build_cost(self,player_id,tile_id):
        p, cell = self._player(player_id), self._cell(tile_id)
        if cell['owner']!=player_id or cell['base']:
            raise ValueError('只能在自己尚未建设据点的领地建设。')
        neighbors = [n for n in self._neighbors(cell) if n['base'] and (n['owner']!=player_id or not self._has_passive(p,'own_base_no_surcharge'))]
        labs = self._adjacent_labs(cell)
        if self._has_passive(p,'own_base_no_surcharge'):
            labs = [other for other in labs if other['id']!=player_id]
        return self.rules['build_cost']+self.rules['adjacent_base_cost']*(len(neighbors)+len(labs))

    def _build(self,p,tile_id,free=False,no_surcharge=False):
        cost = self.build_cost(p['id'],tile_id)
        if no_surcharge:
            cost = self.rules['build_cost']
        self._pay(p,{'gold':max(0,cost-self.rules['build_cost']) if free else cost})
        self._cell(tile_id)['base'] = True
        self._emit(p,'build')

    @staticmethod
    def _hex_distance(a,b):
        q,r = a['q']-b['q'],a['r']-b['r']
        return max(abs(q),abs(r),abs(q+r))

    def _adjacent_labs(self,cell):
        return [p for p in self.state['players'] if p.get('lab') and self._hex_distance(cell,p['lab'])==1]

    def _remote_discount(self,cell):
        if any(n['owner'] is not None for n in self._neighbors(cell)):
            return None
        for other in self.state['players']:
            for _,card,_ in self._active_cards(other):
                passive = card.get('global_passive',{})
                if passive.get('remote_region') == self._region(cell):
                    return passive.get('remote_discount',0)
        return None

    def can_explore(self,player_id,tile_id,allow_hole=False):
        try:
            p,cell = self._player(player_id),self._cell(tile_id)
        except ValueError:
            return False
        if self._tile_locked(cell) or cell['owner'] is not None or (p['available']<=0 and not p.get('lab_ready')):
            return False
        if cell['revealed'] and TILES[cell['loot']].get('ishole') and not allow_hole and not self._has_passive(p,'claim_holes'):
            return False
        return len(self._neighbors(cell))<6 or any(n['owner']==player_id for n in self._neighbors(cell)) or any(x['id']==player_id for x in self._adjacent_labs(cell)) or self._remote_discount(cell) is not None

    def _exploration_cost(self,p,cell,stars,was_revealed,discount=0,flash=False,explain=False):
        neighbors = sum(self._visible_stars(n) for n in self._neighbors(cell) if n['owner'] is None)
        value = 5*((0 if flash and not cell.get('boss') else stars)+neighbors)
        star_discounts=[]
        for passive in self._passives(p):
            if was_revealed:
                discount += passive.get('explore_revealed_discount',0)
            threshold = passive.get('explore_stars_discount',{})
            if stars >= threshold.get('min',10**9):
                discount += threshold.get('discount',0)
                star_discounts.append(dict(min=threshold['min'],amount=threshold.get('discount',0)))
            region = passive.get('explore_region_discount',{})
            if region.get('region')==self._region(cell):
                discount += region.get('discount',0)
            if was_revealed and TILES[cell['loot']].get('point',0)>0:
                discount += passive.get('explore_point_discount',0)
            if any(n['base'] and n['owner']==p['id'] for n in self._neighbors(cell)) or any(x['id']==p['id'] for x in self._adjacent_labs(cell)):
                discount += passive.get('explore_adjacent_base_discount',0)
        discount += self._remote_discount(cell) or 0
        total=max(10,value-discount)
        if explain:
            return dict(raw_gold=value,discount=discount,gold=total,minimum_adjustment=max(0,10-(value-discount)),
                        target_stars=stars,star_discounts=star_discounts)
        return total

    def explore_preview(self,player_id,tile_id,strength=0):
        p,cell = self._player(player_id),self._cell(tile_id)
        if type(strength) is not int or not 0<=strength<=p['strength']:
            raise ValueError('力量数量无效。')
        stars = self._visible_stars(cell)
        known = cell['revealed']
        possible = [t.get('star',0) for t in TILES.values()]
        cost = lambda n:max(0,self._exploration_cost(p,cell,n,known)-5*strength)
        return dict(eligible=self.can_explore(player_id,tile_id),cost=cost(stars),min_cost=cost(stars if known else min(possible)),
                    max_cost=cost(stars if known else max(possible)),uncertain=not known,stars=stars,
                    neighbor_stars=sum(self._visible_stars(n) for n in self._neighbors(cell) if n['owner'] is None),strength=strength)

    def _prepare_explore(self,p,task):
        cell = self._cell(task['step']['tile'])
        if not self.can_explore(p['id'],cell['id'],allow_hole=task['step'].get('hole_claim',False)):
            return False
        task['context']['was_revealed'] = cell['revealed']
        if not cell['revealed']:
            cell['revealed'] = True
            self._emit(p,'reveal',dict(hole=bool(TILES[cell['loot']].get('ishole'))))
        if TILES[cell['loot']].get('ishole') and not task['step'].get('hole_claim',False) and not self._has_passive(p,'claim_holes'):
            if task['step'].get('hole_extra',True):
                p['extra_actions'] += 1
            self._log('%s发现了深渊洞穴。' % p['name'],p)
            return False
        return True

    def _explore(self,p,action):
        cell = self._cell(action.get('tile'))
        if not self.can_explore(p['id'],cell['id'],allow_hole=action.get('hole_claim',False)):
            raise ValueError('不能探索这个位置。')
        strength,pot = action.get('strength',0),action.get('pot',0)
        if type(strength) is not int or type(pot) is not int or not 0<=strength<=p['strength'] or not 0<=pot<=p['pot']:
            raise ValueError('探索支付资源不足。')
        ratio = action.get('_potion_strength',0)
        if pot and not ratio:
            raise ValueError('本次探索不能以秘药替代力量。')
        flash = action.get('flash',False)
        if type(flash) is not bool or (flash and (not self._has_passive(p,'flash_explore') or p.get('flash',0)<1)):
            raise ValueError('不能使用一闪。')
        lab = action.get('lab',False)
        if type(lab) is not bool or (lab and not p.get('lab_ready')) or (not lab and p['available']<1):
            raise ValueError('需要可用冒险者或浮空实验室。')
        pieces = action.get('pieces',[])
        if not isinstance(pieces,list) or Counter(pieces)-Counter(p['tiles']) or (pieces and not self._has_passive(p,'tiles_as_strength')):
            raise ValueError('不能使用这些板块抵扣探索费用。')
        was_revealed = action.get('_context',{}).get('was_revealed',cell['revealed'])
        cell['revealed'] = True
        if TILES[cell['loot']].get('ishole') and not action.get('hole_claim',False) and not self._has_passive(p,'claim_holes'):
            return 'hole'
        if flash:
            self._pay(p,{'flash':1})
        base_price = self._exploration_cost(p,cell,TILES[cell['loot']].get('star',0),was_revealed,
                                           action.get('_discount',0),flash)
        reduction = 5*(strength+ratio*pot+len(pieces))
        # Each selected unit must contribute. A final indivisible potion may
        # cover a partial remainder, but no whole resource may be wasted.
        if ((strength or pieces) and reduction-5 >= base_price
                or pot and reduction-5*ratio >= base_price):
            raise ValueError('抵扣已足够，请减少多余的力量、秘药或板块。')
        price = max(0,base_price-reduction)
        costs = dict(gold=price,strength=strength,pot=pot)
        if not self._affordable(p,costs):
            p['retreat'] += self.rules['retreat_penalty']
            if cell.get('boss'):
                cell['revealed'] = False
            message = '%s探索失败，声望-%s（累计撤退扣分%s）。' % (p['name'],self.rules['retreat_penalty'],p['retreat'])
            self._log(message,p)
            self._feedback('retreat',message,p)
            return 'retreat'
        self._pay(p,costs)
        for tile in pieces:
            p['tiles'].remove(tile)
            self._emit(p,'consume_tile',dict(tile=tile))
        if lab:
            p['lab_ready'] = False
        else:
            p['available'] -= 1
        cell.update(owner=p['id'],base=lab,lab=lab)
        loot = cell['loot']
        if self.state['phase']!='final':
            self.state['miasma'] = max(0,self.state['miasma']-TILES[loot].get('star',0))
        reward = dict(op='take_loot',tile=loot)
        discard_reward = sum(x.get('discard_explore_loot_strength',0) for x in self._passives(p))
        if discard_reward:
            self._enqueue(p,[dict(op='branch',options=[dict(label='获得探索板块与奖励',effect=dict(steps=[reward])),
                          dict(label='放弃板块，获得%s力量'%discard_reward,effect=dict(strength=discard_reward))])],action.get('_source'))
        else:
            self._enqueue(p,[reward],action.get('_source'))
        neighbors={n['owner'] for n in self._neighbors(cell) if n['base'] and n['owner'] is not None}
        neighbors.update(other['id'] for other in self._adjacent_labs(cell))
        if neighbors:
            for pid in neighbors|{p['id']}:self._player(pid)['pot']+=1
        self._emit(p,'explore')
        self._log('%s在%s探索成功。' % (p['name'],cell['id']),p)
        self._feedback('explore','%s探索成功。' % p['name'],p)
        return 'explored'

    def _points(self,p,item):
        points = item.get('point',0)
        for rule in item.get('scoring',[]):
            stat = rule['stat']
            if stat.endswith(':self'):
                meta = item.get('_meta',{})
                key = {'attached:self':'adventurers','attached_tiles:self':'tiles','counters:self':'counters'}[stat]
                value = len(meta.get(key,[])) if key=='tiles' else meta.get(key,0)
            else:
                value = self._stat(p,stat)
            if 'threshold' in rule:
                score = rule.get('point',1) if value>=rule['threshold'] else 0
            else:
                score = value//max(1,rule.get('per',1))*rule.get('point',1)
            points += min(score,rule.get('max',10**9))
        return points + sum(self._tags(p)[tag]*value for tag,value in item.get('point_per_tag',{}).items())

    def score_breakdown(self,player_id):
        p = self._player(player_id)
        active = self._active_cards(p)
        grid = sum(self._region(c)*(2 if c['base'] else 1) for c in self.state['board'] if c['owner']==player_id)
        held = p['tiles']+[t for _,_,m in active for t in m['tiles']]
        return dict(hero=HEROES[p['hero']].get('points',0) if p['hero_level']>=3 else 0,grid=grid,
                    loot=sum(self._points(p,TILES[t]) for t in held),
                    cards=sum(self._points(p,dict(c,_meta=m)) for _,c,m in active),
                    achievements=sum(self._points(p,ACHIEVEMENTS[k]) for k in p['earned_achievements']),
                    reputation=p['reputation'],treasures=sum(self.rules['treasures'][k]['point'] for k in p['treasures']),retreat=-p['retreat'])

    def view(self,player_id=None,reveal=False):
        view = super().view(player_id,reveal)
        view['exchange_rate']=self.rules['exchange_rate']
        for cell in view['board']:
            cell['eligible_for'] = [p['id'] for p in self.state['players'] if self.can_explore(p['id'],cell['id'])]
            if player_id is not None:
                if cell['owner']==player_id and not cell['base']:
                    cell['build_gold'] = self.build_cost(player_id,cell['id'])
        for p in view['players']:
            definition = HEROES[p['hero']]
            p['character'],p['variant'] = definition['character'],definition['variant']
            p['research_free'] = definition.get('passive',{}).get('research_free',0)
            p['research_initial_free'] = definition.get('passive',{}).get('initial_research_free',False)
            p['research_initial_limit'] = definition.get('passive',{}).get('initial_research_limit',12 if self.rules['options'].get('solo_difficulty')=='super' else 8)
            p['strength_as_gold'] = self._has_passive(self._player(p['id']),'strength_as_gold')
        return self._resolution_view(view,player_id,reveal)
