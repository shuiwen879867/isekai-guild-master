"""Standalone-server assets must not rely on the previous installation."""
from pathlib import Path
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'guild-server'))
import guild_card_layouts as layouts
from guild_content import CARDS,ACHIEVEMENTS,TILES

class StandaloneAssets(unittest.TestCase):
    def test_every_replay_atlas_and_paper_is_bundled(self):
        for name in layouts.component_paths():
            with self.subTest(asset=name):self.assertTrue(layouts.component_file(name).is_file())

    def test_all_current_event_and_royal_images_have_fallbacks(self):
        for definition in list(CARDS.values())+list(ACHIEVEMENTS.values()):
            if not definition.get('available',True):continue
            number=definition.get('image')
            if type(number)is not int or layouts.source_for_image(number) in layouts.LAYOUTS:continue
            for folder in ['cards','cardfull']:
                with self.subTest(image=number,folder=folder):self.assertTrue((ROOT/'guild-server/replay_web'/folder/(str(number)+'.jpg')).is_file())

    def test_every_tile_has_a_compositor_or_raster(self):
        for key,tile in TILES.items():
            with self.subTest(tile=key):self.assertTrue(tile['source'] in layouts.LAYOUTS or (ROOT/'guild-server/replay_web/tiles'/(key+'.png')).is_file())
