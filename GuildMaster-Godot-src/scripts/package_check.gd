class_name GuildPackageCheck
extends RefCounted


var ui
var failed = false
var output = ""

func check(value: bool, message: String):
	if not value: failed = true;push_error("PACKAGE_FAIL " + message)
	else: print("PACKAGE_PASS " + message)

func frames(count: int = 4):
	for i in range(count): await ui.get_tree().process_frame

func wait_for(predicate: Callable, seconds: float = 8):
	var deadline = Time.get_ticks_msec() + int(seconds * 1000)
	while not predicate.call() and Time.get_ticks_msec() < deadline: await ui.get_tree().process_frame
	return predicate.call()

func capture(name: String):
	if output.is_empty(): return
	await frames(); await RenderingServer.frame_post_draw
	ui.get_viewport().get_texture().get_image().save_png(output.path_join(name + ".png"))

func find_button(node: Node, text: String):
	for child in node.get_children():
		if child is Button and child.text == text: return child
		var found = find_button(child, text)
		if found: return found
	return null

func verify_network(port: int):
	ui.session.connect_server("127.0.0.1", port, "PackagedLobbyQA");ui.close_dialog()
	check( await wait_for( func(): return ui.session.directory and find_button(ui.content, "创建公会房间") != null), "exported client displays an empty lobby after delayed handshake")
	check(ui.session.rooms.is_empty(), "exported lobby handles zero rooms")
	await capture("empty-lobby")
	ui.session.send({"type": "create_room", "room_name": "PackagedLobbyQA", "max_players": 1})
	check( await wait_for( func(): return not ui.session.room.is_empty()), "exported online client creates a server room")
	ui.session.leave_room()
	check( await wait_for( func(): return ui.session.room.is_empty() and find_button(ui.content, "创建公会房间") != null), "exported client returns to empty lobby after leaving")
	var host = GuildSession.new();ui.add_child(host)
	host.connect_server("127.0.0.1", port, "SpectatorCleanupHost")
	if await wait_for( func(): return host.directory):
		host.send({"type": "create_room", "room_name": "SpectatorCleanup", "max_players": 1, "options": {"disconnect_seconds": 1, "hero_draw": 1, "setup_draft": false}})
		if await wait_for( func(): return not host.room.is_empty()):
			host.send({"type": "ready", "ready": true})
			await wait_for( func(): return host.room.players[0].ready)
			host.send({"type": "start"})
			if await wait_for( func(): return host.room.get("drafting", false)):
				var character = host.room.hero_offers[0]; var variants = ui.store.catalog.characters[character].variants
				var variant = "white" if variants.has("white") and variants.white != "marta_white" else "black"
				host.send({"type": "set_hero", "character": character, "variant": variant})
	check( await wait_for( func(): return not host.game.is_empty()), "original server starts spectator cleanup test game")
	if not host.game.is_empty():
		ui.session.send({"type": "enter_room", "room_id": host.room_id, "role": "spectator"})
		check( await wait_for( func(): return not ui.session.game.is_empty() and ui.session.role == "spectator"), "exported client enters live game as spectator")
		host.close()
		check( await wait_for( func(): return ui.session.game.is_empty() and ui.session.room.is_empty() and ui.session.directory and find_button(ui.content, "创建公会房间") != null), "last player disconnect destroys room after grace and returns spectator to lobby")
		check(ui.session.active, "spectator stays connected to server after room destruction")
	host.close();host.queue_free()
	ui.session.close();ui.rerender(); await frames()
	ui.session.connect_server("127.0.0.1", port, "SilentHandshake");ui.close_dialog()
	if await wait_for( func(): return ui.session.greeted):
		ui.session.connect_stamp = Time.get_ticks_msec() - 16000
	check( await wait_for( func(): return not ui.session.active), "exported client ends unacknowledged handshake with timeout")
	check("同步超时" in ui.toast_label.text, "exported timeout explains failed server synchronization")
	ui.session.close();ui.rerender(); await frames()

func run(client):
	ui = client
	var qa_port = 0
	for argument in OS.get_cmdline_user_args():
		if argument.begins_with("--qa-output="): output = argument.trim_prefix("--qa-output=")
		if argument.begins_with("--qa-server-port="): qa_port = int(argument.trim_prefix("--qa-server-port="))
	var original_preferences = ui.prefs.duplicate(true)
	check(not ui.prefs.voices and ui.prefs.voice_language == "ja", "fresh exported client starts muted with Japanese selected")
	var portrait_count = 0
	for key in ui.store.catalog.heroes:
		var source = ui.store.portrait_source(key)
		check(ui.store.portrait(key) != null and ui.store.portrait_bust(key) != null, "portrait and bust load for every print: " + key)
		if source.begins_with("images/tts/") or source.begins_with("images/standalone/"): portrait_count += 1
	check(portrait_count == 31, "31 prints use verified standalone artwork")
	var voice_result = load("res://scripts/voice_check.gd").new().run(ui)
	check(voice_result.passed, "all character voices decode and trigger in the exported client")
	if not output.is_empty():
		var voice_report = FileAccess.open(output.path_join("voice-results.json"), FileAccess.WRITE)
		voice_report.store_string(JSON.stringify(voice_result, "  "));voice_report.close()
	ui.prefs.voices = true;ui.voice.apply_settings()
	var clips = []
	for variant in ["white", "red"]:
		for rank in range(1, 4): clips.append("card-%s-r%s" % [variant, rank])
	for event in ["select-intro", "select-red", "select-white", "close-first", "close-last", "close-shop", "settle-win", "settle-lose"]:
		for version in range(1, 3): clips.append("%s-v%s" % [event, version])
	for clip in clips:
		var stream = load(GuildVoice.PREFIX + clip + ".ogg")
		check(stream is AudioStreamOggVorbis and stream.get_length() > 0, "exported voice decodes: " + clip)
	ui.voice.play_event("shion_white", "intro");check(ui.voice.player.playing, "exported Shion voice plays")
	ui.prefs.voices = false;ui.voice.apply_settings();check(not ui.voice.player.playing, "exported voice toggle stops audio")
	ui.prefs.voices = original_preferences.voices;ui.voice.apply_settings()
	check(ui.store.catalog.heroes.size() == 57, "all 57 character prints exported")
	for hero in ui.store.catalog.heroes.values():
		if hero.get("screenshot_print", false):
			for face in hero.source: check(ui.store.texture(face) != null, "exported screenshot texture: " + face)
	ui.prefs.language = "zh_CN";ui.apply_language(false);ui.rerender()
	await frames()
	check(ui.store.layouts.size() == 43, "43 original-coordinate layouts load from exported PCK")
	var card = ui.store.card(1)
	var tile_layouts = ui.store.layouts.values().filter( func(spec): return spec.kind == "tile")
	check(tile_layouts.size() == 43 and ui.store.texture(tile_layouts[0].paper) != null, "43 tile composite layouts load from exported PCK")
	check(ui.store.layouts.values().filter( func(spec): return spec.get("render_mode") == "native_font_text").is_empty(), "real-time native font card text is retired; card faces are scans")
	for back_source in ["images/piece_png/2.png", "images/piece_png/17.png", "images/tts/083.webp", "images/tts/087.webp", "images/tts/088.webp"]:
		check(ui.store.tile_texture(back_source) != null, "maze back tile composible from layout: " + back_source)
	var baked_icons = load("res://scripts/hex_map.gd").new();baked_icons.store = ui.store
	check(baked_icons.icon("star") != null and baked_icons.icon("dot_dark") != null and baked_icons.icon("dot_light") != null, "hex map bakes anti-aliased star and score dot icons")
	baked_icons.free()
	check(ui.store.texture(ui.store.catalog.heroes.hainie_red.source[0]) != null, "original character illustration loads")
	check( not ui.prefs.has("music") and not ResourceLoader.exists("res://audio/maoudamashii-acoustic01.ogg"), "background music excluded from exported PCK")
	check(Engine.max_fps == int(ui.prefs.frame_limit), "exported frame limit applies at startup")
	var icon = load(ProjectSettings.get_setting("application/config/icon"))
	check(icon is Texture2D and icon.get_size() == Vector2(512, 512), "original heroine window icon exported")
	ui.dialogs.settings(); await frames()
	check(ui.dialog.find_child("FrameLimit", true, false).get_item_id(3) == 240 and ui.dialog.find_child("VSync", true, false) != null, "240 FPS and vertical sync controls exported")
	ui.close_dialog(false);ui.dialogs.create_room(); await frames()
	var candidates = ui.dialog.find_child("CreateHeroDraw", true, false)
	check(candidates is OptionButton and candidates.item_count == 5, "candidate count dropdown exported")
	check(ui.dialog.find_child("initial_civValue", true, false) != null and ui.dialog.find_child("initial_miasmaValue", true, false) != null, "custom initial civilization and miasma controls exported")
	ui.close_dialog(false)
	check(ResourceLoader.exists("res://ui/backdrop.gdshader"), "animated backdrop shader exported")
	await capture("home")
	ui.hover_source = card.source;ui.last_hover_source = card.source;ui._update_preview(); await frames()
	check( not ui.preview_panel.visible, "exported hover does not open picture")
	# Windows does not reliably accept synthetic modifier-key state for a
	# hidden window. Supply the held state to test the actual preview renderer;
	# normal gameplay continues polling the physical Alt key in _process.
	ui.alt_zoom = true;ui._update_preview()
	check(ui.preview_panel.visible and ui.preview_art.custom_minimum_size.y > 500, "held Alt preview opens exported card")
	ui.alt_zoom = false;ui._update_preview()
	check(not ui.preview_panel.visible, "Alt release hides preview")
	ui.hover_source = "";ui.last_hover_source = "";ui._update_preview()
	if qa_port > 0: await verify_network(qa_port)
	ui.session.start_local("PackageQA")
	check( await wait_for( func(): return not ui.session.room.is_empty()), "bundled portable Python connects inside exported client")
	await capture("room")
	if not ui.session.room.is_empty():
		ui.session.send({"type": "set_guests", "count": 2})
		check( await wait_for( func(): return int(ui.session.room.get("max_players", 1)) == 3), "offline guest mode adds seats")
		ui.dialogs.player_names(); await frames()
		check(ui.dialog.find_child("PlayerName2", true, false) is LineEdit, "guest rename dialog exposes host and every guest")
		await capture("guest-names");ui.close_dialog(false)
		ui.session.send({"type": "rename_players", "names": {"0": "HostQA", "1": "GuestQA1", "2": "GuestQA2"}})
		check( await wait_for( func(): return str(ui.session.room.players[2].name) == "GuestQA2"), "every guest keeps an individual nickname")
		ui.session.send({"type": "set_guests", "count": 0})
		check( await wait_for( func(): return int(ui.session.room.get("max_players", 1)) == 1), "offline room returns to single seat")
		ui.session.send({"type": "set_options", "options": {"guild_board": true}})
		await frames()
		ui.session.send({"type": "start"})
		check( await wait_for( func(): return ui.session.room.get("drafting", false)), "offline room provides original hero offers")
		if ui.session.room.get("drafting", false):
			var character = ui.session.room.hero_offers[0]; var variants = ui.store.catalog.characters[character].variants
			var variant = "white" if variants.has("white") and variants.get("white") != "marta_white" else "black"
			ui.session.send({"type": "set_hero", "character": character, "variant": variant})
			check( await wait_for( func(): return not ui.session.game.is_empty()), "exported client starts original offline rules")
			if not ui.session.game.is_empty():
				ui.session.action("research", {"cards": []})
				check( await wait_for( func(): return ui.session.game.get("phase") == "action", 20), "offline research enters action phase")
				await frames()
				# —— 单人/多人变体卡面：solo 会话须解析出 9B 单人印，multi 须解析出多人印 ——
				check(ui.store.mode == "solo", "exported offline session switches card faces to the solo print")
				var variant_faces = {"53": "pack/9B_2", "65": "pack/9B_3", "77": "pack/9B_4", "83": "pack/9B_1"}
				for cid in variant_faces:
					var face = ui.store.card_face(ui.store.card(int(cid)))
					check(face == variant_faces[cid], "solo print face for card %s (got %s)" % [cid, face])
					check(ui.store.texture(face) != null, "solo variant texture loads for card " + cid)
				ui.dialogs.card_detail(53); await frames(); await capture("variant-solo-card53")
				ui.close_dialog(false)
				ui.store.mode = "multi";ui.dirty = true;ui.dialogs.card_detail(53); await frames()
				await capture("variant-multi-card53")
				ui.store.mode = "solo";ui.dirty = true;ui.close_dialog(false); await frames()
				check(ui.find_child("CivilizationProgress", true, false) != null, "civilization progress bar appears in exported client")
				check(ui.find_child("Seat0", true, false).size.y == 164, "exported single-player seat removes bottom whitespace")
				check(ui.find_child("ExpandHand", true, false) != null, "hand expand button stays visible with fewer than ten cards")
				ui.dialogs.player_names(); await frames()
				check(ui.dialog.find_child("PlayerName0", true, false) is LineEdit, "guest rename dialog exposes every seat nickname")
				await capture("player-names");ui.close_dialog(false)
				ui.session.send({"type": "rename_players", "names": {"0": "PackageQA-Renamed"}})
				check( await wait_for( func(): return str(ui.session.game.players[0].name) == "PackageQA-Renamed"), "offline guest rename updates the running game")
				ui.dialogs.save_picker(); await frames()
				check(ui.dialog.find_child("SaveName", true, false) is LineEdit, "save dialog asks for a custom name")
				await capture("save-picker");ui.close_dialog(false)
				ui.dialogs.quests(); await frames()
				var quest_grid = ui.dialog.find_child("QuestBoardGrid", true, false)
				check(quest_grid != null and quest_grid.get_child_count() == 9, "quest board renders as a 3x3 grid")
				await capture("quest-board");ui.close_dialog(false)
				ui.dialogs.potions(); await frames()
				check(ui.dialog.find_child("UsePotion_gold", true, false) is Button, "potion options render as whole rounded buttons")
				await capture("potions");ui.close_dialog(false)
				var treasure_frame = ui.dialogs.overlay("宝箱选项", Vector2(1080, 360), "qa-treasure")
				var treasure_row = HBoxContainer.new();treasure_row.position = Vector2(32, 110);treasure_frame.add_child(treasure_row)
				var sample = {}
				for item in ui.session.game.get("treasures_available", []): sample = item;break
				if not sample.is_empty():
					var opt = {"value": sample.id, "label": sample.get("name", "宝物奖励"), "description": sample.get("description", "")}
					treasure_row.add_child(ui.dialogs.treasure_choice(opt, false, func(): pass))
					treasure_row.add_child(ui.dialogs.treasure_choice(opt, true, func(): pass))
					var normal_box = treasure_row.get_child(0).get_theme_stylebox("normal")
					check(normal_box is StyleBoxFlat, "treasure options use rounded rectangles instead of button artwork")
				await capture("treasure-options");ui.close_dialog(false)
				ui.dialogs.seat_change(0); await frames()
				check(find_button(ui.dialog, "确认换人 · 继续") != null, "seat change announcement can be confirmed")
				await capture("seat-change");ui.close_dialog(false)
				ui.dialogs.card_detail(1); await frames()
				var detail_title = ui.dialog.find_child("CardDetailTitle", true, false)
				check(detail_title != null and detail_title.position.x > 600, "card detail title sits on the right column")
				await capture("card-detail");ui.close_dialog(false)
				ui.dialogs.quest_report({"serial": 9001, "round": 1, "items": [{"player": "P1", "quest": "商业2＋生活2", "reward": "金币+3"}]})
				check(ui.dialog != null and not ui.dialog.is_queued_for_deletion(), "quest settlement announcement renders")
				await capture("quest-report");ui.close_dialog(false)
				var fake_pending = {"id": 99001, "player": 0, "title": "选择加入手牌", "options": [
					{"value": 0, "card": 1, "label": "选项一", "image": "images/new_art/847200.webp"},
					{"value": 1, "card": 2, "label": "选项二", "image": "images/new_art/847201.webp"}], "min": 1, "max": 1, "payment": {}}
				ui.dialogs.pending(fake_pending); await frames()
				var choice_art = ui.dialog.find_child("ChoiceCard0", true, false)
				check(choice_art != null and str(choice_art.source) == str(ui.store.card(1).source), "pending card options fall back to catalog faces")
				await capture("pending-cards");ui.close_dialog(false)
				check(ui.find_child("ActionReminders", true, false) != null, "action reminder area renders above affection")
				var turn_border = ui.find_child("TurnBorder", true, false)
				check(turn_border != null and turn_border.get_theme_stylebox("panel").border_color == Color("ffd23f"), "acting seat border is bright yellow")
				ui.dialogs.hand([1, 2, 3, 4, 5, 6, 7, 8], "手牌放大预览"); await frames()
				var hand_grid = ui.dialog.find_child("HandGrid", true, false)
				check(hand_grid != null and hand_grid.columns == 4 and hand_grid.get_child_count() == 8, "hand dialog shows four enlarged cards per row")
				await capture("hand-zoom");ui.close_dialog(false)
				check(ResourceLoader.exists("res://ui/symbols/flag.svg") and ResourceLoader.exists("res://ui/symbols/knowledge.svg"), "new flag and knowledge icons exported")
				await capture("table")
				var targets = ui.session.game.board.filter( func(cell): return cell.get("eligible_for", []).has(0))
				check( not targets.is_empty(), "authoritative map targets available")
				if not targets.is_empty():
					var tried = []
					for attempt in range(24):
						targets = ui.session.game.board.filter( func(cell): return cell.get("eligible_for", []).has(0) and not tried.has(cell.id))
						if targets.is_empty(): break
						var target_id = targets[0].id
						var action_count = int(ui.session.game.get("action_count", 0))
						tried.append(target_id)
						ui.session.action("explore", {"tile": target_id})
						var received = await wait_for( func(): return ui.session.game.get("pending") is Dictionary or int(ui.session.game.get("action_count", 0)) > action_count, 16)
						if ui.session.game.get("pending") is Dictionary: break
						var revealed = ui.session.game.board.filter( func(cell): return cell.id == target_id)
						check(received and revealed.size() == 1 and ui.store.catalog.tiles.get(str(revealed[0].loot), {}).get("ishole", false), "exported deep-hole exploration follows original no-payment branch")
						if not received: break
					check(ui.session.game.get("pending") is Dictionary, "exported exploration receives original payment choice")
					if ui.session.game.get("pending") is Dictionary:
						var pending = ui.session.game.pending; await capture("payment")
						ui.session.action("choice", {"choice_id": int(pending.id), "selected": [], "action": {"strength": 0, "pot": 0, "flash": false, "lab": false}})
						check( await wait_for( func(): return ui.session.game.get("pending") == null or int(ui.session.game.pending.id) != int(pending.id), 16), "exported payment resolves in original rules")
	ui.session.leave_room();ui.close_dialog(); await frames()
	check(ui.session.room.is_empty() and ui.session.game.is_empty() and not ui.session.active and ui.session.child_pid == -1, "exported offline leave returns home and stops worker")
	# 大深度迷宫：验证新的区域色环与底部白色星形（一般迷宫配色见 table.png）。
	ui.session.start_local("PackageQA-Deep")
	check( await wait_for( func(): return not ui.session.room.is_empty(), 20), "deep map local session starts")
	if not ui.session.room.is_empty():
		ui.session.send({"type": "set_options", "options": {"map_type": "deep", "guild_board": true, "variable_tiles": true}})
		await frames()
		ui.session.send({"type": "start"})
		check( await wait_for( func(): return ui.session.room.get("drafting", false), 20), "deep map room drafts")
		if ui.session.room.get("drafting", false):
			var character = ui.session.room.hero_offers[0]; var variants = ui.store.catalog.characters[character].variants
			var variant = "white" if variants.has("white") and variants.white != "marta_white" else "black"
			ui.session.send({"type": "set_hero", "character": character, "variant": variant})
			check( await wait_for( func(): return not ui.session.game.is_empty(), 20), "deep map game starts")
			if not ui.session.game.is_empty():
				ui.session.action("research", {"cards": []})
				check( await wait_for( func(): return ui.session.game.get("phase") == "action", 20), "deep map research enters action phase")
				await frames()
				var deep_map = ui.find_child("TableMap", true, false)
				check(deep_map != null and str(ui.session.game.get("rules", {}).get("options", {}).get("map_type", "")) == "deep", "deep map renders the deep board")
				var known_backs = ["images/piece_png/2.png", "images/piece_png/17.png", "images/tts/083.webp", "images/tts/087.webp", "images/tts/088.webp"]
				var down_cells = ui.session.game.get("board", []).filter( func(cell): return cell.get("owner") == null and not cell.get("revealed", false) and not cell.get("blocked", false))
				check( not down_cells.is_empty() and down_cells.all( func(cell): return known_backs.has(str(cell.get("back_source", "")))), "every unrevealed cell carries a real back source")
				var variable_backs = down_cells.filter( func(cell): return str(cell.get("back_source", "")).ends_with("083.webp"))
				check( not variable_backs.is_empty(), "variable maze tiles expose the blue back source")
				await capture("map-deep")
	ui.session.leave_room();ui.close_dialog(); await frames()
	check(ui.session.room.is_empty() and ui.session.game.is_empty() and ui.session.child_pid == -1, "deep map session closes cleanly")
	ui.prefs = original_preferences;ui.stop_audio()
	await ui.get_tree().create_timer(0.12).timeout
	print("PACKAGE_RESULT " + ("FAILED" if failed else "PASSED"))
	var tree = ui.get_tree();ui = null;tree.quit(1 if failed else 0)
