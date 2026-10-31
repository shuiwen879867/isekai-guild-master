extends SceneTree
var ui
var output = ""
var failures = []

func _initialize(): call_deferred("run")
func frames(count = 4):
	for i in range(count): await process_frame
func check(value, message):
	print(("PASS " if value else "FAIL ") + message)
	if not value: failures.append(message)
func capture(name):
	await frames(5);await RenderingServer.frame_post_draw
	root.get_texture().get_image().save_png(output.path_join(name + ".png"))
func run():
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--qa-output="): output = arg.trim_prefix("--qa-output=")
	ui = load("res://main.tscn").instantiate();root.add_child(ui);await frames()
	check(ui.prefs.language == "zh_CN", "clean install defaults to simplified Chinese")
	check(ui.prefs.voice_language == "ja", "clean install defaults to Japanese voice")
	check(not ui.prefs.voices, "clean install defaults to muted voices")
	check(GuildLang.t("異世界公會長") == "异世界公会长", "simplified UI converts traditional source strings")
	check(ui.voice != null and AudioServer.get_bus_index("Voice") >= 0, "independent voice bus")
	var count = 0
	for variant in ["white", "red"]:
		for rank in range(1, 4):
			check(ResourceLoader.exists(GuildVoice.PREFIX + "card-%s-r%s.ogg" % [variant, rank]), "voice rank clip %s %s" % [variant, rank]);count += 1
	ui.prefs.voices = true;ui.voice.apply_settings()
	ui.voice.play_event("shion_white", "intro");check(ui.voice.player.playing, "Shion sample starts playback when enabled")
	ui.prefs.voices = false;ui.voice.apply_settings();check(not ui.voice.player.playing, "voice switch immediately stops playback")
	ui.prefs.voices = true;ui.voice.apply_settings()
	for hero in ui.store.catalog.heroes.values():
		if hero.get("screenshot_print", false):
			for face in hero.source: check(ui.store.texture(face) != null, "new character face " + face)
	for seats in [2, 5]:
		var fixture = GuildSession.normalize(JSON.parse_string(FileAccess.get_file_as_string("res://data/qa-%s.json" % seats)))
		ui.session.set_process(false);ui.session.game = fixture.game;ui.session.room = fixture.room
		ui.session.player_id = 0;ui.session.role = "player";ui.session.active = true;ui.session.local_mode = false;ui.session.synchronized = true;ui.session.room_connected = true
		for layout in ["classic", "dashboard"]:
			ui.prefs.layout = layout;ui.close_dialog(false);ui._render();await frames(7)
			check(ui.content.find_child("DashboardMap" if layout == "dashboard" else "MapPanel", true, false) != null, "%s layout with %s players" % [layout, seats])
			await capture("%s-%s" % [layout, seats])
	ui.dialogs.settings();await capture("settings")
	ui.close_dialog(false);ui.session.game = {};ui.session.room = {};ui.session.directory = false;ui._render();await capture("home")
	ui.stop_audio();ui.session.close();print("UPDATE_QA " + ("PASSED" if failures.is_empty() else "FAILED"))
	quit(0 if failures.is_empty() else 1)
