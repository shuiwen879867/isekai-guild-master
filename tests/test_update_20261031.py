from copy import deepcopy
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'guild-server'))
from guild_engine import Engine
from guild_content import CARDS,HEROES,CHARACTERS

def game(hero,solo=False):
    players=[dict(id=0,name='Test',hero=hero)]
    if not solo:players.append(dict(id=1,name='Other',hero='bai_white'))
    e=Engine(players,options=dict(solo=solo,start_player=0,setup_draft=False),seed=18)
    e.state.update(phase='action',turn=0,pending=None,effects=[])
    return e

def pick(e,values,**extra):
    q=e.state['pending'];e.apply(q['player'],dict(type='choice',choice_id=q['id'],selected=[next(i for i,o in enumerate(q["options"]) if type(o["value"]) is type(v) and o["value"]==v) for v in values],**extra))

class OctoberUpdate(unittest.TestCase):
    def test_bell_uses_printed_units_not_discounted_payment(self):
        for price in (0,5,10,15,20,25,30,11,16,23):
            with self.subTest(price=price):
                e=game('bell_white');p=e._player(0);p.update(gold=100,hand=[5],hero_deck=[1],tags=[])
                with patch.dict(CARDS,{5:dict(CARDS[5],price=price,requirements={},draw=0,gold=0,gold_pro=0,tags=[],steps=[],conditional=[],triggers=[])}):
                    e._play(p,dict(type='play',card=5,_discount=3));e._drain_effects()
                p=e._player(0);trigger=price%10 in (0,5)
                self.assertEqual(p['gold'],100-max(0,price-3)+(2 if trigger else 0))
                self.assertEqual(len(p['hero_deck']),0 if trigger else 1)

    def test_elu_solo_substitutes_all_rules_and_assets(self):
        e=game('elu_red_b',solo=True);p=e._player(0)
        self.assertEqual(p['hero'],'peria_black')
        self.assertEqual(p['gold_pro'],HEROES['peria_black']['gold_pro'])
        self.assertEqual(p['gold'],HEROES['peria_black']['gold'])
        self.assertEqual(game('elu_red_b')._player(0)['hero'],'elu_red_b')

    def test_new_character_choices_have_all_three_faces(self):
        added=[(k,h) for k,h in HEROES.items() if h.get('screenshot_print')]
        self.assertEqual(len(added),11)
        for key,h in added:
            self.assertEqual(CHARACTERS[h['character']]['variants'][h['variant']],key)
            self.assertTrue(all((Path(__file__).resolve().parents[1]/'GuildMaster-Godot/art'/s).is_file() for s in h['source']))

    def test_frida_strength_production_reward_includes_upgrade(self):
        e=game('frida_revised_black');p=e._player(0);before=p['gold']
        e._effects(p,HEROES[p['hero']]['upgrade2'])
        self.assertEqual(p['str_pro'],2)
        self.assertEqual(p['gold'],before+6)
        self.assertEqual(p['gold_pro'],16)

    def test_sif_upgrade_pays_strength_production(self):
        e=game('sif_revised_white');p=e._player(0);p['str_pro']=1
        e._enqueue(p,[dict(op='effect',effect=HEROES[p['hero']]['upgrade2'])]);e._drain_effects()
        pick(e,[True]);p=e._player(0)
        self.assertEqual(p['str_pro'],0);self.assertEqual(p['gold_pro'],27)

    def test_horn_rewards_only_new_complete_sets(self):
        e=game('horn_revised_white');p=e._player(0);before=p['gold']
        e._gain_tags(p,['civ','gold','scrap']);self.assertEqual(p['gold'],before+8)
        e._gain_tags(p,['civ','gold']);self.assertEqual(p['gold'],before+8)
        e._gain_tags(p,['scrap']);self.assertEqual(p['gold'],before+16)
        self.assertEqual(HEROES['horn_five_white']['screenshot_sets'],5)

    def test_marta_lazy_card_is_private_and_changes_civilization(self):
        e=game('marta_revised_white',solo=True);p=e._player(0)
        self.assertIn(303,p['hand']);self.assertNotIn(303,e.state['deck'])
        self.assertEqual(e.state['civ'],4)
        p.update(played=[303],card_states=[],available=2)
        e._card_states(p)[0]['adventurers']=2
        previous=p['gold'];civ=e.state['civ']
        e._enqueue(p,[dict(op='screenshot_lazy_finish')]);e._drain_effects()
        self.assertEqual(p['gold'],previous+30);self.assertEqual(p['available'],4)
        self.assertTrue(e._card_states(p)[0]['face_down']);self.assertEqual(e.state['civ'],max(1,civ-3))

    def test_bell_attached_tile_gives_potions_and_preserves_tile(self):
        e=game('bell_revised_black');p=e._player(0)
        from guild_content import TILES
        tile=next(k for k,v in TILES.items() if v.get('point',0)>0 and not v.get('boss') and k!='boss')
        p['tiles']=[tile];before=(p['gold'],p['pot'])
        e._enqueue(p,[dict(op='screenshot_attach')]);e._drain_effects();pick(e,[0]);p=e._player(0)
        self.assertEqual(p['gold'],before[0]+8);self.assertEqual(p['pot'],before[1]+TILES[tile]['point'])
        self.assertEqual(p['hero_tiles'],[tile])

    def test_all_new_effects_resolve_or_offer_valid_choice(self):
        for key,h in HEROES.items():
            if not h.get('screenshot_print'):continue
            for field in ('ability','upgrade2','upgrade3'):
                with self.subTest(hero=key,effect=field):
                    e=game(key);p=e._player(0);p.update(gold=200,strength=10,pot=10,gold_pro=30,str_pro=10,hand=list(CARDS)[:8],tiles=['tile21'])
                    e._enqueue(p,[dict(op='effect',effect=h[field])]);e._drain_effects()
                    self.assertTrue(e.state.get('pending') or not e.state.get('effects'))

    def test_bell_free_star_exploration_cannot_claim_boss_or_hole(self):
        e=game('bell_revised_black');p=e._player(0)
        p['_print_explore']=dict(no_star=True,hole_retry=True)
        boss=next(c for c in e.state['board'] if c.get('boss'))
        self.assertFalse(e.can_explore(0,boss['id']))
        c=next(c for c in e.state['board'] if not c.get('boss') and e.can_explore(0,c['id']))
        c.update(loot='tile14',revealed=True)
        self.assertFalse(e.can_explore(0,c['id']))
        c.update(loot='tile1',revealed=True)
        actual=e._exploration_cost(p,c,3,True)
        p.pop('_print_explore')
        self.assertLessEqual(actual,e._exploration_cost(p,c,3,True))

    def test_marta_upgrade_builds_two_regions_without_any_gold(self):
        e=game('marta_revised_black');p=e._player(0);p['gold']=0
        cells=[c for c in e.state['board'] if not c.get('boss')][:2]
        for c in cells:c.update(owner=0,base=False,region=2)
        e._enqueue(p,[dict(op='screenshot_build',max=2,optional=True)]);e._drain_effects()
        pick(e,[c['id'] for c in cells]);p=e._player(0)
        self.assertTrue(all(e._cell(c['id'])['base'] for c in cells));self.assertEqual(p['gold'],0)

if __name__=='__main__':unittest.main()
