"""Deterministic, JSON-serializable guild board-game engine (Python 3.9).

Only this module owns rules; clients must submit actions through ``apply``.
``turn`` is a player-list index, while action callers use the player's ID.
Research selections may arrive in any order. Exchange and discarding a held
achievement are free operations, including during research. A final-round pass
forfeits the player's remaining turns, following the official rulebook.

Content is supplied by guild_content. Optional RULES overrides are recorded in
saves. Development/exploration/endgame follow the official 2026 base
rulebook research, including its corrections to the earlier blog summary.
Multiplayer has no round cutoff unless explicitly configured. Solo options
use the supplied expansion rulebook's six-round challenge.
"""

from collections import Counter
from copy import deepcopy
from functools import wraps
import json
import random

try:
    import guild_content as _content
except ModuleNotFoundError as exc:
    if exc.name != "guild_content":
        raise
    _content = None

CARDS = getattr(_content, "CARDS", {})
HEROES = getattr(_content, "HEROES", {})
TILES = getattr(_content, "TILES", {})
ACHIEVEMENTS = getattr(_content, "ACHIEVEMENTS", {})
POTIONS = getattr(_content, "POTIONS", {})
RULES = getattr(_content, "RULES", {})
TAG_NAMES = getattr(_content, "TAG_NAMES", {})
STARTING_RESOURCES = getattr(_content, "starting_resources", None)

DEFAULT_RULES = {
    "development_slots": {
        "gold": {"costs": {"gold": 20}},
        "strength": {"costs": {"strength": 3}},
        "pot": {"costs": {"pot": 2}},
        "territory": {"requirements": {"controlled": 3}},
        "cards": {"requirements": {"played": 8}},
    },
    "build_cost": 15,
    "adjacent_base_cost": 5,
    "exchange_rate": 3,
    "discard_achievement_gold": 5,
    "research_cost": 3,
    "initial_available": 2,
    "treasures": {
        "fame": {"name": "声望宝物", "point": 3},
        "industry": {"name": "工艺宝物", "point": 2, "gold_pro": 2, "str_pro": 1},
        "alchemy": {"name": "炼金宝物", "point": 2, "pot_pro": 1},
        "tags": {"name": "知识宝物", "point": 2, "tags": ["civ", "gold", "scrap"]},
        "potions": {"name": "秘药宝物", "point": 1, "pot": 2},
    },
    "initial_reveals": [[2, 0], [0, 2], [-2, 2], [-2, 0], [0, -2], [2, -2]],
    "retreat_penalty": 1,
    "edition": "Audited earlier-edition cards/blog retreat1; precise shared rules and treasures from official2026",
    "source": "https://drive.google.com/file/d/1bZBzLM2osEQKWaMgNDK4652620cXwGpO/view",
}
RESOURCE_KEYS = ("gold", "strength", "pot", "gold_pro", "str_pro", "pot_pro")
# Display labels live with the engine so the replay viewer never needs Ren'Py.
DEVELOPMENT_SLOT_LABELS = {"gold": "公会投资", "strength": "冒险训练", "pot": "秘药馈赠",
                           "territory": "拓展疆域", "cards": "经营有方"}
DIRECTIONS = ((1, 0), (0, 1), (-1, 1), (-1, 0), (0, -1), (1, -1))


def _zh(message):
    """Keep all rule rejection messages suitable for the Chinese game UI."""
    if any("\u4e00" <= char <= "\u9fff" for char in message):
        return message
    messages = {
        "The game is finished": "对局已经结束。",
        "It is not this player's turn": "现在不是你的行动回合。",
        "Finish research first": "请先等待所有玩家完成情报收集。",
        "Unknown player": "找不到该玩家。",
        "Unknown board cell": "找不到该地图格。",
        "tile must be a board cell ID": "请选择地图上的一个有效格子。",
        "Not enough strength": "力量不足。",
        "Card is not in hand": "手中没有这张卡牌。",
        "Card requirements are not met": "尚未满足这张卡的前置条件。",
        "Not enough loot tiles to consume": "可支付的已获得迷宫板块不足。",
        "Choose the required held loot tiles": "请选择要支付的迷宫板块。",
        "This card cannot use strength for its gold price": "这张卡不能用力量抵扣金币费用。",
        "Selected card copies are not available": "所选卡牌数量超过实际持有数量。",
        "cards must be a list of integer card IDs": "请选择有效的卡牌编号。",
        "Research is not available": "现在不能进行情报收集，或你已选牌完毕。",
        "Player already researched": "你已经完成了本轮选牌。",
        "Explore the border or a cell next to your adventurer": "只能探索外缘或相邻自己领地的未占领格，且需有可派遣冒险者。",
        "Build on your occupied cell without a base": "只能在自己尚未建设据点的领地上建设。",
        "Affection cannot exceed five": "好感度最多为五。",
        "Select one available development slot per affection": "请为每次发展选择一个可解锁的好感度条件。",
        "Development slots must be unused and distinct": "所选发展条件必须尚未解锁，且不能重复。",
        "Development slot requirements are not met": "尚未满足所选发展条件。",
        "Potion slot is unavailable": "该秘药行动本轮已使用，或当前人数不开放。",
        "Hero ability is not available": "看板娘没有可用能力，或本轮已经使用。",
        "Choose the required number of cards to discard": "请选择能力要求数量的手牌弃置。",
        "Card has no available action": "这张已打出的卡没有可用特别行动。",
        "Card action already used this round": "这张卡的特别行动本轮已使用。",
        "Unknown achievement": "找不到该王权卡。",
        "Achievement is unavailable": "该王权卡已被取得，或不在你的手中。",
        "Achievement is not held": "你没有持有这张私人王权卡。",
        "Achievement requirements are not met": "尚未满足这张王权卡的全部条件。",
        "Treasure is unavailable": "该宝物已被拿取，请选择剩余宝物。",
        "Choose a concealed ordinary tile": "请选择背面显示一星的普通迷宫板块。",
        "Unknown effect choice": "请选择有效的升级效果。",
        "Unknown civilization choice": "请选择文明增加或减少。",
        "Choose an affection slot": "请选择要免费解锁的好感度条件。",
    }
    if message in messages:
        return messages[message]
    if message.startswith("Not enough "):
        key = message[len("Not enough "):].split(" ")[0]
        return {"gold": "金币", "pot": "秘药", "strength": "力量", "gold_pro": "金币产能",
                "str_pro": "力量产能", "pot_pro": "秘药产能"}.get(key, "资源") + "不足。"
    if message.startswith("Unknown action type:"):
        return "无法识别该行动。"
    if "must be an integer" in message:
        return "数量或编号必须为有效的非负整数。"
    return "操作参数无效，或未满足规则要求。"


def _localized(method):
    @wraps(method)
    def wrapped(*args, **kwargs):
        try:
            return method(*args, **kwargs)
        except ValueError as exc:
            raise ValueError(_zh(str(exc))) from None
    return wrapped


def _integer(value, name, minimum=0):
    if type(value) is not int or value < minimum:
        raise ValueError("%s must be an integer >= %s" % (name, minimum))
    return value


def _tuples(value):
    return tuple(_tuples(item) for item in value) if isinstance(value, list) else value


class CoreEngine:
    """Authoritative game state, independent of UI, networking and Ren'Py."""

    @_localized
    def __init__(self, player_specs, seed=None, max_rounds=0, options=None):
        if not isinstance(player_specs, (list, tuple)) or not 1 <= len(player_specs) <= 5:
            raise ValueError("一场对局需要 1–5 位玩家")
        if not CARDS or not HEROES or not TILES:
            raise ValueError("guild_content must provide CARDS, HEROES and TILES")
        _integer(max_rounds, "max_rounds")
        self.rules = deepcopy(DEFAULT_RULES)
        self.rules.update(deepcopy(RULES))
        from guild_modes import normalize_options
        self.rules["options"] = normalize_options(options,len(player_specs))
        from guild_mode_variants import apply_mode_variants
        apply_mode_variants(self.rules["options"])
        self.state = {
            "version": 1, "phase": "research", "round": 1, "season": 3,
            "civ": 1, "miasma": 10 * len(player_specs), "turn": 0,
            "start_player": 0, "players": [], "board": [], "deck": [],
            "discard": [], "achievement_deck": [], "achievement_discard": [],
            "public_achievements": [], "potions_used": [],
            "treasure_pool": list(self.rules["treasures"]),
            "potions_disabled": ["gold", "strength"] if len(player_specs) == 2 else ["strength"] if len(player_specs) == 3 else [],
            "final_remaining": [], "final_actions_taken": 0,
            "scores": [], "winners": [], "max_rounds": max_rounds,
            "action_count": 0, "last_action": None, "log": [],
            "rng": json.loads(json.dumps(random.Random(seed).getstate())),
        }
        seen = set()
        for spec in player_specs:
            if not isinstance(spec, dict):
                raise ValueError("Invalid player specification")
            pid = spec.get("id")
            if type(pid) not in (int, str) or pid in seen or pid == "":
                raise ValueError("Player IDs must be unique integers or nonempty strings")
            seen.add(pid)
            hero_id = spec.get("hero", next(iter(HEROES)))
            if self.rules['options'].get('solo'):
                hero_id = HEROES.get(hero_id,{}).get('solo_replacement',hero_id)
            if not isinstance(hero_id, str) or hero_id not in HEROES or not HEROES[hero_id].get('available', True):
                raise ValueError("Unknown hero")
            hero = HEROES[hero_id]
            p = {"id": pid, "name": str(spec.get("name", pid)), "hero": hero_id,
                 "bot": bool(spec.get("bot", False)), "connected": bool(spec.get("connected", True)), "affection": 0,
                 "available": self.rules["initial_available"], "hand": [],
                 "offered": [], "researched": False, "achievements": [],
                 "earned_achievements": [], "played": [], "tiles": [],
                 "used": [], "passed": False, "retreat": 0, "reputation": 0,
                 "treasures": [], "tags": [], "hero_level": 1,
                 "developed": []}
            allocation = STARTING_RESOURCES(hero_id) if STARTING_RESOURCES else hero
            for key in RESOURCE_KEYS:
                p[key] = _integer(allocation.get(key, 0), "hero " + key)
            self.state["players"].append(p)
        # One physical scan per deck entry; dedicated cards belong to heroes.
        self.state["deck"] = [key for key, card in CARDS.items() if self._card_in_deck(card)]
        self._shuffle(self.state["deck"])
        self.state["achievement_deck"] = [k for k,v in ACHIEVEMENTS.items() if not v.get("solo")]
        self._shuffle(self.state["achievement_deck"])
        for unused in range(min(3, len(self.state["achievement_deck"]))):
            self.state["public_achievements"].append(self.state["achievement_deck"].pop())
        for p in self.state["players"]:
            self._draw_achievement(p, 2)
            p["offered"] = self._draw(8)
            hero = HEROES[p["hero"]]
            p["hand"].extend(self._draw(hero.get("draw", 0)))
            self._draw_achievement(p, hero.get("draw_achievement", hero.get("initial_achievements", 0)))
            self._gain_tags(p, hero.get("tags", []))
        self._make_board()
        self._setup_variants()
        from guild_clock import sync
        sync(self)

    def _shuffle(self, items):
        rng = random.Random()
        rng.setstate(_tuples(self.state["rng"]))
        rng.shuffle(items)
        self.state["rng"] = json.loads(json.dumps(rng.getstate()))

    def _draw(self, count):
        count = _integer(count, "draw")
        result = []
        for unused in range(count):
            if not self.state["deck"]:
                self.state["deck"], self.state["discard"] = self.state["discard"], []
                self._shuffle(self.state["deck"])
            if not self.state["deck"]:
                break
            result.append(self.state["deck"].pop())
        return result

    def _draw_achievement(self, player, count):
        for unused in range(_integer(count, "draw_achievement")):
            if not self.state["achievement_deck"]:
                break
            player["achievements"].append(self.state["achievement_deck"].pop())

    def _log(self, message, player=None):
        self.state['log_serial'] = self.state.get('log_serial',0)+1
        self.state["log"].append({"id": self.state['log_serial'], "message": message, "round": self.state["round"],
                                  "player": None if player is None else player["id"]})
        del self.state["log"][:-120]

    def _player(self, player_id):
        for player in self.state["players"]:
            if type(player["id"]) is type(player_id) and player["id"] == player_id:
                return player
        raise ValueError("Unknown player")

    def _cell(self, tile_id):
        if not isinstance(tile_id, str):
            raise ValueError("tile must be a board cell ID")
        for cell in self.state["board"]:
            if cell["id"] == tile_id:
                return cell
        raise ValueError("Unknown board cell")

    def _neighbors(self, cell):
        positions = {(cell["q"] + dq, cell["r"] + dr) for dq, dr in DIRECTIONS}
        return [other for other in self.state["board"] if (other["q"], other["r"]) in positions]

    def _bases(self, player):
        return sum(cell["owner"] == player["id"] and cell["base"] for cell in self.state["board"])

    def _tags(self, player):
        tags = Counter(player.get("tags", []))
        for card in player["played"]:
            tags.update(CARDS[card].get("tags", []))
        for loot in player["tiles"]:
            tags.update(TILES[loot].get("tags", []))
        return tags

    def _stat(self, player, stat):
        if stat in ("tiles", "pieces"):
            return len(player["tiles"])
        if stat in ("played", "cards"):
            return len(player["played"])
        if stat == "bases":
            return self._bases(player)
        if stat == "controlled":
            return sum(c["owner"] == player["id"] for c in self.state["board"])
        if stat == "tags":
            return sum(self._tags(player).values())
        if stat == "heart":
            return player["affection"]
        if stat == "earned_achievements":
            return len(player["earned_achievements"])
        if stat == "civ":
            return self.state["civ"]
        if stat.startswith("tag:"):
            return self._tags(player)[stat[4:]]
        if stat not in player or type(player[stat]) is not int:
            raise ValueError("Unsupported requirement stat: " + stat)
        return player[stat]

    def _requirements(self, player, req, tag_discount=False):
        if not req:
            return True
        if "any" in req and not any(self._requirements(player, r, tag_discount) for r in req["any"]):
            return False
        if "all" in req and not all(self._requirements(player, r, tag_discount) for r in req["all"]):
            return False
        if "stat" in req and self._stat(player, req["stat"]) < req.get("value", 0):
            return False
        actual_tags = self._tags(player)
        shortage = {tag: max(0, amount - actual_tags[tag]) for tag, amount in req.get("tags", {}).items()}
        passive = HEROES[player["hero"]].get("passive", {})
        discount = passive.get("tag_discount", {"tags": passive.get("discount_tags", []),
                                                "amount": passive.get("requirement_tag_discount", 0)}) if tag_discount else {}
        if isinstance(discount, int):
            discount = {"tags": ["civ", "gold", "scrap"], "amount": discount}
        discountable = discount.get("tags", [])
        if any(amount for tag, amount in shortage.items() if tag not in discountable):
            return False
        if sum(shortage.values()) > discount.get("amount", 0):
            return False
        for key in ("heart", "affection", "pieces", "tiles", "civ", "bases", "cards", "played",
                    "gold", "strength", "pot", "gold_pro", "str_pro", "pot_pro", "controlled"):
            if key in req and self._stat(player, key) < req[key]:
                return False
        return True

    def _gain_tags(self, player, tags, store=True):
        if store:
            player["tags"].extend(tags)
        passive = HEROES[player["hero"]].get("passive", {})
        rewards = passive.get("on_tag_strength", {})
        if isinstance(rewards, int):
            rewards = {"scrap": rewards}
        player["strength"] += sum(rewards.get(tag, 0) for tag in tags)

    def _pay(self, player, costs):
        for key, amount in costs.items():
            if key not in RESOURCE_KEYS:
                raise ValueError("Unsupported payment: " + key)
            _integer(amount, "cost")
            if player[key] < amount:
                raise ValueError("Not enough " + key)
        for key, amount in costs.items():
            player[key] -= amount

    def _effects(self, player, effects, action=None):
        action = action or {}
        if not isinstance(effects, dict):
            raise ValueError("Invalid content effect")
        self._pay(player, effects.get("costs", {}))
        if "discard_min" in effects or "discard_max" in effects:
            cards = action.get("cards", action.get("discard", []))
            self._check_cards(cards, player["hand"])
            if not effects.get("discard_min", 0) <= len(cards) <= effects.get("discard_max", len(cards)):
                raise ValueError("Choose the required number of cards to discard")
            for card in cards:
                player["hand"].remove(card)
                self.state["discard"].append(card)
            player["gold"] += len(cards) * effects.get("gold_per_discard", 0)
        for key in RESOURCE_KEYS:
            value = effects.get(key, 0)
            if type(value) is not int:
                raise ValueError("Invalid resource effect")
            # Explicit costs must be paid; an impossible on-play effect is
            # skipped (official Q&A), not silently converted to a partial loss.
            if player[key] + value >= 0:
                player[key] += value
        if self.state["phase"] != "final":
            self.state["civ"] = max(1, self.state["civ"] + effects.get("civ", 0))
            self.state["miasma"] = max(0, self.state["miasma"] + effects.get("miasma", 0))
        player["reputation"] += effects.get("reputation", 0)
        player["gold"] += effects.get("gold_per_played", 0) * len(player["played"])
        for scaled in effects.get("scaled", []):
            resource = scaled["resource"]
            value = self._stat(player, scaled['stat']) // max(1, scaled.get('per',1))
            value = value*scaled.get('multiplier',1)+scaled.get('offset',0)
            value = max(scaled.get('min',-10**9),min(value,scaled.get('max',scaled.get('cap',10**9))))
            if self.rules.get('options',{}).get('solo') and 'solo_max' in scaled:
                value = min(value,scaled['solo_max'])
            player[resource] = max(0,player.get(resource,0)+value)
        player["hand"].extend(self._draw(effects.get("draw", 0)))
        self._draw_achievement(player, effects.get("draw_achievement", 0))
        self._gain_tags(player, effects.get("tags", []))
        if effects.get("affection", 0) and player["affection"] < 5:
            self._develop(player, min(5 - player["affection"], effects["affection"]), action, free=True)
        if effects.get("choices"):
            options = effects["choices"]
            if "choice" not in action:
                raise ValueError("Unknown effect choice")
            choice = _integer(action["choice"], "choice")
            if choice >= len(options):
                raise ValueError("Unknown effect choice")
            self._effects(player, options[choice], action)
        if "civ_choice" in effects:
            if "choice" not in action:
                raise ValueError("Unknown civilization choice")
            choice = _integer(action["choice"], "choice")
            if choice >= len(effects["civ_choice"]):
                raise ValueError("Unknown civilization choice")
            self._effects(player, {"civ": effects["civ_choice"][choice]}, action)

    @staticmethod
    def _check_cards(cards, available):
        if not isinstance(cards, list) or any(type(card) is not int for card in cards):
            raise ValueError("cards must be a list of integer card IDs")
        if Counter(cards) - Counter(available):
            raise ValueError("Selected card copies are not available")

    @_localized
    def apply(self, player_id, action_dict):
        """Apply one request atomically; malformed/illegal requests raise ValueError.

        A legal exploration that reveals an unaffordable tile is a successful
        request with outcome 'retreat'. It reveals the tile and consumes a turn.
        Validation errors, including invalid IDs and overspent strength, reveal
        nothing and do not change state or the random generator.
        """
        if not isinstance(action_dict, dict) or not isinstance(action_dict.get("type"), str):
            raise ValueError("Action must be a dictionary with a type")
        def private_keys(value):
            if isinstance(value,dict):
                return any(str(k).startswith('_') or private_keys(v) for k,v in value.items())
            return isinstance(value,list) and any(private_keys(v) for v in value)
        if private_keys(action_dict):
            raise ValueError('内部规则参数不能由玩家提交。')
        from guild_undo import record, restore
        if action_dict['type'] == 'undo':
            return restore(self, player_id, action_dict)
        trial = self.__class__.__new__(self.__class__)
        trial.state = deepcopy(self.state)
        trial.rules = deepcopy(self.rules)
        try:
            trial._apply(player_id, deepcopy(action_dict))
            trial.view(player_id)
        except ValueError as exc:
            raise ValueError(_zh(str(exc))) from None
        except (KeyError, TypeError, IndexError, OverflowError, AttributeError) as exc:
            raise ValueError("操作参数格式不正确。") from None
        before = self.state
        self.state = trial.state
        record(self, before, player_id, action_dict)
        from guild_clock import sync
        sync(self)
        return self.view(player_id)

    def _apply(self, player_id, action):
        p = self._player(player_id)
        phase = self.state["phase"]
        kind = action["type"]
        if phase == "finished":
            raise ValueError("The game is finished")
        # These rulebook conversions are free, not extra final-round actions.
        if kind == "exchange":
            amount = _integer(action.get("amount", 1), "amount", 1)
            self._pay(p, {"pot": amount})
            p["gold"] += amount * self.rules["exchange_rate"]
            self._log("%s将%s秘药兑换为%s金币。" % (p["name"], amount, amount * self.rules["exchange_rate"]), p)
            return
        if kind == "discard_achievement":
            achievement = action.get("id")
            if achievement not in p["achievements"]:
                raise ValueError("Achievement is not held")
            p["achievements"].remove(achievement)
            self.state["achievement_discard"].append(achievement)
            p["gold"] += self.rules["discard_achievement_gold"]
            self._log("%s弃置一张私人王权卡，获得%s金币。" % (p["name"], self.rules["discard_achievement_gold"]), p)
            return
        if kind == "research":
            if phase != "research" or p["researched"]:
                raise ValueError("Research is not available")
            cards = action.get("cards", [])
            self._check_cards(cards, p["offered"])
            self._pay(p, {"gold": len(cards) * self.rules["research_cost"]})
            p["hand"].extend(cards)
            remaining = Counter(p["offered"]) - Counter(cards)
            self.state["discard"].extend(remaining.elements())
            p["offered"] = []
            p["researched"] = True
            self._log("%s保留%s张情报卡。" % (p["name"], len(cards)), p)
            if all(other["researched"] for other in self.state["players"]):
                self.state["phase"] = "action"
                self.state["turn"] = self.state["start_player"]
            return
        if phase not in ("action", "final"):
            raise ValueError("Finish research first")
        index = self.state["turn"]
        if self.state["players"][index]["id"] != player_id or (p["passed"] and phase != "final"):
            raise ValueError("It is not this player's turn")
        outcome = "ok"
        if kind == "play":
            self._play(p, action)
        elif kind == "explore":
            outcome = self._explore(p, action)
        elif kind == "build":
            self._build(p, action.get("tile"))
        elif kind == "develop":
            self._develop(p, action.get("count", len(action.get("slots", [None]))), action)
        elif kind == "potion":
            self._potion(p, action)
        elif kind == "ability":
            ability = HEROES[p["hero"]].get("ability", {})
            if not ability or "ability" in p["used"]:
                raise ValueError("Hero ability is not available")
            self._effects(p, ability, action)
            p["used"].append("ability")
        elif kind == "card_action":
            card_id = _integer(action.get("card"), "card")
            if card_id not in p["played"] or not CARDS[card_id].get("action"):
                raise ValueError("Card has no available action")
            marker = "card:%s" % card_id
            if p["used"].count(marker) >= p["played"].count(card_id):
                raise ValueError("Card action already used this round")
            self._effects(p, CARDS[card_id]["action"], action)
            p["used"].append(marker)
        elif kind == "achievement":
            self._achievement(p, action)
        elif kind == "pass":
            p["passed"] = True
        else:
            raise ValueError("Unknown action type: " + kind)
        self.state["action_count"] += 1
        self.state["last_action"] = {"player": player_id, "type": kind, "outcome": outcome}
        if kind == "play":
            message = "%s打出了《%s》。" % (p["name"], CARDS[action["card"]].get("name", action["card"]))
        elif kind == "explore":
            result = {"explored": "探索成功", "retreat": "探索撤退", "hole": "发现深渊洞穴，获得额外行动"}[outcome]
            message = "%s在%s%s。" % (p["name"], action["tile"], result)
        elif kind == "build":
            message = "%s在%s建设据点。" % (p["name"], action["tile"])
        elif kind == "achievement":
            message = "%s完成了%s王权《%s》。" % (p["name"], "公开" if action.get("public") else "私人", ACHIEVEMENTS[action["id"]].get("name", action["id"]))
        else:
            message = "%s：%s。" % (p["name"], {"develop": "完成发展", "potion": "使用秘药行动",
                                                     "ability": "使用看板娘能力", "card_action": "使用卡牌特别行动", "pass": "休店"}[kind])
        self._log(message, p)
        if phase == "final":
            if outcome == "hole":
                return
            self.state["final_remaining"][index] -= 1
            if kind == "pass":
                self.state["final_remaining"][index] = 0
            self.state["final_actions_taken"] += 1
            if not any(self.state["final_remaining"]):
                self._finish()
            else:
                self._next_turn(index, final=True)
        elif outcome == "hole":
            # Common exploration of a hole grants the current player another
            # turn; endgame is checked after that complete turn sequence.
            pass
        elif self.state["miasma"] <= self.state["civ"] + 1:
            self._begin_final(index, "tracks")
        elif all(other["passed"] for other in self.state["players"]):
            if self.state["max_rounds"] and self.state["round"] >= self.state["max_rounds"]:
                self._begin_final(index, "round_limit")
            else:
                self._season()
        else:
            self._next_turn(index)

    def _play(self, player, action, free=False):
        card_id = _integer(action.get("card"), "card")
        if card_id not in player["hand"] or card_id not in CARDS:
            raise ValueError("Card is not in hand")
        card = CARDS[card_id]
        strength = _integer(action.get("strength", 0), "strength")
        if strength and (free or not card.get("can_trans", False)):
            raise ValueError("This card cannot use strength for its gold price")
        if not self._requirements(player, card.get("requirements", {}), tag_discount=True):
            raise ValueError("Card requirements are not met")
        consume = _integer(card.get("consume_piece", 0), "consume_piece")
        if len(player["tiles"]) < consume:
            raise ValueError("Not enough loot tiles to consume")
        pieces = action.get("pieces", player["tiles"][:consume])
        if not isinstance(pieces, list) or len(pieces) != consume or Counter(pieces) - Counter(player["tiles"]):
            raise ValueError("Choose the required held loot tiles")
        price = 0 if free else max(0, card.get("price", 0) - 5 * strength)
        self._pay(player, {"gold": price, "strength": strength})
        self._pay(player, card.get("costs", {}))
        for piece in pieces:
            player["tiles"].remove(piece)
        player["hand"].remove(card_id)
        # Tags on played cards remain in the tableau, so do not store twice.
        original_civ = self.state["civ"]
        player["played"].append(card_id)
        self._gain_tags(player, card.get("tags", []), store=False)
        effects = dict(card)
        effects.pop("costs", None)
        effects.pop("tags", None)
        self._effects(player, effects, action)
        for condition in card.get("conditional", []):
            if (condition.get("civ_min", 1) <= original_civ <= condition.get("civ_max", original_civ)
                    and self._requirements(player, condition.get("requirements", {}))):
                self._effects(player, condition.get("effect", {}), action)

    def can_explore(self, player_id, tile_id, allow_hole=False):
        """Read-only topology/availability helper; does not inspect hidden loot."""
        try:
            p, cell = self._player(player_id), self._cell(tile_id)
        except ValueError:
            return False
        border = max(abs(cell["q"]), abs(cell["r"]), abs(cell["q"] + cell["r"])) == 3
        adjacent = any(n["owner"] == player_id for n in self._neighbors(cell))
        hole = cell["revealed"] and TILES[cell["loot"]].get("ishole", False)
        return cell["owner"] is None and not hole and p["available"] > 0 and (border or adjacent)

    @_localized
    def explore_preview(self, player_id, tile_id, strength=0):
        p, cell = self._player(player_id), self._cell(tile_id)
        strength = _integer(strength, "strength")
        if strength > p["strength"]:
            raise ValueError("Not enough strength")
        neighbor_stars = sum(self._visible_stars(n) for n in self._neighbors(cell) if n["owner"] is None)
        stars = self._visible_stars(cell)
        uncertain = not cell["revealed"]
        possible = [tile.get("star", 0) for tile in TILES.values()]
        low = min(possible) if uncertain else stars
        high = max(possible) if uncertain else stars
        cost = lambda s: max(0, max(10, 5 * (s + neighbor_stars)) - 5 * strength)
        return {"eligible": self.can_explore(player_id, tile_id), "cost": cost(stars),
                "min_cost": cost(low), "max_cost": cost(high), "uncertain": uncertain,
                "stars": stars, "neighbor_stars": neighbor_stars, "strength": strength}

    def _visible_stars(self, cell):
        if cell["owner"] is not None:
            return 0
        if cell["revealed"]:
            return TILES[cell["loot"]].get("star", 0)
        return 3 if cell["q"] == cell["r"] == 0 else 1

    def _explore(self, player, action):
        cell = self._cell(action.get("tile"))
        strength = _integer(action.get("strength", 0), "strength")
        if not self.can_explore(player["id"], cell["id"]):
            raise ValueError("Explore the border or a cell next to your adventurer")
        if strength > player["strength"]:
            raise ValueError("Not enough strength")
        cell["revealed"] = True
        if TILES[cell["loot"]].get("ishole"):
            return "hole"
        cost = self.explore_preview(player["id"], cell["id"], strength)["cost"]
        if player["gold"] < cost:
            player["retreat"] += self.rules["retreat_penalty"]
            if cell["q"] == cell["r"] == 0:
                cell["revealed"] = False
            return "retreat"
        self._pay(player, {"gold": cost, "strength": strength})
        player["available"] -= 1
        cell["owner"] = player["id"]
        self._take_loot(player, cell["loot"], action)
        for neighbor in self._neighbors(cell):
            if neighbor["base"] and neighbor["owner"] is not None:
                self._player(neighbor["owner"])["pot"] += 1
                player["pot"] += 1
        return "explored"

    def _take_loot(self, player, loot_id, action=None):
        loot = TILES[loot_id]
        player["tiles"].append(loot_id)
        effects = dict(loot)
        effects.pop("tags", None)
        self._effects(player, effects, action)
        self._gain_tags(player, loot.get("tags", []), store=False)
        if self.state["phase"] != "final":
            self.state["miasma"] = max(0, self.state["miasma"] - loot.get("star", 0))
        if loot.get("treasure") and self.state["treasure_pool"]:
            choice = (action or {}).get("treasure", self.state["treasure_pool"][0])
            if choice not in self.state["treasure_pool"]:
                raise ValueError("Treasure is unavailable")
            self.state["treasure_pool"].remove(choice)
            player["treasures"].append(choice)
            self._effects(player, self.rules["treasures"][choice], action)

    @_localized
    def build_cost(self, player_id, tile_id):
        p, cell = self._player(player_id), self._cell(tile_id)
        if cell["owner"] != p["id"] or cell["base"]:
            raise ValueError("Build on your occupied cell without a base")
        return self.rules["build_cost"] + self.rules["adjacent_base_cost"] * sum(n["base"] for n in self._neighbors(cell))

    def _build(self, player, tile_id, free=False):
        cost = self.build_cost(player["id"], tile_id)
        self._pay(player, {"gold": cost - self.rules["build_cost"] if free else cost})
        self._cell(tile_id)["base"] = True

    def _develop(self, player, count, action, free=False):
        count = _integer(count, "count", 1)
        if player["affection"] + count > 5:
            raise ValueError("Affection cannot exceed five")
        slots = self.rules["development_slots"]
        selected = action.get("slots")
        if free and selected is None:
            raise ValueError("Choose an affection slot")
        if isinstance(selected, list):
            selected = ["territory" if slot == "tiles" else slot for slot in selected]
        if selected is None:
            selected = []
            budget = {key: player[key] for key in RESOURCE_KEYS}
            for key, definition in slots.items():
                if key in player["developed"]:
                    continue
                costs = definition.get("costs", {})
                if free or (self._requirements(player, definition.get("requirements", {}))
                            and all(budget[k] >= v for k, v in costs.items())):
                    selected.append(key)
                    if not free:
                        for k, v in costs.items():
                            budget[k] -= v
                if len(selected) == count:
                    break
        if not isinstance(selected, list) or len(selected) != count or any(not isinstance(key, str) for key in selected):
            raise ValueError("Select one available development slot per affection")
        if len(set(selected)) != count or any(key not in slots or key in player["developed"] for key in selected):
            raise ValueError("Development slots must be unused and distinct")
        costs = Counter()
        for key in selected:
            if not free and not self._requirements(player, slots[key].get("requirements", {})):
                raise ValueError("Development slot requirements are not met")
            if not free:
                costs.update(slots[key].get("costs", {}))
        self._pay(player, costs)
        # All development draws precede either rank upgrade (official Q&A).
        player["hand"].extend(self._draw(count))
        for key in selected:
            player["developed"].append(key)
            player["affection"] += 1
            player["available"] += 1
            passive = HEROES[player["hero"]].get("passive", {})
            player["strength"] += passive.get("on_affection_strength", 0)
            level = {2: 2, 5: 3}.get(player["affection"])
            if level:
                player["hero_level"] = level
                upgrade = HEROES[player["hero"]].get("upgrade%s" % level, {})
                choice_action = dict(action)
                choices = action.get("choices", {})
                if str(level) in choices:
                    choice_action["choice"] = choices[str(level)]
                self._effects(player, upgrade, choice_action)
                if upgrade.get("claim_hidden_star") is not None or upgrade.get("claim_hidden_tile"):
                    target = action.get("tile", action.get("target"))
                    options = [c for c in self.state["board"] if not c["revealed"] and c["owner"] is None
                               and not c["q"] == c["r"] == 0]
                    if options:
                        if target is None:
                            raise ValueError("Choose a concealed ordinary tile")
                        cell = self._cell(target)
                        if cell not in options:
                            raise ValueError("Choose a concealed ordinary tile")
                        self._take_loot(player, cell["loot"], action)
                        ordinary = [key for key, t in TILES.items() if not t.get("boss") and key != "boss" and t.get("image") != 18]
                        self._shuffle(ordinary)
                        cell["loot"] = ordinary[0]
                if "claim_achievement_discount" in upgrade or "achievement_discount" in upgrade:
                    target = action.get("achievement")
                    if target is not None:
                        claim = dict(target) if isinstance(target, dict) else {"id": target, "public": action.get("public", False)}
                        self._achievement(player, claim, discount=upgrade.get("claim_achievement_discount", upgrade.get("achievement_discount", 0)))

    def _potion(self, player, action):
        option = action.get("option")
        if not isinstance(option, str) or option not in POTIONS or option in self.state["potions_used"] or option in self.state["potions_disabled"]:
            raise ValueError("Potion slot is unavailable")
        potion = POTIONS[option]
        if option == "build" or potion.get("effect", {}).get("build"):
            # 与完整版 _potion 一致：营地不存在、或全部营地都支付不起邻接据点化追加费用时，
            # 直接拒绝且不扣秘药（2026-10-26 修复「秘药被扣却无效果」）。
            camps = [c for c in self.state["board"] if c.get("owner") == player["id"] and not c.get("base")]
            if not camps:
                raise ValueError("没有可以据点化的营地，秘药未消耗。")
            if action.get("target") is None and not any(self._affordable(player, {"gold": max(0, self.build_cost(player["id"], c["id"]) - self.rules["build_cost"])}) for c in camps):
                raise ValueError("据点化追加费用全部无法支付，秘药未消耗。")
        self._pay(player, {"pot": potion.get("cost", 0)})
        target = action.get("target")
        effect = potion.get("effect", {})
        if option == "build" or effect.get("build"):
            self._build(player, target, free=True)
        elif option == "free_card" or effect.get("free_card"):
            target_action = {key: deepcopy(value) for key, value in action.items()
                             if key not in ("type", "option", "target")}
            target_action.update(dict(target) if isinstance(target, dict) else {"card": target})
            self._play(player, target_action, free=True)
        self._effects(player, effect, action)
        self.state["potions_used"].append(option)

    def _achievement(self, player, action, discount=0):
        aid = action.get("id")
        public = action.get("public", False)
        if type(public) is not bool or not isinstance(aid, str) or aid not in ACHIEVEMENTS:
            raise ValueError("Unknown achievement")
        source = self.state["public_achievements"] if public else player["achievements"]
        if aid not in source:
            raise ValueError("Achievement is unavailable")
        card = ACHIEVEMENTS[aid]
        if not self._requirements(player, card.get("requirement", {})) or not self._requirements(player, card.get("requirements", {})):
            raise ValueError("Achievement requirements are not met")
        strength = _integer(action.get("strength", 0), "strength")
        if strength and not card.get("can_trans", False):
            raise ValueError("This card cannot use strength for its gold price")
        maximum = (max(0,card.get('price',0)-discount)+4)//5
        if strength > maximum:
            raise ValueError('力量折抵超过费用上限，本次最多使用%s点力量。' % maximum)
        self._pay(player, {"gold": max(0, card.get("price", 0) - discount - 5 * strength), "strength": strength})
        self._pay(player, card.get("costs", {}))
        source.remove(aid)
        player["earned_achievements"].append(aid)
        player["reputation"] += int(public)
        self._effects(player, card.get("effect", {}), action)

    def _next_turn(self, index, final=False):
        players = self.state["players"]
        for distance in range(1, len(players) + 1):
            candidate = (index + distance) % len(players)
            eligible = self.state["final_remaining"][candidate] > 0 if final else not players[candidate]["passed"]
            if eligible:
                self.state["turn"] = candidate
                return
        raise ValueError("No next player")

    def _season(self):
        season = self.state["season"]
        for p in self.state["players"]:
            for resource, production in (("gold", "gold_pro"), ("strength", "str_pro"), ("pot", "pot_pro")):
                p[resource] += p[production]
            if season == 0:
                p["strength"] += 1
            elif season == 1:
                p["pot"] += 1
            elif season == 2:
                p["gold"] += 5
            p["used"] = []
            p["passed"] = False
            p["researched"] = False
            p["offered"] = self._draw(4)
        self.state["potions_used"] = []
        self.state["round"] += 1
        self.state["season"] = (season + 1) % 4
        self.state["start_player"] = (self.state["start_player"] + 1) % len(self.state["players"])
        self.state["turn"] = self.state["start_player"]
        self.state["phase"] = "research"
        self._log("所有玩家完成生产，进入第%s轮情报收集。" % self.state["round"])

    def _begin_final(self, index, reason):
        self.state["phase"] = "final"
        self.state["final_reason"] = reason
        self.state["final_remaining"] = [2] * len(self.state["players"])
        for player in self.state["players"]:
            player["passed"] = False
            payout = min(20, player["gold_pro"])
            player["gold"] += payout
            player["gold_pro"] -= payout
        self._next_turn(index, final=True)
        self._log("文明与瘴气接近，进入终局：减少至多20金币产能并取得等量金币，每人最多两次行动。")

    def _points(self, player, item):
        points = item.get("point", 0)
        scoring = item.get("scoring", [])
        if isinstance(scoring, dict):
            scoring = [scoring]
        for rule in scoring:
            earned = self._stat(player, rule["stat"]) // max(1, rule.get("per", 1)) * rule.get("point", 1)
            points += min(earned, rule.get("max", earned))
        points += sum(self._tags(player)[tag] * value for tag, value in item.get("point_per_tag", {}).items())
        return points

    @_localized
    def score_breakdown(self, player_id):
        p = self._player(player_id)
        grid = sum(min(3, 4 - max(abs(c["q"]), abs(c["r"]), abs(c["q"] + c["r"]))) * (2 if c["base"] else 1)
                   for c in self.state["board"] if c["owner"] == player_id)
        hero = HEROES[p["hero"]]
        points = hero.get("points", 0) if p["hero_level"] >= 3 else 0
        return {"hero": points, "grid": grid,
                "loot": sum(self._points(p, TILES[key]) for key in p["tiles"]),
                "cards": sum(self._points(p, CARDS[key]) for key in p["played"]),
                "achievements": sum(self._points(p, ACHIEVEMENTS[key]) for key in p["earned_achievements"]),
                "reputation": p["reputation"], "treasures": sum(self.rules["treasures"][key]["point"] for key in p["treasures"]), "retreat": -p["retreat"]}

    def _finish(self):
        self.state["phase"] = "finished"
        rows = []
        for p in self.state["players"]:
            breakdown = self.score_breakdown(p["id"])
            rows.append({"id": p["id"], "name": p["name"], "score": sum(breakdown.values()),
                         "total": sum(breakdown.values()), "breakdown": breakdown,
                         "bases": self._bases(p),
                         "adventurers": sum(c["owner"] == p["id"] for c in self.state["board"]),
                         "cardpoints": breakdown["cards"], "card_count": len(p["played"])})
        key = lambda row: (row["score"], row["bases"], row["adventurers"], row["card_count"])
        rows.sort(key=key, reverse=True)
        previous = None
        for i, row in enumerate(rows):
            if previous is None or key(row) != previous:
                rank = i + 1
            row["rank"] = rank
            previous = key(row)
        self.state["scores"] = rows
        self.state["winners"] = [row["id"] for row in rows if row["rank"] == 1]
        self._log("对局结束，已结算最终分数与排名。")

    @_localized
    def view(self, player_id=None, reveal=False):
        """Detached snapshot.

        Spectators never receive any player's private cards while ``reveal`` is
        false. The durable replay recorder passes ``reveal=True`` so the
        read-only archive can show every seat's hand, board and developments.
        """
        if player_id is not None:
            self._player(player_id)
        view = {key: deepcopy(value) for key, value in self.state.items()
                if key not in ("rng", "deck", "discard", "achievement_deck", "achievement_discard", "_clock")}
        from guild_clock import snapshot
        view['clock'] = snapshot(self)
        from guild_undo import available
        can_undo = available(self, player_id)
        view['undo'] = dict(available=can_undo,
                            id=self._undo_checkpoint['id'] if can_undo else None)
        view["rules"] = deepcopy(self.rules)
        view["treasures_available"] = [dict(deepcopy(self.rules["treasures"][key]), id=key) for key in self.state["treasure_pool"]]
        for player in view["players"]:
            player["developed_slots"] = player["developed"][:]
            player["hand_count"] = len(player["hand"])
            player["offered_count"] = len(player["offered"])
            player["achievement_count"] = len(player["achievements"])
            player["score_breakdown"] = self.score_breakdown(player["id"])
            player["score"] = sum(player["score_breakdown"].values())
            player["tag_counts"] = dict(self._tags(player))
            if not reveal and player["id"] != player_id:
                for key in ("hand", "offered", "achievements"):
                    player.pop(key)
        if player_id is not None:
            seat = self._player(player_id)
            for slot in view.get("quests", []):
                if isinstance(slot, dict) and not slot.get("done"):
                    slot["ready"] = bool(self._quest_met(seat, int(slot.get("card", 0))))
            view["hints"] = self._hints(seat)
        for cell in view["board"]:
            cell["point"] = min(3, 4 - max(abs(cell["q"]), abs(cell["r"]), abs(cell["q"] + cell["r"])))
            if cell["revealed"]:
                tile = TILES[cell["loot"]]
                cell["star"] = tile.get("star", 0)
                cell["image"] = tile.get("image", 0)
                cell["name"] = tile.get("name", cell["loot"])
            else:
                cell.pop("loot")
                cell["image"] = 17 if cell["q"] == cell["r"] == 0 else 2
        return view

    def _hints(self, player):
        """Read-only reminder list: what this seat could still do right now."""
        hints = {}
        if player.get("passed") or self.state.get("phase") not in ("action", "final"):
            return hints
        claimable = []
        for aid in list(self.state["public_achievements"]) + list(player["achievements"]):
            card = ACHIEVEMENTS.get(aid)
            if not card:
                continue
            if not self._requirements(player, card.get("requirement", {})) or not self._requirements(player, card.get("requirements", {})):
                continue
            price = max(0, card.get("price", 0))
            spend_cap = (price + 4) // 5 if card.get("can_trans") else 0
            for spend in range(spend_cap + 1):
                costs = dict(card.get("costs", {}))
                if spend:
                    costs["strength"] = costs.get("strength", 0) + spend
                if self._affordable(player, dict(costs, gold=max(0, price - 5 * spend))):
                    claimable.append(aid)
                    break
        if claimable:
            hints["achievements"] = claimable
        slots = self.rules["development_slots"]
        developable = [key for key in slots if key not in player["developed"]
                       and self._requirements(player, slots[key].get("requirements", {}))
                       and self._affordable(player, slots[key].get("costs", {}))]
        if developable and player["affection"] < 5:
            hints["develop"] = developable
        ability = HEROES.get(player["hero"], {}).get("ability", {})
        if ability and "ability" not in player["used"] and player["hero_level"] <= ability.get("max_level", 3):
            hints["ability"] = True
        card_actions = [i for i, card, meta in self._active_cards(player)
                        if card.get("available", False) and card.get("action") and meta.get("used_round") != self.state["round"]
                        and self._requirements(player, card["action"].get("requirements", {}))
                        and len(self.state["players"]) >= card["action"].get("min_players", 1)]
        if card_actions:
            hints["card_actions"] = len(card_actions)
        acts = []
        options = self.rules["options"]
        if options.get("solo") and self.state.get("mercenary_supply") and self._affordable(player, {"gold": 15}):
            acts.append("hire")
        if options.get("monster_quests"):
            season = (self.state["season"] + 1) % 4
            supply = self.state.get("monster_supply", [])
            if season < len(supply) and supply[season] and self._affordable(player, {"strength": 2 if season < 2 else 3}):
                acts.append("monster_hunt")
        if options.get("scouts"):
            ways = ["gold"] + (["strength"] if len(self.state["players"]) >= 4 else [])
            if self._scout_targets(player) and any(kind not in self.state["scouts_used"] and self._affordable(player, {"gold": 3} if kind == "gold" else {"strength": 1}) for kind in ways):
                acts.append("scout")
        if options.get("forest"):
            used = self.state.setdefault("forest_used", [])
            if any(cell["revealed"] and cell["owner"] is None and not self._tile_locked(cell) and TILES[cell["loot"]].get("ishole")
                   and any(n["owner"] == player["id"] for n in self._neighbors(cell)) for cell in self.state["board"]):
                if ("strength" not in used and self._affordable(player, {"strength": 2})) or ("festival" not in used and player.get("festival_tokens", 0) >= 1):
                    acts.append("forest_purify")
        if options.get("dragon"):
            dragon = self.state.get("dragon", {})
            if dragon.get("active"):
                cell = self._cell(dragon["tile"])
                if any(n["owner"] == player["id"] for n in self._neighbors(cell)):
                    cost = 5 * (3 + sum(self._visible_stars(n) for n in self._neighbors(cell)))
                    if player["gold"] + 5 * player["strength"] >= cost:
                        acts.append("dragon_hunt")
        if acts:
            hints["expansions"] = acts
        potions = []
        for key, potion in POTIONS.items():
            if key in self.state["potions_disabled"] or key in self.state["potions_used"]:
                continue
            if key == "build" and not any(cell["owner"] == player["id"] and not cell["base"] for cell in self.state["board"]):
                continue
            if key == "free_card" and not any(self._card_filter(CARDS[card], {}) and self._requirements(player, CARDS[card].get("requirements", {}), True)
                                              and self._can_nested_play(player, card, {}) for card in set(player["hand"])):
                continue
            if player["pot"] + (len(player["tiles"]) if player["hero"] == "horn_black" else 0) < potion.get("cost", 0):
                continue
            potions.append(key)
        if potions:
            hints["potions"] = potions
        return hints

    def replay_catalog(self):
        """Compact, JSON-safe lookup tables for the read-only replay viewer.

        The archive page has no access to Ren'Py or the game content modules, so
        every id stored in a snapshot is paired with a display name, the score
        fields it prints and a portrait URL under the replay website.
        """
        numeric = ("gold", "strength", "pot", "gold_pro", "str_pro", "pot_pro", "civ", "point", "draw", "affection")
        cards = {}
        for key, card in CARDS.items():
            entry = {"name": card.get("name", str(key)), "price": card.get("price", 0),
                     "kind": card.get("kind", "event"), "tags": list(card.get("tags", [])),
                     "image": card.get("image", key)}
            entry.update({field: card[field] for field in numeric if card.get(field)})
            cards[str(key)] = entry
        tiles = {key: {"name": tile.get("name", key), "star": tile.get("star", 0),
                       "point": tile.get("point", 0), "image": tile.get("image", 0),
                       "art": "/assets/tiles/%s.png" % key}
                 for key, tile in TILES.items()}
        achievements = {key: {"name": item.get("name", key), "point": item.get("point", 0),
                              "image": item.get("image", 0)}
                        for key, item in ACHIEVEMENTS.items()}
        heroes = {}
        for key, hero in HEROES.items():
            image = hero.get("image", 0)
            heroes[key] = {"name": hero.get("name", key), "subtitle": hero.get("subtitle", ""),
                           "character": hero.get("character", key), "variant": hero.get("variant", "white"),
                           "points": hero.get("points", 0), "images": list(hero.get("images", [])),
                           "description": hero.get("description", ""),
                           "portrait": "/assets/portraits/%s.png" % key}
        return {"cards": cards, "tiles": tiles, "achievements": achievements, "heroes": heroes,
                "slots": {key: {"name": DEVELOPMENT_SLOT_LABELS.get(key, key)} for key in self.rules["development_slots"]},
                "treasures": {key: {"name": data.get("name", key), "point": data.get("point", 0)}
                              for key, data in self.rules["treasures"].items()},
                "tags": dict(TAG_NAMES)}

    def export(self):
        """Private save data; never send this to remote players or spectators."""
        return {"version": 1, "state": deepcopy(self.state), "rules": deepcopy(self.rules)}

    @classmethod
    @_localized
    def restore(cls, data):
        """Restore a trusted private save, including its deterministic RNG state."""
        try:
            if isinstance(data, str):
                data = json.loads(data)
            if not isinstance(data, dict) or data.get("version") != 1:
                raise ValueError("Unsupported save version")
            obj = cls.__new__(cls)
            obj.state = deepcopy(data["state"])
            obj.rules = deepcopy(DEFAULT_RULES)
            obj.rules.update(deepcopy(data.get("rules", {})))
            from guild_mode_variants import apply_mode_variants
            apply_mode_variants(obj.rules.get("options", {}))
            if obj.state["phase"] not in ("draft", "research", "action", "final", "finished"):
                raise ValueError("Invalid saved phase")
            if not 1 <= len(obj.state["players"]) <= 5:
                raise ValueError("Invalid saved game size")
            from guild_modes import board_layout
            cells, big = board_layout(obj.rules.get("options", {}), len(obj.state["players"]))
            if len(obj.state["board"]) != len(cells):
                raise ValueError("Invalid saved board")
            if not 0 <= obj.state["turn"] < len(obj.state["players"]):
                raise ValueError("Invalid saved turn")
            rng = random.Random()
            rng.setstate(_tuples(obj.state["rng"]))
            json.dumps(obj.state, allow_nan=False)
            obj.view()
            return obj
        except (KeyError, TypeError, IndexError, OverflowError, AttributeError) as exc:
            raise ValueError("Invalid saved game: %s" % exc) from None

    def bot_action(self, player_id):
        """Internal deterministic simulation policy, with no hidden-map lookahead.

        The caller explicitly requests each step; this never schedules a bot,
        replaces a human, mutates state, or exposes an AI player in the UI.
        """
        p = self._player(player_id)
        if self.state["phase"] == "finished":
            raise ValueError("The game is finished")
        if self.state['phase'] == 'draft' and not self.state.get('pending'):
            if p['draft_choice'] is not None:
                raise ValueError('请等待其他玩家完成轮抽。')
            return dict(type='draft_pick', draft_step=self.state['draft_step'], index=0)
        if self.state["phase"] == "research":
            if p["researched"]:
                raise ValueError("Player already researched")
            # Reserve enough cash to actually develop/explore after buying.
            budget = max(0, p["gold"] - 20)
            wanted = []
            ranked = sorted(p["offered"], key=lambda c: (
                CARDS[c].get("gold_pro", 0) * 4 + CARDS[c].get("civ", 0) * 5
                + CARDS[c].get("pot_pro", 0) * 3 + CARDS[c].get("gold", 0)
                - CARDS[c].get("price", 0) / 3), reverse=True)
            for card in ranked[:2]:
                if budget >= self.rules["research_cost"] and len(p["hand"]) + len(wanted) < 8:
                    wanted.append(card)
                    budget -= self.rules["research_cost"]
            return {"type": "research", "cards": wanted}
        if self.state["players"][self.state["turn"]]["id"] != player_id:
            raise ValueError("It is not this player's turn")
        candidates = []
        final = self.state["phase"] == "final"
        def offer(value, action):
            # Internal simulations choose explicitly using public information.
            action = dict(action)
            action["choice"] = 1 if len(HEROES[p["hero"]].get("upgrade3", {}).get("choices", [])) > 1 else 0
            action["choices"] = {"3": action["choice"]}
            if action["type"] in ("play", "potion"):
                cid = action.get("card", action.get("target") if action.get("option") == "free_card" else None)
                if type(cid) is int and cid in CARDS and CARDS[cid].get("affection") and p["affection"] < 5:
                    action["slots"] = [key for key in self.rules["development_slots"] if key not in p["developed"]][:CARDS[cid]["affection"]]
                    if action.get("option") == "free_card":
                        action["target"] = {"card": cid, "slots": action["slots"], "choice": action["choice"]}
            if p["affection"] == 4 and HEROES[p["hero"]].get("upgrade3", {}).get("claim_hidden_star"):
                targets = [c["id"] for c in self.state["board"] if not c["revealed"] and c["owner"] is None and c["id"] != "0,0"]
                if targets and action["type"] in ("develop", "play"):
                    action["tile"] = targets[0]
            candidates.append((value, len(candidates), action))
        for aid in p["achievements"]:
            offer(40 if final else 12, {"type": "achievement", "id": aid})
        for aid in self.state["public_achievements"]:
            offer(45 if final else 14, {"type": "achievement", "id": aid, "public": True})
        for cid in set(p["hand"]):
            card = CARDS[cid]
            value = 3 + card.get("gold_pro", 0) * (1 if final else 6) + card.get("pot_pro", 0) * 5
            value += card.get("civ", 0) * 9 + card.get("point", 0) * (6 if final else 1)
            value += card.get("gold", 0) / 2 + card.get("draw", 0) - card.get("price", 0) / 5
            spent = min(p["strength"], (card.get("price", 0) + 4) // 5) if card.get("can_trans") else 0
            offer(value, {"type": "play", "card": cid, "strength": spent})
            if p["pot"] >= 3:
                offer(value + card.get("price", 0) / 4, {"type": "potion", "option": "free_card", "target": cid})
        for cell in self.state["board"]:
            if self.can_explore(player_id, cell["id"]):
                initial = self.explore_preview(player_id, cell["id"])
                spent = min(p["strength"], max(0, initial["stars"] + initial["neighbor_stars"] - 2))
                preview = self.explore_preview(player_id, cell["id"], spent)
                if p["gold"] >= preview["max_cost"]:
                    star = preview["stars"]
                    offer(26 + star * 3 - preview["cost"] / 8, {"type": "explore", "tile": cell["id"], "strength": spent})
            if cell["owner"] == player_id and not cell["base"]:
                offer(25 if final else 5, {"type": "build", "tile": cell["id"]})
                offer(28 if final else 8, {"type": "potion", "option": "build", "target": cell["id"]})
        if p["affection"] < 5:
            offer(32 if p["available"] == 0 else 9, {"type": "develop"})
        offer(36 if p["available"] == 0 else 16, {"type": "potion", "option": "knowledge"})
        if p["gold"] < 25:
            offer(35, {"type": "potion", "option": "gold"})
        if p["strength"] < 3:
            offer(10, {"type": "potion", "option": "strength"})
            offer(8, {"type": "potion", "option": "power"})
        ability = HEROES[p["hero"]].get("ability", {})
        ability_action = {"type": "ability"}
        if ability.get("discard_min"):
            ability_action["cards"] = p["hand"][:ability["discard_min"]]
        offer(7, ability_action)
        for cid in set(p["played"]):
            offer(8, {"type": "card_action", "card": cid})
        # Trial validation never touches the real state or observes concealed
        # exploration outcomes: only conservatively affordable explores enter.
        for unused, order, action in sorted(candidates, key=lambda row: (-row[0], row[1])):
            trial = self.__class__.__new__(self.__class__)
            trial.state, trial.rules = deepcopy(self.state), deepcopy(self.rules)
            try:
                trial._apply(player_id, deepcopy(action))
                return action
            except (ValueError, KeyError, TypeError, IndexError):
                continue
        return {"type": "pass"}


from guild_full_rules import FullRules


from guild_variant_rules import VariantRules
from guild_hero_rules import HeroRules
from guild_screenshot_rules import ScreenshotRules


class Engine(ScreenshotRules, VariantRules, HeroRules, FullRules, CoreEngine):
    """Single authoritative engine, including ordered full-deck effects."""
