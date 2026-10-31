class_name GuildTableView
extends RefCounted



static func draw(ui, root: Control):
	GuildRenpyTable.draw(ui, root)

static func legacy_draw(ui, root: VBoxContainer):
	var game = ui.session.game; var me = ui.session.me(); var phase = game.get("phase", "")
	var focus = me if not me.is_empty() else game.players[0]
	var actor = game.players[int(game.get("turn", 0))] if phase != "finished" else focus
	var top = HBoxContainer.new();root.add_child(ui.panel(top, 8))
	var status = ui.label("第 %s 轮 · %s季 · %s" % [int(game.get("round", 1)), ["春", "夏", "秋", "冬"][int(game.get("season", 3))], ui.PHASES.get(phase, phase)], 20, ui.GOLD)
	status.size_flags_horizontal = Control.SIZE_EXPAND_FILL;top.add_child(status)
	top.add_child(ui.label("文明 %s / 瘴气 %s" % [int(game.get("civ", 1)), int(game.get("miasma", 0))], 20))
	ui.game_clock = ui.label("", 16, ui.MUTED);top.add_child(ui.game_clock)
	if not ui.session.active: top.add_child(ui.button("恢复连接", ui.session.reconnect))
	var field = HBoxContainer.new();field.size_flags_vertical = Control.SIZE_EXPAND_FILL;root.add_child(field)
	var seats = VBoxContainer.new();seats.name = "PlayerSeats";seats.custom_minimum_size.x = 264;seats.add_theme_constant_override("separation", 8)
	var seat_scroll = ui.scroll(seats);seat_scroll.size_flags_horizontal = Control.SIZE_FILL;field.add_child(seat_scroll)
	for player in game.players: seats.add_child(player_card(ui, player, int(actor.id) == int(player.id)))
	var seat_tools = HBoxContainer.new();seats.add_child(seat_tools)
	if not me.is_empty():
		seat_tools.add_child(ui.symbol_button("territory", "我的板块", func(): ui.dialogs.player_detail(me)))
		seat_tools.add_child(ui.symbol_button("gold", "售卖卡牌", func(): ui.dialogs.market()))
	seat_tools.add_child(ui.button("聊天", func(): ui.dialogs.chat()))
	var table = VBoxContainer.new();table.size_flags_horizontal = Control.SIZE_EXPAND_FILL;field.add_child(table)
	var center = HBoxContainer.new();center.size_flags_vertical = Control.SIZE_EXPAND_FILL;table.add_child(center)
	var map_body = VBoxContainer.new();map_body.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	var map_panel = ui.panel(map_body, 14);map_panel.size_flags_horizontal = Control.SIZE_EXPAND_FILL;center.add_child(map_panel)
	map_body.add_child(ui.label(actor.name + "的回合" if phase in ["action", "final"] else ui.PHASES.get(phase, phase), 28, ui.INK))
	map_body.add_child(ui.label(game.get("map_name", "迷宫"), 16, ui.MUTED))
	var map_row = HBoxContainer.new();map_row.size_flags_vertical = Control.SIZE_EXPAND_FILL;map_body.add_child(map_row)
	var map = GuildHexMap.new();map.name = "TableMap";map.store = ui.store;map.motion = ui.prefs.motion
	map.size_flags_horizontal = Control.SIZE_EXPAND_FILL;map.size_flags_vertical = Control.SIZE_EXPAND_FILL;map_row.add_child(map);map.set_game(game, ui.session.player_id)
	var stock = VBoxContainer.new();stock.custom_minimum_size.x = 176;stock.add_theme_constant_override("separation", 6)
	var stock_scroll = ui.scroll(stock);stock_scroll.size_flags_horizontal = Control.SIZE_FILL;map_row.add_child(stock_scroll)
	stock.add_child(ui.button("我的板块" if not me.is_empty() else "公会板块", func(): ui.dialogs.player_detail(focus)))
	var held = GridContainer.new();held.columns = 2; var held_scroll = ui.scroll(held, Vector2(0, 86));held_scroll.size_flags_vertical = Control.SIZE_FILL;stock.add_child(held_scroll)
	held_scroll.visible = not focus.get("tiles", []).is_empty()
	for key in focus.get("tiles", []):
		var data = ui.store.catalog.tiles.get(key, {})
		held.add_child(ui.card(data.get("source", ""), Vector2(68, 64), func(): ui.dialogs.art_detail(data.get("source", ""), data.get("name", "板块"))))
	var heart_button = ui.button("", func(): ui.dialogs.growth(focus));heart_button.custom_minimum_size.y = 40
	heart_button.tooltip_text = GuildLang.t("成长与序章");heart_button.add_theme_stylebox_override("normal", GuildPaperSkin.paper("normal", 6));stock.add_child(heart_button)
	var hearts = HBoxContainer.new();heart_button.add_child(hearts);hearts.mouse_filter = Control.MOUSE_FILTER_IGNORE;hearts.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	hearts.offset_left = 8;hearts.offset_right = -8;hearts.offset_top = 8;hearts.offset_bottom = -8
	for i in range(5):
		var heart = ui.symbol("affection", 24)
		if i >= int(focus.get("affection", 0)): heart.modulate.a = 0.2
		hearts.add_child(heart)
	hearts.add_theme_constant_override("separation", 2)
	stock.add_child(resources(ui, focus, false));stock.add_child(resources(ui, focus, true))
	stock.add_child(adventurers(ui, focus, 20))
	stock.add_child(ui.label("秘药行动", 17, ui.GOLD))
	var potion_grid = GridContainer.new();potion_grid.name = "PotionActions";potion_grid.columns = 2
	potion_grid.add_theme_constant_override("h_separation", 6);potion_grid.add_theme_constant_override("v_separation", 6);stock.add_child(potion_grid)
	for key in ui.store.catalog.potions:
		if key.begins_with("alchemy_") and not game.get("options", {}).get("alchemy", false): continue
		potion_grid.add_child(potion_button(ui, key))
	var hint = ui.label("红边可探索 · 点击选择板块", 15, ui.MUTED);map_body.add_child(hint)
	var commands = VBoxContainer.new();commands.custom_minimum_size.x = 356;commands.add_theme_constant_override("separation", 8)
	var command_panel = ui.panel(ui.scroll(commands), 14);command_panel.size_flags_horizontal = Control.SIZE_FILL;center.add_child(command_panel)
	var royal_title = HBoxContainer.new();commands.add_child(royal_title);royal_title.add_child(ui.label("王权议事厅", 26, ui.GOLD))
	royal_title.add_child(ui.button("全部", func(): ui.dialogs.achievements()))
	var royals = HBoxContainer.new();commands.add_child(royals)
	for key in game.get("public_achievements", []).slice(0, 3):
		var data = ui.store.catalog.achievements.get(key, {})
		royals.add_child(ui.card(data.get("source", ""), Vector2(105, 106), func(): ui.dialogs.achievements()))
	var selection = VBoxContainer.new();selection.custom_minimum_size.y = 116;commands.add_child(selection)
	var show_cell = func(cell):
		ui.selected_tile = cell.id;draw_selection(ui, selection, cell)
	map.cell_clicked.connect(show_cell)
	map.cell_hovered.connect( func(cell): hint.text = "(%s,%s) · 区域声望 %s" % [int(cell.q), int(cell.r), int(cell.region)])
	var selected = game.board.filter( func(cell): return cell.id == ui.selected_tile)
	draw_selection(ui, selection, selected[0] if not selected.is_empty() else {})
	var can = ui.session.can_act(); var hero = ui.store.catalog.heroes.get(focus.hero, {})
	var first = HBoxContainer.new();commands.add_child(first)
	for node in [ui.symbol_button("affection", "发展", func(): ui.dialogs.develop(), can), ui.symbol_button("pot", "秘药", func(): ui.dialogs.potions(), can), ui.art_button(ui.store.catalog.achievements.royal133.source, "成就", func(): ui.dialogs.achievements())]:
		node.size_flags_horizontal = Control.SIZE_EXPAND_FILL;first.add_child(node)
	var second = HBoxContainer.new();commands.add_child(second)
	var special = ui.button("特殊能力 / 扩展", func(): ui.dialogs.special_actions(), not me.is_empty());special.size_flags_horizontal = Control.SIZE_EXPAND_FILL;second.add_child(special)
	var close = ui.button("本季闭店", func(): ui.dialogs.confirm_pass(), can, true);close.size_flags_horizontal = Control.SIZE_EXPAND_FILL;second.add_child(close)
	var logs = VBoxContainer.new();commands.add_child(ui.panel(logs, 10))
	var log_title = HBoxContainer.new();logs.add_child(log_title);log_title.add_child(ui.label("对局日志", 17, ui.GOLD));log_title.add_child(ui.button("完整记录", func(): ui.dialogs.game_log()))
	var log_items = VBoxContainer.new();logs.add_child(ui.scroll(log_items, Vector2(0, 72)))
	var entries = game.get("log", [])
	for i in range(entries.size() - 1, max(-1, entries.size() - 6), -1): log_items.add_child(ui.dialogs.wrapped(entries[i].get("message", ""), 15, ui.MUTED))
	ui._render_hand(table, focus, phase)
	if phase == "finished": commands.add_child(ui.button("终局结算", func(): ui.dialogs.results(), true, true))
	var feedback = game.get("feedback", {})
	if ui.last_feedback >= 0 and int(feedback.get("id", 0)) != ui.last_feedback: ui.play_sound(feedback.get("kind", "card"));ui.show_toast(feedback.get("message", ""))
	if not ui.last_phase.is_empty() and ui.last_phase != phase: ui.play_sound("final" if phase == "final" else "season")
	ui.last_feedback = int(feedback.get("id", 0));ui.last_phase = phase;ui.last_round = int(game.get("round", 1))

static func resources(ui, player: Dictionary, production: bool) -> HBoxContainer:
	var row = HBoxContainer.new();row.add_theme_constant_override("separation", 8)
	for pair in [["gold_pro", "金币生产力"], ["str_pro", "战力生产力"], ["pot_pro", "秘药生产力"]] if production else [["gold", "金币"], ["strength", "战力"], ["pot", "秘药"]]:
		var column = VBoxContainer.new();column.custom_minimum_size.x = 43;column.tooltip_text = GuildLang.t(pair[1]);column.mouse_filter = Control.MOUSE_FILTER_STOP
		column.add_theme_constant_override("separation", 3)
		column.add_child(ui.symbol(pair[0], 19 if production else 25)); var number = ui.label(str(int(player.get(pair[0], 0))), 18 if production else 22);number.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER;column.add_child(number);row.add_child(column)
	return row

static func compact_resources(ui, player: Dictionary, production: bool) -> HBoxContainer:
	var row = HBoxContainer.new();row.add_theme_constant_override("separation", 8)
	for key in ["gold_pro", "str_pro", "pot_pro"] if production else ["gold", "strength", "pot"]:
		var entry = ui.resource(key, int(player.get(key, 0)), ui.store.catalog.resource_names.get(key, key), 18)
		entry.add_theme_constant_override("separation", 3);row.add_child(entry)
	return row

static func player_card(ui, player: Dictionary, current: bool) -> Control:
	var body = HBoxContainer.new();body.add_theme_constant_override("separation", 8); var node = ui.panel(body, 8);node.name = "Seat" + str(int(player.id));node.add_to_group("guild_seats")
	var hero = ui.store.catalog.heroes.get(player.hero, {})
	var portrait = GuildPortrait.new();portrait.name = "Portrait";portrait.texture = ui.store.portrait_bust(player.hero, int(player.get("affection", 0)))
	portrait.custom_minimum_size = Vector2(73, 116);portrait.size_flags_vertical = Control.SIZE_EXPAND_FILL
	portrait.tooltip_text = GuildLang.t(hero.get("name", player.hero));portrait.on_click = func(): ui.dialogs.player_detail(player)
	body.add_child(portrait)
	var details = VBoxContainer.new();details.add_theme_constant_override("separation", 3);details.size_flags_horizontal = Control.SIZE_EXPAND_FILL;body.add_child(details)
	var name = ui.label("P%s %s" % [int(player.id) + 1, player.name], 16, ui.GOLD if current else ui.INK);name.clip_text = true;name.tooltip_text = GuildLang.t(player.name);details.add_child(name)
	var stock = HBoxContainer.new();stock.add_theme_constant_override("separation", 4);details.add_child(stock)
	for kind in ["gold", "strength", "pot"]: stock.add_child(ui.resource(kind, int(player.get(kind, 0)), {"gold": "金币", "strength": "战力", "pot": "秘药"}[kind], 17))
	var income = HBoxContainer.new();income.add_theme_constant_override("separation", 4);details.add_child(income)
	for kind in ["gold_pro", "str_pro", "pot_pro"]: income.add_child(ui.resource(kind, int(player.get(kind, 0)), {"gold_pro": "金币生产力", "str_pro": "战力生产力", "pot_pro": "秘药生产力"}[kind], 14))
	var counters = HBoxContainer.new();counters.add_theme_constant_override("separation", 6);details.add_child(counters)
	counters.add_child(adventurers(ui, player, 17));counters.add_child(ui.resource("affection", int(player.get("affection", 0)), "好感度", 15));counters.add_child(ui.resource("point", int(player.get("score", 0)), "声望；撤退 %s" % int(player.get("retreat", 0)), 15))
	var state = player_status(ui, player, current); var badge = ui.label(state, 13, ui.GOLD if state.begins_with("断线") or player.get("passed", false) else ui.MUTED)
	badge.name = "SeatStatus";badge.tooltip_text = GuildLang.t(state);badge.custom_minimum_size.y = 18;details.add_child(badge)
	return node

static func adventurers(ui, player: Dictionary, points: int) -> HBoxContainer:
	var row = HBoxContainer.new();row.tooltip_text = GuildLang.t("未使用冒险者碎片");row.mouse_filter = Control.MOUSE_FILTER_STOP;row.add_theme_constant_override("separation", 4)
	var icon = ui.picture(ui.store.adventurer_token(int(player.id)), points + 6);icon.name = "AdventurerIcon";row.add_child(icon)
	var count = ui.label(str(int(player.get("available", 0))), points);count.name = "AdventurerCount";row.add_child(count);return row

static func player_connected(ui, player: Dictionary) -> bool:
	var connected = player.get("connected", true)
	for seat in ui.session.room.get("players", []):
		if int(seat.id) == int(player.id): connected = connected and seat.get("connected", true)
	if int(player.id) == ui.session.player_id and not ui.session.local_mode: connected = connected and ui.session.active and ui.session.synchronized and ui.session.room_connected
	return connected

static func status_masks(ui, panel: Control, player: Dictionary, status: Label):
	var disconnected = not player_connected(ui, player)
	for entry in [["ClosedMask", player.get("passed", false), Color(0.72, 0.7, 0.66, 0.42), 2], ["DisconnectedMask", disconnected, Color(0.19, 0.2, 0.22, 0.45), 3]]:
		if not entry[1]: continue
		var mask = ColorRect.new();mask.name = entry[0];mask.color = entry[2];mask.z_index = entry[3];mask.mouse_filter = Control.MOUSE_FILTER_IGNORE
		panel.add_child(mask);mask.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	if disconnected or player.get("passed", false):
		status.z_index = 8;status.add_theme_color_override("font_color", Color("fffdf7"));status.add_theme_color_override("font_outline_color", Color("343133"));status.add_theme_constant_override("outline_size", 2)

static func player_status(ui, player: Dictionary, current: bool) -> String:
	if not player_connected(ui, player):
		var seconds = ui.session.room.get("disconnect_remaining", {}).get(str(int(player.id)))
		var state = "断线中 · %s秒" % int(seconds) if seconds != null else "断线中"
		return state + " · 本季闭店" if player.get("passed", false) else state
	if player.get("passed", false): return "本季闭店"
	return "行动中" if current else "等待行动"

static func potion_state(ui, key: String) -> String:
	var game = ui.session.game; var me = ui.session.me()
	if game.get("potions_disabled", []).has(key): return "未开放"
	if game.get("potions_used", []).has(key): return "本轮已用"
	if me.is_empty(): return "观战"
	if key == "build" and not game.get("board", []).any( func(cell): return cell.get("owner") != null and int(cell.owner) == int(me.get("id", -1)) and not cell.get("base", false)): return "无可据点化营地"
	if key == "free_card" and me.get("hand", []).is_empty(): return "手牌为空"
	if int(me.get("pot", 0)) + (me.get("tiles", []).size() if me.get("hero") == "horn_black" else 0) < int(ui.store.catalog.potions[key].get("cost", 0)): return "数量不足"
	if me.get("passed", false): return "本季闭店"
	if not ui.session.can_act(): return "等待行动"
	return "可用"

static func potion_button(ui, key: String) -> Button:
	var potion = ui.store.catalog.potions[key]; var state = potion_state(ui, key)
	var node = ui.button("", func(): ui.session.action("potion", {"option": key}), state == "可用")
	node.name = "Potion_" + key;node.custom_minimum_size = Vector2(99, 48)
	for entry in [["normal", Color("f5eee0"), Color("1c1a1e")], ["hover", Color("fdf7ea"), Color("1c1a1e")], ["pressed", Color("eae1ce"), Color("1c1a1e")], ["disabled", Color("e7e1d7"), Color("8c877e")]]:
		var style = StyleBoxFlat.new();style.bg_color = entry[1];style.border_color = entry[2]
		style.set_border_width_all(2);style.set_corner_radius_all(9)
		style.content_margin_top = 3;style.content_margin_bottom = 3
		node.add_theme_stylebox_override(entry[0], style)
	node.tooltip_text = GuildLang.t(potion.get("name", key) + " · " + str(int(potion.cost)) + "秘药 · " + state + "\n" + potion.get("description", ""))
	var column = VBoxContainer.new();node.add_child(column);column.mouse_filter = Control.MOUSE_FILTER_IGNORE;column.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	column.offset_left = 4;column.offset_right = -4;column.offset_top = 3;column.offset_bottom = -3;column.add_theme_constant_override("separation", 1)
	var line = HBoxContainer.new();line.mouse_filter = Control.MOUSE_FILTER_IGNORE;line.add_theme_constant_override("separation", 1);line.alignment = BoxContainer.ALIGNMENT_CENTER;column.add_child(line)
	if key.begins_with("alchemy_"): line.add_child(ui.label({"alchemy_gem": "宝石", "alchemy_card": "召唤", "alchemy_scout": "侦察", "alchemy_build": "筑城", "alchemy_draw": "情报"}.get(key, "炼金"), 12))
	line.add_child(ui.label(str(int(potion.cost)), 16));line.add_child(ui.symbol("pot", 18));line.add_child(ui.label("=", 16))
	line.add_child(ui.symbol({"gold": "gold", "strength": "strength", "knowledge": "event", "build": "territory", "free_card": "event", "power": "strength"}.get(key, "pot"), 18))
	line.add_child(ui.label("×" + str({"gold": 8, "strength": 2, "knowledge": 2, "build": 1, "free_card": 1, "power": 5}.get(key, 1)), 16))
	if key == "knowledge": line.add_child(ui.symbol("civ_plus1", 16))
	var status = ui.label(state, 14, Color("4c6553") if state == "可用" else ui.MUTED);status.name = "PotionStatus";status.mouse_filter = Control.MOUSE_FILTER_IGNORE;status.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER;status.size_flags_horizontal = Control.SIZE_EXPAND_FILL;column.add_child(status)
	if state == "未开放" or state == "本轮已用":
		var mask = ColorRect.new();mask.name = "PotionMask"
		mask.color = Color(0.72, 0.7, 0.66, 0.5) if state == "未开放" else Color(0.529, 0.267, 0.286, 0.62)
		mask.mouse_filter = Control.MOUSE_FILTER_IGNORE;mask.z_index = 6
		node.add_child(mask);mask.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	return node

static func draw_selection(ui, parent: Control, cell: Dictionary):
	for child in parent.get_children(): child.queue_free()
	if cell.is_empty(): parent.add_child(ui.label("选择一个迷宫板块", 20));parent.add_child(ui.label("在地图中点击红边区域", 17, ui.MUTED));return
	var data = ui.store.catalog.tiles.get(cell.get("loot", ""), {}) if cell.get("revealed", false) else {}
	var source = data.get("source", cell.get("back_source", "images/piece_png/2.png"))
	var row = HBoxContainer.new();parent.add_child(row);row.add_child(ui.card(source, Vector2(115, 114), func(): ui.dialogs.art_detail(source, data.get("name", "迷宫板块"))))
	var detail = VBoxContainer.new();detail.size_flags_horizontal = Control.SIZE_EXPAND_FILL;row.add_child(detail)
	detail.add_child(ui.dialogs.wrapped(data.get("name", "未揭示板块"), 20, ui.INK));detail.add_child(ui.label("区域声望 " + str(int(cell.region)), 16, ui.MUTED))
	if cell.get("blocked", false): detail.add_child(ui.label("封锁区域", 17, ui.MUTED))
	elif cell.get("owner") != null:
		detail.add_child(ui.cost_button("建设据点", "gold", int(cell.get("build_gold", 15)), func(): ui.session.action("build", {"tile": cell.id}), ui.session.can_act() and int(cell.owner) == ui.session.player_id and not cell.get("base", false), true))
	else: detail.add_child(ui.button("派遣冒险者", func(): ui.session.action("explore", {"tile": cell.id}), ui.session.can_act() and cell.get("eligible_for", []).has(ui.session.player_id), true))
