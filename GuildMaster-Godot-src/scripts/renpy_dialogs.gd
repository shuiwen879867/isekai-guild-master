class_name GuildRenpyDialogs
extends GuildDialogs

var card_state = {"double": false, "strength": 0, "pieces": []}
var develop_state = {"slots": [], "festival": false}
var potion_tab = ""
var royal_strength = 0

func overlay(title: String, dimensions: Vector2, key: String = "", close_button: bool = true) -> Control:
	ui.close_dialog(false);ui.modal_key = key
	var shade = ColorRect.new();shade.color = Color(0, 0, 0, 0.68);shade.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT);ui.modal_layer.add_child(shade);ui.dialog = shade
	var frame = GuildRenpyTable.player_surface(ui, shade, Rect2((ui.size - dimensions) / 2, dimensions), "RenpyOverlay")
	GuildRenpyTable.caption(ui, frame, title, Rect2(32, 28, dimensions.x - 200, 46), 33, ui.GOLD)
	if key != "pending" and close_button: GuildRenpyTable.action(ui, frame, "关闭", Rect2(dimensions.x - 120, 28, 88, 49), func(): ui.close_dialog(), true, "CloseDialog")
	return frame

func content(frame: Control, rect: Rect2) -> VBoxContainer:
	var body = VBoxContainer.new();body.add_theme_constant_override("separation", 18);GuildRenpyTable.at(frame, ui.scroll(body), rect);return body

func adjust(parent: Control, title: String, maximum: int, value: int, callback: Callable) -> HBoxContainer:
	var row = HBoxContainer.new();row.add_theme_constant_override("separation", 12);parent.add_child(row)
	row.add_child(ui.label(title, 22, ui.MUTED)); var current = ui.label(str(value), 24, ui.GOLD)
	row.add_child(ui.step_button("−", func(): callback.call(max(0, value - 1)), value > 0));row.add_child(current)
	row.add_child(ui.step_button("＋", func(): callback.call(min(maximum, value + 1)), value < maximum));return row

func art_detail(source: String, title: String = "卡牌详情"):
	var frame = overlay(title, Vector2(1440, 1000), "art")
	GuildRenpyTable.at(frame, ui.card(source, Vector2(1250, 845)), Rect2(95, 115, 1250, 845))

func card_detail(number, playable: bool = false, free: bool = false):
	card_state = {"double": false, "strength": 0, "pieces": []};_card_detail(int(number), playable, free)

func _card_detail(number: int, playable: bool, free: bool):
	var data = ui.store.card(number); var me = ui.session.me()
	if data.is_empty(): return
	var frame = overlay("", Vector2(1230, 944), "card", false)
	GuildRenpyTable.at(frame, ui.card(ui.store.card_face(data), Vector2(586, 818)), Rect2(34, 46, 586, 818))
	GuildRenpyTable.caption(ui, frame, data.get("name", "事件卡"), Rect2(654, 34, 502, 56), 33, ui.GOLD).name = "CardDetailTitle"
	var body = content(frame, Rect2(654, 100, 502, 780))
	body.add_child(wrapped(data.get("ui_summary", data.get("description", "")), 22))
	if playable and not me.is_empty() and me.get("hand", []).has(number):
		if me.get("hero") == "vee_white": body.add_child(ui.button(("● " if card_state.double else "") + "双倍打出 / 薇伊", func(): card_state.double = not card_state.double;card_state.pieces = [];card_state.strength = 0;_card_detail(number, playable, free)))
		if me.get("hero") == "horn_black": body.add_child(ui.button("● 优先秘药代替板块" if me.get("prefer_pot", false) else "优先使用实际板块", func(): ui.session.action("horn_preference", {"prefer_pot": not me.get("prefer_pot", false)});card_state.pieces = []))
		body.add_child(ui.box_button("售卖这张事件卡 / +1金币", func(): ui.session.action("sell_event", {"card": number}), ui.session.can_free_action()))
		body.add_child(wrapped("售卖不消耗回合，闭店后也可以操作。", 19))
		if data.get("can_trans", false) and not free:
			var cap = GuildRenpyLogic.strength_cap(data, me, free, 2 if card_state.double else 1)
			card_state.strength = min(card_state.strength, cap)
			adjust(body, "战力折抵", cap, card_state.strength, func(value): card_state.strength = value;_card_detail(number, playable, free))
		var required = GuildRenpyLogic.piece_cost(data, me, card_state.double)
		if required > 0:
			body.add_child(ui.label("选择要支付的 %s 块板块" % required, 21, ui.GOLD))
			var grid = GridContainer.new();grid.columns = 4;grid.add_theme_constant_override("h_separation", 6);body.add_child(grid)
			for index in range(me.get("tiles", []).size()):
				var tile = ui.store.catalog.tiles.get(me.tiles[index], {})
				var art = ui.card(tile.get("source", ""), Vector2(94, 90), func():
					if card_state.pieces.has(index): card_state.pieces.erase(index)
					elif card_state.pieces.size() < required: card_state.pieces.append(index)
					_card_detail(number, playable, free))
				art.name = "PaymentTile" + str(index);art.selected = card_state.pieces.has(index);grid.add_child(art)
		body.add_child(ui.button("以秘药打出" if free else "打出这张牌", func():
			var pieces = []
			for index in card_state.pieces: pieces.append(me.tiles[index])
			var args = {"card": number, "strength": int(card_state.strength), "pieces": pieces, "double": card_state.double}
			if free: submit("potion", {"option": "free_card", "target": args})
			else: submit("play", args), ui.session.can_act() and card_state.pieces.size() == required, true))
	body.add_child(ui.button("关闭", func(): ui.close_dialog()))

func develop():
	develop_state = {"slots": [], "festival": false};_develop()

func _develop():
	var me = ui.session.me(); var frame = overlay("发展公会 / 加深羁绊", Vector2(1120, 820), "develop")
	var body = content(frame, Rect2(32, 96, 1056, 600))
	body.add_child(wrapped("五个条件可按任意顺序完成，每个条件只能解锁一次。", 22))
	body.add_child(wrapped("每解锁一个条件：好感 +1、招募一名冒险者，并免费抽取一张事件卡。", 22))
	if int(me.get("festival_tokens", 0)) > 0: body.add_child(ui.button(("● " if develop_state.festival else "") + "优先使用庆典 / 每枚抵5金币、1力量或1秘药", func(): develop_state.festival = not develop_state.festival;develop_state.slots = [];_develop()))
	for option in GuildRenpyLogic.develop_options(me, ui.session.game, develop_state.festival):
		var used = me.get("developed", []).has(option[0]); var selected = develop_state.slots.has(option[0])
		var node = ui.button(("已解锁" if used else "已选择" if selected else "可解锁" if option[3] else "未满足") + "     " + option[1] + "     " + option[2], func():
			if develop_state.slots.has(option[0]): develop_state.slots.erase(option[0])
			else: develop_state.slots.append(option[0])
			_develop(), not used and option[3] and ui.session.can_act())
		node.name = "Develop_" + option[0];node.custom_minimum_size = Vector2(1032, 70);body.add_child(node)
	body.add_child(wrapped("好感达到 2 / 5 时，看板娘立即升至 2 / 3 级。升级效果不会额外消耗行动。", 20))
	GuildRenpyTable.action(ui, frame, "解锁 %s 个条件" % develop_state.slots.size(), Rect2(32, 720, 250, 50), func():
		var args = {"slots": develop_state.slots.duplicate(), "count": develop_state.slots.size()}
		if develop_state.festival: args.festival = GuildRenpyLogic.festival_payment(me, develop_state.slots)
		submit("develop", args), not develop_state.slots.is_empty() and ui.session.can_act(), "ConfirmDevelop", true)

func potions():
	potion_tab = "alchemy" if ui.session.game.get("options", {}).get("alchemy", false) else "basic";_potions()

func _potions():
	var game = ui.session.game; var me = ui.session.me(); var frame = overlay("秘药工坊", Vector2(1180, 840), "potions")
	var body = content(frame, Rect2(32, 98, 1116, 704))
	body.add_child(wrapped("持有 %s 瓶秘药。每个格子每季仅供所有公会使用一次。" % int(me.get("pot", 0)), 22))
	if game.get("options", {}).get("alchemy", false):
		var tabs = HBoxContainer.new();body.add_child(tabs)
		tabs.add_child(ui.button("基本秘药", func(): potion_tab = "basic";_potions()))
		tabs.add_child(ui.button("炼金工房", func(): potion_tab = "alchemy";_potions()))
	var grid = GridContainer.new();grid.columns = 3 if potion_tab == "basic" else 2;grid.add_theme_constant_override("h_separation", 18);grid.add_theme_constant_override("v_separation", 18);body.add_child(grid)
	var basic = ["gold", "strength", "knowledge", "build", "free_card", "power"]
	var descriptions = {"gold": "获得 8 金币", "strength": "获得 2 战力", "knowledge": "文明 +1，免费抽 2 张事件卡", "build": "在已选营地免费建设，据点相邻费用照付", "free_card": "选择一张手牌，免除其金币费用打出", "power": "获得 5 战力"}
	for key in ui.store.catalog.potions:
		if (potion_tab == "basic") != basic.has(key): continue
		if potion_tab == "alchemy" and game.get("potions_disabled", []).has(key): continue
		var potion = ui.store.catalog.potions[key]; var state = GuildTableView.potion_state(ui, key)
		var use = ui.button("", func(): ui.session.action("potion", {"option": key}), state == "可用");use.name = "UsePotion_" + key
		use.custom_minimum_size = Vector2(352, 210) if potion_tab == "basic" else Vector2(545, 190)
		_rounded_option(use, false)
		var item = VBoxContainer.new();item.mouse_filter = Control.MOUSE_FILTER_IGNORE;use.add_child(item)
		item.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
		item.offset_left = 18;item.offset_right = -18;item.offset_top = 14;item.offset_bottom = -14
		item.add_theme_constant_override("separation", 8)
		item.add_child(ui.label(potion.get("name", key) + "   %s 秘药" % int(potion.cost), 24))
		item.add_child(wrapped(descriptions.get(key, potion.get("description", "")), 20))
		item.add_child(ui.label(state, 18, ui.MUTED))
		grid.add_child(use)
		if state == "未开放" or state == "本轮已用":
			var mask = ColorRect.new();mask.name = "PotionItemMask"
			mask.color = Color(0.72, 0.7, 0.66, 0.5) if state == "未开放" else Color(0.529, 0.267, 0.286, 0.62)
			mask.mouse_filter = Control.MOUSE_FILTER_IGNORE;mask.z_index = 6
			use.add_child(mask);mask.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	var exchange = HBoxContainer.new();body.add_child(exchange);exchange.add_child(ui.label("自由兑换 / 不消耗行动", 24, ui.GOLD))
	var swap = ui.button("1 秘药 → 3 金币", func(): ui.session.action("exchange", {"amount": 1}), int(me.get("pot", 0)) >= 1);_rounded_option(swap, false);exchange.add_child(swap)

func _rounded_option(node: Button, selected: bool = false):
	# 宝箱／秘药选项卡：圆角长方形包住整个选项，整张即为按钮；选中为金色底。
	var palette = [["normal", Color(1, 1, 1, 0.66), Color("6b6460")], ["hover", Color(1, 1, 1, 0.86), Color("565049")],
		["pressed", Color(0.95, 0.92, 0.85, 0.92), Color("4c4650")], ["disabled", Color(0.91, 0.88, 0.83, 0.55), Color("9c948b")]]
	if selected:
		palette = [["normal", Color("f5dfae"), Color("a8791f")], ["hover", Color("f9e8c0"), Color("96711a")],
			["pressed", Color("ecd196"), Color("8a6a1f")], ["disabled", Color(0.91, 0.88, 0.83, 0.55), Color("9c948b")]]
	for entry in palette:
		var style = StyleBoxFlat.new();style.bg_color = entry[1];style.border_color = entry[2]
		style.set_border_width_all(2);style.set_corner_radius_all(16)
		node.add_theme_stylebox_override(entry[0], style)

func expansions():
	# 扩展行动：只放扩展／扩充包带来的额外行动（特殊行动在「特殊行动」按钮的界面里）。
	var game = ui.session.game; var me = ui.session.me(); var options = game.get("options", {}); var frame = overlay("扩展行动", Vector2(1090, 850), "expansions")
	var body = content(frame, Rect2(32, 108, 1026, 704))
	var entries = [["solo", "雇用冒险者 / 15金币", "hire"], ["monster_quests", "讨伐本季魔兽", "monster_hunt"], ["scouts", "派遣侦查队", "scout"], ["dragon", "讨伐潜行之龙", "dragon_hunt"]]
	for entry in entries:
		if not options.get(entry[0], false): continue
		var label = entry[1]
		if entry[0] == "monster_quests":
			body.add_child(wrapped("每季供应 2 只魔兽；支付 2 力量（春季·夏季）或 3 力量（秋季·冬季）讨伐；获得 1 枚魔兽标记（终局每枚按看板娘等级计分）与该季奖励：春＝金币产能+5、夏＝力量产能+1、秋＝秘药+1并抽1张事件卡、冬＝无。", 18))
		if entry[0] == "dragon":
			var dragon = ui.session.game.get("dragon", {})
			label += " / 已被击败" if not (dragon is Dictionary and dragon.get("active", false)) else " / 剩 %s 颗龙蛋" % int(dragon.get("eggs", 0))
		body.add_child(ui.button(label, func(): submit(entry[2]), ui.session.can_act() and (entry[0] != "dragon" or bool(ui.session.game.get("dragon", {}).get("active", false)))))
	if options.get("forest", false):
		var row = HBoxContainer.new();body.add_child(row)
		row.add_child(ui.button("净化洞穴 / 2力量", func(): submit("forest_purify", {"payment": "strength"}), ui.session.can_act()))
		row.add_child(ui.button("净化洞穴 / 1庆典", func(): submit("forest_purify", {"payment": "festival"}), ui.session.can_act()))
	if options.get("guild_board", false): body.add_child(ui.button("公会委托板", quests))
	if options.get("alchemy", false): body.add_child(ui.button("欧贝拉炼金工房", potions))
	if int(me.get("gems", 0)) > 0: body.add_child(ui.button("售卖1枚宝石 / +3金币", func(): ui.session.action("sell_gem")))
	if me.get("hero") == "horn_black": body.add_child(ui.button("● 优先秘药代替板块" if me.get("prefer_pot", false) else "优先实际板块 / 霍伦支付设置", func(): ui.session.action("horn_preference", {"prefer_pot": not me.get("prefer_pot", false)})))

func special_actions(): expansions()

var rule_draft = {}
var rule_rows = {}
var toggle_cards = {}
var initial_on = {}
var initial_rows = {}

func room_options():
	# 对局规则：版式照原客户端；按钮统一 plaque_normal（通常）/plaque_pressed（选中深色）。
	rule_draft = ui.session.room.get("options", ui.store.catalog.defaults).duplicate(true)
	var local = ui.session.local_mode
	var players = int(ui.session.room.get("max_players", 1)); var banned = ui.session.room.get("banned_characters", [])
	var solo = local and players <= 1
	for key in ["festival_preparation", "monster_quests", "scouts"]:
		if solo and bool(rule_draft.get(key, false)): rule_draft[key] = false
	if players > 3 and bool(rule_draft.get("forbidden", false)): rule_draft.forbidden = false
	rule_rows = {};toggle_cards = {};initial_on = {};initial_rows = {}
	var frame = overlay("对局规则", Vector2(1420, 1020), "rules", false); var body = content(frame, Rect2(32, 104, 1356, 892))
	body.add_theme_constant_override("separation", 8)
	var top = HBoxContainer.new();top.add_theme_constant_override("separation", 14);body.add_child(top)
	top.add_child(ui.label("迷宫", 24, ui.GOLD))
	top.add_child(_segment("map_type", [["normal", "一般迷宫"], ["deep", "大深度迷宫"], ["training", "训练迷宫"]]))
	var spacer = Control.new();spacer.size_flags_horizontal = Control.SIZE_EXPAND_FILL;top.add_child(spacer)
	top.add_child(ui.label("候选", 24, ui.GOLD))
	var draw = OptionButton.new();draw.name = "RoomHeroDraw";draw.custom_minimum_size = Vector2(150, 46)
	for count in range(1, 6): draw.add_item(GuildLang.t("%s 张" % count), count)
	draw.select(clampi(int(rule_draft.get("hero_draw", 2)), 1, 5) - 1)
	var limit = GuildRoomSetup.candidate_limit(ui.store.catalog, players, banned)
	for index in range(5): draw.set_item_disabled(index, index >= limit)
	top.add_child(draw)
	body.add_child(wrapped("可用角色 %s 名 · 每位最多 %s 张候选" % [GuildRoomSetup.character_pool(ui.store.catalog, banned).size(), limit], 17))
	body.add_child(wrapped("每个开关会改变本局规则；开局后锁定。角色开始对局后才抽取。", 19))
	var grid = GridContainer.new();grid.columns = 3;grid.add_theme_constant_override("h_separation", 14);grid.add_theme_constant_override("v_separation", 8);body.add_child(grid)
	for key in ui.store.catalog.option_labels:
		var forbidden_locked = key == "forbidden" and players > 3
		var locked_option = forbidden_locked or (solo and ["festival_preparation", "monster_quests", "scouts"].has(key))
		var card = ui.button(("● " if bool(rule_draft.get(key, false)) else "○ ") + ui.store.catalog.option_labels[key], func(): _flip_toggle(key), not locked_option)
		card.name = "RuleToggle_" + key;card.custom_minimum_size = Vector2(442, 46)
		_style_plaque(card, bool(rule_draft.get(key, false)))
		if locked_option:
			card.disabled = true;rule_draft[key] = false
			if forbidden_locked: card.tooltip_text = GuildLang.t("禁止区域仅支持 1–3 人。")
			else: card.tooltip_text = GuildLang.t("单人规则不使用侦查队、魔兽讨伐与庆典准备。")
		toggle_cards[key] = card;grid.add_child(card)
	var seconds = HBoxContainer.new();seconds.add_theme_constant_override("separation", 26);body.add_child(seconds)
	_stepper(seconds, "基础秒数", 1, 3600, "base_seconds")
	_stepper(seconds, "备用秒数", 0, 7200, "reserve_seconds")
	_stepper(seconds, "断线宽限", 1, 3600, "disconnect_seconds")
	body.add_child(wrapped("备用整局共用；超时自动选择并闭店。", 17))
	if local:
		var difficulty_row = HBoxContainer.new();difficulty_row.add_theme_constant_override("separation", 14);body.add_child(difficulty_row)
		difficulty_row.add_child(ui.label("挑战难度", 24, ui.GOLD))
		difficulty_row.add_child(_segment("solo_difficulty", [["beginner", "初级"], ["advanced", "上级"], ["expert", "特级"], ["super", "超级"]]))
	var start_row = HBoxContainer.new();start_row.add_theme_constant_override("separation", 14);body.add_child(start_row)
	start_row.add_child(ui.label("先手", 24, ui.GOLD))
	var first = OptionButton.new();first.name = "StartPlayerPick";first.custom_minimum_size = Vector2(230, 46)
	first.add_item(GuildLang.t("随机先手"), 0)
	for i in range(players): first.add_item(GuildLang.t("席位 %s 先手" % (i + 1)), i + 1)
	var start_value = rule_draft.get("start_player", "auto")
	first.select(0 if str(start_value) == "auto" else clampi(int(start_value) + 1, 1, first.item_count - 1))
	start_row.add_child(first)
	var initial = HBoxContainer.new();initial.add_theme_constant_override("separation", 30);body.add_child(initial)
	rule_rows.civ = _initial_row(initial, "initial_civ", "初始文明", rule_draft.get("initial_civ"), 1)
	rule_rows.miasma = _initial_row(initial, "initial_miasma", "初始瘴气", rule_draft.get("initial_miasma"), 10 * players)
	body.add_child(wrapped("初始文明/初始瘴气不勾选时，遵循人数、扩充及单人难度的标准初始值。", 17))
	var bottom = HBoxContainer.new();bottom.add_theme_constant_override("separation", 16);body.add_child(bottom)
	var apply = ui.button("应用规则", func(): _submit_rules());_style_plaque(apply, false, true);bottom.add_child(apply)
	var back = ui.button("返回", func(): ui.close_dialog());_style_plaque(back, false);bottom.add_child(back)
	rule_rows.hero_draw = draw;rule_rows.start_player = first

func _segment(key: String, options: Array) -> HBoxContainer:
	var group = HBoxContainer.new();group.add_theme_constant_override("separation", 8)
	toggle_cards["segment_" + key] = group
	for option in options:
		var node = ui.button(option[1], func(): rule_draft[key] = option[0];_restyle_segment(group, options, key))
		_style_plaque(node, str(rule_draft.get(key, null)) == str(option[0]))
		group.add_child(node)
	return group

func _restyle_segment(group: Control, options: Array, key: String):
	for index in range(group.get_child_count()):
		var node = group.get_child(index) as Button
		if node == null or index >= options.size(): continue
		_style_plaque(node, str(rule_draft.get(key, null)) == str(options[index][0]))

func _style_plaque(node: Button, selected: bool, primary: bool = false):
	# 四种状态都明确指定 plaque 样式，不回退主题默认；选中＝pressed 深色，酒红染色＝primary。
	for state in ["normal", "hover", "pressed"]:
		var kind = "pressed" if selected else ("primary" if primary else state)
		node.add_theme_stylebox_override(state, GuildPaperSkin.plaque(kind, 8))
	node.add_theme_stylebox_override("disabled", GuildPaperSkin.plaque("disabled", 8))
	if selected or primary:
		for state in ["font_color", "font_hover_color", "font_pressed_color"]: node.add_theme_color_override(state, Color("fffdf7"))
	else:
		for state in ["font_color", "font_hover_color", "font_pressed_color"]: node.remove_theme_color_override(state)

func _flip_toggle(key: String):
	rule_draft[key] = not bool(rule_draft.get(key, false))
	_restyle_toggle(toggle_cards[key], key)

func _restyle_toggle(node: Button, key: String):
	var on = bool(rule_draft.get(key, false))
	node.text = GuildLang.t(("● " if on else "○ ") + str(ui.store.catalog.option_labels[key]))
	_style_plaque(node, on)

func _initial_row(parent: Control, key: String, title: String, value, fallback: int) -> Dictionary:
	var card_key = "on_" + key; var label = title + "（自定义）"
	var card = ui.button(("● " if value != null else "○ ") + label, func(): _flip_initial(card_key, label))
	card.custom_minimum_size = Vector2(268, 46);_style_plaque(card, value != null)
	var amount = SpinBox.new();amount.min_value = 0;amount.max_value = 1000;amount.step = 1
	amount.value = fallback if value == null else int(value);amount.editable = value != null;amount.custom_minimum_size = Vector2(150, 46)
	var row = HBoxContainer.new();row.add_theme_constant_override("separation", 10);parent.add_child(row)
	row.add_child(card);row.add_child(amount)
	toggle_cards[card_key] = card;initial_on[card_key] = value != null;initial_rows[card_key] = amount
	return {"card": card, "amount": amount}

func _flip_initial(card_key: String, label: String):
	initial_on[card_key] = not bool(initial_on.get(card_key, false))
	var card = toggle_cards[card_key]
	card.text = GuildLang.t(("● " if bool(initial_on[card_key]) else "○ ") + label)
	_style_plaque(card, bool(initial_on[card_key]))
	initial_rows[card_key].editable = bool(initial_on[card_key])

func _stepper(parent: Control, title: String, minimum: int, maximum: int, key: String):
	var row = HBoxContainer.new();row.add_theme_constant_override("separation", 10);parent.add_child(row)
	row.add_child(ui.label(title, 22, ui.GOLD))
	var value_node = ui.label(str(int(rule_draft.get(key, 0))), 23)
	value_node.custom_minimum_size.x = 62;value_node.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	var write = func(amount):
		amount = clampi(amount, minimum, maximum)
		rule_draft[key] = amount;value_node.text = str(amount)
	row.add_child(ui.step_button("−", func(): write.call(int(rule_draft.get(key, 0)) - 1)))
	row.add_child(value_node)
	row.add_child(ui.step_button("＋", func(): write.call(int(rule_draft.get(key, 0)) + 1)))

func _submit_rules():
	var values = rule_draft.duplicate(true)
	values.map_type = str(values.get("map_type", "normal"));values.hero_draw = rule_rows.hero_draw.get_selected_id()
	values.solo_difficulty = str(values.get("solo_difficulty", "beginner"))
	var start = values.get("start_player", "auto")
	values.start_player = "auto" if str(start) == "auto" else int(start)
	values.initial_civ = int(rule_rows.civ.amount.value) if bool(initial_on.get("on_initial_civ", false)) else null
	values.initial_miasma = int(rule_rows.miasma.amount.value) if bool(initial_on.get("on_initial_miasma", false)) else null
	values.base_seconds = int(rule_draft.get("base_seconds", 30));values.reserve_seconds = int(rule_draft.get("reserve_seconds", 120));values.disconnect_seconds = int(rule_draft.get("disconnect_seconds", 30))
	ui.session.send({"type": "set_options", "options": values});ui.close_dialog()

func abilities():
	var me = ui.session.me(); var hero = ui.store.catalog.heroes.get(me.get("hero", ""), {}); var ability = hero.get("ability", {})
	var frame = overlay("特殊行动", Vector2(1160, 850), "abilities"); var body = content(frame, Rect2(32, 102, 1096, 702))
	body.add_child(wrapped(hero.get("name", "") + " / 看板娘能力", 28));body.add_child(wrapped(hero.get("description", ""), 23))
	if not ability.is_empty(): body.add_child(ui.button("发动看板娘能力", hero_ability, ui.session.can_act() and not me.get("used", []).has("ability") and int(me.get("hero_level", 1)) <= int(ability.get("max_level", 3)), true))
	else: body.add_child(wrapped("这位看板娘的被动效果会自动结算。", 22))
	body.add_child(ui.label("已打出卡牌的特别行动", 27, ui.GOLD))
	for i in range(me.get("played", []).size()):
		var number = int(me.played[i]); var data = ui.store.card(number); var states = me.get("card_states", []); var state = states[i] if i < states.size() else {}
		if data.get("action", {}).is_empty() or state.get("face_down", false): continue
		body.add_child(ui.label(data.get("name", "事件卡"), 25))
		body.add_child(wrapped(data.get("ui_summary", data.get("description", "")), 21))
		body.add_child(ui.button("使用特别行动", func(): ui.session.action("card_action", {"card": number}), ui.session.can_act() and int(state.get("used_round", 0)) != int(ui.session.game.round)))

func market():
	var me = ui.session.me(); var frame = overlay("售卖卡牌 / 自由行动", Vector2(1380, 900), "market")
	GuildRenpyTable.caption(ui, frame, "金币 %s / 事件手牌 1金 / 私人王权卡 %s金 / 不消耗回合，闭店后仍可售卖" % [int(me.get("gold", 0)), int(ui.session.game.get("rules", {}).get("discard_achievement_gold", 5))], Rect2(32, 94, 1312, 32), 23, ui.GOLD)
	var body = content(frame, Rect2(32, 142, 1312, 690)); var seen = []
	for number in me.get("hand", []):
		if seen.has(number): continue
		seen.append(number); var data = ui.store.card(number); var row = HBoxContainer.new();row.add_theme_constant_override("separation", 24);body.add_child(ui.panel(row, 18))
		row.add_child(ui.card(ui.store.card_face(data), Vector2(72, 100)))
		var title = wrapped(data.get("name", "") + " ×" + str(me.hand.count(number)), 25);title.custom_minimum_size = Vector2(750, 100);row.add_child(title)
		row.add_child(ui.button("卖一张 / +1金", func(): ui.session.action("sell_event", {"card": int(number)}), ui.session.can_free_action(), true))
	for key in me.get("achievements", []):
		var data = ui.store.catalog.achievements.get(key, {}); var row = HBoxContainer.new();row.add_theme_constant_override("separation", 24);body.add_child(ui.panel(row, 18))
		row.add_child(ui.card(data.get("source", ""), Vector2(72, 100))); var title = wrapped("王权 / " + data.get("name", key), 25);title.custom_minimum_size = Vector2(750, 100);row.add_child(title)
		row.add_child(ui.button("卖一张 / +%s金" % int(ui.session.game.get("rules", {}).get("discard_achievement_gold", 5)), func(): ui.session.action("discard_achievement", {"id": key}), ui.session.can_free_action(), true))
	if body.get_child_count() == 0: body.add_child(wrapped("没有可售卖的手牌或私人王权卡。", 28))

func tiles(player: Dictionary):
	var frame = overlay(player.get("name", "") + " / 迷宫板块", Vector2(1320, 880), "tiles")
	GuildRenpyTable.caption(ui, frame, "公开收藏 / 包括持有、人物卡与事件卡上的板块", Rect2(32, 91, 1252, 32), 22, ui.MUTED)
	var grid = GridContainer.new();grid.columns = 4;grid.add_theme_constant_override("h_separation", 16);grid.add_theme_constant_override("v_separation", 16)
	GuildRenpyTable.at(frame, ui.scroll(grid), Rect2(32, 138, 1252, 685))
	var entries = []
	for key in player.get("tiles", []): entries.append([key, "持有板块"])
	for key in player.get("hero_tiles", []): entries.append([key, "附在人物卡上 / 不可当作持有板块支付"])
	for state in player.get("card_states", []):
		for key in state.get("tiles", []): entries.append([key, "附在事件卡上 / 不可当作持有板块支付"])
	for entry in entries:
		var data = ui.store.catalog.tiles.get(entry[0], {}); var column = VBoxContainer.new(); var panel = ui.panel(column, 16);panel.custom_minimum_size = Vector2(294, 300);grid.add_child(panel)
		column.add_child(ui.card(data.get("source", ""), Vector2(170, 170), func(): art_detail(data.get("source", ""), data.get("name", "板块"))))
		column.add_child(wrapped("%s / %s星 / %s声望" % [data.get("name", ""), int(data.get("star", 0)), int(data.get("point", 0))], 20));column.add_child(wrapped(entry[1], 18))
	if entries.is_empty(): grid.add_child(wrapped("这个公会暂时没有获得板块。", 28))

func hand(cards: Array = [], title: String = "我的手牌"):
	if cards.is_empty(): cards = ui.session.me().get("hand", [])
	var frame = overlay(title, Vector2(1440, 1000), "hand")
	var grid = GridContainer.new();grid.name = "HandGrid";grid.columns = 4;grid.add_theme_constant_override("h_separation", 14);grid.add_theme_constant_override("v_separation", 14)
	GuildRenpyTable.at(frame, ui.scroll(grid), Rect2(32, 103, 1376, 850))
	if cards.is_empty(): grid.add_child(ui.label("手牌为空", 26, ui.MUTED))
	for i in range(cards.size()):
		var number = cards[i]
		var art = ui.card(ui.store.card_face(ui.store.card(number)), Vector2(330, 470), func(): card_detail(int(number), true))
		art.name = "HandCard" + str(i);grid.add_child(art)

func private_tiles():
	var me = ui.session.me()
	var notes = me.get("private_tiles", {})
	var frame = overlay("我的迷宫笔记 / 仅自己可见", Vector2(1080, 800), "private_tiles")
	var snapshot = ui.session.game.duplicate(true)
	for cell in snapshot.get("board", []):
		var key = str(cell.get("id", ""))
		var noted = notes.has(key)
		cell["revealed"] = noted
		if noted: cell["loot"] = notes[key]
	var map = GuildHexMap.new();map.store = ui.store;map.motion = ui.prefs.motion;map.renpy_geometry = true
	GuildRenpyTable.at(frame, map, Rect2(32, 104, 640, 648), "NotesMap")
	map.set_game(snapshot, ui.session.player_id)
	map.cell_clicked.connect( func(cell):
		var key = str(cell.get("id", ""))
		if not notes.has(key): return
		var tile = ui.store.catalog.tiles.get(notes[key], {})
		art_detail(tile.get("source", ""), tile.get("name", "迷宫板块")))
	var side = content(frame, Rect2(692, 104, 356, 648))
	GuildRenpyTable.caption(ui, frame, "笔记内容 / 仅自己可见", Rect2(692, 74, 356, 26), 20, ui.MUTED)
	if notes.is_empty(): side.add_child(wrapped("本局尚未私下查看任何迷宫板块。", 20, ui.MUTED))
	for key in notes:
		var tile = ui.store.catalog.tiles.get(notes[key], {})
		var row = HBoxContainer.new();row.add_theme_constant_override("separation", 14)
		row.add_child(ui.card(tile.get("source", ""), Vector2(104, 104), func(): art_detail(tile.get("source", ""), tile.get("name", "迷宫板块"))))
		var info = VBoxContainer.new();info.add_theme_constant_override("separation", 2)
		info.add_child(ui.label(str(tile.get("name", notes[key])), 22))
		info.add_child(ui.label("坐标 " + str(key), 18, ui.MUTED))
		row.add_child(info)
		side.add_child(ui.panel(row, 10))

func payment_preference():
	var me = ui.session.me(); var frame = overlay("金币费用的力量折抵", Vector2(1050, 600), "payment_preference"); var body = content(frame, Rect2(32, 98, 986, 430))
	var count = integer_row(body, "优先抵付力量", int(me.get("strength", 0)), int(me.get("gold_payment_strength", 0)))
	body.add_child(ui.button("应用设置", func(): ui.session.action("payment_preference", {"strength": int(count.value)});ui.close_dialog(), ui.session.can_free_action(), true))

func treasures(player: Dictionary = {}):
	if player.is_empty(): player = ui.session.me()
	var frame = overlay("宝箱与公会宝物", Vector2(1200, 880), "treasures"); var body = content(frame, Rect2(32, 98, 1136, 730))
	body.add_child(wrapped("开启宝箱后，从尚未领取的宝物中选择一件；产能在季节生产时结算。", 22))
	for key in ui.session.game.get("treasure_rewards", {}):
		var reward = ui.session.game.treasure_rewards[key]; var owner = ""
		for seat in ui.session.game.get("players", []):
			if seat.get("treasures", []).has(key): owner = seat.name;break
		var row = HBoxContainer.new();row.add_theme_constant_override("separation", 18);body.add_child(ui.panel(row, 10))
		var icon = treasure_icon(key, 40)
		icon.modulate.a = 1 if owner.is_empty() else 0.35;row.add_child(icon)
		var detail = VBoxContainer.new();detail.add_theme_constant_override("separation", 3);row.add_child(detail)
		detail.add_child(ui.label(reward.get("name", key), 24, ui.GOLD))
		detail.add_child(wrapped(reward.get("description", "").replace("三种标记各 +1", "生活、商业、零件标记各 +1"), 21))
		detail.add_child(ui.label("未领取 / 可在开启宝箱时选择" if owner.is_empty() else "已获得：" + owner, 18, ui.MUTED))

func season_forecast():
	var game = ui.session.game
	var seasons = ["春", "夏", "秋", "冬"]
	var season_index = clampi(int(game.get("season", 0)), 0, 3)
	var frame = overlay("季节与生产预告", Vector2(1000, 700), "forecast"); var body = content(frame, Rect2(32, 98, 936, 520))
	body.add_child(wrapped("第 %s 季 · 当前季节: %s → 下一季 %s" % [int(game.get("round", 1)), seasons[season_index], seasons[(season_index + 1) % 4]], 27, ui.GOLD))
	body.add_child(wrapped("春：力量 +1；夏：秘药 +1；秋：金币 +5；冬：结算产能。扩展规则以本局设置为准。", 24, ui.MUTED))
	var order = ["春季：各公会力量 +1", "夏季：各公会秘药 +1", "秋季：各公会长获得 +5 金币", "冬季：按各公会的生产力结算本季产能"]
	for i in range(4):
		body.add_child(wrapped(("▶ 当前 " if i == season_index else "　%s  " % (i + 1)) + order[i] + ("（即将到来）" if (season_index + 1) % 4 == i else ""), 22 if i == season_index else 20, ui.GOLD if i == season_index else ui.INK))
	body.add_child(wrapped("── 各公会生产力（冬季结算时按此发放）──", 22, ui.GOLD))
	for player in ui.session.game.get("players", []): body.add_child(wrapped("%s / 金币产能 %s / 力量产能 %s / 秘药产能 %s" % [player.name, int(player.gold_pro), int(player.str_pro), int(player.pot_pro)], 22))

func quests():
	var game = ui.session.game; var slots = game.get("quests", [])
	if not slots is Array: slots = []
	var frame = overlay("公会委托", Vector2(1360, 1000), "quests")
	var body = content(frame, Rect2(32, 103, 1296, 850))
	var rewards = ["金币+3", "无额外奖励", "力量+1", "额外贡献+1", "秘药+1", "抽牌+2"] if slots.size() == 6 else ["金币+3", "金币+3", "无额外奖励", "力量+1", "力量+1", "额外贡献+1", "秘药+1", "秘药+1", "抽牌+2"]
	body.add_child(wrapped("3×3 委托板 · 金色外框＝当前公会长已满足条件，本季结算时可完成。", 22, ui.MUTED))
	var center = CenterContainer.new();body.add_child(center)
	var grid = GridContainer.new();grid.columns = 3;grid.name = "QuestBoardGrid";grid.add_theme_constant_override("h_separation", 22);grid.add_theme_constant_override("v_separation", 16);center.add_child(grid)
	var solo = bool(game.get("options", {}).get("solo", false))
	for index in range(9):
		var item = slots[index] if index < slots.size() else null
		var reward = rewards[index] if index < rewards.size() else "—"
		if item is Dictionary:
			var data = ui.store.catalog.quests.get(str(int(item.get("card", 0))), {});var source = data.get("source", "")
			var done = bool(item.get("done", false));var ready = bool(item.get("ready", false)) and not done
			var art = ui.card(source, Vector2(372, 240), func(): art_detail(source, data.get("name", "公会委托")))
			art.highlight = ready
			if done: art.modulate = Color(1, 1, 1, 0.42)
			art.tooltip_text = "%s\n格位奖励：%s%s" % [data.get("name", ""), reward, "\n已完成" if done else "\n已过期" if bool(item.get("expired", false)) else "\n本季可完成" if ready else ""]
			grid.add_child(art)
		else:
			var empty = Panel.new();empty.custom_minimum_size = Vector2(372, 240)
			var style = StyleBoxFlat.new();style.bg_color = Color(0.12, 0.1, 0.11, 0.35);style.border_color = Color(0.72, 0.65, 0.58, 0.5)
			style.set_border_width_all(2);style.set_corner_radius_all(10);empty.add_theme_stylebox_override("panel", style)
			var hint = ui.label(("本局无此格位" if solo else "等待发布") + "\n第 %s 格 · %s" % [index + 1, reward], 21, ui.MUTED)
			hint.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER;hint.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
			empty.add_child(hint);hint.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
			grid.add_child(empty)
	body.add_child(wrapped("点击卡面可放大查看委托条件；每格奖励印在提示文字中。", 19, ui.MUTED))

func results_inline(parent: Control):
	var frame = GuildRenpyTable.player_surface(ui, parent, Rect2(362, 116, 1546, 906), "Results")
	var game = ui.session.game; var solo = game.get("solo_result") != null and not str(game.get("solo_result", "")).is_empty()
	var title = "单人挑战成功" if game.get("solo_result") == "win" else "单人挑战结束 / 未达成" if solo else "这一段冒险，值得铭记。"
	GuildRenpyTable.caption(ui, frame, title, Rect2(40, 34, 1462, 65), 45).name = "ResultsTitle"
	if solo: GuildRenpyTable.caption(ui, frame, "%s · 文明 %s / 瘴气 %s" % [game.get("solo_rank", ""), int(game.civ), int(game.miasma)], Rect2(40, 108, 1462, 44), 29, ui.GOLD).name = "SoloResultDetails"
	GuildRenpyTable.caption(ui, frame, "第 %s 季  /  %s 位公会长的最终成绩" % [int(game.round), game.players.size()], Rect2(40, 166 if solo else 108, 1462, 35), 23, ui.MUTED)
	var list = VBoxContainer.new();list.add_theme_constant_override("separation", 22)
	GuildRenpyTable.at(frame, ui.scroll(list), Rect2(40, 226 if solo else 166, 1462, 510 if solo else 570))
	for score in game.get("scores", []):
		var row = HBoxContainer.new();row.add_theme_constant_override("separation", 28);row.alignment = BoxContainer.ALIGNMENT_BEGIN
		var card = ui.panel(row, 20);card.custom_minimum_size = Vector2(1462, 128);list.add_child(card)
		var rank = ui.label("%02d" % int(score.rank), 45, ui.GOLD);rank.custom_minimum_size.x = 60;row.add_child(rank)
		var identity = VBoxContainer.new();identity.custom_minimum_size.x = 220;row.add_child(identity)
		var name = ui.label(str(score.get("name", "")).left(12), 30);name.clip_text = true;identity.add_child(name)
		identity.add_child(ui.label(game.get("solo_rank", "") if solo else "本次优胜" if int(score.rank) == 1 else "冒险伙伴", 18, ui.MUTED))
		for category in [["hero", "看板娘"], ["grid", "疆域"], ["loot", "板块"], ["cards", "事件"], ["achievements", "成就"], ["reputation", "额外"], ["treasures", "宝物"], ["retreat", "撤退"]]:
			var column = VBoxContainer.new();column.custom_minimum_size.x = 78;row.add_child(column)
			column.add_child(ui.label(category[1], 17, ui.MUTED));column.add_child(ui.label(str(int(score.get("breakdown", {}).get(category[0], 0))), 28))
		var total = VBoxContainer.new();row.add_child(total);total.add_child(ui.label(str(int(score.get("score", score.get("total", 0)))), 47, ui.GOLD));total.add_child(ui.label("总声望", 16, ui.MUTED))
	var note = "第六轮结束时文明与瘴气相邻即挑战成功；全程可离线游玩。" if solo else "扩展资源声望已计入总分。点击公会可查看持有的宝石、庆典与贡献。"
	GuildRenpyTable.caption(ui, frame, note, Rect2(40, 765, 1462, 35), 20, ui.MUTED).name = "ResultsNote"
	var buttons = HBoxContainer.new();buttons.add_theme_constant_override("separation", 18);GuildRenpyTable.at(frame, buttons, Rect2(40, 826, 1462, 54))
	buttons.add_child(ui.button("查看公会记录", game_log))
	if not ui.session.local_mode and int(ui.session.room.get("host_id", -1)) == ui.session.player_id: buttons.add_child(ui.button("返回房间", func(): ui.session.send({"type": "return_lobby"});ui.close_dialog()))
	buttons.add_child(ui.button("返回主菜单", func(): ui.session.close();ui.close_dialog(), true, true))

func confirm_pass():
	var frame = overlay("稍作确认", Vector2(840, 330), "confirm", false); var body = content(frame, Rect2(48, 100, 744, 180));body.add_child(wrapped("闭店后本季不能继续行动。", 27))
	var row = HBoxContainer.new();body.add_child(row);row.add_child(ui.button("再想一下", func(): ui.close_dialog()))
	row.add_child(ui.button("确认", func(): submit("pass"), ui.session.can_act(), true))

func connect_setup():
	var frame = overlay("连接服务器，找一桌伙伴", Vector2(1030, 800), "connect"); var body = content(frame, Rect2(42, 100, 946, 580))
	body.add_child(wrapped("连接成功后，可创建房间、选择房间或进入观战席。", 23))
	body.add_child(ui.label("公会长昵称 / 重连时请使用原昵称", 23))
	var name_input = LineEdit.new();name_input.text = ui.prefs.name;name_input.max_length = 20;body.add_child(name_input)
	body.add_child(ui.label("游戏服务器", 28, ui.GOLD)); var fields = HBoxContainer.new();body.add_child(fields)
	var address = LineEdit.new();address.text = ui.prefs.address;address.custom_minimum_size = Vector2(610, 62);fields.add_child(address)
	var port = SpinBox.new();port.min_value = 1;port.max_value = 65535;port.value = ui.prefs.port;port.custom_minimum_size = Vector2(190, 62);fields.add_child(port)
	body.add_child(wrapped("默认 guanpeng666.cn:6677 / 修改后在下次连接生效。", 20))
	var row = HBoxContainer.new();body.add_child(row)
	var connect = ui.button("连接服务器", func():
		ui.prefs.name = name_input.text.strip_edges();ui.prefs.address = address.text.strip_edges();ui.prefs.port = int(port.value);ui.save_preferences()
		ui.session.connect_server(ui.prefs.address, ui.prefs.port, ui.prefs.name);ui.close_dialog(), true, true)
	connect.custom_minimum_size.x = 650;row.add_child(connect)
	var cancel = ui.button("返回", func(): ui.session.close();ui.close_dialog());cancel.custom_minimum_size.x = 260;row.add_child(cancel)

func menu(title: String, key: String) -> VBoxContainer:
	var frame = overlay(title, Vector2(1920, 1080), key)
	for node in frame.get_children(): node.queue_free()
	GuildRenpyTable.caption(ui, frame, "异世界", Rect2(94, 80, 245, 45), 27, ui.GOLD);GuildRenpyTable.caption(ui, frame, "公会长", Rect2(94, 125, 245, 60), 42)
	var entries = [["卡牌图鉴", gallery], ["游玩指南", help], ["偏好设置", settings]]
	if not ui.session.game.is_empty(): entries.append(["公会日志", game_log])
	entries.append(["关于作品", about])
	for i in range(entries.size()): GuildRenpyTable.action(ui, frame, entries[i][0], Rect2(72, 245 + i * 73, 230, 65), entries[i][1], true, "Nav_" + entries[i][0])
	GuildRenpyTable.action(ui, frame, "回到主菜单", Rect2(72, 830, 230, 65), leave, not ui.session.game.is_empty())
	GuildRenpyTable.action(ui, frame, "退出游戏", Rect2(72, 907, 230, 65), confirm_quit)
	GuildRenpyTable.caption(ui, frame, title, Rect2(396, 74, 1200, 70), 46, ui.GOLD)
	GuildRenpyTable.action(ui, frame, "返回主菜单" if ui.session.game.is_empty() else "返回对局", Rect2(1638, 80, 200, 49), func(): ui.close_dialog(), true, "ReturnToGame")
	return content(frame, Rect2(396, 182, 1456, 792))

func settings():
	var body = menu("偏好设置", "settings");body.add_child(wrapped("让这间公会，更合你的习惯。", 25))
	body.add_child(ui.label("桌面布局", 30, ui.GOLD))
	var layouts = HBoxContainer.new();body.add_child(layouts)
	for pair in [["经典布局", "classic"], ["总览布局", "dashboard"]]:
		layouts.add_child(ui.button(pair[0], func(): ui.prefs.layout = pair[1];ui.save_preferences();ui.rerender();ui.close_dialog(false);ui.dialogs.settings(), true, ui.prefs.get("layout", "classic") == pair[1]))
	body.add_child(wrapped("总览布局参考所提供的面板位置，沿用当前纸面与配色；切换不影响对局。", 20))
	body.add_child(ui.label("语言 / 語言", 30, ui.GOLD))
	var langs = HBoxContainer.new();body.add_child(langs)
	for pair in [["简体中文", "zh_CN"], ["繁體中文", "zh_TW"]]:
		var active = str(ui.prefs.get("language", "zh_CN")) == pair[1]
		langs.add_child(ui.button(pair[0], func(): ui.set_language(pair[1]);ui.close_dialog(false);ui.dialogs.settings(), true, active))
	body.add_child(wrapped("繁體中文使用「宇文天穹」字型；切換後整個介面立即更新。", 20))
	body.add_child(ui.label("游戏服务器", 28, ui.GOLD)); var fields = HBoxContainer.new();body.add_child(fields)
	var address = LineEdit.new();address.text = ui.prefs.address;address.custom_minimum_size = Vector2(610, 62);fields.add_child(address)
	address.text_changed.connect( func(value): ui.prefs.address = value;ui.save_preferences())
	var port = SpinBox.new();port.min_value = 1;port.max_value = 65535;port.value = ui.prefs.port;port.custom_minimum_size = Vector2(190, 62);fields.add_child(port)
	port.value_changed.connect( func(value): ui.prefs.port = int(value);ui.save_preferences())
	body.add_child(wrapped("默认 guanpeng666.cn:6677 / 修改后在下次连接生效。", 20))
	body.add_child(ui.label("界面动画", 30, ui.GOLD)); var motion = HBoxContainer.new();body.add_child(motion)
	for pair in [["开启", true], ["关闭", false]]:
		var active = bool(ui.prefs.motion) == pair[1]
		motion.add_child(ui.button(pair[0], func():
			ui.prefs.motion = pair[1];ui.save_preferences()
			ui.close_dialog(false);ui.dialogs.settings(), true, active))
	body.add_child(wrapped("将鼠标移到卡牌上，按住 Alt 查看大图；松开后收起。", 23))
	frame_settings(body)
	body.add_child(ui.label("操作提示", 26)); var hints = HBoxContainer.new();body.add_child(hints)
	for pair in [["显示", true], ["收起", false]]:
		var active = bool(ui.prefs.hints) == pair[1]
		hints.add_child(ui.button(pair[0], func():
			ui.prefs.hints = pair[1];ui.save_preferences()
			ui.close_dialog(false);ui.dialogs.settings(), true, active))
	body.add_child(ui.label("声音", 30, ui.GOLD))
	var sound = HBoxContainer.new();body.add_child(sound)
	for pair in [["音效开启", true], ["关闭音效", false]]:
		var active = bool(ui.prefs.sounds) == pair[1]
		sound.add_child(ui.button(pair[0], func():
			ui.prefs.sounds = pair[1];ui.save_preferences()
			if pair[1]: ui.play_sound()
			ui.close_dialog(false);ui.dialogs.settings(), true, active))
	body.add_child(ui.label("音效音量", 23))
	var volume = HSlider.new();volume.min_value = 0;volume.max_value = 1;volume.step = 0.01;volume.value = ui.prefs.sound_volume;body.add_child(volume);volume.value_changed.connect( func(value): ui.prefs.sound_volume = value;ui.save_preferences())
	body.add_child(ui.label("人物配音 · 全角色", 30, ui.GOLD))
	var language_row = HBoxContainer.new();body.add_child(language_row)
	language_row.add_child(ui.label("配音语言", 23))
	for choice in [["日语", "ja"], ["中文", "zh_CN"]]:
		language_row.add_child(ui.button(choice[0], func():
			ui.prefs.voice_language = choice[1];ui.save_preferences();ui.close_dialog(false);ui.dialogs.settings(), true, str(ui.prefs.get("voice_language", "ja")) == choice[1]))
	var voices = HBoxContainer.new();body.add_child(voices)
	for pair in [["配音开启", true], ["配音关闭", false]]:
		voices.add_child(ui.button(pair[0], func(): ui.prefs.voices = pair[1];ui.save_preferences();ui.close_dialog(false);ui.dialogs.settings(), true, bool(ui.prefs.voices) == pair[1]))
	var preview = OptionButton.new();preview.custom_minimum_size.x = 210;voices.add_child(preview)
	var named = {}
	for hero_key in ui.voice.catalog.get("heroes", {}):
		var definition = ui.voice.catalog.heroes[hero_key]
		if named.has(definition.name): continue
		named[definition.name] = true
		preview.add_item(GuildLang.t(definition.name));preview.set_item_metadata(preview.item_count - 1, hero_key)
		if hero_key == "shion_white": preview.select(preview.item_count - 1)
	voices.add_child(ui.button("试听人物", func():
		if preview.selected >= 0: ui.voice.play_event(str(preview.get_item_metadata(preview.selected)), "intro"), bool(ui.prefs.voices)))
	body.add_child(wrapped("配音默认关闭，开启后默认日语，可切换中文。日语优先使用已提供录音，缺少的片段与中文保留角色合成配音。", 18))
	var voice_volume = HSlider.new();voice_volume.min_value = 0;voice_volume.max_value = 1;voice_volume.step = 0.01;voice_volume.value = ui.prefs.voice_volume;body.add_child(voice_volume)
	voice_volume.value_changed.connect(func(value): ui.prefs.voice_volume = value;ui.save_preferences())

func help():
	var body = menu("游玩指南", "help")
	body.add_child(wrapped("经营公会、收集情报、探索迷宫、发展好感度、完成王权。轮到自己时进行行动；关闭公会后等待下一季。", 27))
	body.add_child(wrapped("先点击地图选择板块，再点击「派遣冒险者」。翻开后按服务器给出的费用支付。售卖卡牌不消耗行动，闭店后仍可操作。", 24))
	body.add_child(wrapped("Alt 放大卡片；Esc 打开设置。联机与离线使用相同的原版规则。", 24))
	body.add_child(ui.label("扩充规则", 32, ui.GOLD))
	body.add_child(wrapped("开局时可勾选下列扩充，本局规则随之改变。下面依扩充分别说明。", 21))
	for section in expansion_guide():
		body.add_child(ui.label(section[0], 28, ui.GOLD))
		for entry in section[1]:
			body.add_child(ui.label(entry[0], 23, ui.INK))
			body.add_child(wrapped(entry[1], 21))

func expansion_guide() -> Array:
	return [
		["◆ 魔兽讨伐任务", [
			["讨伐行动", "· 每季供应 2 只魔兽；讨伐支付 2 力量（春、夏季魔兽）或 3 力量（秋、冬季魔兽）。\n· 讨伐成功：获得 1 枚魔兽标记（终局每枚按看板娘等级计分）与该魔兽所属季的奖励——春＝金币产能+5、夏＝力量产能+1、秋＝秘药+1并抽1张事件卡、冬＝无。\n· 单人规则不使用本扩充。"],
		]],
		["◆ 变动板块", [
			["开局设置", "· 一般迷宫的 6 个指定位置（大深度迷宫 5/3 个，依地图大小）放置变动迷宫板块，正面朝下，背面为 2 星。"],
			["板块效果", "· 供应堆共 15 种变动板块，星数、声望与效果各不相同；有的可领取宝箱，有的本身就是深渊洞穴。探索翻开并支付费用后按正面结算。\n· 变动板块是许多「替换板块」类效果的目标：这些效果会从供应堆随机领取新的变动板块放入迷宫。\n· 单人模式：领取变动板块放入迷宫时，瘴气 +1。"],
		]],
		["◆ 都市群像剧", [
			["事件卡", "· 加入 39 张「都市群像剧」事件卡到本局牌库；未开启时这些卡不会出现。打出方式与原版事件卡相同。"],
		]],
		["◆ 旗标碎片", [
			["开局设置", "· 在文明与瘴气之间每隔 5 放置一枚旗标（只放高于当前文明的门槛）。"],
			["领取时机", "· 当你在一次行动中使文明或瘴气到达或越过门槛，立即领取该旗标：未开启公会委托时 +1 声望，开启公会委托时改为 +1 贡献标记。\n· 一次行动可以同时领取多个门槛的旗标，直到旗标领完。"],
		]],
		["◆ 故事之始", [
			["开局设置", "· 每位玩家获得 2 张序章卡。多人免费选择其中 1 张；单人可以选择 0–2 张，每张支付 10 金币。\n· 开启本模块时，初始瘴气为 人数×11（搭配污染领地 人数×13）。"],
			["序章效果", "· 立即获得该序章的资源、标记与一次性效果，例如额外金币、抽牌、发展、查看迷宫等。"],
		]],
		["◆ 污染领地", [
			["开局设置", "· 初始瘴气改为 人数×12（搭配故事之始 人数×13）。"],
			["额外冒险者", "· 第 4 轮季末，每位公会长额外获得 1 名可用冒险者，第 5 轮起可派遣。"],
		]],
		["◆ 冒险者的祭典", [
			["事件卡", "· 加入 14 张庆典事件卡：S级冒险者队伍·勇敢行者、与运输公会的合作、巨兽贝希摩斯的觉醒、讨伐矿石兽、侵占救援物资、方舟遗迹、意外邂逅、魔兽的生态调查、开发魔法炉、加蕾特建筑公司、积分卡、精灵的居住园地、魔力工业联合体、情报贩子琪修。"],
			["庆典准备", "· 开局放置 人数−1 个庆典格位；闭店时领取一个未领取的格位。\n· 前两个格位有额外奖励（3 人以上）：第 1 格＝查看 4 张保留 2 张，第 2 格＝查看 3 张保留 1 张；1–2 人只有第 1 格＝查看 3 张保留 1 张。其余格位领取 1 枚庆典碎片。\n· 每季开始时重新补满空格位（庆典碎片供应有限）。"],
			["庆典碎片", "· 发展公会时可以抵扣条件：1 枚当作 5 金币（单项最多 4 枚）、或 1 力量（最多 3）、或 1 秘药（最多 2）。\n· 终局时未使用的庆典碎片每枚 1 声望。"],
		]],
		["◆ 禁止区域", [
			["开局设置", "· 仅 1–3 人可用，不能与「强制大地图」同时开启。\n· 一般迷宫移除最外一列，大深度迷宫移除外侧斜边；新的边界格变为「禁止进入」板块。"],
			["禁止进入", "· 不能探索、建设、替换；可见星数计算中算 1 星；不计入区域分数。"],
		]],
		["◆ 公会委托", [
			["开局设置", "· 委托板有 6 个（1–2 人）或 9 个（3 人以上）委托格位。"],
			["发布委托", "· 第 1–3 轮，闭店的玩家按闭店顺序获得委托卡：2 人为 4/2 张，3 人以上为前三位闭店者 4/3/2 张；每人从中选择 1 张放上委托板空格。"],
			["达成结算", "· 每季结算与终局时检查未完成的委托：所有达成条件的玩家各获得 1 贡献标记和该格位奖励（金币+3、力量+1、秘药+1、抽牌+2、贡献+1 或无奖励），委托完成并关闭。\n· 委托条件共 29 种（如「商业2＋生活2」「控制区域5」「好感度5」），具体要求见委托卡。"],
			["贡献标记", "· 终局计分：0–1＝0 分、2–3＝1 分、4–5＝2 分、6–7＝4 分、8＝6 分、9＝8 分。\n· 开启公会委托时，文明/瘴气旗标改为发放贡献标记。\n· 单人：委托板固定 6 张委托（不需发布），第 2–4 轮结算，第 4 轮未完成的委托过期。"],
		]],
		["◆ 欧贝拉炼金工房", [
			["炼金药水", "· 开启后解锁炼金药水（秘药行动，费用为秘药数）：\n· 炼金宝石 / 1秘药：金币+2，并获得 1 枚宝石（宝石值 2 声望，可随时以 3 金币售卖）。\n· 炼金召唤 / 2秘药：免金币打出 1 张费用不超过 14 的手牌，其他费用照付。\n· 炼金筑城 / 3秘药（2–4 人）：免费建设 1 座据点，免相邻据点的追加费用。\n· 炼金侦察 / 2秘药（单人与 5 人）：力量+3，并查看 1 块迷宫，可自行决定是否公开。\n· 炼金情报 / 1秘药（5 人）：抽取 2 张事件卡。\n· 未开启时炼金药水不开放（除非另开「开放所有秘药行动」）。"],
		]],
		["◆ 潜行之龙", [
			["开局设置", "· 将潜行之龙标记放在魔王格，龙蛋标记放在地图外侧。\n· 龙蛋数量依人数：2 人 0 颗、3 人 1 颗、4-5 人 2 颗。"],
			["潜行之龙效果", "· 封锁占据格：龙所在格视为封锁，不能探索、建设、替换等。\n· 星数影响：龙所在格在「可见星数」计算中算 3 星，影响探索费用。\n· 移动：每当有人翻开新板块（探索、公开、私下查看后公开），龙就往该板块的方向移动一格；只走无主、非封锁、非魔之森的格子。若同时有多个方向可走，由触发翻开的玩家选择方向。"],
			["讨伐行动", "· 玩家必须控制与龙相邻的区域。\n· 费用：5 ×（3 ＋ 龙相邻格可见星数合计）金币，1 力量可抵 5 金币。\n· 尚有龙蛋时：击破 1 颗蛋，龙标放回魔王格，立即获得一个宝箱，并获得一个龙蛋标记（值 2 名声）。\n· 已无龙蛋时：潜行之龙被永久击败，玩家获得龙标记（值 6 点名声）。\n· 若魔王板块被控制而尚有龙蛋标记，移除所有龙蛋标记（非玩家取得）。"],
		]],
		["◆ 魔之森", [
			["开局设置", "· 将魔之森标记放置在迷宫预设的位置（依迷宫不同而不同）。"],
			["魔之森效果", "· 封锁占据格：魔之森所在格视为封锁，不能探索、建设、替换等。\n· 星数影响：魔之森所在格在「可见星数」计算中算 2 星，影响探索费用。"],
			["净化行动", "· 据点化：当玩家于魔之森周围板块执行据点化行动时，可顺势移除 1 个魔之森标记（一个据点只能移除一个标记），并获得 1 枚庆典碎片。\n· 净化洞穴：支付 2 力量或 1 枚庆典碎片（两种方式每轮各限一次），夺取一个与自己领地相邻、已公开的深渊洞穴板块的宝藏，并将其净化成普通板块。"],
		]],
	]

func about():
	var body = menu("关于作品", "about");body.add_child(wrapped("异世界公会长 4.1.0 · Godot 客户端\n沿用当前 Ren’Py 的操作流程。", 27))

func confirm_quit():
	var frame = overlay("稍作确认", Vector2(840, 400), "confirm", false); var body = content(frame, Rect2(48, 100, 744, 240));body.add_child(wrapped("要离开公会吗？当前单人挑战将结束；联机将断开连接。", 27))
	var row = HBoxContainer.new();body.add_child(row);row.add_child(ui.button("再想一下", func(): ui.close_dialog()));row.add_child(ui.button("确认", func(): ui.session.close();ui.get_tree().quit(), true, true))

func confirm_kick(player: Dictionary):
	var frame = overlay("稍作确认", Vector2(840, 400), "confirm"); var body = content(frame, Rect2(48, 100, 744, 240));body.add_child(wrapped("将%s移出房间？" % player.name, 27))
	var row = HBoxContainer.new();body.add_child(row);row.add_child(ui.button("再想一下", func(): ui.close_dialog()));row.add_child(ui.button("确认", func(): ui.session.send({"type": "kick", "target_id": int(player.id)});ui.close_dialog(), true, true))

func hero_detail(player: Dictionary): _hero_detail(player, 0)

func _hero_detail(player: Dictionary, rank: int):
	var hero = ui.store.catalog.heroes.get(player.get("hero", ""), {}); var frame = overlay(hero.get("name", "") + " / " + hero.get("subtitle", ""), Vector2(1160, 870), "hero")
	var body = content(frame, Rect2(32, 94, 1096, 702)); var row = HBoxContainer.new();body.add_child(row)
	for i in range(3): row.add_child(ui.button("等级 %s" % (i + 1), func(): _hero_detail(player, i)))
	var sources = hero.get("source", [])
	if not sources.is_empty(): body.add_child(ui.card(sources[min(rank, sources.size() - 1)], Vector2(716, 510)))
	body.add_child(wrapped(hero.get("description", ""), 20))

func guest_picker():
	var guests = maxi(0, int(ui.session.room.get("max_players", 1)) - 1)
	var frame = overlay("客座模式", Vector2(700, 640), "guests")
	GuildRenpyTable.caption(ui, frame, "选择与你轮流操作的客座玩家数量（目前 %s 位）" % guests, Rect2(32, 62, 636, 40), 22, ui.GOLD)
	for i in range(5):
		var count = i
		GuildRenpyTable.action(ui, frame, ["不使用（单人）", "1 位客座", "2 位客座", "3 位客座", "4 位客座"][i], Rect2(52, 122 + i * 84, 596, 68), func(): ui.session.send({"type": "set_guests", "count": count});ui.close_dialog();ui.rerender(), true, "GuestCount" + str(i))

func load_picker():
	var saves = ui.session.room.get("saves", [])
	var frame = overlay("读取进度", Vector2(700, 740), "saves")
	GuildRenpyTable.caption(ui, frame, "选择要读取的存档（共 %s 份）" % saves.size(), Rect2(32, 62, 636, 40), 22, ui.GOLD)
	if saves.is_empty():
		GuildRenpyTable.caption(ui, frame, "还没有存档。先开始一局，再在游戏内左侧使用「存档」。", Rect2(32, 116, 636, 60), 20, ui.MUTED)
	var count = mini(saves.size(), 8)
	for i in range(count):
		var index = i
		var entry = saves[index]
		var save_name = str(entry.name) if entry is Dictionary else str(entry)
		var info = "读取 · " + save_name.trim_suffix(".json")
		if entry is Dictionary:
			var title = str(entry.get("title", "")).strip_edges()
			if title.is_empty(): title = save_name.trim_suffix(".json")
			if title.length() > 16: title = title.left(16) + "…"
			info = "%s（%s · %s · %s 人）" % [title, str(entry.get("time", "")), str(entry.get("phase", "")), str(entry.get("seats", 1))]
		GuildRenpyTable.action(ui, frame, info, Rect2(52, 116 + i * 72, 596, 62), func(): ui.session.send({"type": "load_game", "name": save_name});ui.close_dialog(), true, "Load" + str(index))

func save_picker():
	var frame = overlay("保存进度", Vector2(760, 430), "save")
	var body = content(frame, Rect2(32, 103, 696, 270))
	body.add_child(wrapped("为这一局取一个名字；存档会在名称后面自动补上时间。", 21, ui.MUTED))
	var name_input = LineEdit.new();name_input.name = "SaveName";name_input.placeholder_text = GuildLang.t("例如：第一次冒险");name_input.text = "存档";name_input.max_length = 32
	body.add_child(name_input)
	body.add_child(ui.button("保存", func():
		ui.session.send({"type": "save_game", "name": name_input.text})
		ui.close_dialog(), true, true))
	body.add_child(wrapped("离线模式最多保留最近 20 份存档。", 18, ui.MUTED))

func player_names():
	var players = ui.session.room.get("players", [])
	var frame = overlay("玩家昵称 · 客座模式", Vector2(800, 720), "names")
	var body = content(frame, Rect2(32, 103, 736, 550))
	body.add_child(wrapped("客座模式由你轮流操作所有席位；这里可以为每一位玩家分别设定昵称。", 21, ui.MUTED))
	var fields = {}
	for i in range(players.size()):
		var player = players[i]
		var row = HBoxContainer.new();row.add_theme_constant_override("separation", 14);body.add_child(row)
		var tag = ui.label("P%s" % (int(player.get("id", i)) + 1), 25, ui.GOLD);tag.custom_minimum_size.x = 58;row.add_child(tag)
		var edit = LineEdit.new();edit.name = "PlayerName" + str(int(player.get("id", i)));edit.text = str(player.get("name", ""));edit.max_length = 20;edit.placeholder_text = GuildLang.t("玩家昵称");edit.size_flags_horizontal = Control.SIZE_EXPAND_FILL;row.add_child(edit)
		fields[str(player.get("id", i))] = edit
	body.add_child(ui.button("保存全部昵称", func():
		var names = {}
		for key in fields: names[key] = fields[key].text
		ui.session.send({"type": "rename_players", "names": names})
		ui.close_dialog(), true, true))

func quest_report(report: Dictionary):
	var items = report.get("items", [])
	if not items is Array: items = []
	var frame = overlay("公会委托 · 季结算公告", Vector2(900, 800), "quest_report", false)
	var body = content(frame, Rect2(32, 103, 836, 650))
	body.add_child(wrapped("第 %s 季结算 · 委托板完成公告" % int(report.get("round", 1)), 30, ui.GOLD))
	body.add_child(wrapped("本季结算时，以下公会长完成了公告板上的委托：", 22))
	if items.is_empty():
		body.add_child(wrapped("本季没有公会委托被完成。", 24, ui.MUTED))
	for item in items:
		var reward = str(item.get("reward", "无额外奖励"))
		body.add_child(wrapped("◆ %s 完成《%s》 → 贡献 +1、%s" % [str(item.get("player", "")), str(item.get("quest", "")), reward], 24))
	body.add_child(wrapped("每份完成的委托会让完成者获得 1 贡献标记与该格位奖励；委托完成并关闭。", 19, ui.MUTED))
	body.add_child(ui.button("继续", func(): ui.close_dialog(), true, true))

func seat_change(player_id: int):
	var player = {}
	for seat in ui.session.game.get("players", []):
		if int(seat.get("id", -1)) == player_id: player = seat;break
	if player.is_empty(): return
	var hero = ui.store.catalog.heroes.get(player.get("hero", ""), {})
	var frame = overlay("换人公告", Vector2(780, 470), "seat", false)
	var body = content(frame, Rect2(32, 103, 716, 310))
	body.add_child(wrapped("轮到 %s 行动。" % ("P%s %s" % [player_id + 1, str(player.get("name", ""))]), 32, ui.GOLD))
	if not hero.is_empty(): body.add_child(wrapped("看板娘：%s" % hero.get("name", ""), 23))
	body.add_child(wrapped("客座模式请确认桌面已经交给这位玩家，再按继续。", 21, ui.MUTED))
	body.add_child(ui.button("确认换人 · 继续", func(): ui.close_dialog(), true, true))

func treasure_icon(key: String, points: int = 40) -> Control:
	if key == "tags": return ui.picture(load("res://ui/symbols/knowledge.svg"), points)
	return ui.symbol({"fame": "point", "industry": "gold_pro", "alchemy": "pot_pro", "potions": "pot"}.get(key, "point"), points)

func titled_rule(text: String) -> Control:
	var row = HBoxContainer.new();row.add_theme_constant_override("separation", 12)
	row.add_child(ui.label(text, 24, ui.GOLD))
	var rule = ColorRect.new();rule.color = Color(ui.GOLD.r, ui.GOLD.g, ui.GOLD.b, 0.45)
	rule.custom_minimum_size = Vector2(0, 2);rule.size_flags_horizontal = Control.SIZE_EXPAND_FILL;rule.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	rule.mouse_filter = Control.MOUSE_FILTER_IGNORE;row.add_child(rule)
	return row

func player_detail(player: Dictionary):
	var frame = overlay(player.name + " / 公会总览", Vector2(1310, 990), "player"); var body = content(frame, Rect2(32, 98, 1246, 820))
	body.add_child(wrapped("当前声望 %s    手牌 %s / 已打出 %s / 撤退 %s" % [int(player.get("score", 0)), int(player.get("hand_count", 0)), player.get("played", []).size(), int(player.get("retreat", 0))], 30))
	var top = HBoxContainer.new();body.add_child(top); var hero = ui.store.catalog.heroes.get(player.hero, {})
	top.add_child(ui.card(hero.get("source", [""])[0], Vector2(294, 210), func(): hero_detail(player)))
	var stocks = VBoxContainer.new();top.add_child(stocks);stocks.add_child(GuildTableView.resources(ui, player, false));stocks.add_child(GuildTableView.resources(ui, player, true))
	var tags = HBoxContainer.new();tags.add_theme_constant_override("separation", 36);top.add_child(tags)
	var marks = VBoxContainer.new();marks.add_theme_constant_override("separation", 6);tags.add_child(marks)
	marks.add_child(ui.label("标记", 18, ui.MUTED))
	var counts = player.get("tag_counts", {})
	var tag_grid = GridContainer.new();tag_grid.columns = 2;tag_grid.add_theme_constant_override("h_separation", 18);tag_grid.add_theme_constant_override("v_separation", 4);marks.add_child(tag_grid)
	for key in ["civ", "gold", "scrap", "character"]:
		var texture = ui.store.texture("images/ui/icon_" + key + ".png")
		if texture == null:
			tag_grid.add_child(ui.label(ui.store.catalog.tag_names.get(key, key) + " %s" % int(counts.get(key, 0)), 20))
			continue
		var cell = HBoxContainer.new();cell.add_theme_constant_override("separation", 6)
		cell.tooltip_text = GuildLang.t(ui.store.catalog.tag_names.get(key, key))
		cell.mouse_filter = Control.MOUSE_FILTER_STOP
		cell.add_child(ui.picture(texture, 26))
		cell.add_child(ui.label(str(int(counts.get(key, 0))), 20))
		tag_grid.add_child(cell)
	var treasures = VBoxContainer.new();treasures.add_theme_constant_override("separation", 6);tags.add_child(treasures)
	treasures.add_child(ui.label("已获宝物", 18, ui.MUTED))
	var owned = player.get("treasures", [])
	var treasure_row = HBoxContainer.new();treasure_row.add_theme_constant_override("separation", 16);treasures.add_child(treasure_row)
	if owned.is_empty(): treasure_row.add_child(ui.label("尚未获得宝物", 18, ui.MUTED))
	for key in owned:
		var reward = ui.session.game.get("treasure_rewards", {}).get(key, {})
		var entry = HBoxContainer.new();entry.add_theme_constant_override("separation", 6)
		entry.tooltip_text = GuildLang.t(reward.get("description", reward.get("name", key)));entry.mouse_filter = Control.MOUSE_FILTER_STOP
		entry.add_child(treasure_icon(key, 26))
		entry.add_child(ui.label(str(reward.get("name", key)), 20))
		treasure_row.add_child(entry)
	var actions = VBoxContainer.new();top.add_child(actions)
	if int(ui.session.room.get("host_id", -1)) == ui.session.player_id and int(player.id) != ui.session.player_id and not ui.session.local_mode: actions.add_child(ui.button("踢出玩家", func(): confirm_kick(player)))
	var card_size = Vector2(148, 185)
	var story_size = Vector2(294, 210)
	body.add_child(ui.label("序章卡", 24, ui.GOLD))
	var stories = GridContainer.new();stories.columns = 4;stories.add_theme_constant_override("h_separation", 12);stories.add_theme_constant_override("v_separation", 12);body.add_child(stories)
	var prologue = player.get("prologue", [])
	if prologue.is_empty(): stories.add_child(ui.label("尚未选择序章", 20, ui.MUTED))
	for key in prologue:
		var story = ui.store.catalog.prologues.get(str(int(key)), {})
		stories.add_child(ui.card(story.get("source", ""), story_size, func(): art_detail(story.get("source", ""), story.get("name", "序章"))))
	body.add_child(ui.label("已打出卡牌", 24, ui.GOLD))
	var grid = GridContainer.new();grid.columns = 6;grid.add_theme_constant_override("h_separation", 12);grid.add_theme_constant_override("v_separation", 12);body.add_child(grid)
	for i in range(player.get("played", []).size()):
		var number = int(player.played[i]); var data = ui.store.card(number);grid.add_child(ui.card(ui.store.card_face(data), card_size, func(): card_detail(number)))
	body.add_child(titled_rule("已打出的王权卡"))
	var royals = GridContainer.new();royals.columns = 6;royals.add_theme_constant_override("h_separation", 12);royals.add_theme_constant_override("v_separation", 12);body.add_child(royals)
	var earned = player.get("earned_achievements", [])
	if earned.is_empty(): royals.add_child(ui.label("尚未打出王权卡", 20, ui.MUTED))
	for key in earned:
		var royal = ui.store.catalog.achievements.get(key, {})
		royals.add_child(ui.card(royal.get("source", ""), card_size, func(): art_detail(royal.get("source", ""), royal.get("name", "王权"))))
	body.add_child(titled_rule("全部持有板块与卡牌上的板块"))
	var tiles_grid = GridContainer.new();tiles_grid.columns = 6;tiles_grid.add_theme_constant_override("h_separation", 12);tiles_grid.add_theme_constant_override("v_separation", 12);body.add_child(tiles_grid)
	var owned_tiles = player.get("tiles", []) + player.get("hero_tiles", [])
	if owned_tiles.is_empty(): tiles_grid.add_child(ui.label("尚无持有板块", 20, ui.MUTED))
	for key in owned_tiles:
		var tile = ui.store.catalog.tiles.get(key, {})
		tiles_grid.add_child(ui.card(tile.get("source", ""), card_size, func(): art_detail(tile.get("source", ""), tile.get("name", "迷宫板块"))))

func player_royals(player: Dictionary):
	var frame = overlay(player.name + " / 已打出的王权卡", Vector2(1120, 820), "royals"); var body = content(frame, Rect2(32, 100, 1056, 670))
	for key in player.get("earned_achievements", []):
		var data = ui.store.catalog.achievements.get(key, {});body.add_child(ui.card(data.get("source", ""), Vector2(180, 252), func(): art_detail(data.get("source", ""), data.get("name", "王权"))))

func growth(player: Dictionary):
	var frame = overlay(player.name + " / 序章与成长", Vector2(1280, 880), "growth"); var body = content(frame, Rect2(32, 108, 1216, 690)); var row = HBoxContainer.new();row.add_theme_constant_override("separation", 18);body.add_child(row)
	for item in [["gold", "金币", "支付20金币"], ["strength", "力量", "支付3力量"], ["pot", "秘药", "支付2秘药"], ["territory", "疆域", "控制3个区域"], ["cards", "情报", "打出8张事件"]]:
		var column = VBoxContainer.new(); var panel = ui.panel(column, 15);panel.custom_minimum_size = Vector2(222, 112);row.add_child(panel);column.add_child(ui.label(item[1], 26));column.add_child(ui.label("已解锁" if player.get("developed", []).has(item[0]) else item[2], 20))
	body.add_child(ui.label("已选择的序章", 27, ui.GOLD)); var stories = HBoxContainer.new();body.add_child(stories)
	for key in player.get("prologue", []):
		var data = ui.store.catalog.prologues.get(str(int(key)), {});stories.add_child(ui.card(data.get("source", ""), Vector2(300, 420), func(): art_detail(data.get("source", ""), data.get("name", "序章"))))
	if stories.get_child_count() == 0: stories.add_child(wrapped("尚未选择序章", 25))
	body.add_child(ui.button("人物卡附属板块 %s / 查看全部板块" % player.get("hero_tiles", []).size(), func(): tiles(player)))

func _choice_button(text: String, callback: Callable, width: float) -> Button:
	# 结算窗口内的一般选项钮：限宽防溢出，字过长时自动缩小字号（与选牌右栏同手法）。
	var node = ui.button(text, callback)
	node.custom_minimum_size = Vector2(width, 46)
	var font: Font = ui.theme.default_font
	var points = 20
	while points > 13 and font.get_string_size(node.text, HORIZONTAL_ALIGNMENT_LEFT, -1, points).x + 80.0 > width:
		points -= 1
	node.add_theme_font_size_override("font_size", points)
	if points <= 13: node.clip_text = true;node.text_overrun_behavior = TextServer.OVERRUN_TRIM_ELLIPSIS
	return node

func pending(pending: Dictionary):
	var frame = overlay("结算卡牌效果", Vector2(1450, 940), "pending");ui.pending_id = int(pending.id)
	var options = pending.get("options", []); var cache = ui.choice_states.get(str(ui.pending_id), {"selected": [], "strength": 0, "pot": 0, "flash": false, "lab": false})
	ui.choice_states = {str(ui.pending_id): cache}; var selected = cache.selected
	GuildRenpyTable.caption(ui, frame, pending.get("title", "结算卡牌效果"), Rect2(32, 65, 880, 45), 30)
	GuildRenpyTable.caption(ui, frame, "按顺序完成选择后，游戏会继续；私人选项不会发送给观战者。", Rect2(32, 114, 1384, 30), 20, ui.MUTED)
	GuildRenpyTable.action(ui, frame, "撤回上一步", Rect2(1082, 66, 150, 49), func(): ui.undo(), ui.session.game.get("undo", {}).get("available", false), "ChoiceUndo")
	var choices = VBoxContainer.new(); var scroller = ui.scroll(choices);GuildRenpyTable.at(frame, scroller, Rect2(32, 166, 990, 656), "ChoiceCards")
	ui.preserve_selection_scroll(scroller, "pending", JSON.stringify([pending.id, options]))
	var preview = ""
	for option in options:
		if not str(option.get("preview", "")).is_empty(): preview = str(option["preview"]);break
	if not preview.is_empty():
		var holder = HBoxContainer.new();holder.alignment = BoxContainer.ALIGNMENT_CENTER
		holder.add_child(ui.card(preview, Vector2(276, 386)));choices.add_child(holder)
	var grid = GridContainer.new();grid.columns = 4;grid.add_theme_constant_override("h_separation", 14);grid.add_theme_constant_override("v_separation", 14);choices.add_child(grid)
	var choose = func(index):
		if selected.has(index): selected.erase(index)
		elif int(pending.get("max", 1)) == 1: selected.clear();selected.append(index)
		elif selected.size() < int(pending.get("max", 1)): selected.append(index)
		self.pending(pending)
	var board_options = options.filter( func(option): return option.get("board", false))
	var treasure_options = options.any( func(option): return option.get("value") is String and ui.session.game.get("treasures_available", []).any( func(item): return item.get("id") == option.get("value")))
	if treasure_options: grid.columns = 3
	if not board_options.is_empty():
		var map = GuildHexMap.new();map.store = ui.store;map.selection_only = true;map.motion = ui.prefs.motion;map.custom_minimum_size = Vector2(990, 656);map.renpy_geometry = true
		var snapshot = ui.session.game.duplicate(true)
		for i in range(options.size()):
			if not options[i].get("board", false): continue
			var id = str(int(options[i].q)) + "," + str(int(options[i].r));map.option_ids[id] = i
			if not snapshot.board.any( func(cell): return cell.id == id): snapshot.board.append({"id": id, "q": int(options[i].q), "r": int(options[i].r), "owner": null, "region": 0, "outer": true})
		map.chosen_ids = []
		for i in selected: map.chosen_ids.append(str(int(options[i].q)) + "," + str(int(options[i].r)))
		map.set_game(snapshot, ui.session.player_id);choices.add_child(map);map.cell_clicked.connect( func(cell): if map.option_ids.has(cell.id): choose.call(map.option_ids[cell.id]))
	else:
		for i in range(options.size()):
			var option = options[i]
			if treasure_options: grid.add_child(treasure_choice(option, selected.has(i), func(): choose.call(i)))
			elif not option.get("image", "").is_empty():
				var image = str(option.image)
				var option_card = int(option.get("card", -1))
				if option_card >= 0:
					var option_data = ui.store.card(option_card)
					if not option_data.is_empty() and not str(option_data.get("source", "")).is_empty(): image = ui.store.card_face(option_data)
				var art = ui.card(image, Vector2(228, 305), func(): choose.call(i));art.name = "ChoiceCard" + str(i);art.selected = selected.has(i);grid.add_child(art)
			else: grid.add_child(_choice_button(option.get("label", "选项"), func(): choose.call(i), (990.0 - 14.0 * (grid.columns - 1)) / grid.columns))
	var payment = pending.get("payment", {})
	if options.is_empty() and payment.has("target_image"): choices.add_child(ui.card(payment.target_image, Vector2(620, 530)))
	var side = content(frame, Rect2(1052, 173, 364, 650))
	side.add_child(ui.button("查看我的公会总览", func(): player_detail(ui.session.me())))
	if not pending.get("payment", {}).is_empty() and ui.session.me().get("strength_as_gold", false): side.add_child(ui.button("金币费用的力量折抵", payment_preference))
	if int(pending.get("max", 0)) > 0: side.add_child(ui.label("已选 %s / %s" % [selected.size(), int(pending.max)], 26, ui.GOLD));side.add_child(wrapped("至少选择 %s 项" % int(pending.get("min", 0)), 20))
	var limits = GuildRenpyLogic.payment_limits(payment, selected, int(cache.strength), int(cache.pot), cache.flash);cache.strength = limits[2];cache.pot = limits[3]
	if payment.get("target", false):
		side.add_child(wrapped("目标：" + payment.get("target_name", "迷宫"), 23));side.add_child(wrapped("板块已公开；费用不足则声望 -1。", 20))
		var gold = int(payment.get("gold_flash" if cache.flash else "gold_base", 0))
		side.add_child(ui.label("本次需付 %s 金币" % max(0, gold - 5 * (cache.strength + cache.pot * int(payment.get("potion_strength", 0)) + (selected.size() if payment.get("tiles_as_strength", false) else 0))), 26, ui.GOLD))
	if int(payment.get("strength_max", 0)) > 0: adjust(side, "力量", limits[0], cache.strength, func(value): cache.strength = value;self.pending(pending))
	if int(payment.get("pot_max", 0)) > 0: adjust(side, "秘药", limits[1], cache.pot, func(value): cache.pot = value;self.pending(pending))
	if payment.get("flash", false): side.add_child(ui.button("● 使用一闪" if cache.flash else "使用一闪", func(): cache.flash = not cache.flash;self.pending(pending)))
	if payment.get("lab", false): side.add_child(ui.button("● 派遣浮空实验室" if cache.lab else "派遣浮空实验室", func(): cache.lab = not cache.lab;self.pending(pending)))
	var ready = ui.session.can_choose() and selected.size() >= int(pending.get("min", 0)) and selected.size() <= int(pending.get("max", 1))
	if payment.get("tiles_as_strength", false): ready = ready and selected.size() <= ceili(float(payment.get("gold_flash" if cache.flash else "gold_base", 0)) / 5)
	side.add_child(ui.button("确认并继续", func(): ui.session.action("choice", {"choice_id": int(pending.id), "selected": selected.duplicate(), "skip": false, "action": {"strength": int(cache.strength), "pot": int(cache.pot), "flash": cache.flash, "lab": cache.lab}}), ready, true))
	if str(pending.get("title", "")).begins_with("选择序章"):
		# 选择序章时，在选项下方列出本人手牌供参考（点击查看卡牌详情）。
		var hand = ui.session.me().get("hand", [])
		if not hand.is_empty():
			choices.add_child(ui.label("我的手牌（%s 张）· 供选择序章时参考" % hand.size(), 24, ui.GOLD))
			var hand_grid = GridContainer.new();hand_grid.columns = 4;hand_grid.add_theme_constant_override("h_separation", 14);hand_grid.add_theme_constant_override("v_separation", 14)
			for number in hand:
				var data = ui.store.card(int(number))
				var face = ui.store.card_face(data)
				hand_grid.add_child(ui.card(face, Vector2(228, 305), func(): art_detail(face, data.get("name", "事件卡"))))
			choices.add_child(hand_grid)
	if pending.get("optional", false): side.add_child(ui.button("跳过此效果", func(): ui.session.action("choice", {"choice_id": int(pending.id), "selected": [], "skip": true, "action": {"strength": 0, "pot": 0, "flash": false, "lab": false}}), ui.session.can_choose()))
	GuildRenpyTable.action(ui, frame, "售卖卡牌 / 不消耗行动", Rect2(662, 859, 260, 49), market, ui.session.can_free_action(), "ChoiceMarket")
	GuildRenpyTable.action(ui, frame, "卖1秘药 / +%s金币" % int(ui.session.game.get("exchange_rate", 3)), Rect2(1102, 859, 280, 49), func(): ui.session.action("exchange", {"amount": 1}), ui.session.can_free_action() and int(ui.session.me().get("pot", 0)) > 0, "ChoiceExchange")

func treasure_choice(option: Dictionary, selected: bool, callback: Callable) -> Button:
	var reward = {}
	for item in ui.session.game.get("treasures_available", []):
		if item.get("id") == option.get("value"): reward = item;break
	var node = ui.button("", callback, true, selected);node.name = "Treasure_" + str(option.get("value", ""));node.custom_minimum_size = Vector2(310, 238)
	_rounded_option(node, selected)
	var column = VBoxContainer.new();node.add_child(column);column.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	column.offset_left = 16;column.offset_right = -16;column.offset_top = 14;column.offset_bottom = -14;column.add_theme_constant_override("separation", 14)
	column.add_child(ui.label(("已选择 · " if selected else "") + option.get("label", "宝物奖励"), 25, Color("4a3210") if selected else ui.INK))
	var icons = HBoxContainer.new();icons.add_theme_constant_override("separation", 12);column.add_child(icons)
	for key in ["point", "gold", "strength", "pot", "gold_pro", "str_pro", "pot_pro"]:
		if int(reward.get(key, 0)) != 0:
			icons.add_child(ui.symbol(key, 32));icons.add_child(ui.label("+%s" % int(reward[key]), 24, Color("4a3210") if selected else ui.INK))
	var description = option.get("description", "")
	if not reward.get("tags", []).is_empty():
		var tags = []
		for tag in reward.tags: tags.append(ui.store.catalog.tag_names.get(tag, tag))
		description = description.replace("三种标记各 +1", "、".join(tags) + "标记各 +1")
	var detail = wrapped(description.replace(" / ", "\n"), 22, Color("4a3210") if selected else ui.INK);detail.name = "RewardDescription";column.add_child(detail)
	ignore_mouse(column)
	return node

func ignore_mouse(node: Control):
	node.mouse_filter = Control.MOUSE_FILTER_IGNORE
	for child in node.get_children():
		if child is Control: ignore_mouse(child)

func achievements():
	royal_strength = 0;_achievements()

func _achievements():
	var me = ui.session.me(); var frame = overlay("王权成就", Vector2(1200, 880), "achievements"); var body = content(frame, Rect2(32, 102, 1136, 730))
	if not me.is_empty(): adjust(body, "可折抵目标投入战力", int(me.get("strength", 0)), royal_strength, func(value): royal_strength = value;_achievements())
	body.add_child(wrapped("仅带战力折抵标识的目标使用这笔战力，其他目标仍支付金币。", 19))
	for public in [true, false]:
		body.add_child(ui.label("公开成就 / 完成额外获得 1 声望" if public else "私人目标 / 未完成不计分", 25, ui.GOLD))
		for key in ui.session.game.get("public_achievements", []) if public else me.get("achievements", []):
			var data = ui.store.catalog.achievements.get(key, {}); var row = HBoxContainer.new();row.add_theme_constant_override("separation", 22)
			var ready = GuildRenpyLogic.achievement_ready(me, ui.session.game, ui.store.catalog, data, royal_strength)
			var panel = ui.panel(row, 20);body.add_child(panel)
			var frame_style = StyleBoxFlat.new();frame_style.set_border_width_all(2);frame_style.set_corner_radius_all(16)
			frame_style.content_margin_left = 20;frame_style.content_margin_right = 20;frame_style.content_margin_top = 20;frame_style.content_margin_bottom = 20
			if ready:
				frame_style.bg_color = Color("fdf6e4");frame_style.border_color = Color("c39a4d")
			else:
				frame_style.draw_center = false;frame_style.border_color = Color("6b6460")
			panel.add_theme_stylebox_override("panel", frame_style)
			row.add_child(ui.card(data.get("source", ""), Vector2(93, 130), func(): art_detail(data.get("source", ""), data.get("name", "王权"))))
			var descriptions = VBoxContainer.new();descriptions.custom_minimum_size.x = 660;row.add_child(descriptions);descriptions.add_child(ui.label(data.get("name", key), 27));descriptions.add_child(wrapped(data.get("description", ""), 21));descriptions.add_child(wrapped("支付 %s 金币 / 声望 %s" % [int(data.get("price", 0)), int(data.get("point", 0))], 21))
			if ready: descriptions.add_child(ui.label("◆ 条件与费用均已满足 / 可达成", 20, Color("8a6a1f")))
			var buttons = VBoxContainer.new();row.add_child(buttons); var used = min(royal_strength, GuildRenpyLogic.strength_cap(data, me)) if data.get("can_trans", false) else 0
			buttons.add_child(ui.button("达成成就 / 抵扣%s力" % used if data.get("can_trans", false) else "达成成就", func(): ui.session.action("achievement", {"id": key, "public": public, "strength": used}), ui.session.can_act(), ready))
			if not public: buttons.add_child(ui.button("放弃 / 获得 5 金币", func(): confirm_discard_royal(key)))

func confirm_discard_royal(key: String):
	var body = content(overlay("稍作确认", Vector2(840, 330), "confirm"), Rect2(48, 100, 744, 180));body.add_child(wrapped("放弃这个私人目标，立即获得 5 金币？", 27))
	var row = HBoxContainer.new();body.add_child(row);row.add_child(ui.button("再想一下", func(): _achievements()));row.add_child(ui.button("确认", func(): ui.session.action("discard_achievement", {"id": key});_achievements(), true, true))

func chat():
	var body = content(overlay("房间聊天", Vector2(900, 760), "chat"), Rect2(32, 102, 834, 600))
	for item in ui.session.room.get("chat", []): body.add_child(wrapped(item.get("name", "访客") + "： " + item.get("message", ""), 23))
	if ui.session.local_mode: body.add_child(wrapped("本地练习不连接聊天室。", 23));return
	var field = LineEdit.new();field.max_length = 180;body.add_child(field)
	var send = func():
		if not field.text.strip_edges().is_empty(): ui.session.send({"type": "chat", "message": field.text.strip_edges()});field.clear()
	body.add_child(ui.button("发送", send, true, true));field.text_submitted.connect( func(_text): send.call())

func leave():
	var body = content(overlay("稍作确认", Vector2(840, 400), "confirm"), Rect2(48, 100, 744, 240));body.add_child(wrapped("离开房间？席位会显示为断线；轮到你时可在房间设定的等待时间内用原昵称重连。", 27))
	var row = HBoxContainer.new();body.add_child(row);row.add_child(ui.button("再想一下", func(): ui.close_dialog()))
	row.add_child(ui.button("确认", func():
		ui.session.leave_room()
		ui.close_dialog(), true, true))

func game_log():
	var body = menu("公会日志", "history")
	for entry in ui.session.game.get("log", []): body.add_child(wrapped(entry.get("message", ""), 23))

func refresh_snapshot():
	if not is_instance_valid(ui): return
	if ui.modal_key == "market": market()
	elif ui.modal_key == "potions": _potions()
	elif ui.modal_key == "develop": _develop()
	elif ui.modal_key == "achievements": _achievements()
	elif ui.modal_key == "chat": chat()
	elif ui.modal_key == "treasures": treasures()
