import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class StandalonePortraits(unittest.TestCase):
    def test_every_portrait_source_exists_and_legacy_crops_are_explicit(self):
        catalog = json.loads((ROOT / 'GuildMaster-Godot-src/data/catalog.json').read_text('utf8'))
        record = json.loads((ROOT / 'GuildMaster-Godot-src/data/portraits.json').read_text('utf8'))
        self.assertEqual(set(record['sources']), set(catalog['heroes']))
        cards = {source for hero in catalog['heroes'].values() for source in hero['source']}
        for key, source in record['sources'].items():
            with self.subTest(hero=key):
                self.assertTrue(source)
                self.assertNotIn(source, cards)
                self.assertNotIn(source, catalog['atlas'])
                self.assertTrue((ROOT / 'GuildMaster-Godot/art' / source.removeprefix('images/')).is_file())
                self.assertEqual(source.startswith('images/portraits/'), key in record['legacy_crops'])
        self.assertEqual(len(record['legacy_crops']), 26)
        self.assertEqual(sum(x.startswith('images/tts/') for x in record['sources'].values()), 31)

    def test_new_rule_prints_reuse_the_same_characters_standalone_art(self):
        sources = json.loads((ROOT / 'GuildMaster-Godot-src/data/portraits.json').read_text('utf8'))['sources']
        for hero in ('sif', 'frida', 'bell', 'horn', 'marta'):
            for side in ('white', 'black'):
                self.assertEqual(sources[hero + '_revised_' + side], sources[hero + '_' + side])
        self.assertEqual(sources['horn_five_white'], sources['horn_white'])
