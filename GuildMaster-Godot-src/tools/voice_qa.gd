extends SceneTree

func _initialize(): call_deferred("run")

func run():
	var ui = load("res://main.tscn").instantiate();root.add_child(ui)
	await process_frame;await process_frame
	var result = load("res://scripts/voice_check.gd").new().run(ui)
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--qa-output="):
			var file = FileAccess.open(arg.trim_prefix("--qa-output="), FileAccess.WRITE)
			file.store_string(JSON.stringify(result, "  "));file.close()
	ui.stop_audio();ui.session.close();quit(0 if result.passed else 1)
