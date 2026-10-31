class_name GuildRoomSetup
extends RefCounted

static func character_pool(catalog: Dictionary, banned: Array = []) -> Array:
	var pool = []
	for key in catalog.get("characters", {}):
		if banned.has(key): continue
		var variants = catalog.characters[key].get("variants", {})
		if variants.values().any( func(hero): return catalog.heroes.get(hero, {}).get("available", false)): pool.append(key)
	return pool

static func candidate_limit(catalog: Dictionary, players: int, banned: Array = []) -> int:
	return mini(5, character_pool(catalog, banned).size() / maxi(1, players))

static func options(catalog: Dictionary, requested: Dictionary, players: int, banned: Array = []) -> Dictionary:
	var result = catalog.get("defaults", {}).duplicate(true)
	result.merge(requested, true)

	for key in ["base_seconds", "reserve_seconds", "disconnect_seconds"]: result[key] = int(result[key])
	if str(result.get("start_player", "auto")) != "auto": result.start_player = int(result.start_player)
	for key in ["initial_civ", "initial_miasma"]:
		if result.get(key) != null: result[key] = int(result[key])
	var limit = candidate_limit(catalog, players, banned)
	if limit > 0: result.hero_draw = clampi(int(result.get("hero_draw", 2)), 1, limit)
	return result
