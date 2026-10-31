extends RefCounted

var checks = 0
var failures = []

func check(value: bool, message: String):
	checks += 1
	if value: print("VOICE_PASS " + message)
	else:
		failures.append(message);push_error("VOICE_FAIL " + message)

func playing(voice, hero: String, event: String, rank: int = 1) -> bool:
	return voice.player.playing and voice.player.stream != null and voice.player.stream.resource_path.trim_prefix("res://") in voice.clips_for_event(hero, event, rank)

func run(ui) -> Dictionary:
	var voice = ui.voice
	var session = ui.session
	var saved_game = session.game.duplicate(true)
	var saved_room = session.room.duplicate(true)
	var saved_role = session.role
	var saved_local = session.local_mode
	var saved_id = session.player_id
	var saved_prefs = ui.prefs.duplicate(true)
	ui.prefs.voices = true;ui.prefs.voice_volume = 0.0;voice.apply_settings()
	check(voice.catalog.get("heroes", {}).size() == ui.store.catalog.heroes.size(), "voice manifest covers every playable print")
	check(voice.catalog.get("characters", {}).size() == 25, "all 25 named characters have voices")
	for path in voice.catalog.get("clips", {}):
		var stream = load("res://" + path)
		check(stream is AudioStreamOggVorbis and stream.get_length() > 0.5, "decodable exported clip " + path)
	var cases = []
	for hero_key in ui.store.catalog.heroes:
		for locale in ["ja", "zh_CN"]: cases.append([hero_key, locale])
	for entry in cases:
		var hero = str(entry[0]);ui.prefs.voice_language = entry[1];voice.apply_settings()
		for event in ["intro", "select", "close-first", "close-last", "close-shop", "settle-win", "settle-lose"]:
			voice.stop();voice.play_event(hero, event)
			check(playing(voice, hero, event), hero + " plays " + event)
		for rank in range(1, 4):
			voice.stop();voice.play_event(hero, "rank", rank)
			check(playing(voice, hero, "rank", rank), "%s plays level %s" % [hero, rank])
		session.local_mode = true;session.role = "player";session.player_id = 0;session.room = {}
		session.game = {"phase": "action", "players": [{"id": 0, "hero": hero, "hero_level": 1, "passed": false}, {"id": 1, "hero": "bai_white", "hero_level": 1, "passed": false}, {"id": 2, "hero": "bai_red", "hero_level": 1, "passed": false}], "options": {"solo": false}, "action_count": 0, "last_action": {}, "winners": []}
		voice.stop();voice.last_scope = "";voice.last_hero = "";voice.last_phase = "";voice.sync()
		var includes_first = voice.catalog.get("clips", {}).get(voice.last_clip, {}).get("includes_rank_one", false)
		check(playing(voice, hero, "select") and (voice.queued.is_empty() if includes_first else voice.queued.size() == 1), hero + " selection respects included level-one dialogue")
		if includes_first: check(voice.queued.is_empty(), hero + " supplied selection avoids duplicate level-one dialogue")
		else:
			voice.player.stop();voice.player.finished.emit()
			check(playing(voice, hero, "rank", 1), hero + " queued level-one cue plays")
		var before = voice.serial;voice.sync()
		check(voice.serial == before, hero + " rerender does not repeat selection")
		for rank in [2, 3]:
			voice.stop();session.game.players[0].hero_level = rank;voice.sync()
			check(playing(voice, hero, "rank", rank), "%s level-up triggers rank %s" % [hero, rank])
		for count in [1, 2, 3]:
			voice.stop();voice.last_passed = false
			for index in range(3): session.game.players[index].passed = index < count
			session.game.action_count += 1;session.game.last_action = {"type": "pass", "player": 0};voice.sync()
			var event = "close-first" if count == 1 else "close-last" if count == 3 else "close-shop"
			check(playing(voice, hero, event), hero + " pass triggers " + event)
		for solo in [false, true]:
			for won in [false, true]:
				voice.stop();voice.last_phase = "action";session.game.phase = "finished";session.game.options.solo = solo
				session.game.winners = [0] if won else [1];session.game.solo_result = "win" if won else "lose";voice.sync()
				check(playing(voice, hero, "settle-win" if won else "settle-lose"), "%s triggers %s result %s" % [hero, "solo" if solo else "multiplayer", won])
	voice.stop();voice.play_event("bai_white", "select");voice.play_event("bai_white", "rank", 1)
	ui.prefs.voices = false;voice.apply_settings()
	check(not voice.player.playing and voice.queued.is_empty() and AudioServer.is_bus_mute(AudioServer.get_bus_index("Voice")), "disable stops audio and cancels queued speech immediately")
	var muted_serial = voice.serial;voice.play_event("marta_white", "intro")
	check(voice.serial == muted_serial, "disabled speech cannot restart")
	ui.prefs.voices = true;ui.prefs.voice_language = "ja";voice.apply_settings()
	voice.play_event("bai_white", "select");voice.play_event("bai_white", "rank", 1)
	ui.prefs.voice_language = "zh_CN";voice.apply_settings()
	check(not voice.player.playing and voice.queued.is_empty(), "language switch cancels both current and queued speech")
	voice.play_event("bai_white", "intro")
	check(playing(voice, "bai_white", "intro") and "/ja/" not in voice.player.stream.resource_path, "Chinese selection plays Chinese assets")
	ui.prefs.voice_language = "ja";voice.apply_settings();voice.play_event("bai_white", "intro")
	check(playing(voice, "bai_white", "intro") and "/ja/" in voice.player.stream.resource_path, "Japanese selection plays Japanese assets")
	ui.prefs.voices = true;ui.prefs.voice_volume = 0.35;voice.apply_settings()
	check(not AudioServer.is_bus_mute(AudioServer.get_bus_index("Voice")) and absf(db_to_linear(AudioServer.get_bus_volume_db(AudioServer.get_bus_index("Voice"))) - 0.35) < 0.001, "voice volume applies to the independent bus")
	voice.play_event("marta_white", "intro");session.role = "spectator";voice.sync()
	check(not voice.player.playing, "spectator does not impersonate a player voice")
	session.role = "player";session.local_mode = true;session.player_id = 1;session.game.phase = "action";voice.last_scope = "local:0";voice.sync()
	check(playing(voice, "bai_white", "select"), "guest seat handoff switches to the new player's voice")
	voice.stop();session.player_id = 0;session.game.phase = "action";session.game.players[0].hero = "marta_revised_black";session.game.players[0].hero_level = 3
	voice.last_scope = "local:0";voice.last_hero = "marta_revised_white";voice.last_level = 2;voice.last_phase = "action";voice.sync()
	check(playing(voice, "marta_revised_white", "rank", 3), "Marta's upgrade flip narrates the white level-three ability")
	voice.stop();voice.last_hero = "marta_revised_white";voice.last_phase = "action";session.game.phase = "finished";session.game.options.solo = false;session.game.winners = [0];voice.sync()
	check(playing(voice, "marta_revised_black", "settle-win"), "ending on a print change prioritizes the result cue")
	voice.stop();session.game = saved_game;session.room = saved_room;session.role = saved_role;session.local_mode = saved_local;session.player_id = saved_id
	ui.prefs = saved_prefs;voice.apply_settings();voice.last_scope = "";voice.last_hero = "";voice.last_phase = "";voice.last_level = 0;voice.last_passed = false;voice.last_action = -1
	var result = {"passed": failures.is_empty(), "checks": checks, "failures": failures, "clips": voice.catalog.get("clips", {}).size(), "hero_versions": voice.catalog.get("heroes", {}).size(), "languages": ["ja", "zh_CN"], "manifest_sha256": FileAccess.get_sha256(GuildVoice.MANIFEST)}
	print("VOICE_RESULT " + JSON.stringify(result))
	return result
