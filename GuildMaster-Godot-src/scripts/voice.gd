class_name GuildVoice
extends Node

# Supplied by the user: kanban-010 is Shion / 紫苑, not character index 10.
const PREFIX = "res://audio/voice/kanban-010/kanban-010__"
var ui
var player: AudioStreamPlayer
var last_hero = ""
var last_level = 0
var last_passed = false
var last_phase = ""
var last_scope = ""
var last_action = -1
var serial = 0
var queued = []

func setup(owner_ui):
	ui = owner_ui
	if AudioServer.get_bus_index("Voice") < 0:
		AudioServer.add_bus();AudioServer.set_bus_name(AudioServer.bus_count - 1, "Voice")
	player = AudioStreamPlayer.new();player.bus = "Voice";add_child(player);apply_settings()
	player.finished.connect(func():
		if not queued.is_empty():
			var next = queued.pop_front();play_event(next[0], next[1], next[2]))

func apply_settings():
	var bus = AudioServer.get_bus_index("Voice")
	AudioServer.set_bus_mute(bus, not bool(ui.prefs.get("voices", true)))
	AudioServer.set_bus_volume_db(bus, linear_to_db(maxf(0.0001, float(ui.prefs.get("voice_volume", 0.85)))))
	if not ui.prefs.get("voices", true): stop()

func play_event(hero: String, event: String, rank: int = 1):
	if not hero.begins_with("shion_") or not ui.prefs.get("voices", true): return
	var red = hero.ends_with("red") or hero.ends_with("black")
	var variant = "red" if red else "white"
	var clip = ""
	match event:
		"intro": clip = "select-intro-v%s" % randi_range(1, 2)
		"select": clip = "select-%s-v%s" % [variant, randi_range(1, 2)]
		"rank": clip = "card-%s-r%s" % [variant, clampi(rank, 1, 3)]
		"close-first", "close-last", "close-shop", "settle-win", "settle-lose": clip = "%s-v%s" % [event, randi_range(1, 2)]
	if clip.is_empty() or not ResourceLoader.exists(PREFIX + clip + ".ogg"): return
	if event == "rank" and player.playing:
		queued.append([hero, event, rank]);return
	serial += 1;player.stream = load(PREFIX + clip + ".ogg");player.play()

func sync():
	var session = ui.session
	var hero = ""
	var level = 1
	var passed = false
	var phase = str(session.game.get("phase", ""))
	var action_count = int(session.game.get("action_count", -1))
	var action = session.game.get("last_action", {})
	if not action is Dictionary: action = {}
	var scope = ("local" if session.local_mode else session.room_id) + ":" + str(session.player_id)
	var me = session.me()
	if not me.is_empty():
		hero = str(me.get("hero", ""));level = int(me.get("hero_level", 1));passed = bool(me.get("passed", false))
	else:
		for seat in session.room.get("players", []):
			if int(seat.id) == session.player_id and seat.get("hero_chosen", false): hero = str(seat.get("hero", ""))
	if hero.is_empty():
		last_hero = "";last_level = 0;last_phase = "";last_scope = scope;last_passed = false;last_action = -1;stop();return
	if scope != last_scope:
		last_hero = hero;last_level = level;last_passed = passed;last_phase = phase;last_action = int(session.game.get("action_count", -1))
	elif hero != last_hero:
		play_event(hero, "select")
		if not phase.is_empty(): play_event(hero, "rank", level)
	elif phase == "finished" and last_phase != "finished":
		var won = session.game.get("solo_result", "") == "win" if session.game.get("options", {}).get("solo", false) else session.game.get("winners", []).has(session.player_id)
		play_event(hero, "settle-win" if won else "settle-lose")
	elif level > last_level: play_event(hero, "rank", level)
	elif (passed and not last_passed) or (action_count != last_action and action.get("type") == "pass" and int(action.get("player", -1)) == session.player_id):
		var count = session.game.players.filter(func(p): return p.get("passed", false)).size()
		if not passed: count = session.game.players.size()
		play_event(hero, "close-first" if count == 1 else "close-last" if count == session.game.players.size() else "close-shop")
	last_scope = scope;last_hero = hero;last_level = level;last_passed = passed;last_phase = phase;last_action = action_count

func stop():
	queued.clear()
	if is_instance_valid(player): player.stop();player.stream = null
