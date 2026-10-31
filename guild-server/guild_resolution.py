"""Ordered, JSON-native effect resolution for the full scanned deck.

This module is deliberately independent of Ren'Py and sockets. A choice is
owned by an authenticated player, carries a monotonically increasing ID, and
contains server-generated options. Hidden choices are stripped from views.
"""
from collections import Counter
from copy import deepcopy

from guild_content import CARDS, HEROES, TILES, POTIONS, ACHIEVEMENTS

RESOURCES = ('gold', 'strength', 'pot', 'gold_pro', 'str_pro', 'pot_pro', 'wisdom', 'flash')
LABELS = {'gold': '金币', 'strength': '力量', 'pot': '秘药', 'gold_pro': '金币产能',
          'str_pro': '力量产能', 'pot_pro': '秘药产能', 'wisdom': '睿智', 'flash': '一闪',
          'territory': '控制区域', 'cards': '事件卡'}


class ResolutionRules:
    """Mixin for the rules engine; not a second game-state owner."""

    def _resolution_init(self):
        self.state.update(effects=[], pending=None, choice_serial=0, instance_serial=0,
                          action_frame=None, final_bonus_started=False)
        for p in self.state['players']:
            p.update(card_states=[], extra_actions=0, first_action_round=0,
                     lab=None, lab_ready=False, private_tiles={}, gold_payment_strength=0)
            for key in ('wisdom', 'flash'):
                p[key] = HEROES[p['hero']].get(key, 0)

    def _card_states(self, p):
        # Older in-memory snapshots and developer fixtures have no metadata.
        states = p.setdefault('card_states', [])
        while len(states) < len(p['played']):
            self.state['instance_serial'] = self.state.get('instance_serial', 0) + 1
            states.append(dict(uid=self.state['instance_serial'], face_down=False,
                               adventurers=0, tiles=[], counters=0))
        return states

    def _source(self, p, index):
        return dict(player=p['id'], uid=self._card_states(p)[index]['uid'])

    def _source_card(self, source):
        if not source or 'uid' not in source:
            return None
        for p in self.state['players']:
            for i, meta in enumerate(self._card_states(p)):
                if meta['uid'] == source['uid']:
                    return p, i, CARDS[p['played'][i]], meta
        return None

    def _active_cards(self, p):
        return [(i, CARDS[c], meta) for i, (c, meta) in
                enumerate(zip(p['played'], self._card_states(p))) if not meta['face_down']]

    def _passives(self, p):
        return [HEROES[p['hero']].get('passive', {})] + [c.get('passive', {}) for _, c, _ in self._active_cards(p)]

    def _has_passive(self, p, name):
        return any(x.get(name) for x in self._passives(p))

    def _stat(self, p, stat):
        if stat == 'extra_cost_cards':
            return sum(bool(c.get('costs') or c.get('consume_piece')) for _, c, _ in self._active_cards(p))
        if stat in ('holes', 'holes_or_variable', 'strong_tiles', 'boss_tiles'):
            tiles = p['tiles'] + [t for m in self._card_states(p) if not m['face_down'] for t in m['tiles']]
            if stat == 'holes':
                return sum(bool(TILES[t].get('ishole')) for t in tiles)
            if stat == 'holes_or_variable':
                return sum(bool(TILES[t].get('ishole') or TILES[t].get('variable')) for t in tiles)
            if stat == 'boss_tiles':
                return sum(bool(t == 'boss' or TILES[t].get('boss')) for t in tiles)
            return sum(TILES[t].get('star', 0) >= 2 and t != 'boss' and not TILES[t].get('boss') for t in tiles)
        if stat in ('tiles', 'pieces'):
            return len(p['tiles']) + sum(len(m['tiles']) for m in self._card_states(p) if not m['face_down'])
        if stat == 'earned_achievements':
            return len(p['earned_achievements'])
        if stat == 'untagged':
            return sum(not c.get('tags') and not self._conditional_tags(p, c) for _, c, _ in self._active_cards(p))
        if stat in ('minimum_tags', 'maximum_tags'):
            values = [self._tags(p)[tag] for tag in ('civ', 'gold', 'scrap')]
            return min(values) if stat == 'minimum_tags' else max(values)
        if stat == 'best_event_point':
            # D-014 Phrase百貨：指定一張已打出的正面事件卡，
            # 獲得與該卡目前名聲相同的名聲（含計數/個別卡加減等變動後的值）。
            best = 0
            for _, card, meta in self._active_cards(p):
                rules = [r for r in card.get('scoring', []) if r.get('stat') != 'best_event_point']
                item = dict(card, _meta=meta)
                if len(rules) != len(item.get('scoring', [])):
                    item = dict(item, scoring=rules)
                best = max(best, self._points(p, item))
            return best
        return super()._stat(p, stat)

    def _conditional_tags(self, p, c):
        rule = c.get('conditional_tags', {})
        return rule.get('tags', []) if rule and self._condition(p, rule['condition']) else []

    def _tags(self, p):
        result = Counter(p.get('tags', []))
        for _, card, meta in self._active_cards(p):
            result.update(card.get('tags', []))
            result.update(self._conditional_tags(p, card))
            for t in meta['tiles']:
                result.update(TILES[t].get('tags', []))
        for t in p['tiles']:
            result.update(TILES[t].get('tags', []))
        return result

    def _condition(self, p, cond, context=None):
        context = context or {}
        if 'not' in cond and self._condition(p, cond['not'], context):
            return False
        if 'any' in cond and not any(self._condition(p, c, context) for c in cond['any']):
            return False
        if 'stat' in cond:
            value = self._stat(p, cond['stat'])
            if value < cond.get('min', cond.get('value', 0)) or value > cond.get('max', float('inf')):
                return False
        if 'round' in cond and self.state['round'] != cond['round']:
            return False
        if 'discounted' in cond and bool(context.get('discounted')) != cond['discounted']:
            return False
        return True

    def _requirements(self, p, req, tag_discount=False):
        if not super()._requirements(p, req, tag_discount):
            return False
        return all(self._stat(p, k) >= req[k] for k in
                   ('holes', 'untagged', 'earned_achievements', 'wisdom', 'flash') if k in req)

    def _pay(self, p, costs):
        budget = {k: p.get(k, 0) for k in RESOURCES}
        for key, amount in costs.items():
            if key not in RESOURCES or type(amount) is not int or amount < 0:
                raise ValueError('支付数量无效。')
            budget[key] -= amount
        if costs.get('gold',0)>0 and self._has_passive(p,'strength_as_gold'):
            preferred = min(p.get('gold_payment_strength',0),max(0,budget['strength']),(costs['gold']+4)//5)
            budget['strength'] -= preferred
            budget['gold'] = p['gold'] - max(0,costs['gold']-5*preferred)
        # White Skadi can use strength for every gold payment. Explicitly
        # reserved strength costs are deducted first; excess gives no change.
        if budget['gold'] < 0 and self._has_passive(p, 'strength_as_gold'):
            spend = (-budget['gold'] + 4) // 5
            budget['strength'] -= spend
            budget['gold'] = 0
        for key, amount in budget.items():
            if amount < 0:
                raise ValueError(LABELS[key] + '不足。')
        p.update(budget)
        if costs.get('gold',0)>0:
            p['gold_payment_strength'] = 0

    def _affordable(self, p, costs):
        # Read-only check, including the white Skadi substitution.
        budget = {k: p.get(k, 0) - costs.get(k, 0) for k in RESOURCES}
        if budget['gold'] < 0 and self._has_passive(p, 'strength_as_gold'):
            budget['strength'] -= (-budget['gold'] + 4) // 5
            budget['gold'] = 0
        return all(v >= 0 for v in budget.values())

    def _enqueue(self, p, steps, source=None, context=None, front=False):
        tasks = [dict(player=p['id'], step=deepcopy(step), source=deepcopy(source),
                      context=deepcopy(context or {})) for step in steps]
        queue = self.state.setdefault('effects', [])
        if front:
            queue[:0] = tasks
        else:
            queue.extend(tasks)

    def _emit(self, p, event, context=None):
        context = context or {}
        listeners = [(HEROES[p['hero']], dict(player=p['id'], hero=p['hero']))]
        listeners += [(card, self._source(p, i)) for i, card, _ in self._active_cards(p)]
        for definition, source in listeners:
            for rule in definition.get('triggers', []):
                if rule['event'] != event:
                    continue
                cond = rule.get('condition', {})
                if 'any_tags' in cond and not set(cond['any_tags']).intersection(context.get('tags', [])):
                    continue
                if 'tag' in cond and context.get('tag') != cond['tag']:
                    continue
                if 'any_tag' in cond and context.get('tag') not in cond['any_tag']:
                    continue
                if 'origin' in cond and context.get('origin') != cond['origin']:
                    continue
                if 'hole' in cond and bool(context.get('hole')) != cond['hole']:
                    continue
                if 'price_min' in cond and context.get('price', 0) < cond['price_min']:
                    continue
                if cond.get('has_point') and not context.get('has_point'):
                    continue
                if cond.get('not_self') and context.get('uid') == source.get('uid'):
                    continue
                if 'achievement_total' in cond and len(p['earned_achievements']) != cond['achievement_total']:
                    continue
                self._enqueue(p, [dict(op='effect', effect=rule['effect'])], source, context)

    def _gain_tags(self, p, tags, store=True, origin=None):
        super()._gain_tags(p, tags, store)
        if origin == 'card':
            self._emit(p, 'card_tags', dict(tags=list(tags), origin='card'))
        for tag in tags:
            self._emit(p, 'tag', dict(tag=tag, origin=origin or 'effect'))

    def _effects(self, p, effects, action=None):
        action = action or {}
        source, context = action.get('_source'), action.get('_context', {})
        before = {k:p.get(k,0) for k in RESOURCES}
        before_hand, before_civ = len(p['hand']), self.state['civ']
        base = deepcopy(effects)
        steps = base.pop('steps', [])
        affection = base.pop('affection', 0)
        choices = base.pop('choices', [])
        civ_choice = base.pop('civ_choice', [])
        # All proportional gains (including free plays) have one owner: the
        # core arithmetic. Never also settle them in this resolution layer.
        super()._effects(p, base, action)
        for key in ('wisdom', 'flash'):
            p[key] = max(0, p.get(key, 0) + effects.get(key, 0))
        p['retreat'] = max(0, p['retreat'] + effects.get('retreat', 0))
        if effects.get('civ') and self.state['phase'] != 'final':
            self._emit(p, 'civ', dict(origin=context.get('origin', 'effect')))
        prefix = []
        if affection and p['affection'] < 5:
            prefix.append(dict(op='develop', count=min(5-p['affection'], affection)))
        if choices or civ_choice:
            options = choices or [dict(civ=n) for n in civ_choice]
            prefix.append(dict(op='branch', options=[dict(label=('文明%+d' % e['civ']) if 'civ' in e else '效果%s' % (i+1), effect=e) for i,e in enumerate(options)]))
        self._enqueue(p, prefix + steps, source, context)
        found = self._source_card(source) if source and source.get('uid') else None
        if found:
            changes = ['%s%+d' % (LABELS[k],p.get(k,0)-before[k]) for k in RESOURCES if p.get(k,0)!=before[k]]
            if len(p['hand'])>before_hand:
                changes.append('抽取%s张手牌' % (len(p['hand'])-before_hand))
            if self.state['civ']!=before_civ:
                changes.append('文明%+d' % (self.state['civ']-before_civ))
            if changes:
                self._log('%s的《%s》结算：%s。' % (p['name'],found[2]['name'],'、'.join(changes)),p)

    def _prompt(self, task, title, options, minimum=1, maximum=1, optional=False, mode='select'):
        if len(options) < minimum and mode == 'select':
            self._effects(self._player(task['player']), task['step'].get('otherwise', {}),
                          dict(_source=task['source'], _context=task['context']))
            return
        self.state['choice_serial'] = self.state.get('choice_serial', 0) + 1
        self.state['pending'] = dict(id=self.state['choice_serial'], player=task['player'],
            title=title, options=options, min=minimum, max=min(maximum, len(options)) if mode == 'select' else maximum,
            optional=optional, mode=mode, task=task)

    def _resolve_choice(self, p, action):
        pending = self.state.get('pending')
        if not pending or pending['player'] != p['id'] or action.get('choice_id') != pending['id']:
            raise ValueError('此选择已更新，或不属于你的公会。')
        selected = action.get('selected', [])
        if not isinstance(selected, list) or any(type(i) is not int for i in selected) or len(set(selected)) != len(selected):
            raise ValueError('请选择有效且不重复的项目。')
        if any(i < 0 or i >= len(pending['options']) for i in selected):
            raise ValueError('所选项目不在当前选项中。')
        skipping = action.get('skip') is True
        if skipping and not pending['optional']:
            raise ValueError('当前效果必须完成选择。')
        if not skipping and pending['mode'] in ('select', 'payment') and not pending['min'] <= len(selected) <= pending['max']:
            raise ValueError('选择数量不符合当前效果。')
        self.state['pending'] = None
        old_queue = self.state['effects']
        self.state['effects'] = []
        if skipping:
            task = pending['task']
            self._effects(p, task['step'].get('otherwise', {}), dict(_source=task['source'], _context=task['context']))
        else:
            values = [deepcopy(pending['options'][i]['value']) for i in selected]
            self._complete_step(p, pending['task'], values, action.get('action', {}))
        self.state['effects'].extend(old_queue)
        self._drain_effects()

    def _drain_effects(self):
        while self.state.get('effects') and not self.state.get('pending'):
            task = self.state['effects'].pop(0)
            remaining = self.state['effects']
            self.state['effects'] = []
            self._run_step(self._player(task['player']), task)
            self.state['effects'].extend(remaining)

    @staticmethod
    def _card_option(card_id, value=None):
        card = CARDS[card_id]
        # `card` 让客户端用目录内的扫描卡面渲染（image_path 指向的 TTS 图未必随包附带）。
        return dict(value=card_id if value is None else value, card=card_id, label=card['name'], image=card['image_path'])

    def _tile_options(self, p):
        return [dict(value=i, label=TILES[t]['name'], image=TILES[t].get('source','images/piece_png/%s.png' % TILES[t]['image'])) for i,t in enumerate(p['tiles'])]

    @staticmethod
    def _board_option(c):
        return dict(value=c['id'], label='选择此处', board=True, q=c['q'], r=c['r'])

    def _flip(self, source):
        found = self._source_card(source)
        if not found or found[3]['face_down']:
            return
        p, i, card, meta = found
        meta.update(face_down=True, adventurers=0, tiles=[], counters=0)
        self._log('%s将《%s》翻至背面。' % (p['name'], card['name']), p)

    def _supply(self, p, step, action):
        if step.get('variable'):
            if not self.state.get('variable_supply'):
                self._log('变动板块供应已用完，跳过领取。',p)
                return
            loot = self._draw_variable(placed=False)
        else:
            loot = step.get('tile', 'tile21')
        self._take_loot(p, loot, dict(action, no_miasma=True))

    def _run_step(self, p, task):
        before=self._card_effect_counts(p)
        self._execute_step(p,task)
        self._log_card_effect_counts(p,task,before)

    def _execute_step(self, p, task):
        step, source, context = task['step'], task['source'], task['context']
        op = step['op']
        action = dict(_source=source, _context=context)
        if op == 'effect':
            self._effects(p, step['effect'], action)
        elif op == 'take_loot':
            self._take_loot(p,step['tile'],dict(action,no_miasma=True))
        elif op == 'if':
            if self._condition(p, step['condition'], context):
                self._effects(p, step.get('effect', {}), action)
        elif op == 'all':
            for other in self.state['players']:
                self._enqueue(other, [dict(op='effect', effect=step['effect'])], source, context)
        elif op == 'branch':
            self._prompt(task, '选择卡牌效果', [dict(value=i, label=o['label']) for i,o in enumerate(step['options'])], optional=step.get('optional', False))
        elif op == 'pay_resource':
            resource = step['resource']
            options = [dict(value=n, label='支付%s%s' % (n,LABELS[resource]))
                       for n in range(step.get('min',1),step.get('max',1)+1)
                       if self._affordable(p,{resource:n})]
            self._prompt(task, '选择支付数量', options, optional=step.get('optional',False))
        elif op == 'draw_achievement_select':
            deck = self.state['achievement_deck']
            drawn = [deck.pop() for _ in range(min(step['count'],len(deck)))]
            if drawn:
                task = deepcopy(task)
                task['step']['drawn'] = drawn
                keep = min(step.get('keep',1),len(drawn))
                self._prompt(task, '选择保留的成就卡', [dict(value=k,label=ACHIEVEMENTS[k]['name'],
                    image=ACHIEVEMENTS[k].get('source')) for k in drawn],keep,keep)
        elif op == 'supply':
            self._supply(p, step, action)
        elif op == 'treasure':
            self._prompt(task, '开启宝箱 / 选择宝物奖励', [dict(value=t, label=self.rules['treasures'][t]['name'],
                         description=self._treasure_reward(t)) for t in self.state['treasure_pool']])
        elif op == 'counter':
            found = self._source_card(source)
            if found and not found[3]['face_down']:
                found[3]['counters'] += step.get('count', 1)
        elif op == 'extra_action':
            p['extra_actions'] += step.get('count', 1)
            if step.get('explore_discount'):
                p['next_explore_discount'] = int(step['explore_discount'])
                self._log('获得效果：下一次探索必要成本-%s。' % step['explore_discount'], p)
        elif op == 'pass_out':
            if not p['passed']:
                p.update(passed=True, extra_actions=0)
                self._log('%s选择Pass，获得金币并休店：本季无法再行动。' % p['name'], p)
        elif op == 'return_special':
            for i, card, meta in self._active_cards(p):
                if card['name'] == step['name']:
                    p['hand'].append(p['played'].pop(i))
                    p['card_states'].pop(i)
                    break
        elif op == 'pass_left':
            found = self._source_card(source)
            if found:
                owner, i, card, meta = found
                target = self.state['players'][(self.state['players'].index(owner)+1) % len(self.state['players'])]
                if target is not owner:
                    target['played'].append(owner['played'].pop(i))
                    target['card_states'].append(owner['card_states'].pop(i))
        elif op == 'flip':
            if step.get('self') and not step.get('optional'):
                self._flip(source)
            else:
                options = [self._card_option(p['played'][i], meta['uid']) for i,card,meta in self._active_cards(p)
                           if not step.get('self') or (source and meta['uid'] == source.get('uid'))]
                self._prompt(task, '选择翻至背面的事件卡（不能翻回）', options, step.get('min', 1), step.get('max', 1), step.get('optional', False))
        elif op in ('discard_draw', 'discard_gain', 'play_facedown'):
            self._prompt(task, '选择手牌：' + {'discard_draw':'弃牌后补抽', 'discard_gain':'弃牌获得资源', 'play_facedown':'背面打出'}[op],
                         [self._card_option(c, i) for i,c in enumerate(p['hand'])], step.get('min', 1),
                         len(p['hand']) if step.get('all_hand') else step.get('max', step.get('count', 1)), step.get('optional', False))
        elif op == 'attach_adventurer':
            options = [dict(value=i, label='安置%s名未使用冒险者' % i) for i in range(1,min(p['available'],step.get('max',1))+1)]
            self._prompt(task, '把冒险者放在卡上；翻面后不会返还', options, optional=step.get('optional', False))
        elif op in ('consume_tiles', 'attach_tile'):
            if not self._affordable(p, step.get('costs', {})):
                return
            self._prompt(task, '选择' + ('支付的迷宫板块' if op=='consume_tiles' else '放在卡上的迷宫板块'),
                         self._tile_options(p), step.get('min',1), step.get('max',1), step.get('optional',False))
        elif op == 'consumed_bonus':
            for tile in context.get('consumed', []):
                data = TILES[tile]
                if step.get('stars_resource'):
                    self._effects(p, {step['stars_resource']:data.get('star',0)}, action)
                if data.get('ishole'):
                    self._effects(p, step.get('hole_bonus', {}), action)
                if data.get('star',0) >= step.get('star_min',10**9):
                    self._effects(p, step.get('effect', {}), action)
        elif op == 'pay_effect':
            costs = step.get('costs', {})
            possible = self._affordable(p, costs)
            if step.get('can_trans'):
                possible = possible or self._affordable(p, dict(costs, gold=max(0,costs.get('gold',0)-5*p['strength'])))
            if not possible:
                self._effects(p, step.get('otherwise', {}), action)
                return
            label = '、'.join('%s%s' % (v,LABELS[k]) for k,v in costs.items())
            self._prompt(task, '是否支付'+label+'？', [dict(value=True,label='支付并执行'),dict(value=False,label='不支付')])
        elif op == 'reveal_draw':
            cards = self._draw(step.get('count', 1))
            self._log('%s公开牌库顶卡：%s。' % (p['name'], '、'.join(CARDS[c]['name'] for c in cards)),p)
            if 'keep_filter' in step:
                kept = [c for c in cards if self._card_filter(CARDS[c], step['keep_filter'])]
                p['hand'].extend(kept)
                remaining = Counter(cards)-Counter(kept)
                self.state['discard'].extend(remaining.elements())
            else:
                p['hand'].extend(cards)
            for card_id in cards:
                tags = CARDS[card_id].get('tags', [])
                if step.get('tag_potions'):
                    self._effects(p, {'pot':len(tags)} if tags else {'strength':1}, action)
                if step.get('tag_affection'):
                    self._effects(p, {'affection':1} if tags else {'strength':2}, action)
        elif op in ('reveal', 'peek', 'peek_publish'):
            if op == 'peek_publish':
                cell = self._cell(step['tile'])
                data = TILES[cell['loot']]
                self._prompt(task, '已查看 %s：%s，%s星。是否公开？' % (cell['id'],data['name'],data.get('star',0)),
                             [dict(value=True,label='公开给所有人',description='%s · %s星'%(data['name'],data.get('star',0)),preview=data['source']),dict(value=False,label='保持私密',preview=data['source'])])
            else:
                options = [self._board_option(c) for c in self.state['board'] if c['owner'] is None
                           and not c['revealed'] and not c.get('boss') and not self._tile_locked(c) and c['id'] not in context.get('seen', [])]
                self._prompt(task, '选择一块非首领迷宫' + ('公开' if op=='reveal' else '私下查看'), options,optional=step.get('optional',False))
        elif op in ('purify', 'replace', 'replace_hole', 'claim_replace', 'downgrade_base'):
            if step.get('variable') and not self.state.get('variable_supply'):
                self._log('变动板块供应已用完，跳过替换。',p)
                return
            options = []
            for c in self.state['board']:
                if op == 'downgrade_base':
                    eligible = c['owner'] == p['id'] and c['base'] and not c.get('lab')
                else:
                    eligible = c['owner'] is None and not c.get('boss') and not self._tile_locked(c)
                    if op == 'purify':
                        eligible = eligible and c['revealed'] and TILES[c['loot']].get('ishole')
                    if step.get('adjacent_own'):
                        eligible = eligible and any(n['owner']==p['id'] for n in self._neighbors(c))
                    if step.get('concealed'):
                        eligible = eligible and not c['revealed']
                    if step.get('region'):
                        eligible = eligible and self._region(c) == step['region']
                    if step.get('adjacent_base'):
                        eligible = eligible and any(n['owner']==p['id'] and n['base'] for n in self._neighbors(c))
                if eligible:
                    options.append(self._board_option(c))
            self._prompt(task, {'purify':'净化一个已公开的深渊洞穴', 'replace':'替换一个迷宫板块', 'replace_hole':'放置一个深渊洞穴',
                               'claim_replace':'获得一个迷宫并补充供应板块', 'downgrade_base':'将自己的据点降为冒险者'}[op], options, optional=step.get('optional',False))
        elif op == 'develop':
            names = {'gold':'金币 / 通常支付20金币','strength':'力量 / 通常支付3力量','pot':'秘药 / 通常支付2秘药','territory':'领地 / 通常控制3个地图格','cards':'事件 / 通常打出8张事件卡'}
            options = [dict(value=s,label=names[s]) for s in self.rules['development_slots'] if s not in p['developed'] and s not in step.get('exclude',[])]
            count = min(5-p['affection'],step.get('count',1))
            if count:
                self._prompt(task,'选择免费解锁的好感度条件',options,count,count)
        elif op == 'play':
            options = [self._card_option(c) for c in dict.fromkeys(p['hand']) if self._card_filter(CARDS[c],step.get('filter',{}))
                       and (self._requirements(p,{'tags':CARDS[c].get('requirements',{}).get('tags',{})},True) if step.get('ignore_non_tag_requirements') else self._requirements(p,CARDS[c].get('requirements',{}),True)) and self._can_nested_play(p,c,step)]
            self._prompt(task,'选择要打出的事件卡',options,optional=step.get('optional',False))
        elif op in ('play_payment', 'explore_payment'):
            if op == 'explore_payment' and not self._prepare_explore(p,task):
                return
            card = CARDS.get(step.get('card'),{})
            consume = 0 if step.get('ignore_extra') or op=='explore_payment' else card.get('consume_piece',0)
            if p['hero']=='horn_black':consume=max(0,consume-p['pot']) if p.get('prefer_pot') else min(consume,len(p['tiles']))
            maximum = len(p['tiles']) if op=='explore_payment' and self._has_passive(p,'tiles_as_strength') else consume
            self._prompt(task,'探索 / 翻开后支付' if op=='explore_payment' else '出牌 / 支付费用',
                         self._tile_options(p) if maximum else [],consume,maximum,mode='payment')
        elif op == 'build':
            options = []
            for cell in self.state['board']:
                if cell['owner'] != p['id'] or cell['base']:
                    continue
                if step.get('adjacent_base') and not any(n['base'] and n['owner']==p['id'] for n in self._neighbors(cell)):
                    continue
                cost = self.build_cost(p['id'],cell['id'])
                cost = max(0,cost-self.rules['build_cost']) if step.get('free') else cost
                if step.get('no_surcharge'):
                    cost = 0 if step.get('free') else self.rules['build_cost']
                if self._affordable(p,{'gold':cost}):
                    options.append(dict(self._board_option(cell),label='建设 / %s金币' % cost))
            self._prompt(task,'选择据点位置',options,optional=step.get('optional',True))
        elif op == 'explore':
            options = [self._board_option(c) for c in self.state['board'] if self.can_explore(p['id'],c['id'],allow_hole=step.get('hole_claim',False))]
            self._prompt(task,'选择探索目标',options,optional=step.get('optional',False))
        elif op == 'potion':
            options = [dict(value=k,label='%s · %s秘药' % (v['name'],v['cost'])) for k,v in POTIONS.items()
                       if self._affordable(p,{'pot':v['cost']}) and (step.get('ignore_slot') or k not in self.state['potions_used']+self.state['potions_disabled'])]
            self._prompt(task,'选择秘药行动',options)
        elif op == 'achievement':
            options = []
            for public, ids in ((False,p['achievements']),(True,self.state['public_achievements'])):
                for aid in ids:
                    card = ACHIEVEMENTS[aid]
                    if self._requirements(p,card.get('requirement',{})) and self._requirements(p,card.get('requirements',{})):
                        if self._affordable(p,{'gold':max(0,card['price']-step.get('discount',0))}):
                            options.append(dict(value=dict(id=aid,public=public),label=('公开 · ' if public else '私人 · ')+card['name'],image=card['source']))
            self._prompt(task,'立即完成一张王权',options,optional=True)
        elif op == 'lab_move':
            options = []
            occupied={(c['q'],c['r']) for c in self.state['board']}
            rim={(q+dq,r+dr) for q,r in occupied for dq,dr in ((1,0),(0,1),(-1,1),(-1,0),(0,-1),(1,-1))}-occupied
            for q,r in sorted(rim):
                options.append(dict(value=[q,r],label='地图外缘',board=True,q=q,r=r))
            self._prompt(task,'选择浮空实验室位置（地图外侧）',options)
        elif op == 'lab_recall':
            p['lab'], p['lab_ready'] = None, True
        else:
            raise ValueError('尚未支持的卡牌步骤：'+str(op))

    @staticmethod
    def _card_filter(card, rule):
        tags = card.get('tags', [])
        if card.get('price',0)>rule.get('price_max',10**9):return False
        if rule.get('extra_cost') and not (card.get('costs') or card.get('consume_piece')):return False
        if rule.get('has_point') and not (card.get('point') or card.get('scoring')):
            return False
        if rule.get('tag') and rule['tag'] not in tags:
            return False
        if rule.get('any_tag') and not any(t in tags for t in rule['any_tag']):
            return False
        return True

    @staticmethod
    def _region(c):
        return c.get('region',min(3,4-max(abs(c['q']),abs(c['r']),abs(c['q']+c['r']))))

    def _nested_discount(self,p,step):
        return step.get('discount',0)+sum(self._stat(p,s) for s in step.get('discount_stats',[]))

    def _can_nested_play(self,p,c,step):
        card = CARDS[c]
        if not card.get('available',False):
            return False
        consume = 0 if step.get('ignore_extra') else card.get('consume_piece',0)
        if len(p['tiles'])+(p['pot'] if p['hero']=='horn_black' else 0) < consume:
            return False
        costs = Counter(step.get('costs',{}))
        if not step.get('ignore_extra'):
            costs.update(card.get('costs',{}))
        price = 0 if step.get('free') else max(0,card['price']-self._nested_discount(p,step))
        if card.get('can_trans'):
            price = max(0,price-5*max(0,p['strength']-costs.get('strength',0)))
        costs['gold'] += price
        if p['hero']=='horn_black':
            # Check the two interchangeable resources as one payment pool.
            costs=dict(costs)
            if consume+costs.pop('pot',0)>len(p['tiles'])+p['pot']:return False
        return self._affordable(p,costs)

    def _complete_step(self, p, task, values, extra):
        before = self._card_effect_counts(p)
        self._execute_choice_step(p,task,values,extra)
        self._log_card_effect_counts(p,task,before)

    def _card_effect_counts(self,p):
        return {'持有迷宫板块':len(p['tiles']),'手牌':len(p['hand']),
                '好感度':p['affection'],'可用冒险者':p['available'],
                '声望奖励':p.get('reputation',0),
                '据点':sum(c['owner']==p['id'] and c['base'] for c in self.state['board']),
                '公开迷宫':sum(bool(c['revealed']) for c in self.state['board'])}

    def _log_card_effect_counts(self,p,task,before):
        found=self._source_card(task.get('source'))
        if not found:
            return
        after=self._card_effect_counts(p)
        changes=['%s%+d' % (key,after[key]-before[key]) for key in before if before[key]!=after[key]]
        if changes:
            self._log('%s的《%s》效果：%s。' % (p['name'],found[2]['name'],'、'.join(changes)),p)

    def _execute_choice_step(self, p, task, values, extra):
        step, source, context = task['step'], task['source'], task['context']
        op = step['op']
        action = dict(_source=source, _context=context)
        if op == 'branch':
            self._effects(p,step['options'][values[0]]['effect'],action)
        elif op == 'pay_resource':
            self._pay(p,{step['resource']:values[0]})
            for _ in range(values[0]):
                self._effects(p,step.get('per',{}),action)
        elif op == 'draw_achievement_select':
            p['achievements'].extend(values)
            # Unselected unused cards return to the bottom of the unused deck.
            self.state['achievement_deck'][:0] = [k for k in step['drawn'] if k not in values]
        elif op == 'treasure':
            key = values[0]
            self.state['treasure_pool'].remove(key)
            p['treasures'].append(key)
            self._effects(p,self.rules['treasures'][key],action)
            self._log('%s开启宝箱，获得%s：%s。' % (p['name'],self.rules['treasures'][key]['name'],self._treasure_reward(key)),p)
        elif op == 'flip':
            for uid in values:
                self._flip(dict(player=p['id'],uid=uid))
                self._effects(p,step.get('per',{}),action)
        elif op in ('discard_draw','discard_gain','play_facedown'):
            cards = [p['hand'][i] for i in values]
            for i in sorted(values,reverse=True):
                p['hand'].pop(i)
            if op == 'play_facedown':
                for card in cards:
                    p['played'].append(card)
                    self._card_states(p)[-1]['face_down'] = True
                self._effects(p,step.get('effect',{}),action)
            else:
                self.state['discard'].extend(c for c in cards if not CARDS[c].get('special'))
                if op == 'discard_draw':
                    p['hand'].extend(self._draw(len(cards)+step.get('bonus',0)))
                elif step.get('resource'):
                    self._effects(p,{step['resource']:len(cards)*step.get('per',1)},action)
                self._effects(p,step.get('effect',{}),action)
        elif op == 'attach_adventurer':
            found = self._source_card(source)
            if found and not found[3]['face_down']:
                p['available'] -= values[0]
                found[3]['adventurers'] += values[0]
                self._effects(p,step.get('effect',{}),action)
        elif op in ('consume_tiles','attach_tile'):
            tiles = [p['tiles'][i] for i in values]
            for i in sorted(values,reverse=True):
                p['tiles'].pop(i)
            # Reserve selected tiles before Horn substitutes other tiles for potions.
            # Engine.apply rolls back the entire choice if the remaining cost fails.
            self._pay(p,step.get('costs',{}))
            if op == 'attach_tile':
                found = self._source_card(source)
                if not found or found[3]['face_down']:
                    raise ValueError('附着目标已经失效。')
                found[3]['tiles'].extend(tiles)
                for tile in tiles:
                    self._effects(p,step.get('per',{}),action)
            else:
                for tile in tiles:
                    self._emit(p,'consume_tile',dict(tile=tile))
                    if step.get('stars_gold'):
                        self._effects(p,dict(gold=TILES[tile].get('star',0)*step['stars_gold']),action)
                    self._effects(p,step.get('per',{}),action)
                    if 'scrap' in TILES[tile].get('tags',[]):
                        self._effects(p,step.get('scrap_bonus',{}),action)
                    if TILES[tile].get('star',0) >= step.get('star_min',10**9):
                        self._effects(p,step.get('star_bonus',{}),action)
            self._effects(p,step.get('effect',{}),action)
        elif op == 'pay_effect':
            if values[0]:
                costs = dict(step.get('costs',{}))
                if step.get('can_trans') and costs.get('gold',0) > p['gold']:
                    needed = (costs['gold']-p['gold']+4)//5
                    costs['strength'] = costs.get('strength',0)+needed
                    costs['gold'] = max(0,costs['gold']-5*needed)
                self._pay(p,costs)
                self._effects(p,step.get('effect',{}),action)
            else:
                self._effects(p,step.get('otherwise',{}),action)
        elif op in ('reveal','peek'):
            cell = self._cell(values[0])
            seen = context.get('seen',[]) + [cell['id']]
            next_context = dict(context,seen=seen)
            sequence = []
            if op == 'reveal':
                cell['revealed'] = True
                self._emit(p,'reveal',dict(hole=bool(TILES[cell['loot']].get('ishole'))))
            else:
                p['private_tiles'][cell['id']] = cell['loot']
                sequence.append(dict(op='peek_publish',tile=cell['id']))
            if step.get('count',1) > 1:
                sequence.append(dict(step,count=step['count']-1))
            self._enqueue(p,sequence,source,next_context)
        elif op == 'peek_publish':
            if values[0]:
                cell = self._cell(step['tile'])
                cell['revealed'] = True
                self._emit(p,'reveal',dict(hole=bool(TILES[cell['loot']].get('ishole'))))
        elif op in ('purify','replace','replace_hole','claim_replace','downgrade_base'):
            cell = self._cell(values[0])
            if op == 'downgrade_base':
                cell['base'] = False
                self._effects(p,step.get('effect',{}),action)
                return
            previous = cell['loot']
            if op in ('purify','claim_replace'):
                self._take_loot(p,previous,dict(action,no_miasma=not step.get('reduce_miasma',False)))
                if TILES[previous].get('ishole'):
                    self._effects(p,step.get('hole_bonus',{}),action)
                if step.get('variable_flip') and TILES[previous].get('variable'):
                    self._flip(source)
            replacement = 'tile14' if op=='replace_hole' else step.get('tile','tile21')
            if step.get('variable'):
                choices = [k for k,t in TILES.items() if t.get('variable')]
                if not choices:
                    raise ValueError('缺少变动迷宫供应数据。')
                replacement = self._draw_variable()
            cell.update(loot=replacement,revealed=replacement in ('tile14','tile21'),back_star=2 if TILES[replacement].get('variable') else 1)
            for other in self.state['players']:
                other['private_tiles'].pop(cell['id'],None)
        elif op == 'develop':
            self._develop(p,len(values),dict(action,slots=values),free=True)
        elif op == 'play':
            self._enqueue(p,[dict(step,op='play_payment',card=values[0])],source,context)
        elif op == 'explore':
            step = dict(step, op='explore_payment', tile=values[0])
            step['discount'] = step.get('discount', 0) + p.pop('next_explore_discount', 0)
            self._enqueue(p,[step],source,context)
        elif op in ('play_payment','explore_payment'):
            if not isinstance(extra,dict):
                raise ValueError('费用参数无效。')
            strength, pot = extra.get('strength',0), extra.get('pot',0)
            if type(strength) is not int or type(pot) is not int or strength < 0 or pot < 0:
                raise ValueError('支付数量必须是非负整数。')
            pieces = [p['tiles'][i] for i in values]
            if op == 'play_payment':
                self._play(p,dict(action,card=step['card'],strength=strength,pieces=pieces,
                           _discount=self._nested_discount(p,step),_ignore_extra=step.get('ignore_extra',False),
                           _ability_costs=step.get('costs',{}),_ignore_non_tag_requirements=step.get('ignore_non_tag_requirements',False)),free=step.get('free',False))
                self._effects(p,step.get('on_success',{}),action)
            else:
                outcome = self._explore(p,dict(action,tile=step['tile'],strength=strength,pieces=pieces,pot=pot,
                                       flash=extra.get('flash',False),lab=extra.get('lab',False),hole_claim=step.get('hole_claim',False),
                                       _discount=step.get('discount',0),_potion_strength=step.get('potion_strength',0)))
                if self.state.get('last_action'):
                    self.state['last_action']['outcome'] = outcome
                if outcome == 'explored':
                    self._effects(p,step.get('on_success',{}),action)
                elif outcome == 'hole' and step.get('hole_extra',True):
                    p['extra_actions'] += 1
        elif op == 'build':
            self._build(p,values[0],free=step.get('free',False),no_surcharge=step.get('no_surcharge',False))
            if step.get('reveal_neighbors'):
                for cell in self._neighbors(self._cell(values[0])):
                    if cell['owner'] is None and not cell['q']==cell['r']==0:
                        cell['revealed'] = True
        elif op == 'potion':
            self._potion(p,dict(action,option=values[0],_ignore_slot=step.get('ignore_slot',False),_preserve_slot=step.get('preserve_slot',False)))
        elif op == 'achievement':
            self._achievement(p,values[0],discount=step.get('discount',0))
        elif op == 'lab_move':
            p['lab'] = dict(q=values[0][0],r=values[0][1])
        else:
            raise ValueError('此选择不能在当前步骤执行。')

    def _resolution_view(self, view, player_id, reveal=False):
        view['treasure_rewards'] = {key:dict(data,description=self._treasure_reward(key)) for key,data in self.rules['treasures'].items()}
        view.pop('effects',None)
        view.pop('action_frame',None)
        pending = self.state.get('pending')
        if pending:
            own = pending['player'] == player_id
            view['pending'] = {k:deepcopy(pending[k]) for k in ('id','player')}
            if own:
                view['pending'].update({k:deepcopy(pending[k]) for k in ('title','options','min','max','optional','mode')})
                if pending['mode']=='payment':
                    p = self._player(player_id)
                    step = pending['task']['step']
                    card = CARDS.get(step.get('card'),{})
                    view['pending']['payment'] = dict(
                        strength_max=p['strength'] if step['op']=='explore_payment' else
                            min(max(0,p['strength']-card.get('costs',{}).get('strength',0)),
                                (max(0,card.get('price',0)-self._nested_discount(p,step))+4)//5)
                            if not step.get('free') and (card.get('can_trans') or self._has_passive(p,'strength_as_gold')) else 0,
                        pot_max=p['pot'] if step.get('potion_strength') else 0,
                        flash=bool(step['op']=='explore_payment' and p.get('flash') and self._has_passive(p,'flash_explore')),
                        lab=bool(step['op']=='explore_payment' and p.get('lab_ready')),
                        target=step.get('tile'),card=step.get('card'),discount=self._nested_discount(p,step),
                        free=step.get('free',False),ignore_extra=step.get('ignore_extra',False))
                    if step['op'] == 'explore_payment':
                        cell = self._cell(step['tile'])
                        context = pending['task']['context']
                        cost = lambda flash: self._exploration_cost(p,cell,TILES[cell['loot']].get('star',0),
                            context.get('was_revealed',cell['revealed']),step.get('discount',0),flash)
                        view['pending']['payment'].update(gold_base=cost(False), gold_flash=cost(True),
                            strength_max=min(p['strength'],(cost(False)+4)//5),
                            pot_max=min(p['pot'],(cost(False)+5*step['potion_strength']-1)//(5*step['potion_strength'])) if step.get('potion_strength') else 0,
                            cost_details=self._exploration_cost(p,cell,TILES[cell['loot']].get('star',0),
                                context.get('was_revealed',cell['revealed']),step.get('discount',0),explain=True),
                            flash_cost_details=self._exploration_cost(p,cell,TILES[cell['loot']].get('star',0),
                                context.get('was_revealed',cell['revealed']),step.get('discount',0),True,explain=True),
                            target_name=TILES[cell['loot']]['name'], target_image=TILES[cell['loot']]['source'],
                            potion_strength=step.get('potion_strength',0),
                            tiles_as_strength=self._has_passive(p,'tiles_as_strength'))
            else:
                view['pending']['title'] = '等待对方完成卡牌效果'
                if pending['task']['step']['op']=='explore_payment':
                    view['pending'].update(title='等待对方支付探索资源',target=pending['task']['step']['tile'])
        for player in view['players']:
            own = player['id']==player_id
            if not own and not reveal:
                player.pop('private_tiles',None)
        return view

    def _treasure_reward(self, key):
        data = self.rules['treasures'][key]
        parts = ['声望 +%s' % data.get('point',0)]
        parts += ['%s +%s' % (LABELS[k],data[k]) for k in RESOURCES if data.get(k)]
        if data.get('tags'):
            parts.append('三种标记各 +1')
        return ' / '.join(parts)
