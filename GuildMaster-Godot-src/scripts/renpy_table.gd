class_name GuildRenpyTable
extends RefCounted



static func at(parent: Control, node: Control, rect: Rect2, id: String = "") -> Control:
	parent.add_child(node);node.position = rect.position;node.size = rect.size
	if not id.is_empty(): node.name = id
	return node

static func surface(ui, parent: Control, rect: Rect2, id: String = "", style: StyleBox = null) -> Control:
	var panel = Panel.new();panel.add_theme_stylebox_override("panel", style if style != null else GuildPaperSkin.paper("paper", 0))
	at(parent, panel, rect, id);return panel

static func main_surface(ui, parent: Control, rect: Rect2, id: String = "") -> Control:
	return surface(ui, parent, rect, id, GuildPaperSkin.main_frame(0))

static func player_surface(ui, parent: Control, rect: Rect2, id: String = "") -> Control:
	return surface(ui, parent, rect, id, GuildPaperSkin.player_frame(0))

static func caption(ui, parent: Control, text: String, rect: Rect2, points: int = 22, color: Color = Color("343133")):
	return at(parent, ui.label(text, points, color), rect)

static func action(ui, parent: Control, text: String, rect: Rect2, callback: Callable, enabled: bool = true, id: String = "", primary: bool = false) -> Button:
	var node = ui.button(text, callback, enabled, primary);node.custom_minimum_size = Vector2.ZERO
	node.add_theme_font_override("font", ui.theme.default_font)
	var wide = rect.size.x >= 150.0 and rect.size.y >= 44.0
	var base = 18 if rect.size.x <= 120 or rect.size.y < 40 else 24 if rect.size.y == 50 else 21
	if wide:
		var flat = maxf(30.0, rect.size.x - 251.0 * rect.size.y / 167.0)
		base = clampi(mini(base, int(flat / maxf(1.0, float(text.length()) * 1.05))), 12, 26)
	node.add_theme_font_size_override("font_size", base)
	for state in ["normal", "hover", "pressed", "disabled"]:
		if wide: node.add_theme_stylebox_override(state, GuildPaperSkin.banner(GuildPaperSkin.primary_state(state) if primary else state, 4))
		else: node.add_theme_stylebox_override(state, GuildPaperSkin.paper("primary" if primary and state == "normal" else state, 4))
	var points = 21
	while (node.get_combined_minimum_size().x > rect.size.x or node.get_combined_minimum_size().y > rect.size.y) and points > 12:
		points -= 1;node.add_theme_font_size_override("font_size", points)
	at(parent, node, rect, id);return node

static func side_button(ui, text: String, callback: Callable, enabled: bool = true, primary: bool = false) -> Button:
	# 选牌画面右侧栏按钮：固定 300 宽；字数过长时按项目字体＋按钮内距估算并自动缩小字号
	#（不能在树外用 get_combined_minimum_size：那时主题还没挂上，估出的宽度偏小）。
	var node = ui.button(text, callback, enabled, primary)
	node.custom_minimum_size = Vector2(300, 46)
	var font: Font = ui.theme.default_font
	var points = 20
	while points > 13 and font.get_string_size(node.text, HORIZONTAL_ALIGNMENT_LEFT, -1, points).x + 80.0 > 300.0:
		points -= 1
	node.add_theme_font_size_override("font_size", points)
	if points <= 13: node.clip_text = true;node.text_overrun_behavior = TextServer.OVERRUN_TRIM_ELLIPSIS
	return node

static func draw(ui, parent: Control):
	if ui.prefs.get("layout", "classic") == "dashboard":
		GuildDashboardTable.draw(ui, parent);return
	var game = ui.session.game; var me = ui.session.me(); var phase = game.get("phase", "")
	var actor = game.players[int(game.get("turn", 0))] if phase != "finished" else {}
	var focus = me if not me.is_empty() else actor if not actor.is_empty() else game.players[0]
	ui.player_clocks = []
	header(ui, parent, game, actor)
	players(ui, parent, game, me)
	if phase == "finished":
		ui.dialogs.results_inline(parent);return
	if (phase == "draft" or (phase == "research" and not me.get("researched", false))) and not me.is_empty():
		selection_phase(ui, parent, game, me, phase);return
	var map_panel = main_surface(ui, parent, Rect2(362, 116, 990, 694), "MapPanel")
	var title = caption(ui, map_panel, actor.get("name", focus.name) + "的回合" if phase in ["action", "final"] else "等待公会完成情报收集", Rect2(22, 20, 488, 48), 37)
	title.clip_text = true;title.text_overrun_behavior = TextServer.OVERRUN_TRIM_ELLIPSIS;title.tooltip_text = title.text
	caption(ui, map_panel, game.get("map_name", "迷宫疆域"), Rect2(24, 75, 700, 24), 18, ui.MUTED)
	var map = GuildHexMap.new();map.store = ui.store;map.motion = ui.prefs.motion;map.renpy_geometry = true
	at(map_panel, map, Rect2(22, 107, 724, 538), "TableMap");map.set_game(game, ui.session.player_id)
	map.chosen_ids = [ui.selected_tile]
	if phase != "final":
		caption(ui, map_panel, "◇ 可探索", Rect2(22, 659, 110, 24), 17, ui.GOLD)
		caption(ui, map_panel, "◇ 已选择", Rect2(150, 659, 110, 24), 17, Color("c9982e"))
		caption(ui, map_panel, "点击板块查看详情", Rect2(280, 659, 400, 24), 17, ui.MUTED)
	stock(ui, map_panel, focus)
	var commands = main_surface(ui, parent, Rect2(1374, 116, 534, 694), "CommandsPanel")
	caption(ui, commands, "王权议事厅", Rect2(22, 20, 153, 38), 27, ui.GOLD)
	action(ui, commands, "全部成就 ›", Rect2(175, 20, 107, 49), func(): ui.dialogs.achievements(), true, "AllAchievements")
	var royal_grid = GridContainer.new();royal_grid.columns = 3;royal_grid.add_theme_constant_override("h_separation", 10);royal_grid.add_theme_constant_override("v_separation", 10)
	at(commands, ui.scroll(royal_grid), Rect2(22, 77, 490, 150), "Royals")
	for key in game.get("public_achievements", []):
		var data = ui.store.catalog.achievements.get(key, {})
		royal_grid.add_child(ui.card(data.get("source", ""), Vector2(148, 140), func(): ui.dialogs.achievements()))
	var selected = Control.new();at(commands, selected, Rect2(22, 251, 490, 163), "SelectedTile")
	var update_selection = func(cell):
		ui.selected_tile = cell.get("id", "");map.chosen_ids = [ui.selected_tile];map.queue_redraw()
		draw_selection(ui, selected, cell)
	map.cell_clicked.connect(update_selection)
	var existing = game.board.filter( func(cell): return cell.id == ui.selected_tile)
	draw_selection(ui, selected, existing[0] if not existing.is_empty() else {})
	var can = ui.session.can_act()
	action(ui, commands, "特殊行动", Rect2(22, 420, 150, 50), func(): ui.dialogs.abilities(), can, "SpecialActions")
	action(ui, commands, "秘药", Rect2(182, 420, 150, 50), func(): ui.dialogs.potions(), can, "Potions")
	action(ui, commands, "成就", Rect2(342, 420, 150, 50), func(): ui.dialogs.achievements(), true, "Achievements")
	action(ui, commands, "扩展行动", Rect2(22, 480, 230, 50), func(): ui.dialogs.expansions(), not me.is_empty(), "ExpansionActions")
	action(ui, commands, "本季闭店", Rect2(262, 480, 230, 50), func(): ui.dialogs.confirm_pass(), can, "SeasonClose")
	var log_panel = surface(ui, commands, Rect2(22, 548, 490, 130), "MatchLog")
	caption(ui, log_panel, "对局日志", Rect2(12, 8, 150, 25), 18, ui.GOLD)
	action(ui, log_panel, "完整记录", Rect2(394, 8, 84, 33), func(): ui.dialogs.game_log(), true, "FullLog")
	var log_items = VBoxContainer.new();log_items.add_theme_constant_override("separation", 5)
	at(log_panel, ui.scroll(log_items), Rect2(12, 37, 466, 85))
	var entries = game.get("log", [])
	for i in range(entries.size() - 1, -1, -1): log_items.add_child(ui.dialogs.wrapped(entries[i].get("message", ""), 17, ui.MUTED))
	hand(ui, parent, me)
	if phase == "final":
		var status = surface(ui, parent, Rect2(375, 775, 965, 43), "FinalStatus")
		var row = HBoxContainer.new();row.add_theme_constant_override("separation", 22);at(status, row, Rect2(14, 8, 937, 28))
		row.add_child(ui.label("最终行动", 21, ui.GOLD))
		for index in range(game.players.size()):
			var remaining = int(game.final_remaining[index])
			var text = ui.label("P%s  %s次" % [int(game.players[index].id) + 1, remaining], 20)
			text.name = "FinalRemaining" + str(int(game.players[index].id));row.add_child(text)

static func header(ui, parent: Control, game: Dictionary, actor: Dictionary):
	var frame = player_surface(ui, parent, Rect2(12, 22, 1896, 72), "TableHeader")
	caption(ui, frame, "异世界公会长", Rect2(24, 10, 170, 32), 26)
	caption(ui, frame, "观战中" if ui.session.role == "spectator" else ui.session.room.get("name", "我的公会"), Rect2(24, 43, 170, 20), 14, ui.MUTED)
	var seasons = ["春", "夏", "秋", "冬"]
	var season_index = clampi(int(game.get("season", 0)), 0, 3)
	caption(ui, frame, "第 %s 季 · %s" % [int(game.get("round", 1)), seasons[season_index]], Rect2(213, 10, 240, 22), 17, ui.MUTED).name = "SeasonLabel"
	var link = RichTextLabel.new();link.bbcode_enabled = true;link.fit_content = true;link.scroll_active = false;link.selection_enabled = false;link.mouse_filter = Control.MOUSE_FILTER_STOP
	link.text = "[u]%s[/u]" % GuildLang.t("季节生产预告: %s" % seasons[(season_index + 1) % 4])
	link.add_theme_font_override("normal_font", ui.theme.default_font)
	link.add_theme_font_size_override("normal_font_size", 18)
	link.add_theme_color_override("default_color", ui.GOLD)
	link.mouse_default_cursor_shape = Control.CURSOR_POINTING_HAND
	link.gui_input.connect( func(event):
		if event is InputEventMouseButton and event.pressed and event.button_index == MOUSE_BUTTON_LEFT: ui.dialogs.season_forecast())
	at(frame, link, Rect2(213, 34, 176, 31), "SeasonForecastLink")
	caption(ui, frame, ui.PHASES.get(game.phase, game.phase), Rect2(393, 23, 160, 35), 23, ui.GOLD)
	caption(ui, frame, "文明 %s" % int(game.civ), Rect2(532, 16, 94, 24), 17, ui.GOLD).name = "CivilizationValue"
	var remaining = maxi(0, int(game.miasma) - int(game.civ) - 1)
	var progress = ProgressBar.new();progress.show_percentage = false;progress.min_value = 0;progress.max_value = maxi(1, int(game.miasma) - 1)
	progress.value = progress.max_value if remaining == 0 else clampi(int(game.civ), 0, int(progress.max_value))
	progress.add_theme_stylebox_override("background", ui.box(Color("c7b9b1"), Color("6b6460"), 6, 0))
	progress.add_theme_stylebox_override("fill", ui.box(Color("64866d") if remaining == 0 else Color("9f4c50"), Color("64866d") if remaining == 0 else Color("9f4c50"), 6, 0))
	progress.tooltip_text = GuildLang.t("文明推进：文明 +1 达到瘴气时达标。\n当前文明 %s / 瘴气 %s" % [int(game.civ), int(game.miasma)])
	at(frame, progress, Rect2(632, 18, 166, 20), "CivilizationProgress")
	caption(ui, frame, "文明已达标" if remaining == 0 else "还差 %s 文明" % remaining, Rect2(632, 44, 166, 18), 13, Color("4c6553") if remaining == 0 else ui.MUTED).name = "CivilizationRemaining"
	caption(ui, frame, "瘴气 %s" % int(game.miasma), Rect2(812, 16, 110, 24), 17, ui.MUTED).name = "MiasmaValue"
	var callbacks = {"公会记录": func(): ui.dialogs.game_log(), "撤回上一步": func(): ui.undo(), "王权": func(): ui.dialogs.achievements(), "售牌": func(): ui.dialogs.market(), "宝箱": func(): ui.dialogs.treasures(), "离开": func(): ui.dialogs.leave()}
	var shift = 0.0
	for data in ui.renpy_reference.get("table", []):
		var text = data.text
		if not callbacks.has(text): continue
		if text in ["撤回上一步", "售牌"] and ui.session.role != "player": shift += data.rect[2] + 16;continue
		var rect = data.rect; var enabled = game.get("undo", {}).get("available", false) if text == "撤回上一步" else ui.session.can_free_action() if text == "售牌" else true
		action(ui, parent, text, Rect2(rect[0] - shift, rect[1], rect[2], rect[3]), callbacks[text], enabled, "Header_" + text)
	flag_rewards(ui, parent, game)
	var starter = game.players[int(game.get("start_player", 0))]
	caption(ui, parent, "◆ 本季起始玩家：P%s %s" % [int(starter.id) + 1, starter.name], Rect2(36, 95, 440, 22), 15, Color("fffdf7"))
	caption(ui, parent, "ISEKAI GUILD MASTER  /  公会日志与规则可随时查阅", Rect2(12, 1053, 1896, 22), 14, Color("f8efe4"))

static func flag_rewards(ui, parent: Control, game: Dictionary):
	var strip = Control.new();at(parent, strip, Rect2(1514, 27, 374, 60), "FlagRewards")
	var options = game.get("options", {}); var contribution = options.get("guild_board", false) and not options.get("solo", false)
	var flags = game.get("flags", [])
	if flags.is_empty():
		var icon = ui.picture(load("res://ui/symbols/flag.svg"), 26);icon.modulate.a = 0.35;at(strip, icon, Rect2(0, 14, 26, 26))
		caption(ui, strip, "旗标已领完" if options.get("flags", false) or contribution else "未开启旗标奖励", Rect2(34, 16, 270, 26), 16, ui.MUTED)
		return
	var grid = GridContainer.new();grid.columns = 8;grid.add_theme_constant_override("h_separation", 2);grid.add_theme_constant_override("v_separation", 2);at(strip, grid, Rect2(0, 0, 254, 60))
	for threshold in flags:
		var badge = Control.new();badge.custom_minimum_size = Vector2(30, 28);badge.name = "FlagThreshold_" + str(int(threshold));badge.mouse_filter = Control.MOUSE_FILTER_STOP
		badge.tooltip_text = GuildLang.t("文明或瘴气变化经过 %s 时，触发者获得 %s；每个旗标只能领取一次。" % [int(threshold), "1 贡献标记" if contribution else "1 声望"])
		grid.add_child(badge);at(badge, ui.picture(load("res://ui/symbols/flag.svg"), 28), Rect2(0, 0, 30, 28))
		var number = caption(ui, badge, str(int(threshold)), Rect2(5, 3, 23, 19), 13);number.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER;number.mouse_filter = Control.MOUSE_FILTER_IGNORE
	if contribution: caption(ui, strip, "贡献 +1", Rect2(270, 18, 100, 26), 18, ui.GOLD).name = "FlagRewardType"
	else:
		at(strip, ui.symbol("point", 26), Rect2(270, 16, 26, 26));caption(ui, strip, "+1", Rect2(300, 17, 65, 26), 20, ui.GOLD)
	caption(ui, strip, "旗标奖励", Rect2(270, 43, 100, 17), 12, ui.MUTED)

static func players(ui, parent: Control, game: Dictionary, me: Dictionary):
	var list = VBoxContainer.new();list.add_theme_constant_override("separation", 14)
	at(parent, ui.scroll(list), Rect2(12, 116, 344, 906), "PlayerSeats")
	for player in game.players:
		var node = Control.new();node.custom_minimum_size = Vector2(308, 164)
		node.name = "Seat" + str(int(player.id));node.add_to_group("guild_seats");list.add_child(node)
		var panel = player_surface(ui, node, Rect2(0, 0, 308, 164));panel.mouse_filter = Control.MOUSE_FILTER_STOP
		panel.gui_input.connect( func(event):
			if event is InputEventMouseButton and event.pressed and event.button_index == MOUSE_BUTTON_LEFT: ui.dialogs.player_detail(player))
		at(panel, ui.picture(ui.store.adventurer_token(int(player.id)), 25), Rect2(12, 8, 25, 25))
		caption(ui, panel, "P%s %s%s" % [int(player.id) + 1, player.name.left(8), " 你" if int(player.id) == ui.session.player_id else ""], Rect2(45, 8, 250, 28), 21)
		var portrait = GuildPortrait.new();portrait.texture = ui.store.portrait_bust(player.hero, int(player.get("affection", 0)));portrait.on_click = func(): ui.dialogs.player_detail(player)
		at(panel, portrait, Rect2(12, 37, 82, 110), "Portrait")
		var resources = HBoxContainer.new();resources.add_theme_constant_override("separation", 9)
		for kind in ["gold", "strength", "pot"]: resources.add_child(ui.resource(kind, int(player.get(kind, 0)), kind, 20))
		at(panel, resources, Rect2(102, 37, 190, 26))
		var income = HBoxContainer.new();income.add_theme_constant_override("separation", 9)
		for kind in ["gold_pro", "str_pro", "pot_pro"]: income.add_child(ui.resource(kind, int(player.get(kind, 0)), kind, 17))
		at(panel, income, Rect2(102, 66, 190, 23))
		caption(ui, panel, "声望 %s / 撤退 -%s" % [int(player.get("score", 0)), int(player.get("retreat", 0))], Rect2(102, 89, 190, 22), 17)
		var state = GuildTableView.player_status(ui, player, int(game.players[int(game.turn)].id) == int(player.id))
		if state in ["行动中", "等待行动"]: state = ""
		if state.is_empty() and game.get("phase") == "final": state = "剩余 %s 次行动" % int(game.final_remaining[game.players.find(player)])
		var passed = player.get("passed", false)
		var status = caption(ui, panel, state, Rect2(150, 139, 150, 20) if passed else Rect2(102, 115, 190, 21), 15, ui.GOLD);status.name = "SeatStatus"
		if passed: status.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
		var bank = game.get("clock", {});bank = bank if bank is Dictionary else {}
		if state.is_empty() and bank.has(str(int(player.id))): ui.player_clocks.append({"label": status, "id": str(int(player.id))})
		var counters = HBoxContainer.new();counters.add_theme_constant_override("separation", 8)
		counters.add_child(GuildTableView.adventurers(ui, player, 17))
		var hearts = HBoxContainer.new();hearts.add_theme_constant_override("separation", 3);hearts.tooltip_text = GuildLang.t("好感度");hearts.mouse_filter = Control.MOUSE_FILTER_STOP
		hearts.add_child(ui.symbol("affection", 16));hearts.add_child(ui.label(str(int(player.get("affection", 0))), 15))
		counters.add_child(hearts)
		at(panel, counters, Rect2(102, 137 if (not state.is_empty() and not passed) or not bank.is_empty() else 115, 190, 22))
		GuildTableView.status_masks(ui, panel, player, status)
		if game.get("phase") in ["action", "final"] and int(player.id) == int(game.players[int(game.turn)].id):
			var border = Panel.new();border.mouse_filter = Control.MOUSE_FILTER_IGNORE;border.name = "TurnBorder"
			var bstyle = StyleBoxFlat.new();bstyle.draw_center = false;bstyle.border_color = Color("ffd23f")
			bstyle.set_border_width_all(4);bstyle.set_corner_radius_all(10)
			border.add_theme_stylebox_override("panel", bstyle);border.z_index = 5
			panel.add_child(border);border.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	if not me.is_empty():
		if not me.get("private_tiles", {}).is_empty(): list.add_child(ui.button("查看私密迷宫笔记", func(): ui.dialogs.private_tiles()))
		if me.get("strength_as_gold", false): list.add_child(ui.button("设置金币费用折抵", func(): ui.dialogs.payment_preference()))
	if ui.session.local_mode:
		list.add_child(ui.button("存档", func(): ui.dialogs.save_picker()))
		list.add_child(ui.button("玩家昵称", func(): ui.dialogs.player_names()))
	list.add_child(ui.button("房间聊天", func(): ui.dialogs.chat()))

static func stock(ui, parent: Control, focus: Dictionary):
	var affection = int(focus.get("affection", 0))
	_action_reminders(ui, parent)
	caption(ui, parent, "好感度", Rect2(768, 258, 202, 24), 22, ui.GOLD)
	var hearts_panel = Panel.new();hearts_panel.name = "AffectionHearts"
	var style = StyleBoxFlat.new();style.bg_color = Color("f5eee0");style.border_color = Color("1c1a1e")
	style.set_border_width_all(2);style.set_corner_radius_all(9)
	hearts_panel.add_theme_stylebox_override("panel", style)
	hearts_panel.tooltip_text = GuildLang.t("好感度 %s / 5 · 点按打开发展界面" % affection);hearts_panel.mouse_filter = Control.MOUSE_FILTER_STOP
	hearts_panel.gui_input.connect( func(event):
		if event is InputEventMouseButton and event.pressed and event.button_index == MOUSE_BUTTON_LEFT: ui.dialogs.develop())
	var row = HBoxContainer.new();row.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT);row.add_theme_constant_override("separation", 6);row.alignment = BoxContainer.ALIGNMENT_CENTER
	for i in range(5):
		var slot = CenterContainer.new();slot.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		var heart = ui.symbol("affection", 22)
		if i >= affection: heart.modulate.a = 0.2
		slot.add_child(heart);row.add_child(slot)
	hearts_panel.add_child(row)
	at(parent, hearts_panel, Rect2(768, 286, 194, 40))
	caption(ui, parent, "秘药行动", Rect2(768, 330, 202, 27), 22, ui.GOLD)
	for i in range(6):
		var key = ["gold", "strength", "knowledge", "build", "free_card", "power"][i]
		at(parent, GuildTableView.potion_button(ui, key), Rect2(768, 360 + i * 52, 194, 48))

static func _action_reminders(ui, parent: Control):
	# 迷宫地图右侧、好感度上方：可用行动提醒区（点按直达对应界面）。
	var hints = ui.session.game.get("hints", {})
	if not hints is Dictionary: hints = {}
	var rows = []
	if hints.get("achievements", []).size() > 0: rows.append(["◆ 可完成成就 ×%s" % hints.achievements.size(), func(): ui.dialogs.achievements(), "有已满足条件的王权卡；点按打开王权界面完成"])
	if hints.get("develop", []).size() > 0: rows.append(["◆ 可解锁好感度", func(): ui.dialogs.develop(), "有可解锁的发展条件；点按打开发展界面"])
	if bool(hints.get("ability", false)) or int(hints.get("card_actions", 0)) > 0: rows.append(["◆ 可用特殊行动", func(): ui.dialogs.abilities(), "看板娘能力或卡牌特别行动可发动；点按打开特殊行动界面"])
	if hints.get("expansions", []).size() > 0: rows.append(["◆ 可用扩展行动 ×%s" % hints.expansions.size(), func(): ui.dialogs.expansions(), "扩展行动可执行；点按打开扩展行动界面"])
	if hints.get("potions", []).size() > 0: rows.append(["◆ 可用秘药行动 ×%s" % hints.potions.size(), func(): ui.dialogs.potions(), "秘药行动可使用；点按打开秘药工坊"])
	var height = 50 if rows.is_empty() else 27 + rows.size() * 21 + (rows.size() - 1) * 2 + 7
	var frame = Panel.new();frame.name = "ActionReminders"
	var style = StyleBoxFlat.new();style.bg_color = Color("f5eee0");style.border_color = Color("1c1a1e")
	style.set_border_width_all(2);style.set_corner_radius_all(9);frame.add_theme_stylebox_override("panel", style)
	at(parent, frame, Rect2(768, 107, 194, height))
	caption(ui, frame, "行动提醒", Rect2(10, 5, 174, 20), 15, ui.GOLD)
	if rows.is_empty():
		var empty_text = "观战中" if ui.session.me().is_empty() else "暂无可操作的行动"
		caption(ui, frame, empty_text, Rect2(10, 27, 174, 18), 14, ui.MUTED)
		return
	var enabled = ui.session.can_act()
	var column = VBoxContainer.new();column.add_theme_constant_override("separation", 2)
	at(frame, column, Rect2(10, 27, 174, rows.size() * 21 + (rows.size() - 1) * 2))
	for i in range(rows.size()):
		var node = ui.button(rows[i][0], rows[i][1], enabled);node.name = "ActionHint" + str(i)
		node.tooltip_text = GuildLang.t(rows[i][2]);node.custom_minimum_size = Vector2(174, 21)
		node.alignment = HORIZONTAL_ALIGNMENT_LEFT;node.add_theme_font_size_override("font_size", 13)
		for state in ["normal", "hover", "pressed", "disabled"]: node.add_theme_stylebox_override(state, StyleBoxEmpty.new())
		column.add_child(node)

static func draw_selection(ui, parent: Control, cell: Dictionary):
	for child in parent.get_children(): parent.remove_child(child);child.queue_free()
	var data = ui.store.catalog.tiles.get(cell.get("loot", ""), {}) if cell.get("revealed", false) else {}
	var source = data.get("source", cell.get("back_source", "images/piece_png/17.png"))
	at(parent, ui.card(source, Vector2(126, 126), func(): ui.dialogs.art_detail(source, data.get("name", "未揭示板块"))), Rect2(10, 14, 126, 126))
	caption(ui, parent, data.get("name", "选择一个迷宫板块" if cell.is_empty() else "未揭示的迷宫"), Rect2(160, 0, 308, 35), 23)
	if cell.is_empty(): caption(ui, parent, "选择地图亮边区域开始探索" if ui.session.can_act() else "等待其他公会完成行动", Rect2(160, 43, 308, 65), 20, ui.MUTED);return
	var owner = cell.get("owner"); var me = ui.session.me()
	if owner != null:
		caption(ui, parent, "P%s / %s" % [int(owner) + 1, "据点" if cell.get("base", false) else "营地"], Rect2(160, 43, 308, 30), 21)
		action(ui, parent, "建设据点", Rect2(160, 81, 200, 50), func(): ui.session.action("build", {"tile": cell.id}), ui.session.can_act() and not me.is_empty() and int(owner) == int(me.id) and not cell.get("base", false), "BuildBase", true)
	else:
		caption(ui, parent, "★ %s / 声望 %s" % [int(data.get("star", 0)), int(data.get("point", 0))] if not data.is_empty() else "翻开后支付探索费用", Rect2(160, 43, 308, 30), 19, ui.MUTED)
		action(ui, parent, "派遣冒险者", Rect2(160, 81, 200, 50), func(): ui.session.action("explore", {"tile": cell.id}), ui.session.can_act() and cell.get("eligible_for", []).has(ui.session.player_id), "Explore", true)

static func hand(ui, parent: Control, me: Dictionary):
	var frame = player_surface(ui, parent, Rect2(362, 832, 1546, 190), "HandStrip")
	caption(ui, frame, "我的手牌" if not me.is_empty() else "冒险纪事", Rect2(22, 16, 148, 32), 23)
	var cards = me.get("hand", []);ui.hand_page = min(ui.hand_page, max(0, (cards.size() - 1) / 9))
	caption(ui, frame, "%s 张情报" % cards.size(), Rect2(22, 55, 148, 25), 17, ui.MUTED)
	if not me.is_empty():
		action(ui, frame, "我的板块", Rect2(22, 86, 140, 47), func(): ui.dialogs.tiles(me), true, "MyTiles")
		action(ui, frame, "售卖卡牌", Rect2(22, 139, 140, 47), func(): ui.dialogs.market(), ui.session.can_free_action(), "SellCards")
	if not me.is_empty():
		action(ui, frame, "展开全部", Rect2(1370, 18, 150, 49), func(): ui.dialogs.hand(), true, "ExpandHand")
	if cards.size() > 9:
		action(ui, frame, "<", Rect2(1370, 75, 46, 33), func(): ui.hand_page -= 1;ui.rerender(), ui.hand_page > 0, "PreviousHand")
		action(ui, frame, ">", Rect2(1424, 75, 46, 33), func(): ui.hand_page += 1;ui.rerender(), (ui.hand_page + 1) * 9 < cards.size(), "NextHand")
	for i in range(min(9, cards.size() - ui.hand_page * 9)):
		var number = int(cards[ui.hand_page * 9 + i]);at(frame, ui.card(ui.store.card_face(ui.store.card(number)), Vector2(100, 140), func(): ui.dialogs.card_detail(number, true), 5.0), Rect2(190 + i * 116, 18, 100, 140), "HandCard" + str(i))

static func selection_phase(ui, parent: Control, game: Dictionary, me: Dictionary, phase: String):
	var draft = phase == "draft"; var cards = me.get("draft_cards", []) if draft else me.get("offered", [])
	var signature = JSON.stringify([phase, game.get("round"), game.get("draft_step"), cards])
	if ui.research_packet != signature: ui.research_packet = signature;ui.selected_research = []
	var frame = player_surface(ui, parent, Rect2(362, 116, 1546, 906), "SelectionPhase")
	caption(ui, frame, "开局轮抽 / 第 %s 次选择" % int(game.get("draft_step", 0)) if draft else "初次情报收集" if int(game.round) == 1 else "新的情报收集", Rect2(32, 28, 1470, 48), 36, ui.GOLD)
	caption(ui, frame, "留1张，其余传给左侧。轮抽后再选择付费保留，最后1张自动留下。" if draft else "选择要保留的事件卡；保留费用与打出费用分别计算。", Rect2(32, 87, 1470, 35), 22, ui.MUTED)
	var grid = GridContainer.new();grid.columns = 4;grid.add_theme_constant_override("h_separation", 14);grid.add_theme_constant_override("v_separation", 14)
	var scroller = ui.scroll(grid);at(frame, scroller, Rect2(32, 143, 1114, 748), "SelectionCards")
	ui.preserve_selection_scroll(scroller, "research", signature)
	for index in range(cards.size()):
		var art = ui.card(ui.store.card_face(ui.store.card(cards[index])), Vector2(262, 345), func():
			if ui.selected_research.has(index): ui.selected_research.erase(index)
			elif draft: ui.selected_research = [index]
			else: ui.selected_research.append(index)
			ui.rerender())
		art.name = "SelectionCard" + str(index);art.selected = ui.selected_research.has(index);art.interactive = not me.get("draft_ready", false) and game.get("pending") == null;grid.add_child(art)
	var side = VBoxContainer.new();side.add_theme_constant_override("separation", 18);at(frame, ui.scroll(side), Rect2(1182, 160, 300, 704))
	side.add_child(side_button(ui, "查看我的资料", func(): ui.dialogs.player_detail(ui.session.me())))
	if draft:
		side.add_child(ui.label("等待其他公会" if me.get("draft_ready", false) else "选择要留下的牌", 27, ui.GOLD))
		side.add_child(ui.label("当前牌包 %s 张" % cards.size(), 24));side.add_child(ui.label("已经留下 %s / 8 张" % me.get("draft_kept", []).size(), 24))
		side.add_child(side_button(ui, "已确认，等待传牌" if me.get("draft_ready", false) else "确认留牌", func(): ui.session.action("draft_pick", {"index": int(ui.selected_research[0]), "draft_step": int(game.draft_step)}), ui.selected_research.size() == 1 and not me.get("draft_ready", false) and game.get("pending") == null, true))
		side.add_child(side_button(ui, "查看已留牌", func(): ui.dialogs.hand(me.get("draft_kept", []), "轮抽已留牌 / 仅自己可见")))
		side.add_child(side_button(ui, "查看已有手牌", func(): ui.dialogs.hand()))
	else:
		var total = GuildRenpyLogic.research_price(me, game, ui.selected_research.size())
		side.add_child(ui.label("为公会做好准备", 29, ui.GOLD));side.add_child(ui.label("可用金币  %s" % int(me.gold), 25));side.add_child(ui.label("已选 %s 张" % ui.selected_research.size(), 26));side.add_child(ui.label("合计 %s 金币" % total, 32, ui.GOLD))
		var selected = []
		for index in ui.selected_research: selected.append(int(cards[index]))
		var limit = int(me.get("research_initial_limit", 8)) if int(game.round) == 1 else cards.size()
		side.add_child(side_button(ui, "确认情报", func(): ui.session.action("research", {"cards": selected}), GuildRenpyLogic.can_pay_gold(me, total) and selected.size() <= limit and game.get("pending") == null, true))
		side.add_child(side_button(ui, "全部取消", func(): ui.selected_research = [];ui.rerender()))
		side.add_child(side_button(ui, "查看已有手牌（%s张）" % me.get("hand", []).size(), func(): ui.dialogs.hand()))
		if int(game.round) == 1 and not me.get("mulligan_done", false): side.add_child(side_button(ui, "更换所选牌（最多5张，仅一次）", func(): ui.session.action("mulligan", {"cards": selected});ui.selected_research = [], selected.size() > 0 and selected.size() <= 5 and game.get("pending") == null))
		side.add_child(side_button(ui, "查看私人目标", func(): ui.dialogs.achievements()))
