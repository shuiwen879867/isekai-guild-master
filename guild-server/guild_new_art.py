"""Compact manifest for the replacement artwork supplied in 新图包."""


def _path(number):
    return 'images/new_art/%s.webp' % number


NEW_ART_IDS = tuple(
    list(range(841100, 841109)) + list(range(841200, 841209)) + list(range(841600, 841618))
    + list(range(842700, 842713)) + list(range(842800, 842830)) + list(range(842900, 842915))
    + list(range(843100, 843114)) + [843213] + list(range(843400, 843421))
    + list(range(845600, 845622)) + list(range(845900, 845918))
    + list(range(846000, 846018)) + list(range(846100, 846118))
    + list(range(846200, 846218)) + list(range(846300, 846318))
    + list(range(846400, 846418)) + list(range(846500, 846517))
    + list(range(846600, 846618)) + list(range(846700, 846712))
    + list(range(846800, 846811)) + list(range(846900, 846907))
    + list(range(847000, 847014)) + list(range(847200, 847218))
    + list(range(847400, 847417)) + list(range(847500, 847521))
    + [847600, 847700, 847800, 847900, 848000, 848200, 848400, 848500, 848600]
    + list(range(848700, 848703)))


def _event_art():
    result = {}
    for index in range(18):
        result['A-%03d' % (index + 1)] = _path(847200 + index)
    result['A-036'] = _path(845900)
    for index in range(1, 18):
        result['A-%03d' % (18 + index)] = _path(845900 + index)
    result['A-054'] = _path(846100)
    for index in range(1, 18):
        result['A-%03d' % (36 + index)] = _path(846100 + index)
    for index in range(6):
        result['A-%03d' % (67 + index)] = _path(846000 + index)
    for index in range(6, 18):
        result['A-%03d' % (49 + index)] = _path(846000 + index)
    result['A-090'] = _path(846200)
    for index in range(1, 18):
        result['A-%03d' % (72 + index)] = _path(846200 + index)
    result['A-108'] = _path(846300)
    for index in range(1, 18):
        result['A-%03d' % (90 + index)] = _path(846300 + index)
    result['C-018'] = _path(846400)
    for index in range(1, 18):
        result['C-%03d' % index] = _path(846400 + index)
    for index in range(19, 23):
        result['C-%03d' % index] = _path(846500 + index - 19)
    for index in range(1, 14):
        result['D-%03d' % index] = _path(846504 + index - 1)
    for index in range(1, 19):
        result['E-%03d' % index] = _path(846600 + index - 1)
    for index in range(19, 25):
        result['E-%03d' % index] = _path(846901 + index - 19)
    for index in range(1, 13):
        result['B-%03d' % index] = _path(846700 + index - 1)
    # The last ordinary event sheet contains the remaining B/C cards.  Its
    # first scan is C-026, followed by B-013..B-025 and C-023..C-025.
    result['C-026'] = _path(847400)
    for index in range(13, 26):
        result['B-%03d' % index] = _path(847401 + index - 13)
    for index in range(23, 26):
        result['C-%03d' % index] = _path(847414 + index - 23)
    # The correction/reprint group supersedes the ordinary scans.
    result.update({'E-007': _path(847000), 'B-017': _path(847001),
                   'D-002': _path(847002), 'E-001': _path(847003),
                   'E-015': _path(847004), 'A-071': _path(847005),
                   'A-080': _path(847006), 'A-083': _path(847007),
                   'A-088': _path(847008), 'A-092': _path(847009),
                   'A-095': _path(847010), 'E-012': _path(847011),
                   'A-042': _path(847012)})
    # Later standalone scans supersede three entries from the sheets above.
    result.update({'Z-001': _path(847800), 'C-022': _path(848000),
                   'E-012': _path(848400)})
    return result


EVENT_ART = _event_art()


def _royal_art():
    result = {'R-022': _path(845600)}
    result.update({'R-%03d' % index: _path(845600 + index)
                   for index in range(1, 22)})
    return result


ROYAL_ART = _royal_art()

WHITE_HERO_ART = {
    'alicia_white': tuple(_path(841600 + i) for i in range(0, 3)),
    'hainie_white': tuple(_path(841600 + i) for i in range(3, 6)),
    'misha_white': tuple(_path(841600 + i) for i in range(6, 9)),
    'shion_white': tuple(_path(841600 + i) for i in range(9, 12)),
    'sofia_white': tuple(_path(841600 + i) for i in range(12, 15)),
    'bai_white': tuple(_path(841600 + i) for i in range(15, 18)),
}


def _descending_triplet(first):
    """The Taiwanese black-side sheets are scanned rank 3, 2, 1."""
    return tuple(_path(first + i) for i in (2, 1, 0))


BLACK_HERO_ART = {
    # P-036b, P-006b, P-003b, P-012b, P-009b, P-015b, P-018b.
    'ruby_black': _descending_triplet(843400),
    'shion_red': _descending_triplet(843403),
    'alicia_red': _descending_triplet(843406),
    'hainie_red': _descending_triplet(843409),
    'sofia_red': _descending_triplet(843412),
    'bai_red': _descending_triplet(843415),
    'misha_red': _descending_triplet(843418),
    # P-024b (original/B), P-021b, P-027b, P-030b, P-033b, P-039b.
    'elu_red': _descending_triplet(847500),
    'elu_red_b': _descending_triplet(847503),
    'ayaka_red_b': _descending_triplet(847506),
    'skadi_red': _descending_triplet(847509),
    'siren_red': _descending_triplet(847512),
    'melissa_red': _descending_triplet(847515),
    'peria_black': _descending_triplet(847518),
}

HERO_ART = dict(WHITE_HERO_ART, **BLACK_HERO_ART)


NEW_ART_GALLERY = {
    number: dict(id=number, name='新版图包 %s' % number,
                 image_path=_path(number), available=True)
    for number in NEW_ART_IDS
}


def _printed_codes_by_image():
    result = {}
    ranges = (
        (1, 18, 'A', 1), (233, 241, 'A', 19), (19, 27, 'A', 28),
        (224, 232, 'A', 37), (155, 163, 'A', 46), (215, 223, 'A', 55),
        (164, 172, 'A', 64), (28, 45, 'A', 73), (173, 190, 'A', 91),
        (124, 132, 'B', 1), (46, 54, 'B', 10), (191, 197, 'B', 19),
        (55, 63, 'C', 1), (115, 123, 'C', 10), (198, 205, 'C', 19),
        (64, 76, 'D', 1), (77, 100, 'E', 1), (206, 214, 'A', 109),
    )
    for first, last, prefix, code in ranges:
        for image in range(first, last + 1):
            result[image] = '%s-%03d' % (prefix, code + image - first)
    result[101] = 'Z-001'
    result.update({102:'A-041', 103:'B-017', 104:'D-002', 105:'E-001',
                   106:'E-007', 107:'A-071', 108:'A-080', 109:'A-083',
                   110:'A-088', 111:'A-092', 112:'A-095', 113:'E-012',
                   114:'E-015'})
    return result


PRINTED_CODES_BY_IMAGE = _printed_codes_by_image()


def install(namespace):
    """Replace every unambiguous active print and expose the full new pack."""
    cards = namespace['CARDS']
    achievements = namespace['ACHIEVEMENTS']
    for card in cards.values():
        if card.get('id') in PRINTED_CODES_BY_IMAGE:
            card['printed_code'] = PRINTED_CODES_BY_IMAGE[card['id']]
        path = EVENT_ART.get(card.get('printed_code'))
        if path:
            card.update(source=path, image_path=path, new_art=True)
    # B-017 / D-002 / E-001 / E-007 keep their multiplayer-print base effects;
    # the solo prints are applied per game mode by guild_mode_variants.
    for card in cards.values():
        code = card.get('printed_code')
        if code == 'A-080':
            card['draw'] = 1
            card['steps'] = [dict(op='purify'),
                             dict(op='consume_tiles', min=1, max=3, per={'gold': 5})]
        elif code == 'Z-001':
            card.update(price=6, strength=0, str_pro=2)
        elif code == 'C-022':
            card['point'] = -4
        elif code == 'E-012':
            card['steps'] = [dict(op='replace', concealed=True, variable=True),
                             dict(op='all', effect={'str_pro': 1}),
                             dict(op='pay_effect', costs={'pot': 1},
                                  otherwise={'steps': [dict(op='flip', self=True)]})]
            card['requires_dlc'] = ['variable_labyrinth']
    for image in range(102, 115):
        if image in cards:
            cards[image].update(available=False, special=True, archived_print=True,
                                unavailable_reason='效果已合并到新版印刷卡，不重复加入牌库。')
    retired = {'A-%03d' % n for n in range(109, 118)}
    for card in cards.values():
        if card.get('printed_code') in retired:
            card.update(available=False, special=True, archived_print=True,
                        unavailable_reason='新版图包不再收录此旧印刷版本。')
    for item in achievements.values():
        path = ROYAL_ART.get(item.get('printed_code'))
        if path:
            item.update(source=path, image_path=path, new_art=True)
    archive = namespace['HERO_ARCHIVE']
    for key, sources in HERO_ART.items():
        if key in archive:
            archive[key]['source'] = list(sources)
            archive[key]['new_art'] = True
    achievements_by_image = {item.get('image'): item for item in achievements.values()}
    for item in namespace['CARD_GALLERY'].values():
        source = cards.get(item.get('id'), achievements_by_image.get(item.get('id'), {}))
        if source.get('new_art'):
            item.update(image_path=source['image_path'], source=source['source'], new_art=True)
    for item in namespace['HERO_GALLERY'].values():
        hero = archive.get(item.get('hero'))
        level = item.get('level', 1) - 1
        if hero and hero.get('new_art') and 0 <= level < len(hero['source']):
            item['image_path'] = hero['source'][level]
            item['new_art'] = True
    # Old scans that have no replacement print are retired, not packaged as a
    # second hidden gallery.  Every supplied replacement file remains visible
    # through NEW_ART_GALLERY below.
    card_gallery = namespace['CARD_GALLERY']
    for ident, item in list(card_gallery.items()):
        if str(item.get('image_path', '')).startswith('images/cards/'):
            del card_gallery[ident]
    hero_gallery = namespace['HERO_GALLERY']
    for ident, item in list(hero_gallery.items()):
        if str(item.get('image_path', '')).startswith('images/hero/'):
            del hero_gallery[ident]
    namespace['CARD_COUNT'] = len(card_gallery)
    namespace['NEW_ART_GALLERY'] = NEW_ART_GALLERY
