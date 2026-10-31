extends RefCounted

var ui
var failures = []

func check(value: bool, description: String):
	print(("CONNECTION_PASS " if value else "CONNECTION_FAIL ") + description)
	if not value: failures.append(description)

func wait_for(predicate: Callable, seconds: float = 25):
	var deadline = Time.get_ticks_msec() + int(seconds * 1000)
	while not predicate.call() and Time.get_ticks_msec() < deadline: await ui.get_tree().process_frame
	return predicate.call()

func run(client):
	ui = client
	var host = "guanpeng666.cn"
	var port = 6677
	var web_port = 0
	var output = ""
	var force_fallback = OS.get_cmdline_user_args().has("--qa-force-fallback")
	for argument in OS.get_cmdline_user_args():
		if argument.begins_with("--qa-host="): host = argument.trim_prefix("--qa-host=")
		if argument.begins_with("--qa-port="): port = int(argument.trim_prefix("--qa-port="))
		if argument.begins_with("--qa-websocket-port="): web_port = int(argument.trim_prefix("--qa-websocket-port="))
		if argument.begins_with("--qa-output="): output = argument.trim_prefix("--qa-output=")
	if web_port > 0: ui.session.connect_websocket(host, web_port, "ExportConnectionCheck")
	else: ui.session.connect_server(host, port, "ExportConnectionCheck")
	if force_fallback and web_port == 0:
		# Reproduce an unavailable/unacknowledged TCP connection before polling.
		ui.session.peer.disconnect_from_host();ui.session.connect_stamp = Time.get_ticks_msec() - 3500
	check(await wait_for(func(): return ui.session.handshake_complete and ui.session.directory_received), "server welcome and actual room directory received")
	var transport = "websocket" if ui.session.websocket_mode else "tcp"
	if force_fallback: check(ui.session.fallback_attempted and transport == "websocket", "unacknowledged TCP automatically switches transport")
	if failures.is_empty():
		ui.session.send({"type": "create_room", "room_name": "ConnectionCheck", "max_players": 2})
		check(await wait_for(func(): return ui.session.room_connected and ui.session.synchronized), "server creates room and synchronizes its snapshot")
		if failures.is_empty():
			# An unstarted room is intentionally deleted when its last player leaves.
			# Keep a second authenticated player present while testing reconnect.
			var keeper = GuildSession.new();ui.add_child(keeper)
			if transport == "websocket": keeper.connect_websocket(host, web_port if web_port > 0 else 6680, "ConnectionKeeper")
			else: keeper.connect_server(host, port, "ConnectionKeeper")
			check(await wait_for(func(): return keeper.handshake_complete and keeper.directory_received), "second client receives lobby directory")
			keeper.send({"type": "enter_room", "room_id": ui.session.room_id, "role": "player"})
			check(await wait_for(func(): return keeper.room_connected and keeper.synchronized), "second client joins test room")
			var room_id = ui.session.room_id
			var player_id = ui.session.player_id
			# Public/default connections must also restore seats after fallback.
			if web_port == 0:
				ui.session.reconnect()
				if force_fallback: ui.session.peer.disconnect_from_host();ui.session.connect_stamp = Time.get_ticks_msec() - 3500
				check(await wait_for(func(): return ui.session.handshake_complete and ui.session.room_connected and ui.session.synchronized), "reconnect restores the authenticated room")
				check(ui.session.room_id == room_id and ui.session.player_id == player_id, "reconnect preserves the same seat")
			ui.session.leave_room()
			check(await wait_for(func(): return ui.session.room.is_empty() and not ui.session.room_connected), "leaving returns to the directory")
			keeper.leave_room();await wait_for(func(): return keeper.room.is_empty());keeper.close();keeper.queue_free()
	var result = {"passed": failures.is_empty(), "host": host, "port": port, "transport": transport, "failures": failures}
	if not output.is_empty():
		DirAccess.make_dir_recursive_absolute(output)
		var file = FileAccess.open(output.path_join("connection-results.json"), FileAccess.WRITE)
		if file: file.store_string(JSON.stringify(result, "  "));file.close()
		else: check(false, "connection report can be saved")
	print("CONNECTION_RESULT " + JSON.stringify(result))
	ui.session.close();ui.get_tree().quit(0 if failures.is_empty() else 1)
