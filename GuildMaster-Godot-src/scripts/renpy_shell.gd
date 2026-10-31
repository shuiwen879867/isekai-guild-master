class_name GuildRenpyShell
extends RefCounted

static func home(ui, parent: Control):
	var world = GuildRenpyTable.caption(ui, parent, "异世界", Rect2(108, 174, 700, 86), 64, Color("f3d2a6"))
	var title = GuildRenpyTable.caption(ui, parent, "公会长", Rect2(108, 250, 700, 135), 112, Color("fff8eb"))
	for heading in [world, title]:
		heading.add_theme_color_override("font_shadow_color", Color(0.1, 0.06, 0.08, 0.65))
		heading.add_theme_constant_override("shadow_offset_x", 2);heading.add_theme_constant_override("shadow_offset_y", 3)
	GuildRenpyTable.caption(ui, parent, "从一张委托，走向属于你的冒险。", Rect2(108, 410, 800, 46), 28, Color("fff8eb"))
	GuildRenpyTable.caption(ui, parent, "经营公会 / 探索迷宫 / 与同伴一起成长", Rect2(108, 464, 800, 35), 23, Color("eadccf"))
	var callbacks = {"连接游戏服务器 开房 / 加入 / 观战": func(): ui.dialogs.connect_setup(), "离线单人": func(): ui.session.start_local(ui.prefs.name), "连接设置": func(): ui.dialogs.settings(), "规则": func(): ui.dialogs.help(), "卡牌图鉴": func(): ui.dialogs.gallery(), "游玩指南": func(): ui.dialogs.help(), "偏好设置": func(): ui.dialogs.settings(), "关于": func(): ui.dialogs.about(), "退出": func(): ui.dialogs.confirm_quit()}
	for data in ui.renpy_reference.get("home", []):
		var rect = data.rect; var text = data.text
		if text in ["查阅规则", "认识她"]: continue
		if not callbacks.has(text): continue
		if text == "关于": rect[2] = 120.0
		elif text == "退出": rect[0] = 656.0;rect[2] = 120.0
		var node = GuildRenpyTable.action(ui, parent, text, Rect2(rect[0], rect[1], rect[2], rect[3]), callbacks[text], true, "Home_" + text, text.begins_with("连接游戏"))
		if rect[2] < 150.0:
			for state in ["normal", "hover", "pressed", "disabled"]: node.add_theme_stylebox_override(state, GuildPaperSkin.plaque(state, 6))
	var card = GuildRenpyTable.surface(ui, parent, Rect2(1124, 112, 614, 850))
	var keys = []
	for key in ui.store.catalog.heroes:
		if ui.store.catalog.heroes[key].get("available", false): keys.append(key)
	if keys.is_empty():
		keys = ["hainie_red"]
	if ui.home_portrait == "" or not keys.has(ui.home_portrait): ui.home_portrait = keys[randi() % keys.size()]
	var current = ui.home_portrait
	var portrait = GuildPortrait.new();portrait.texture = ui.store.portrait(current);portrait.on_click = func(): ui.dialogs.hero_detail({"hero": current})
	GuildRenpyTable.at(card, portrait, Rect2(20, 20, 574, 810))
	if keys.size() > 1:
		for pair in [["◀", Rect2(26, 396, 54, 58), -1, "PortraitPrev"], ["▶", Rect2(534, 396, 54, 58), 1, "PortraitNext"]]:
			var arrow = GuildRenpyTable.action(ui, card, pair[0], pair[1], func(): ui.home_portrait = keys[posmod(keys.find(ui.home_portrait) + pair[2], keys.size())];ui.rerender(), true, pair[3])
			for state in ["normal", "hover", "pressed", "disabled"]:
				var style = StyleBoxFlat.new()
				style.bg_color = Color(0.09, 0.07, 0.09, 0.34) if state == "normal" else Color(0.09, 0.07, 0.09, 0.56)
				style.set_corner_radius_all(20);style.set_border_width_all(1)
				style.border_color = Color(0.95, 0.82, 0.64, 0.35)
				arrow.add_theme_stylebox_override(state, style)
			for tone in [["font_color", Color("fff8eb")], ["font_hover_color", Color("fffdf7")], ["font_pressed_color", Color("f3d2a6")], ["font_disabled_color", Color("fff8eb")]]:
				arrow.add_theme_color_override(tone[0], tone[1])
			arrow.add_theme_font_override("font", ui.theme.default_font)
			arrow.add_theme_font_size_override("font_size", 26)
			arrow.add_theme_constant_override("outline_size", 3)
			arrow.add_theme_color_override("font_outline_color", Color(0.12, 0.08, 0.1, 0.85))
	GuildRenpyTable.caption(ui, parent, "异世界公会长  /  3.2.0", Rect2(108, 994, 800, 30), 18, Color("d2c4b6"))
	GuildRenpyTable.caption(ui, parent, "慢慢来，公会的灯为你亮着。", Rect2(1124, 994, 750, 30), 20, Color("d2c4b6"))

static func room(ui, parent: Control):
	var room = ui.session.room; var host = int(room.get("host_id", -1)) == ui.session.player_id
	var draft = room.get("drafting", false); var offers = room.get("hero_offers", []); var mine = {}
	for seat in room.get("players", []):
		if int(seat.id) == ui.session.player_id: mine = seat
	GuildRenpyTable.caption(ui, parent, room.get("name", "公会房间"), Rect2(24, 65, 1560, 65), 48, Color("fff8eb"))
	var caption_text = "全部准备后开始对局，再抽取候选角色"
	if draft:
		var selecting_name = ""
		for entry in room.get("players", []):
			if int(entry.get("id", -1)) == int(room.get("selecting_seat", 0)): selecting_name = entry.get("name", "")
		caption_text = "选择本局看板娘 · %s 正在选择" % selecting_name if selecting_name else "选择本局看板娘 / 候选仅自己可见"
	GuildRenpyTable.caption(ui, parent, caption_text, Rect2(26, 139, 1560, 40), 25, Color("eadccf"))
	GuildRenpyTable.action(ui, parent, "离开房间", Rect2(1726, 60, 170, 65), func(): ui.session.leave_room();ui.close_dialog())
	for i in range(int(room.get("max_players", 1))):
		var seat = room.players[i] if i < room.players.size() else {}
		var frame = GuildRenpyTable.surface(ui, parent, Rect2(24 + i * 358, 210, 340, 140))
		if draft and int(seat.get("id", -1)) == int(room.get("selecting_seat", 0)):
			var sborder = Panel.new();sborder.mouse_filter = Control.MOUSE_FILTER_IGNORE;sborder.name = "SelectingBorder"
			var sstyle = StyleBoxFlat.new();sstyle.draw_center = false;sstyle.border_color = Color("874449")
			sstyle.set_border_width_all(3);sstyle.set_corner_radius_all(10)
			sborder.add_theme_stylebox_override("panel", sstyle);sborder.z_index = 5
			frame.add_child(sborder);sborder.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
		GuildRenpyTable.caption(ui, frame, seat.get("name", "等待伙伴"), Rect2(20, 18, 300, 38), 27)
		GuildRenpyTable.caption(ui, frame, "已断线" if not seat.get("connected", true) else "已选择" if seat.get("hero_chosen", false) else "已准备" if seat.get("ready", false) else "未准备", Rect2(20, 85, 300, 28), 18, ui.GOLD)
		if host and not seat.is_empty() and int(seat.id) != ui.session.player_id: GuildRenpyTable.action(ui, frame, "踢出", Rect2(240, 88, 80, 42), func(): ui.dialogs.confirm_kick(seat))
	var left = GuildRenpyTable.surface(ui, parent, Rect2(24, 385, 1200, 625))
	if draft and not mine.is_empty():
		if not offers.has(ui.browsing_character): ui.browsing_character = offers[0] if not offers.is_empty() else ""
		for i in range(offers.size()):
			var key = offers[i];var identity = ui.store.catalog.characters.get(key, {});GuildRenpyTable.action(ui, left, identity.get("pool_name", identity.get("name", key)), Rect2(26, 24 + i * 65, 220, 50), func(): ui.browsing_character = key;ui.rerender())
		var identity = ui.store.catalog.characters.get(ui.browsing_character, {})
		for i in range(2):
			var variant = "white" if i == 0 else "black"; var key = identity.get("variants", {}).get(variant, ""); var hero = ui.store.catalog.heroes.get(key, {})
			if hero.is_empty(): continue
			var solo_replacement = str(hero.get("solo_replacement", "")) if room.get("options", {}).get("solo", false) else ""
			if not solo_replacement.is_empty(): hero = ui.store.catalog.heroes.get(solo_replacement, hero)
			GuildRenpyTable.caption(ui, left, hero.get("name", key), Rect2(272 + i * 426, 24, 390, 40), 26, ui.GOLD)
			if not solo_replacement.is_empty():
				GuildRenpyTable.caption(ui, left, "单人：艾露背面替换为皮耶利亚背面", Rect2(272 + i * 426, 351, 390, 22), 15, ui.GOLD)
			GuildRenpyTable.at(left, ui.card(hero.source[0], Vector2(390, 278)), Rect2(272 + i * 426, 79, 390, 278))
			GuildRenpyTable.caption(ui, left, "金币 %s / 力量 %s / 秘药 %s" % [int(hero.get("gold", 0)), int(hero.get("strength", 0)), int(hero.get("pot", 0))], Rect2(272 + i * 426, 372, 390, 30), 20)
			GuildRenpyTable.action(ui, left, "已选择" if mine.get("hero_chosen", false) and mine.get("hero") == key else "选择白版" if i == 0 else "选择黑版", Rect2(272 + i * 426, 417, 390, 65), func(): ui.session.send({"type": "set_hero", "character": ui.browsing_character, "variant": variant}), hero.get("available", false), "Choose_" + variant, true)
			GuildRenpyTable.action(ui, left, "三级能力", Rect2(272 + i * 426, 497, 390, 50), func(): ui.dialogs.hero_detail({"hero": key}))
	else:
		GuildRenpyTable.caption(ui, left, "伙伴正在选择本局角色" if draft else "对局规则", Rect2(26, 24, 1080, 45), 32, ui.GOLD)
		var labels = rule_labels(ui, room)
		GuildRenpyTable.at(left, ui.dialogs.wrapped(" · ".join(labels), 24 if labels.size() <= 14 else 20), Rect2(26, 93, 1080, 256))
		if host and not draft: GuildRenpyTable.action(ui, left, "修改规则与候选张数", Rect2(26, 365, 360, 65), func(): ui.dialogs.room_options(), true, "RoomOptions", true)
	var right = GuildRenpyTable.surface(ui, parent, Rect2(1250, 385, 646, 625))
	GuildRenpyTable.caption(ui, right, "离线单人挑战" if ui.session.local_mode else "房间信息", Rect2(30, 28, 570, 45), 32, ui.GOLD)
	if ui.session.local_mode and not draft:
		GuildRenpyTable.caption(ui, right, "客座模式：%s 位客座玩家" % maxi(0, int(room.get("max_players", 1)) - 1), Rect2(30, 96, 586, 30), 22, ui.GOLD)
		GuildRenpyTable.action(ui, right, "客座模式 · 选择客座人数", Rect2(30, 134, 586, 60), func(): ui.dialogs.guest_picker(), true, "GuestMode")
		GuildRenpyTable.action(ui, right, "读取进度 · 选择存档", Rect2(30, 202, 586, 60), func(): ui.dialogs.load_picker(), true, "LoadSave")
		GuildRenpyTable.action(ui, right, "玩家昵称 · 客座改名", Rect2(30, 270, 586, 60), func(): ui.dialogs.player_names(), true, "PlayerNames")
	if ui.session.local_mode and draft:
		GuildRenpyTable.action(ui, right, "玩家昵称 · 客座改名", Rect2(30, 96, 586, 60), func(): ui.dialogs.player_names(), true, "PlayerNames")
	if not draft and not mine.is_empty():
		if not ui.session.local_mode: GuildRenpyTable.action(ui, right, "取消准备" if mine.get("ready", false) else "准备好了", Rect2(30, 180, 586, 65), func(): ui.session.send({"type": "ready", "ready": not mine.get("ready", false)}), true, "Ready", true)
		if host: GuildRenpyTable.action(ui, right, "开始冒险", Rect2(30, 338 if ui.session.local_mode else 269, 586, 65), func(): ui.session.send({"type": "start"}), room.players.all( func(seat): return seat.get("ready", false) and seat.get("connected", true)), "StartGame", true)
	if not ui.session.local_mode: GuildRenpyTable.action(ui, right, "房间聊天", Rect2(30, 358, 586, 50), func(): ui.dialogs.chat())

static func rule_labels(ui, room) -> Array:
	var options = room.get("options", {})
	var labels = []
	for key in ui.store.catalog.option_labels:
		if options.get(key, false): labels.append(ui.store.catalog.option_labels[key])
	if options.get("solo", false): labels.append("单人挑战")
	var map_names = {"normal": "一般迷宫", "deep": "大深度迷宫", "training": "训练迷宫"}
	var map_type = options.get("map_type", "normal")
	labels.append(("大地图 · " if options.get("force_large", false) and map_type != "training" else "") + map_names.get(map_type, map_type))
	if options.get("solo", false):
		labels.append("单人难度 · " + {"beginner": "初级", "advanced": "上级", "expert": "特级", "super": "超级"}.get(options.get("solo_difficulty", "beginner"), "初级"))
	labels.append("候选 " + str(int(options.get("hero_draw", 2))) + " 名")
	var start = options.get("start_player", "auto")
	labels.append("随机先手" if start == "auto" else "席位 %s 先手" % (int(start) + 1))
	if options.get("initial_civ") != null: labels.append("初始文明 %s" % int(options["initial_civ"]))
	if options.get("initial_miasma") != null: labels.append("初始瘴气 %s" % int(options["initial_miasma"]))
	if options.get("action_timer", false):
		labels.append("倒计时 每回合 %ss / 备用 %ss" % [int(options.get("base_seconds", 30)), int(options.get("reserve_seconds", 120))])
	return labels
