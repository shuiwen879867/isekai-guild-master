"""Ordered resolution for the alternative prints in guild_screenshot_heroes."""
from copy import deepcopy
from guild_content import CARDS,HEROES,TILES


class ScreenshotRules:
    def _effects(self,p,effects,action=None):
        previous=p['str_pro']
        super()._effects(p,effects,action)
        if p['hero']=='frida_revised_black' and p['str_pro']>previous:
            p['gold']+=3*(p['str_pro']-previous)

    def _play(self,p,action,free=False):
        card=CARDS.get(action.get('card'),{})
        super()._play(p,action,free)
        if p['hero']=='sif_revised_white' and not card.get('tags'):
            p['gold']+=3
        if p['hero']=='frida_revised_white' and card.get('price',-1)%10 in (3,6,9):
            p['gold']+=3

    def _gain_tags(self,p,tags,store=True,origin=None):
        previous=self._tags(p).copy()
        # A newly played card is already in played when its printed tags emit.
        if not store and origin=='card':previous.subtract(tags)
        super()._gain_tags(p,tags,store,origin)
        reward=HEROES[p['hero']].get('screenshot_sets',0)
        if reward:
            now=self._tags(p)
            earned=min(now[k] for k in ('civ','gold','scrap'))-min(previous[k] for k in ('civ','gold','scrap'))
            p['gold']+=max(0,earned)*reward

    def can_explore(self,player_id,tile_id,allow_hole=False):
        p=self._player(player_id);mode=p.get('_print_explore')
        if mode and self._cell(tile_id).get('boss'):return False
        if mode and mode.get('remote'):
            c=self._cell(tile_id)
            return (c['owner'] is None and not c.get('boss') and not self._tile_locked(c)
                    and (p['available']>0 or p.get('lab_ready'))
                    and (allow_hole or not c['revealed'] or not TILES[c['loot']].get('ishole')))
        return super().can_explore(player_id,tile_id,allow_hole)

    def _exploration_cost(self,p,cell,stars,was_revealed,discount=0,flash=False,explain=False):
        mode=p.get('_print_explore',{})
        if mode.get('no_star'):stars=0
        if mode.get('point_discount') and self._region(cell)<=2:discount+=mode['point_discount']
        return super()._exploration_cost(p,cell,stars,was_revealed,discount,flash,explain)

    def _prepare_explore(self,p,task):
        mode=p.get('_print_explore',{})
        ready=super()._prepare_explore(p,task)
        if not ready and mode.get('hole_retry') and TILES[self._cell(task['step']['tile'])['loot']].get('ishole'):
            # The printed retry replaces the hole action, without granting an
            # additional ordinary action on top of the new exploration.
            p['extra_actions']=max(0,p['extra_actions']-1)
            self._enqueue(p,[dict(op='explore',optional=True,hole_extra=False)],task['source'])
        return ready

    def _complete_action_frame(self):
        super()._complete_action_frame()
        if not self.state.get('action_frame') and not self.state.get('pending') and not self.state.get('effects'):
            for p in self.state['players']:p.pop('_print_explore',None)

    def _execute_step(self,p,task):
        step,source=task['step'],task['source'];op=step['op']
        if op=='screenshot_sif_income':
            p['gold']+=2*(self._stat(p,'untagged')//3+self._tags(p)['character'])
        elif op=='screenshot_frida_strength':
            p['strength']+=3 if any(c['owner']==p['id'] and self._region(c)>=3 for c in self.state['board']) else 1
        elif op=='screenshot_tag_money':
            p['gold']+=min(30,sum(self._tags(p)[k] for k in ('civ','gold','scrap')))
        elif op=='screenshot_bell_extra':
            self._enqueue(p,[dict(op='pay_resource',resource='strength',min=1,max=2,per=dict(gold=8),optional=True),dict(op='extra_action')],source)
            p['used']=[u for u in p['used'] if u!='ability']
        elif op=='screenshot_explore':
            p['_print_explore']=dict(step,remote=False)
            self._enqueue(p,[dict(op='explore',optional=step.get('optional',False),hole_claim=step.get('allow_hole',False))],source)
        elif op in ('screenshot_recall','screenshot_sif_blank','screenshot_build'):
            cells=[]
            for c in self.state['board']:
                if self._tile_locked(c) or c.get('boss'):continue
                if op=='screenshot_recall':eligible=c['owner']==p['id'] and not c['base']
                elif op=='screenshot_sif_blank':eligible=c['owner'] is None and c['revealed'] and c['loot']=='tile21' and p['available']>0
                else:eligible=c['owner']==p['id'] and not c['base'] and self._region(c)<=2
                if eligible:cells.append(self._board_option(c))
            self._prompt(task,{'screenshot_recall':'收回一枚已探索冒险者并补为空白','screenshot_sif_blank':'支配一块空白板块（不限制邻接）','screenshot_build':'将至多两个名声2以下区域据点化'}[op],cells,
                         0 if step.get('optional') else 1,step.get('max',1),optional=step.get('optional',False))
        elif op=='screenshot_attach':
            options=[dict(value=i,label=TILES[t]['name'],image=TILES[t].get('source')) for i,t in enumerate(p['tiles']) if t!='boss' and not TILES[t].get('boss')]
            self._prompt(task,'放置1块迷宫，获得8金币及等于名声的秘药',options)
        elif op=='screenshot_horn_start':
            cards=self._draw(4);task['step']['cards']=cards
            self._prompt(task,'免费保留一张初始事件，其余可在情报阶段购买',[self._card_option(c,i) for i,c in enumerate(cards)])
        elif op=='screenshot_horn_flip':
            options=[]
            for i,cid in enumerate(p['played']):
                if self._card_states(p)[i]['face_down']:
                    check=deepcopy(p);check['hand'].append(cid)
                    if self._can_nested_play(check,cid,dict(discount=10)):options.append(self._card_option(cid,self._card_states(p)[i]['uid']))
            self._prompt(task,'选择背面事件：按正常条件打出，金币费用减少10',options,optional=True)
        elif op=='screenshot_lazy_develop':
            options=[dict(value=k,label=k) for k,v in self.rules['development_slots'].items() if k not in p['developed']]
            if not self._affordable(p,dict(gold=5+self.state['civ'])):raise ValueError('懒散生活需要5＋当前文明值的金币。')
            self._prompt(task,'选择符合条件的发展格，冒险者留在懒散生活上',options)
        elif op=='screenshot_lazy_finish':
            for i,card,meta in self._active_cards(p):
                if card.get('printed_code')=='Z-003':
                    n=meta['adventurers'];meta['adventurers']=0;p['available']+=n
                    self._effects(p,dict(gold=15*n,draw=n),dict(_source=source))
                    self._flip(self._source(p,i));break
            self._effects(p,dict(civ=-3),dict(_source=source))
        else:return super()._execute_step(p,task)

    def _execute_choice_step(self,p,task,values,extra):
        op,source=task['step']['op'],task['source']
        if op in ('screenshot_recall','screenshot_sif_blank','screenshot_build'):
            for value in values:
                c=self._cell(value)
                if op=='screenshot_recall':
                    c.update(owner=None,base=False,loot='tile21',revealed=True,back_star=1);p['available']+=1
                elif op=='screenshot_sif_blank':
                    self._take_loot(p,'tile21',dict(no_miasma=True));c.update(owner=p['id'],base=False);p['available']-=1
                else:self._build(p,value,free=True,no_surcharge=True)
        elif op=='screenshot_attach':
            t=p['tiles'].pop(values[0]);p['hero_tiles'].append(t);p['gold']+=8;p['pot']+=max(0,TILES[t].get('point',0))
        elif op=='screenshot_horn_start':
            cards=task['step']['cards'];p['hand'].append(cards[values[0]])
            p['offered'] += [c for i,c in enumerate(cards) if i!=values[0]]
        elif op=='screenshot_horn_flip':
            if values:
                found=self._source_card(dict(player=p['id'],uid=values[0]))
                if not found:raise ValueError('背面事件已失效。')
                owner,i,card,meta=found
                if not meta['face_down']:raise ValueError('只能翻开背面事件。')
                p['played'].pop(i);p['card_states'].pop(i);p['hand'].append(card['id'])
                self._enqueue(p,[dict(op='play_payment',card=card['id'],discount=10)],source)
        elif op=='screenshot_lazy_develop':
            self._pay(p,dict(gold=5+self.state['civ']))
            self._develop(p,1,dict(slots=values),free=True)
            found=self._source_card(source)
            if found:found[3]['adventurers']+=1;p['available']-=1
            self._effects(p,dict(civ=1),dict(_source=source))
        else:return super()._execute_choice_step(p,task,values,extra)
