"""One authoritative checkpoint; never part of a client snapshot or replay."""
from copy import deepcopy


def information_changed(before, after):
    # A new season/deal and any random supply draw cannot be unlearned.
    keys = ('round', 'draft_step', 'rng', 'deck', 'achievement_deck', 'tile_supply',
            'variable_supply', 'quest_deck', 'prologue_deck')
    if any(before.get(k) != after.get(k) for k in keys):
        return True
    old_cells = {c['id']: c for c in before['board']}
    for cell in after['board']:
        old = old_cells.get(cell['id'], {})
        if cell.get('revealed') and (not old.get('revealed') or old.get('loot') != cell.get('loot')):
            return True
    for old, new in zip(before['players'], after['players']):
        if (old.get('private_tiles') != new.get('private_tiles')
                or old.get('hero_deck') != new.get('hero_deck')):
            return True
    return False


def available(engine, player_id):
    checkpoint = getattr(engine, '_undo_checkpoint', None)
    return bool(checkpoint and player_id is not None
                and type(checkpoint['player']) is type(player_id)
                and checkpoint['player'] == player_id
                and engine.state['phase'] != 'finished'
                and not engine._player(player_id).get('withdrawn')
                and engine._player(player_id).get('timeout_round') != engine.state['round'])


def record(engine, before, player_id, action):
    engine._undo_serial = getattr(engine, '_undo_serial', 0) + 1
    engine._undo_checkpoint = None
    if engine.state['phase'] != 'finished' and not information_changed(before, engine.state):
        engine._undo_checkpoint = dict(id=engine._undo_serial, player=player_id,
                                       state=before, action=action['type'])


def restore(engine, player_id, action):
    if (not available(engine, player_id) or type(action.get('undo_id')) is not int
            or action['undo_id'] != engine._undo_checkpoint['id']):
        raise ValueError('无法撤回：其他玩家已行动、已有新信息，或撤回按钮已过期。')
    current = engine.state
    restored = deepcopy(engine._undo_checkpoint['state'])
    # Undo itself is a visible event. Keep IDs monotonic so neither clients nor
    # replay viewers confuse restored choices/logs with previously sent ones.
    restored['log'] = deepcopy(current['log'])
    restored['log_serial'] = current.get('log_serial', 0)
    restored['choice_serial'] = max(current.get('choice_serial', 0), restored.get('choice_serial', 0)) + 1
    if restored.get('pending'):
        restored['pending']['id'] = restored['choice_serial']
    restored.pop('feedback', None)
    for old, live in zip(restored['players'], current['players']):
        for key in ('connected', 'withdrawn', 'timeout_round'):
            if key in live:
                old[key] = live[key]
    clock = deepcopy(current.get('_clock'))
    if clock:
        restored['_clock'] = clock
    engine.state = restored
    engine._undo_checkpoint = None
    engine._log('%s撤回了上一步行动。' % engine._player(player_id)['name'], engine._player(player_id))
    from guild_clock import sync
    banks = deepcopy(clock['players']) if clock else {}
    sync(engine)
    # Changing back to the previous turn must never refund elapsed time.
    for pid, bank in engine.state.get('_clock', {}).get('players', {}).items():
        if pid in banks:
            for key in ('base', 'reserve'):
                bank[key] = min(bank[key], banks[pid][key])
    return engine.view(player_id)
