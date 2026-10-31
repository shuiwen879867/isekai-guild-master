extends SceneTree

var ui
var failures = []

func _initialize(): call_deferred("run")
func frames():
	for unused in range(5): await process_frame
func find_button(node, title):
	for child in node.get_children():
		if child is Button and child.text == title: return child
		var found = find_button(child, title)
		if found: return found
	return null
func check(value, message):
	print(("SETTINGS_PASS " if value else "SETTINGS_FAIL ") + message)
	if not value: failures.append(message)
func restart_ui():
	if is_instance_valid(ui): ui.queue_free();await frames()
	ui = load("res://main.tscn").instantiate();root.add_child(ui);await frames()
func run():
	await restart_ui()
	check(not ui.prefs.voices and ui.prefs.voice_language == "ja", "fresh install is muted and selects Japanese")
	ui.voice.play_event("bai_white", "intro");ui.voice.play_event("bai_white", "rank", 1)
	check(not ui.voice.player.playing and ui.voice.queued.is_empty(), "muted events neither play nor queue")
	ui.dialogs.settings();await frames()
	check(find_button(ui, "日语") != null and find_button(ui, "中文") != null, "both voice languages are available")
	find_button(ui, "配音开启").pressed.emit();await frames()
	ui.voice.play_event("bai_white", "intro")
	check(ui.voice.player.playing and ui.prefs.voices, "manual enabling plays Japanese")
	find_button(ui, "中文").pressed.emit();await frames()
	check(ui.prefs.voice_language == "zh_CN" and not ui.voice.player.playing and ui.voice.queued.is_empty(), "language change stops old speech and queue")
	ui.voice.play_event("bai_white", "intro")
	check(ui.voice.player.playing and ui.voice.clips_for_event("bai_white", "intro", 1, "zh_CN").has(ui.voice.last_clip), "Chinese uses the Chinese recording")
	find_button(ui, "配音关闭").pressed.emit();await frames()
	check(not ui.prefs.voices and not ui.voice.player.playing, "off immediately stops playback")
	await restart_ui()
	check(ui.prefs.voice_language == "zh_CN" and not ui.prefs.voices, "language and off survive restart")
	ui.dialogs.settings();await frames()
	find_button(ui, "日语").pressed.emit();await frames();find_button(ui, "配音开启").pressed.emit();await frames()
	await restart_ui()
	check(ui.prefs.voices and ui.prefs.voice_language == "ja", "manual enable survives restart after migration")
	ui.queue_free();await frames()
	var legacy = ConfigFile.new()
	legacy.set_value("preferences", "voices", true)
	legacy.set_value("preferences", "name", "MigrationKeepName")
	legacy.set_value("preferences", "sound_volume", 0.27)
	legacy.set_value("preferences", "voice_language", "zh_CN")
	legacy.save("user://preferences.cfg")
	ui = load("res://main.tscn").instantiate();root.add_child(ui);await frames()
	check(not ui.prefs.voices and ui.prefs.voice_settings_version == 1, "legacy enabled preference migrates once to muted")
	check(ui.prefs.name == "MigrationKeepName" and is_equal_approx(ui.prefs.sound_volume, 0.27) and ui.prefs.voice_language == "zh_CN", "migration preserves unrelated preferences and chosen language")
	await restart_ui()
	check(not ui.prefs.voices, "migration is persisted to disk")
	ui.stop_audio();ui.session.close();print("SETTINGS_RESULT " + ("PASSED" if failures.is_empty() else "FAILED"))
	quit(0 if failures.is_empty() else 1)
