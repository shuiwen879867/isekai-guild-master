"""Public match summaries and finished-game statistics from replay snapshots."""
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
import re

LOCAL_ZONE = timezone(timedelta(hours=8))


def day_key(value=None):
    if not value or value == 'today':
        return datetime.now(LOCAL_ZONE).date().isoformat()
    if value == 'all':
        return 'all'
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
        raise ValueError('Use YYYY-MM-DD, today or all.')
    return date.fromisoformat(value).isoformat()


def match_day(value):
    try:
        moment = datetime.fromisoformat(value.replace('Z', '+00:00'))
        if moment.tzinfo is None:
            moment = moment.replace(tzinfo=timezone.utc)
        return moment.astimezone(LOCAL_ZONE).date().isoformat()
    except (ValueError, TypeError, AttributeError):
        return ''


def match_preview(meta, initial, latest):
    players = latest.get('players', [])
    original = initial.get('players', players)
    order = [p['id'] for p in original]
    first = int(initial.get('start_player', 0)) % max(1, len(order))
    positions = {pid: (index - first) % len(order) + 1 for index, pid in enumerate(order)}
    finished = latest.get('phase') == 'finished' and meta.get('status') == '已结束'
    winners = latest.get('winners', []) if finished else []
    scores = {row['id']: row for row in latest.get('scores', [])} if finished else {}
    heroes = meta.get('catalog', {}).get('heroes', {})
    public = []
    for seat, player in enumerate(players, 1):
        pid = player['id']; hero = player.get('hero', ''); definition = heroes.get(hero, {})
        score = scores.get(pid, {})
        public.append(dict(id=pid, name=player.get('name', ''), hero=hero,
                           hero_name=definition.get('name', hero),
                           variant=player.get('variant', definition.get('variant', '')),
                           seat=seat, position=positions.get(pid),
                           score=score.get('total', score.get('score', player.get('score'))),
                           rank=score.get('rank'), winner=pid in winners))
    rules = latest.get('rules', {}).get('options', {})
    return dict(players=public, winners=winners,
                winner_names=[p['name'] for p in public if p['winner']],
                finished=finished, mode='solo' if rules.get('solo') or len(players)==1 else 'multiplayer',
                solo_result=latest.get('solo_result'), phase=latest.get('phase'),
                round=latest.get('round'), civilization=latest.get('civ'), miasma=latest.get('miasma'))


def win_statistics(matches, players=None):
    positions, heroes = defaultdict(lambda: [0, 0]), {}
    eligible = [m for m in matches if m.get('preview', {}).get('finished')
                and m['preview']['mode']=='multiplayer'
                and m['preview']['winners']
                and (players is None or len(m['preview']['players'])==players)]
    for match in eligible:
        for player in match['preview']['players']:
            won = int(player['winner'])
            key=player['position']
            if key is not None:
                positions[key][0]+=1;positions[key][1]+=won
            hero = heroes.setdefault(player['hero'], dict(hero=player['hero'], name=player['hero_name'],
                                    variant=player['variant'], games=0, wins=0))
            hero['games'] += 1; hero['wins'] += won
    def rate(games, wins):
        return round(wins * 100 / games, 2) if games else 0
    def rows(table):
        return [dict(position=key, games=values[0], wins=values[1], win_rate=rate(*values))
                for key, values in sorted(table.items())]
    for hero in heroes.values():
        hero['win_rate'] = rate(hero['games'], hero['wins'])
    return dict(matches=len(eligible), positions=rows(positions),
                heroes=sorted(heroes.values(), key=lambda h: (-h['games'], -h['win_rate'], h['hero'])),
                note='仅计已结束的多人对局；并列第一各记一胜。行动顺位按开局先手起算，角色黑白版本分别统计。')
