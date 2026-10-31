"""Expansion p6: eight starting events, pick one and pass left, then buy.

Selections are simultaneous: a packet moves only after every seat commits.
The final single card is kept automatically. Hero bonus cards never circulate.
"""


def setup(engine):
    players = engine.state['players']
    options = engine.rules['options']
    if not options.get('setup_draft') or options.get('solo') or len(players) < 2:
        return
    engine.state.update(phase='draft', draft_step=1)
    for player in players:
        player.update(draft_cards=player['offered'], draft_kept=[], draft_choice=None,
                      offered=[], mulligan_done=True)
    engine._log('开局轮抽开始：每次留1张，其余传给左侧公会；轮抽后再付费保留。')


def pick(engine, player, action):
    state = engine.state
    if state['phase'] != 'draft' or state.get('pending'):
        raise ValueError('当前不能进行轮抽，请先完成待处理效果。')
    if type(action.get('draft_step')) is not int or action['draft_step'] != state['draft_step']:
        raise ValueError('轮抽已进入下一次选择，请使用最新牌包。')
    if player['draft_choice'] is not None:
        raise ValueError('你已确认本次轮抽，请等待其他玩家。')
    index = action.get('index')
    if type(index) is not int or not 0 <= index < len(player['draft_cards']):
        raise ValueError('请从当前牌包选择1张事件卡。')
    player['draft_choice'] = index
    engine._log('%s已确认第%s次轮抽选择。' % (player['name'], state['draft_step']), player)
    # Status is already visible beside the packet; retain the log without
    # flooding the card area with up to 35 floating confirmation messages.
    state['log'][-1]['quiet'] = True
    players = state['players']
    if any(p['draft_choice'] is None for p in players):
        return
    remaining = []
    for p in players:
        cards = list(p['draft_cards'])
        p['draft_kept'].append(cards.pop(p['draft_choice']))
        remaining.append(cards)
    for i, p in enumerate(players):
        # The same leftward seat order used by the start-player marker.
        p.update(draft_cards=remaining[(i-1) % len(players)], draft_choice=None)
    state['draft_step'] += 1
    if all(len(p['draft_cards']) == 1 for p in players):
        for p in players:
            p['offered'] = p.pop('draft_kept') + p.pop('draft_cards')
            p.pop('draft_choice')
        state['phase'] = 'research'
        engine._log('开局轮抽完成：每位公会获得8张候选情报，请选择付费保留；本局不再进行开局换牌。')


def redact(view, player_id):
    # Never include another seat's packet/picks, even in public replay files.
    for p in view['players']:
        if 'draft_cards' not in p:
            continue
        p['draft_ready'] = p['draft_choice'] is not None
        p['draft_kept_count'] = len(p['draft_kept'])
        if p['id'] != player_id:
            for key in ('draft_cards', 'draft_kept', 'draft_choice'):
                p.pop(key, None)
