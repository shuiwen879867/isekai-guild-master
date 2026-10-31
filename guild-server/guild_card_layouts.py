"""Original-coordinate card components used by the live card compositor.

The bitmap card faces are authoring references only. A displayed card consists
of a small paper plate and separately placed original glyph/icon components.
"""
import json
import base64
from functools import lru_cache
from pathlib import Path

INDEX = Path(__file__).with_name('guild_card_layouts.json')
LAYOUTS = json.loads(INDEX.read_text(encoding='utf-8')) if INDEX.is_file() else {}


def authoring_sources():
    import guild_content as c
    from guild_new_content import PROLOGUES, asset
    from guild_new_art import NEW_ART_IDS
    numbers=set()
    for first,last in ((842900,842914),(845600,845621),(845900,845917),
                       (846000,846017),(846100,846117),(846200,846217),
                       (846300,846317),(846400,846417),(846500,846516),
                       (846700,846711),(846800,846810),(847200,847217),(847400,847416)):
        numbers.update(range(first,last+1))
    numbers.update((847001,847002,847005,847006,847007,847008,847009,847010,
                    847600,848000,848200))
    result={'images/new_art/%s.webp'%n:'card' for n in numbers if n in NEW_ART_IDS}
    for data in c.CARDS.values():
        source=data.get('source','')
        if source.startswith('tts_128_') and data['id']!=337:
            result[source]='card'
    for data in c.ACHIEVEMENTS.values():
        result[data['source']]='card'
    for data in PROLOGUES.values():
        result[data['source']]='card'
    for data in c.TILES.values():
        result[data['source']]='tile'
    for number in range(1,23):
        result['images/piece_png/%s.png'%number]='tile'
    for number in (63,83,87,88):
        result[asset(number)]='tile'
    return result


def excluded_faces():
    import guild_content  # Install the atlas aliases before finding unused sheets.
    from guild_new_content import ATLAS
    paths={source for source in LAYOUTS if source.startswith('images/')}
    for path in {data['path'] for key,data in ATLAS.items() if key in LAYOUTS}:
        names={key for key,data in ATLAS.items() if data['path']==path}
        if names<=LAYOUTS.keys():
            paths.add(path)
    return sorted(paths)


def source_for_image(number):
    import guild_content as c
    for card in c.ACHIEVEMENTS.values():
        if card.get('image')==number:
            return card['source']
    return c.CARDS.get(number,{}).get('source')


def layout_for_image(number):
    return LAYOUTS.get(source_for_image(number))


def component_paths():
    return sorted({layout[key] for layout in LAYOUTS.values() for key in ('paper','atlas')})


def component_file(path):
    root=Path(__file__).resolve().parent
    native=root/path
    return native if native.is_file() else root/path.removeprefix('images/')


@lru_cache(maxsize=512)
def render_svg(source):
    """The web client draws the same original-coordinate atlas fragments."""
    layout=LAYOUTS[source]
    width,height=layout['width'],layout['height']
    def encoded(path):
        return 'data:image/webp;base64,'+base64.b64encode(component_file(path).read_bytes()).decode('ascii')
    aw,ah=layout['atlas_size']
    result=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
            f'<defs><image id="glyphs" href="{encoded(layout["atlas"])}" width="{aw}" height="{ah}"/></defs>',
            f'<image href="{encoded(layout["paper"])}" width="{width}" height="{height}" preserveAspectRatio="none"/>']
    for part in layout['parts']:
        x,y,w,h=part['box']
        result.append(f'<svg x="{part["x"]}" y="{part["y"]}" width="{w}" height="{h}" viewBox="{x} {y} {w} {h}" overflow="hidden"><use href="#glyphs"/></svg>')
    result.append('</svg>')
    return ''.join(result).encode('utf-8')
