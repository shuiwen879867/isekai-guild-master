class_name GuildVoice
extends Node

# Supplied by the user: kanban-010 is Shion / 紫苑, not character index 10.
const PREFIX = "res://audio/voice/kanban-010/kanban-010__"
const MANIFEST = "res://data/voice_manifest.json"
var catalog = {}
var last_language = ""
var last_clip = ""
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
	var parsed = JSON.parse_string(FileAccess.get_file_as_string(MANIFEST))
	if parsed is Dictionary: catalog = parsed
	if AudioServer.get_bus_index("Voice") < 0:
		AudioServer.add_bus();AudioServer.set_bus_name(AudioServer.bus_count - 1, "Voice")
	player = AudioStreamPlayer.new();player.bus = "Voice";add_child(player);apply_settings()
	player.finished.connect(func():
		if not queued.is_empty():
			var next = queued.pop_front();play_event(next[0], next[1], next[2]))

func apply_settings():
	var language = str(ui.prefs.get("voice_language", "ja"))
	if language != last_language:
		stop();last_language = language
	var bus = AudioServer.get_bus_index("Voice")
	AudioServer.set_bus_mute(bus, not bool(ui.prefs.get("voices", false)))
	AudioServer.set_bus_volume_db(bus, linear_to_db(maxf(0.0001, float(ui.prefs.get("voice_volume", 0.85)))))
	if not ui.prefs.get("voices", false): stop()

func clips_for_event(hero: String, event: String, rank: int = 1, language: String = "") -> Array:
	var key = "rank_%s" % clampi(rank, 1, 3) if event == "rank" else event
	var locale = str(ui.prefs.get("voice_language", "ja")) if language.is_empty() else language
	if locale not in catalog.get("locales", []): locale = "ja"
	return catalog.get("heroes", {}).get(hero, {}).get("events", {}).get(locale, {}).get(key, [])

func play_event(hero: String, event: String, rank: int = 1):
	if not ui.prefs.get("voices", false): return
	var clips = clips_for_event(hero, event, rank)
	if clips.is_empty(): return
	if event == "rank" and player.playing:
		queued.append([hero, event, rank]);return
	var path = "res://" + str(clips.pick_random())
	if not ResourceLoader.exists(path): return
	if event != "rank": queued.clear()
	last_clip = path.trim_prefix("res://")
	serial += 1;player.stream = load(path);player.play()

func play_selection(hero: String, level: int, started: bool):
	stop();play_event(hero, "select")
	var includes_first = catalog.get("clips", {}).get(last_clip, {}).get("includes_rank_one", false)
	if started and (level != 1 or not includes_first): play_event(hero, "rank", level)

func sync():
	var session = ui.session
	if session.role == "spectator":
		stop();last_hero = "";last_scope = "";return
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
		stop()
		if phase != "finished":
			play_selection(hero, level, not phase.is_empty())
	elif phase == "finished" and last_phase != "finished":
		var won = session.game.get("solo_result", "") == "win" if session.game.get("options", {}).get("solo", false) else session.game.get("winners", []).has(session.player_id)
		play_event(hero, "settle-win" if won else "settle-lose")
	elif hero != last_hero and level > last_level and catalog.get("heroes", {}).get(hero, {}).get("character", "") == catalog.get("heroes", {}).get(last_hero, {}).get("character", "missing"):
		# Marta's level-three effect flips the print. Narrate the ability that
		# caused the flip rather than pretending a new character was selected.
		stop();play_event(last_hero, "rank", level)
	elif hero != last_hero:
		play_selection(hero, level, not phase.is_empty())
	elif not phase.is_empty() and last_phase.is_empty(): play_event(hero, "rank", level)
	elif level > last_level: play_event(hero, "rank", level)
	elif (passed and not last_passed) or (action_count != last_action and action.get("type") == "pass" and int(action.get("player", -1)) == session.player_id):
		var count = session.game.players.filter(func(p): return p.get("passed", false)).size()
		if not passed: count = session.game.players.size()
		play_event(hero, "close-first" if count == 1 else "close-last" if count == session.game.players.size() else "close-shop")
	last_scope = scope;last_hero = hero;last_level = level;last_passed = passed;last_phase = phase;last_action = action_count

func stop():
	queued.clear()
	last_clip = ""
	if is_instance_valid(player): player.stop();player.stream = null
