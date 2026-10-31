"""Authoritative per-turn clocks. Reserve survives every turn and season."""
import itertools
import math
import time


def waiting(engine):
    s = engine.state
    if s['phase'] == 'finished':
        return {}
    frame = s.get('action_frame')
    scope = '%s:%s:%s' % (s['round'], s['phase'], s['action_count'] - bool(frame))
    if s.get('pending'):
        return {str(s['pending']['player']): scope}
    if s['phase'] == 'draft':
        return {str(p['id']): scope+':draft:%s' % s['draft_step']
                for p in s['players'] if p['draft_choice'] is None}
    if s['phase'] == 'research':
        return {str(p['id']): scope for p in s['players'] if not p['researched']}
    return {str(s['players'][s['turn']]['id']): scope}


def sync(engine, now=None):
    now = time.monotonic() if now is None else now
    options = engine.rules.get('options', {})
    enabled = options.get('action_timer', False)
    if not enabled and not any(p.get('withdrawn') or p.get('timeout_round')==engine.state['round']
                               for p in engine.state['players']):
        return
    clock = engine.state.setdefault('_clock', dict(stamp=now, active={}, players={}))
    elapsed = max(0, now-clock['stamp'])
    for pid in clock['active']:
        bank = clock['players'][pid]
        remaining = max(0, elapsed-bank['base'])
        bank['base'] = max(0, bank['base']-elapsed)
        bank['reserve'] = max(0, bank['reserve']-remaining)
    clock['stamp'] = now
    active = waiting(engine)
    if enabled:
        # A disconnected seat is governed by the room's independent reconnect
        # grace period. Its normal action bank must not also drain in parallel.
        autonomous = {str(p['id']): p.get('connected', True) or p.get('withdrawn')
                      or p.get('timeout_round')==engine.state['round'] for p in engine.state['players']}
        active = {pid: scope for pid, scope in active.items()
                  if autonomous.get(pid, True)}
    for pid, scope in active.items():
        bank = clock['players'].setdefault(pid, dict(base=0, reserve=options.get('reserve_seconds',120), scope=None))
        if bank['scope'] != scope:
            bank.update(scope=scope, base=options.get('base_seconds',30))
    clock['active'] = active


def snapshot(engine):
    if not engine.rules.get('options',{}).get('action_timer'):
        return None
    clock = engine.state.get('_clock', {})
    options = engine.rules['options']
    return {str(p['id']): dict(
        base=math.ceil(clock.get('players',{}).get(str(p['id']),{}).get('base',options['base_seconds'])),
        reserve=math.ceil(clock.get('players',{}).get(str(p['id']),{}).get('reserve',options['reserve_seconds'])),
        active=str(p['id']) in clock.get('active',{}),
        timed_out=p.get('timeout_round')==engine.state['round']) for p in engine.state['players']}


def automatic_action(engine, pid):
    """Submit legal choices through the same atomic path used by humans."""
    s = engine.state
    pending = s.get('pending')
    if not pending:
        if s['phase']=='draft':
            action = dict(type='draft_pick', draft_step=s['draft_step'], index=0)
        else:
            action = dict(type='research', cards=[]) if s['phase']=='research' else dict(type='pass')
        engine.apply(pid, action)
        return
    request = dict(type='choice', choice_id=pending['id'])
    if pending['optional']:
        engine.apply(pid, dict(request, skip=True))
        return
    # Minimum selection avoids spending optional resources. Try alternatives
    # when one selected card/target cannot currently be paid for.
    candidates = itertools.chain.from_iterable(
        itertools.combinations(range(len(pending['options'])), count)
        for count in range(pending['min'], pending['max']+1))
    payments = [{}]
    if pending['mode']=='payment' and pending['task']['step']['op']=='play_payment':
        maximum=engine.view(pid)['pending']['payment']['strength_max']
        if maximum:payments.append(dict(strength=maximum))
    for selected in itertools.islice(candidates, 4096):
        for payment in payments:
            try:
                engine.apply(pid, dict(request, selected=list(selected),action=payment))
                return
            except ValueError:
                continue
    # An unaffordable compulsory nested play can arise after selling cards.
    # Cancel only that impossible step, never award its resources or cancel
    # another player's remaining effects.
    engine.state['pending'] = None
    engine._log('超时选择已无可执行项目，跳过该步骤。',engine._player(pid))
    engine._drain_effects()
    engine._complete_action_frame()


def advance(engine, now=None, on_step=None):
    before = snapshot(engine)
    sync(engine, now)
    clock = engine.state.get('_clock')
    if not clock:
        return False
    changed = before != snapshot(engine)
    # One step per tick preserves replay granularity and avoids blocking I/O.
    for key in list(clock['active']):
        p = next(p for p in engine.state['players'] if str(p['id'])==key)
        bank = clock['players'][key]
        expired = engine.rules['options'].get('action_timer') and bank['base']+bank['reserve'] <= 0
        if p.get('withdrawn') or p.get('timeout_round') == engine.state['round'] or expired:
            reason = '已被移出房间' if p.get('withdrawn') else '等待时间耗尽'
            close_for_round(engine, p['id'], reason, now, on_step)
            return True
    return changed


def close_for_round(engine, pid, reason='等待时间耗尽', now=None, on_step=None):
    """Resolve mandatory choices and close one seat for the current season."""
    p = engine._player(pid)
    current_round = engine.state['round']
    if p.get('timeout_round') != current_round:
        p['timeout_round'] = current_round
        engine._log('%s%s，自动完成必要选择并本季闭店。' % (p['name'], reason), p)
    automatic_action(engine, pid)
    p = engine._player(pid)
    s = engine.state
    pending = s.get('pending')
    if (s['phase'] in ('action', 'final') and not p['passed'] and not pending
            and s['players'][s['turn']]['id'] == pid):
        # A research timeout can advance the table straight into this same
        # disconnected player's action turn. The single reconnect grace closes
        # that turn too; it must not start a second grace period.
        automatic_action(engine, pid)
        p = engine._player(pid)
        s = engine.state
        pending = s.get('pending')
    if (s['phase'] in ('action', 'final') and not p['passed']
            and s['players'][s['turn']]['id'] != pid
            and (not pending or pending['player'] != pid)):
        engine._on_pass(p)
        p.update(passed=True, extra_actions=0)
        if not pending:
            engine._drain_effects()
            engine._complete_action_frame()
    sync(engine, now)
    engine._undo_checkpoint = None
    if on_step:
        on_step(pid)
    return True
