class_name GuildDashboardTable
extends RefCounted

# Reference layout only: every surface uses the established paper skin/colors.
static func draw(ui, parent: Control):
	var game = ui.session.game;var me = ui.session.me();var phase = str(game.get("phase", ""))
	if phase in ["draft", "research"] or phase == "finished":
		# Selection and results keep the same complete, private workflows.
		GuildRenpyTable.header(ui, parent, game, {})
		GuildRenpyTable.players(ui, parent, game, me)
		if phase == "finished": ui.dialogs.results_inline(parent)
		else: GuildRenpyTable.selection_phase(ui, parent, game, me, phase)
		return
	var focus = me if not me.is_empty() else game.players[int(game.get("turn", 0))]
	var can = ui.session.can_act()
	var T = GuildRenpyTable
	ui.player_clocks = []
	var left = T.surface(ui, parent, Rect2(12, 12, 286, 775), "DashboardSidebar")
	T.caption(ui, left, ui.PHASES.get(phase, phase), Rect2(14, 10, 258, 34), 25, ui.GOLD)
	T.caption(ui, left, "玩家状态", Rect2(14, 52, 258, 25), 18, ui.MUTED)
	for i in range(game.players.size()):
		var p = game.players[i];var row = T.surface(ui, left, Rect2(10, 84 + i * 75, 266, 69), "DashboardPlayer" + str(i))
		var portrait = GuildPortrait.new();portrait.texture = ui.store.portrait_bust(p.hero, int(p.get("affection", 0)));portrait.on_click = func(): ui.dialogs.player_detail(p)
		T.at(row, portrait, Rect2(5, 4, 44, 60))
		T.caption(ui, row, "P%s  %s" % [int(p.id) + 1, p.name], Rect2(55, 4, 202, 24), 18, ui.GOLD if int(game.turn) == i else ui.INK)
		T.caption(ui, row, "金币 %s  力量 %s  秘药 %s" % [int(p.gold), int(p.strength), int(p.pot)], Rect2(55, 29, 204, 20), 14)
		var state = GuildTableView.player_status(ui, p, int(game.turn) == i)
		T.caption(ui, row, state, Rect2(55, 49, 204, 18), 13, ui.MUTED)
	var y = 84 + game.players.size() * 75 + 8
	for entry in [["手牌 / 情报", func(): ui.dialogs.hand(), true], ["特殊行动", func(): ui.dialogs.abilities(), can], ["扩充行动", func(): ui.dialogs.expansions(), not me.is_empty()], ["本季闭店", func(): ui.dialogs.confirm_pass(), can], ["偏好设置", func(): ui.dialogs.settings(), true], ["返回 / 离开", func(): ui.dialogs.leave(), true]]:
		T.action(ui, left, entry[0], Rect2(12, y, 262, 40), entry[1], entry[2]);y += 45
	# Three horizontal public zones, matching the supplied reference.
	var zones = [["秘药行动", Rect2(310, 12, 535, 80)], ["公共成就", Rect2(855, 12, 500, 80)], ["剩余宝箱", Rect2(1365, 12, 418, 80)]]
	for zone in zones:
		var panel = T.surface(ui, parent, zone[1]);T.caption(ui, panel, zone[0], Rect2(12, 6, 300, 25), 19, ui.GOLD)
		if zone[0] == "秘药行动":
			for i in range(6):
				var key = ["gold", "strength", "knowledge", "build", "free_card", "power"][i]
				T.action(ui, panel, str(i + 1), Rect2(12 + i * 66, 36, 58, 34), func(): ui.dialogs.potions(), can and not game.get("potions_used", []).has(key) and not game.get("potions_disabled", []).has(key))
		elif zone[0] == "公共成就":
			T.action(ui, panel, "%s 张 · 查看成就" % game.get("public_achievements", []).size(), Rect2(12, 35, 470, 37), func(): ui.dialogs.achievements())
		else:
			T.action(ui, panel, "%s 个 · 查看宝物" % game.get("treasure_pool", []).size(), Rect2(12, 35, 388, 37), func(): ui.dialogs.treasures())
	var map_panel = T.main_surface(ui, parent, Rect2(310, 102, 1473, 685), "DashboardMap")
	var map = GuildHexMap.new();map.store = ui.store;map.motion = ui.prefs.motion;map.renpy_geometry = true
	T.at(map_panel, map, Rect2(130, 12, 1020, 510), "DashboardHexMap");map.set_game(game, ui.session.player_id);map.chosen_ids = [ui.selected_tile]
	var selection = Control.new();T.at(map_panel, selection, Rect2(660, 516, 490, 163), "DashboardSelection")
	var existing = game.board.filter(func(cell): return cell.id == ui.selected_tile)
	T.draw_selection(ui, selection, existing[0] if not existing.is_empty() else {})
	map.cell_clicked.connect(func(cell): ui.selected_tile = cell.id;map.chosen_ids = [cell.id];map.queue_redraw();T.draw_selection(ui, selection, cell))
	T.action(ui, map_panel, "撤回上一步", Rect2(20, 534, 200, 46), func(): ui.undo(), game.get("undo", {}).get("available", false))
	T.action(ui, map_panel, "售牌 / 王权", Rect2(230, 534, 200, 46), func(): ui.dialogs.market(), ui.session.can_free_action())
	T.action(ui, map_panel, "发展公会", Rect2(20, 592, 200, 46), func(): ui.dialogs.develop(), can)
	T.action(ui, map_panel, "我的板块", Rect2(230, 592, 200, 46), func(): ui.dialogs.tiles(me), not me.is_empty())
	# Right-side civilization/miasma track, with round and season beneath.
	var track = T.surface(ui, parent, Rect2(1795, 12, 113, 775), "DashboardTrack")
	T.caption(ui, track, "瘴气 %s" % int(game.miasma), Rect2(8, 8, 98, 30), 17, ui.GOLD)
	var bar = ProgressBar.new();bar.fill_mode = ProgressBar.FILL_BOTTOM_TO_TOP;bar.min_value = 0;bar.max_value = maxf(1, float(game.miasma));bar.value = game.civ;bar.show_percentage = false
	bar.add_theme_stylebox_override("background", ui.box(Color("d6c7b5"), ui.MUTED, 6, 0));bar.add_theme_stylebox_override("fill", ui.box(ui.GOLD, ui.GOLD, 6, 0))
	T.at(track, bar, Rect2(34, 48, 42, 533), "DashboardCivilization")
	T.caption(ui, track, "文明 %s" % int(game.civ), Rect2(8, 592, 98, 30), 17, ui.GOLD)
	T.caption(ui, track, "第 %s 轮" % int(game.round), Rect2(8, 640, 98, 30), 19)
	T.caption(ui, track, ["春", "夏", "秋", "冬"][clampi(int(game.season), 0, 3)], Rect2(8, 683, 98, 30), 21, ui.GOLD)
	# Personal information/resource row along the bottom.
	var personal = T.surface(ui, parent, Rect2(12, 800, 286, 243), "DashboardPersonal")
	var portrait = GuildPortrait.new();portrait.texture = ui.store.portrait(focus.hero, int(focus.get("affection", 0)));portrait.on_click = func(): ui.dialogs.hero_detail(focus)
	T.at(personal, portrait, Rect2(8, 8, 100, 184))
	T.caption(ui, personal, ui.store.catalog.heroes.get(focus.hero, {}).get("name", ""), Rect2(116, 12, 160, 30), 23)
	T.caption(ui, personal, "好感 %s / 5\n声望 %s" % [int(focus.get("affection", 0)), int(focus.get("score", 0))], Rect2(116, 60, 160, 70), 19)
	T.action(ui, personal, "公会详情", Rect2(116, 145, 155, 45), func(): ui.dialogs.player_detail(focus))
	for i in range(3):
		var resource = ["gold", "strength", "pot"][i];var production = ["gold_pro", "str_pro", "pot_pro"][i]
		var panel = T.surface(ui, parent, Rect2(310 + i * 148, 800, 138, 243), "DashboardResource" + str(i))
		T.at(panel, ui.symbol(resource, 38), Rect2(48, 24, 42, 42))
		T.caption(ui, panel, str(int(focus.get(resource, 0))), Rect2(18, 78, 108, 58), 43, ui.GOLD)
		T.caption(ui, panel, "产能 %s" % int(focus.get(production, 0)), Rect2(18, 160, 108, 30), 20)
	var hand = T.surface(ui, parent, Rect2(754, 800, 190, 243), "DashboardHand")
	T.caption(ui, hand, str(me.get("hand", []).size()), Rect2(55, 28, 120, 70), 54, ui.GOLD)
	T.action(ui, hand, "浏览全部手牌", Rect2(12, 118, 166, 49), func(): ui.dialogs.hand(), not me.is_empty())
	T.caption(ui, hand, "事件牌库 %s" % int(game.get("deck_count", 0)), Rect2(14, 188, 162, 25), 16, ui.MUTED)
	var stats = [["迷宫板块", focus.get("tiles", []).size()], ["好感 / 等级", "%s / %s" % [int(focus.get("affection", 0)), int(focus.get("hero_level", 1))]], ["当前声望", focus.get("score", 0)], ["可派冒险者", focus.get("available", 0)], ["已出事件", focus.get("played", []).size()], ["贡献标记", focus.get("contribution", 0)]]
	for i in range(stats.size()):
		var panel = T.surface(ui, parent, Rect2(955 + (i % 3) * 177, 800 + (i / 3) * 126, 167, 117))
		T.caption(ui, panel, str(stats[i][0]), Rect2(10, 8, 147, 25), 17, ui.MUTED)
		T.caption(ui, panel, str(stats[i][1]), Rect2(12, 43, 143, 50), 34, ui.GOLD)
	var logs = T.surface(ui, parent, Rect2(1486, 800, 422, 243), "DashboardLog")
	T.action(ui, logs, "已出牌", Rect2(12, 8, 184, 38), func(): ui.dialogs.player_detail(focus))
	T.action(ui, logs, "对局日志", Rect2(208, 8, 202, 38), func(): ui.dialogs.game_log())
	var items = VBoxContainer.new();var entries = game.get("log", [])
	for i in range(entries.size() - 1, maxi(-1, entries.size() - 4), -1): items.add_child(ui.dialogs.wrapped(entries[i].get("message", ""), 16, ui.MUTED))
	T.at(logs, ui.scroll(items), Rect2(12, 58, 398, 169))
