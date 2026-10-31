class_name GuildRenpyLogic
extends RefCounted

static func can_pay_gold(me: Dictionary, amount: int) -> bool:
	return int(me.get("gold", 0)) + (5 * int(me.get("strength", 0)) if me.get("strength_as_gold", false) else 0) >= amount

static func research_price(me: Dictionary, game: Dictionary, count: int) -> int:
	if int(game.get("round", 1)) == 1 and me.get("research_initial_free", false): return 0
	return max(0, count - int(me.get("research_free", 0))) * int(game.get("rules", {}).get("research_cost", 3))

static func strength_cap(card: Dictionary, me: Dictionary, free: bool = false, multiplier: int = 1, discount: int = 0) -> int:
	if free or not (card.get("can_trans", false) or me.get("strength_as_gold", false)): return 0
	return min(max(0, int(me.get("strength", 0)) - int(card.get("costs", {}).get("strength", 0)) * multiplier), ceili(float(max(0, int(card.get("price", 0)) * multiplier - discount)) / 5))

static func piece_cost(card: Dictionary, me: Dictionary, double: bool = false) -> int:
	var count = int(card.get("consume_piece", 0)) * (2 if double else 1)
	if me.get("hero") == "horn_black": return max(0, count - int(me.get("pot", 0))) if me.get("prefer_pot", false) else min(count, me.get("tiles", []).size())
	return count

static func develop_options(me: Dictionary, game: Dictionary, use_festival: bool = false) -> Array:
	var controlled = game.get("board", []).filter( func(cell): return cell.get("owner") != null and int(cell.owner) == int(me.id)).size()
	var n = int(me.get("festival_tokens", 0)) if use_festival else 0
	return [["gold", "公会投资", "支付 20 金币", can_pay_gold(me, max(0, 20 - n * 5))], ["strength", "冒险训练", "支付 3 战力", int(me.get("strength", 0)) + n >= 3], ["pot", "秘药馈赠", "支付 2 秘药", int(me.get("pot", 0)) + n + (me.get("tiles", []).size() if me.get("hero") == "horn_black" else 0) >= 2], ["territory", "拓展疆域", "控制至少 3 个地图格子", controlled >= 3], ["cards", "经营有方", "打出至少 8 张事件卡", me.get("played", []).size() >= 8]]

static func achievement_stat(me: Dictionary, game: Dictionary, catalog: Dictionary, stat: String) -> int:
	var tag_counts = me.get("tag_counts", {})
	if stat in ["tiles", "pieces"]:
		var total = me.get("tiles", []).size()
		for state in me.get("card_states", []):
			if not state.get("face_down", false): total += state.get("tiles", []).size()
		return total
	if stat == "holes":
		var holes = 0
		for key in me.get("tiles", []):
			if catalog.get("tiles", {}).get(key, {}).get("ishole", false): holes += 1
		for state in me.get("card_states", []):
			if state.get("face_down", false): continue
			for key in state.get("tiles", []):
				if catalog.get("tiles", {}).get(key, {}).get("ishole", false): holes += 1
		return holes
	if stat == "earned_achievements": return me.get("earned_achievements", []).size()
	if stat == "tags": return tag_counts.values().reduce(func(a, b): return a + int(b), 0)
	if stat in ["heart", "affection"]: return int(me.get("affection", 0))
	if stat == "civ": return int(game.get("civ", 0))
	if stat in ["bases", "controlled"]:
		var count = 0
		for cell in game.get("board", []):
			if cell.get("owner") == null or int(cell.owner) != int(me.get("id", -1)): continue
			if stat == "bases" and not cell.get("base", false): continue
			count += 1
		return count
	if stat in ["cards", "played"]: return me.get("played", []).size()
	if stat.begins_with("tag:"): return int(tag_counts.get(stat.substr(4), 0))
	if me.has(stat) and typeof(me[stat]) == TYPE_INT: return int(me[stat])
	return -1

static func achievement_requirements_met(me: Dictionary, game: Dictionary, catalog: Dictionary, requirement) -> bool:
	if not requirement is Dictionary or requirement.is_empty(): return true
	if requirement.has("any"):
		var found = false
		for option in requirement["any"]:
			if achievement_requirements_met(me, game, catalog, option): found = true;break
		if not found: return false
	if requirement.has("all"):
		for option in requirement["all"]:
			if not achievement_requirements_met(me, game, catalog, option): return false
	if requirement.has("stat") and achievement_stat(me, game, catalog, str(requirement["stat"])) < int(requirement.get("value", 0)): return false
	var tag_counts = me.get("tag_counts", {})
	for tag in requirement.get("tags", {}):
		if int(tag_counts.get(tag, 0)) < int(requirement["tags"][tag]): return false
	for key in ["heart", "affection", "pieces", "tiles", "civ", "bases", "cards", "played", "gold", "strength", "pot", "gold_pro", "str_pro", "pot_pro", "controlled"]:
		if requirement.has(key) and achievement_stat(me, game, catalog, key) < int(requirement[key]): return false
	return true

static func achievement_ready(me: Dictionary, game: Dictionary, catalog: Dictionary, data: Dictionary, strength_used: int = 0) -> bool:
	if me.is_empty(): return false
	if not achievement_requirements_met(me, game, catalog, data.get("requirement", {})): return false
	if not achievement_requirements_met(me, game, catalog, data.get("requirements", {})): return false
	var used = min(int(strength_used), strength_cap(data, me))
	var costs = data.get("costs", {})
	if int(me.get("gold", 0)) < max(0, int(data.get("price", 0)) - 5 * used) + int(costs.get("gold", 0)): return false
	if int(me.get("strength", 0)) < used + int(costs.get("strength", 0)): return false
	for key in costs:
		if key in ["gold", "strength"]: continue
		if int(me.get(key, 0)) < int(costs[key]): return false
	return true

static func festival_payment(me: Dictionary, slots: Array) -> Dictionary:
	var remaining = int(me.get("festival_tokens", 0)); var result = {}
	for key in slots:
		if key in ["gold", "strength", "pot"]:
			var count = min(remaining, {"gold": 4, "strength": 3, "pot": 2}[key]);remaining -= count
			if count > 0: result[key] = count
	return result

static func payment_limits(payment: Dictionary, selected: Array, strength: int, pot: int, flash: bool) -> Array:
	var sm = int(payment.get("strength_max", 0)); var pm = int(payment.get("pot_max", 0))
	if not payment.get("target", false): return [sm, pm, min(strength, sm), min(pot, pm)]
	var gold = int(payment.get("gold_flash" if flash else "gold_base", 0)); var tiles = selected.size() if payment.get("tiles_as_strength", false) else 0
	var remaining = max(0, ceili(float(gold) / 5) - tiles); var ratio = int(payment.get("potion_strength", 0))
	pot = min(pot, min(pm, ceili(float(remaining) / ratio) if ratio > 0 else 0));strength = min(strength, min(sm, max(0, remaining - pot * ratio)))
	return [min(sm, max(0, remaining - pot * ratio)), min(pm, ceili(float(max(0, remaining - strength)) / ratio) if ratio > 0 else 0), strength, pot]
