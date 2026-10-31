import json
from pathlib import Path
import sys
import unittest
import hashlib

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from validate_voice_assets import validate


class BilingualVoiceRelease(unittest.TestCase):
    def test_supplied_partial_replacement_preserves_every_unmatched_file(self):
        record=json.loads((ROOT/'docs/SUPPLIED_VOICE_OVERRIDES.json').read_text('utf8'))
        self.assertEqual(record['source_recordings'],284)
        for path,expected in record['unmatched_assets_sha256'].items():
            self.assertEqual(hashlib.sha256((ROOT/'GuildMaster-Godot-src'/path).read_bytes()).hexdigest(),expected,path)
        self.assertEqual({entry['member'] for entry in record['missing_retained']},{'kanban-005__card-red-r1.ogg','kanban-005__card-red-r2.ogg'})
    def test_every_playable_print_has_validated_bilingual_audio(self):
        manifest=validate()
        self.assertEqual(len(manifest['heroes']),57)
        self.assertEqual(len(manifest['characters']),25)
        self.assertEqual(manifest['default_locale'],'ja')
        for locale in ('ja','zh_CN'):
            paths={p for hero in manifest['heroes'].values() for choices in hero['events'][locale].values() for p in choices}
            self.assertEqual(len(paths),567,locale)

    def test_supplied_shion_recording_is_japanese_only(self):
        manifest=json.loads((ROOT/'GuildMaster-Godot-src/data/voice_manifest.json').read_text('utf8'))
        for key in ('shion_white','shion_red'):
            for paths in manifest['heroes'][key]['events']['ja'].values():
                self.assertTrue(all(manifest['clips'][p]['source']=='supplied_recording' for p in paths))
            for paths in manifest['heroes'][key]['events']['zh_CN'].values():
                self.assertTrue(all(manifest['clips'][p]['source']=='synthetic' for p in paths))

    def test_rule_variants_have_their_own_level_cues(self):
        manifest=json.loads((ROOT/'GuildMaster-Godot-src/data/voice_manifest.json').read_text('utf8'))
        for locale in ('ja','zh_CN'):
            for base,revised in [('sif_white','sif_revised_white'),('frida_white','frida_revised_white'),('horn_white','horn_revised_white'),('marta_white','marta_revised_white'),('bell_white','bell_revised_white')]:
                for rank in (1,2,3):
                    self.assertNotEqual(manifest['heroes'][base]['events'][locale]['rank_'+str(rank)],manifest['heroes'][revised]['events'][locale]['rank_'+str(rank)])


if __name__=='__main__':unittest.main()
