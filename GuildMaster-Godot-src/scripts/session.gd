class_name GuildSession
extends Node

signal changed
signal notice(message: String)
signal connected

const MAX_FRAME = 262144
var peer = StreamPeerTCP.new()
var websocket: WebSocketPeer
var websocket_mode = false
var fallback_attempted = false
var incoming = PackedByteArray()
var outgoing = PackedByteArray()
var hello = {}
var active = false
var greeted = false
var handshake_complete = false
var directory = false
var directory_received = false
var local_mode = false
var room = {}
var game = {}
var rooms = []
var player_id = -1
var role = "browser"
var resume_token = ""
var room_id = ""
var password = ""
var address = ""
var port = 6677
var nickname = "公会长"
var child_pid = -1
var endpoint = ""
var waiting_local = false
var connect_stamp = 0
var reconnect_room = {}
var synchronized = false
var room_connected = false
var rules_catalog = {}

static func normalize(value):

	if value is float and is_finite(value) and value == floor(value) and abs(value) < 9.007199e+15: return int(value)
	if value is Array:
		for i in range(value.size()): value[i] = normalize(value[i])
	elif value is Dictionary:
		for key in value: value[key] = normalize(value[key])
	return value

func _process(_delta):
	if waiting_local:
		if FileAccess.file_exists(endpoint):
			var record = JSON.parse_string(FileAccess.get_file_as_string(endpoint))
			if record is Dictionary and record.has("port"):
				waiting_local = false
				_open("127.0.0.1", int(record.port), {"type": "local_hello", "token": record.token})
		elif Time.get_ticks_msec() - connect_stamp > 12000:
			waiting_local = false
			notice.emit("离线模式启动失败，请检查完整客户端运行库。")
	if not active: return
	if websocket_mode:
		_poll_websocket();return
	peer.poll()
	var status = peer.get_status()
	if status == StreamPeerTCP.STATUS_CONNECTED:
		if not greeted:
			greeted = true
			send(hello)
			if local_mode: send({"type": "local_lobby", "name": nickname, "options": {}})
		var available = peer.get_available_bytes()
		if available > 0:
			var result = peer.get_data(min(available, MAX_FRAME + 4))
			if result[0] != OK:
				_transport_failed("连接读取失败。");return
			incoming.append_array(result[1])
			_decode()
			if not active: return
		if not outgoing.is_empty():
			var sent = peer.put_partial_data(outgoing)
			if sent[0] != OK:
				_transport_failed("连接发送失败。");return
			outgoing = outgoing.slice(int(sent[1]))
		if not handshake_complete and Time.get_ticks_msec() - connect_stamp > 3000 and _try_fallback(): return
		if not handshake_complete and Time.get_ticks_msec() - connect_stamp > 15000:
			_transport_failed("公会同步超时，请稍后重新连接。")
	elif status == StreamPeerTCP.STATUS_ERROR or (greeted and status == StreamPeerTCP.STATUS_NONE):
		_transport_failed("与服务器的连接已断开，可重新连接恢复席位。")
	elif Time.get_ticks_msec() - connect_stamp > 3000 and _try_fallback(): return
	elif Time.get_ticks_msec() - connect_stamp > 15000:
		_transport_failed("连接超时，请检查服务器地址和端口。")

func _disconnect_transport():
	peer.disconnect_from_host()
	if websocket != null: websocket.close();websocket = null
	websocket_mode = false

func _try_fallback() -> bool:
	if local_mode or handshake_complete or fallback_attempted or port != 6677 or address.to_lower() not in ["guanpeng666.cn", "154.36.164.109"]: return false
	fallback_attempted = true
	_open_websocket(address, 6680)
	notice.emit("正在重试连接…")
	return true

func _transport_failed(message: String):
	if not _try_fallback(): _fail(message)

func _open_websocket(host: String, site_port: int):
	_disconnect_transport();incoming.clear();outgoing.clear()
	websocket_mode = true;greeted = false;handshake_complete = false;active = true;connect_stamp = Time.get_ticks_msec()
	synchronized = false;room_connected = false;directory_received = false
	websocket = WebSocketPeer.new()
	websocket.inbound_buffer_size = 4 * (MAX_FRAME + 4)
	websocket.outbound_buffer_size = 4 * (MAX_FRAME + 4)
	websocket.max_queued_packets = 128
	var error = websocket.connect_to_url("ws://%s:%s/game/socket" % [host, site_port])
	if error != OK: _fail("无法连接：" + error_string(error))

func connect_websocket(host: String, site_port: int, name_text: String):
	close();address = host;nickname = name_text;local_mode = false;fallback_attempted = true
	hello = {"type": "hello", "name": nickname, "client_version": "4.1.0", "protocol": 3}
	_open_websocket(host, site_port)

func _poll_websocket():
	websocket.poll()
	var state = websocket.get_ready_state()
	if state == WebSocketPeer.STATE_OPEN:
		if not greeted: greeted = true;send(hello)
		while websocket.get_available_packet_count() > 0:
			var data = websocket.get_packet()
			if websocket.get_packet_error() != OK or websocket.was_string_packet() or incoming.size() + data.size() > 4 * (MAX_FRAME + 4):
				_fail("连接读取失败。");return
			incoming.append_array(data);_decode()
			if not active: return
		if not outgoing.is_empty():
			var count = min(outgoing.size(), MAX_FRAME + 4)
			var error = websocket.send(outgoing.slice(0, count), WebSocketPeer.WRITE_MODE_BINARY)
			if error == OK: outgoing = outgoing.slice(count)
			elif error != ERR_BUSY: _fail("连接发送失败。");return
	elif state == WebSocketPeer.STATE_CLOSED:
		_fail("与服务器的连接已断开，可重新连接恢复席位。");return
	if not handshake_complete and Time.get_ticks_msec() - connect_stamp > 15000:
		_fail("公会同步超时，请稍后重新连接。")

func transport_connected() -> bool:
	return websocket.get_ready_state() == WebSocketPeer.STATE_OPEN if websocket_mode and websocket != null else peer.get_status() == StreamPeerTCP.STATUS_CONNECTED

func _open(host: String, number: int, handshake: Dictionary):
	_disconnect_transport();peer = StreamPeerTCP.new();incoming.clear();outgoing.clear();fallback_attempted = false
	hello = handshake;greeted = false;handshake_complete = false;active = true;connect_stamp = Time.get_ticks_msec()
	synchronized = false;room_connected = false;directory_received = false
	var error = peer.connect_to_host(host, number)
	if error != OK: _transport_failed("无法连接：" + error_string(error))

func connect_server(host: String, number: int, name_text: String):
	close()
	address = host.strip_edges();port = number;nickname = name_text.strip_edges();local_mode = false
	if nickname.is_empty() or address.is_empty() or port < 1 or port > 65535:
		notice.emit("请输入昵称、服务器地址及有效端口。");return
	_open(address, port, {"type": "hello", "name": nickname, "client_version": "4.1.0", "protocol": 3})

func start_local(name_text: String):
	close();nickname = name_text;local_mode = true
	var root = ProjectSettings.globalize_path("res://") if OS.has_feature("editor") else OS.get_executable_path().get_base_dir()
	var python = root.path_join("runtime/pythonw.exe")
	if not FileAccess.file_exists(python):
		notice.emit("缺少离线运行库，请使用完整客户端包。");return
	endpoint = ProjectSettings.globalize_path("user://local-" + str(Time.get_ticks_usec()) + ".json")
	child_pid = OS.create_process(python, [root.path_join("rules/local_bridge.py"), "--endpoint", endpoint], false)
	if child_pid < 0:
		notice.emit("无法启动离线规则模块。");return
	waiting_local = true;connect_stamp = Time.get_ticks_msec()

func send(message: Dictionary):
	if not active: return
	var kind = message.get("type", "")
	if kind in ["create_room", "set_options", "start"]:
		if rules_catalog.is_empty(): rules_catalog = JSON.parse_string(FileAccess.get_file_as_string("res://data/catalog.json"))
		var players = int(message.get("max_players", 4)) if kind == "create_room" else int(room.get("max_players", 1))
		var banned = message.get("banned_characters", []) if kind == "create_room" else room.get("banned_characters", [])
		var requested = message.get("options", {}) if kind != "start" else room.get("options", {})
		if not banned is Array or not requested is Dictionary:
			notice.emit("房间选项或禁用角色格式不正确。");return
		var limit = GuildRoomSetup.candidate_limit(rules_catalog, players, banned)
		if limit < 1:
			notice.emit("可用角色不足以分配给所有玩家，请减少禁用角色或房间人数。");return
		var adjusted = GuildRoomSetup.options(rules_catalog, requested, players, banned)
		var count = int(requested.get("hero_draw", rules_catalog.defaults.get("hero_draw", 2)))
		if int(adjusted.hero_draw) != count: notice.emit("可用角色不足，候选张数已自动调整为 %s 张。" % int(adjusted.hero_draw))
		if kind == "start":
			if int(adjusted.hero_draw) != count:
				send({"type": "set_options", "options": adjusted})
				notice.emit("候选张数已更新，请所有玩家重新准备后开始。");return
		else:
			message = message.duplicate(true);message.options = adjusted
	var data = JSON.stringify(message).to_utf8_buffer()
	if data.is_empty() or data.size() > MAX_FRAME:
		notice.emit("请求超过协议允许的大小。");return
	var frame = PackedByteArray();frame.resize(4)
	for i in range(4): frame[i] = (data.size() >> ((3 - i) * 8)) & 255
	frame.append_array(data);outgoing.append_array(frame)

func action(kind: String, args: Dictionary = {}):
	if role == "spectator": notice.emit("观战者只能查看公开信息。");return
	var command = args.duplicate(true);command["type"] = kind
	send({"type": "action", "action": command})

func leave_room():
	if local_mode or (room.is_empty() and game.is_empty()):
		close()
	elif not active or not transport_connected():

		close()
		reconnect()
	else:
		send({"type": "leave_room"})
	changed.emit()

func _decode():
	while incoming.size() >= 4:
		var length = 0
		for i in range(4): length = (length << 8) | incoming[i]
		if length < 1 or length > MAX_FRAME:
			_fail("服务器消息长度无效。");return
		if incoming.size() < length + 4: return
		var parser = JSON.new()
		var error = parser.parse(incoming.slice(4, length + 4).get_string_from_utf8())
		incoming = incoming.slice(length + 4)
		if error != OK or not parser.data is Dictionary:
			_fail("服务器消息格式无效。");return
		_receive(normalize(parser.data))

func _receive(message: Dictionary):
	match message.get("type", ""):
		"server_welcome":
			if not handshake_complete: handshake_complete = true;connected.emit()
			directory = true
			if not reconnect_room.is_empty(): send(reconnect_room);reconnect_room = {}
		"directory": rooms = message.get("rooms", []);directory_received = true
		"welcome":
			if local_mode and not handshake_complete: handshake_complete = true;connected.emit()
			room_connected = true
			player_id = int(message.get("player_id", -1)) if message.get("player_id") != null else -1
			role = message.get("role", "player");resume_token = message.get("resume_token", "");room_id = message.get("room_id", "")
		"snapshot":
			synchronized = true
			room = message.get("room") if message.get("room") is Dictionary else {}
			game = message.get("game") if message.get("game") is Dictionary else {}
			if local_mode and not game.is_empty() and game.get("view_player") != null:
				player_id = int(game.view_player)
		"left_room": room = {};game = {};player_id = -1;role = "browser";room_id = "";resume_token = "";room_connected = false;directory = true
		"error":
			if not handshake_complete: _fail(message.get("message", "服务器拒绝连接。"));return
			notice.emit(message.get("message", ""))
		"notice", "chat": notice.emit(message.get("message", ""))
	changed.emit()

func me() -> Dictionary:
	for player in game.get("players", []):
		if int(player.id) == player_id: return player
	return {}

func can_act() -> bool:
	if game.is_empty() or role == "spectator" or game.get("pending") != null or room.get("paused", false) or not active or not synchronized or not room_connected: return false
	var phase = game.get("phase", "")
	var players = game.get("players", [])
	return phase in ["action", "final"] and not players.is_empty() and int(players[int(game.turn)].id) == player_id

func can_choose() -> bool:
	var pending = game.get("pending")
	return pending is Dictionary and int(pending.player) == player_id and active and synchronized and room_connected and not room.get("paused", false)

func can_free_action() -> bool:
	return not game.is_empty() and game.get("phase", "") not in ["finished", "draft"] and role == "player" and active and synchronized and room_connected

func reconnect():
	if local_mode: return
	var restore = {"type": "enter_room", "room_id": room_id, "password": password, "role": role, "resume_token": resume_token}
	_disconnect_transport();active = false
	_open(address, port, {"type": "hello", "name": nickname, "client_version": "4.1.0", "protocol": 3})
	if not room_id.is_empty(): reconnect_room = restore

func _fail(message: String):
	active = false;_disconnect_transport();notice.emit(message);changed.emit()

func close():
	active = false;waiting_local = false;_disconnect_transport()
	handshake_complete = false
	directory_received = false
	synchronized = false;room_connected = false
	if child_pid > 0 and OS.is_process_running(child_pid): OS.kill(child_pid)
	child_pid = -1;room = {};game = {};rooms = [];role = "browser";player_id = -1;directory = false
	resume_token = "";room_id = "";reconnect_room = {}

func _exit_tree(): close()
