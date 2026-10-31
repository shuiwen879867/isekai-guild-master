class_name GuildDialogs
extends RefCounted

var ui

func chat():
	var body = ui.open_dialog("房间聊天", Vector2(780, 510))
	if ui.session.local_mode: body.add_child(wrapped("当前为离线单人挑战。"));return
	var list = VBoxContainer.new();body.add_child(ui.scroll(list)); var entries = ui.session.room.get("chat", [])
	for entry in entries: list.add_child(wrapped(str(entry), 18))
	var input = LineEdit.new();input.placeholder_text = GuildLang.t("和公会伙伴说些什么…");body.add_child(input)
	var send = func():
		if input.text.strip_edges().is_empty(): return
		ui.session.send({"type": "chat", "message": input.text});list.add_child(wrapped(ui.session.nickname + "：" + input.text, 18, ui.INK));input.clear()
	body.add_child(ui.button("发送", send));input.text_submitted.connect( func(_text): send.call())

func special_actions():
	var body = ui.open_dialog("公会行动与扩展", Vector2(800, 660)); var me = ui.session.me(); var hero = ui.store.catalog.heroes.get(me.get("hero", ""), {})
	if hero.has("source"): body.add_child(ui.card(hero.source[0], Vector2(740, 270), func(): hero_detail(me)))
	body.add_child(ui.button("看板娘特别行动", hero_ability, ui.session.can_act() and not hero.get("ability", {}).is_empty() and not me.get("used", []).has("ability"), true))
	body.add_child(ui.button("扩充行动", expansions, ui.session.can_act()))

func game_log():
	var body = ui.open_dialog("公会记录", Vector2(980, 790)); var list = VBoxContainer.new();body.add_child(ui.scroll(list))
	for entry in ui.session.game.get("log", []): list.add_child(wrapped(entry.get("message", ""), 19, ui.INK))

func wrapped(text: String, size: int = 19, color: Color = Color("5b5860")) -> Label:
	var node = ui.label(text, size, color);node.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART;return node

func integer_row(parent: Control, title: String, maximum: int, value: int = 0, kind: String = "") -> SpinBox:
	var row = HBoxContainer.new();parent.add_child(row)
	if not kind.is_empty(): row.add_child(ui.symbol(kind, 32))
	var title_node = ui.label(title, 19);title_node.size_flags_horizontal = Control.SIZE_EXPAND_FILL;row.add_child(title_node)
	var spin = SpinBox.new();spin.min_value = 0;spin.max_value = maximum;spin.step = 1;spin.value = value;spin.custom_minimum_size.x = 140;row.add_child(spin);return spin

func toggle(parent: Control, title: String, value: bool) -> CheckButton:
	var check = CheckButton.new();check.text = GuildLang.t(title);check.button_pressed = value;parent.add_child(check);return check

func hero_draw_row(parent: Control, value: int, id: String) -> OptionButton:
	var row = HBoxContainer.new();parent.add_child(row)
	var title = ui.label("角色候选张数", 19);title.size_flags_horizontal = Control.SIZE_EXPAND_FILL;row.add_child(title)
	var picker = OptionButton.new();picker.name = id;picker.custom_minimum_size.x = 160
	for count in range(1, 6): picker.add_item(GuildLang.t("%s 张" % count), count)
	picker.select(clampi(value, 1, 5) - 1);row.add_child(picker);return picker

func refresh_hero_draw(picker: OptionButton, hint: Label, players: int, banned: Array = []) -> int:
	var limit = GuildRoomSetup.candidate_limit(ui.store.catalog, players, banned)
	for index in range(5): picker.set_item_disabled(index, index >= limit)
	if limit > 0 and picker.get_selected_id() > limit: picker.select(limit - 1)
	hint.text = "可用角色 %s 名 · 每位最多 %s 张候选" % [GuildRoomSetup.character_pool(ui.store.catalog, banned).size(), limit]
	picker.disabled = limit < 1
	return limit

func submit(kind: String, args: Dictionary = {}):
	ui.session.action(kind, args);ui.close_dialog()

func initial_resource_row(parent: Control, key: String, title: String, value, fallback: int, minimum: int) -> Dictionary:
	var row = HBoxContainer.new();parent.add_child(row)
	var custom = toggle(row, title + "（自定义）", value != null);custom.name = key + "Enabled";custom.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	var amount = SpinBox.new();amount.name = key + "Value";amount.min_value = minimum;amount.max_value = 1000;amount.step = 1
	amount.value = fallback if value == null else int(value);amount.editable = custom.button_pressed;amount.custom_minimum_size.x = 140;row.add_child(amount)
	custom.toggled.connect( func(enabled): amount.editable = enabled)
	return {"enabled": custom, "amount": amount}

func settings():
	var body = ui.open_dialog("设置与声音", Vector2(680, 690), "settings")
	var sounds = toggle(body, "按钮与游戏音效", ui.prefs.sounds);sounds.toggled.connect( func(value): ui.prefs.sounds = value;ui.save_preferences())
	var sfx = HSlider.new();sfx.min_value = 0;sfx.max_value = 1;sfx.step = 0.01;sfx.value = ui.prefs.sound_volume;body.add_child(ui.label("音效音量", 18));body.add_child(sfx)
	sfx.value_changed.connect( func(value): ui.prefs.sound_volume = value;ui.save_preferences();ui.play_sound())
	var motion = toggle(body, "界面动画与环境光效", ui.prefs.motion);motion.toggled.connect( func(value): ui.prefs.motion = value;ui.save_preferences();ui.dirty = true;ui.last_signature = "")
	frame_settings(body)
	body.add_child(wrapped("Alt：放大当前卡片\nEsc：关闭面板 / 打开设置\nF11：切换全屏", 18))

func frame_settings(body: Control):
	var frame_row = HBoxContainer.new();body.add_child(frame_row)
	var frame_title = ui.label("帧率上限", 19);frame_title.size_flags_horizontal = Control.SIZE_EXPAND_FILL;frame_row.add_child(frame_title)
	var frames = OptionButton.new();frames.name = "FrameLimit";frame_row.add_child(frames)
	for limit in [60, 120, 144, 240, 0]:
		frames.add_item(GuildLang.t("不限" if limit == 0 else "%s FPS" % limit), limit)
		if limit == int(ui.prefs.frame_limit): frames.select(frames.item_count - 1)
	frames.item_selected.connect( func(_index): ui.prefs.frame_limit = frames.get_selected_id();ui.save_preferences())
	var vsync = toggle(body, "垂直同步", ui.prefs.vsync);vsync.name = "VSync";vsync.toggled.connect( func(value): ui.prefs.vsync = value;ui.save_preferences())
	body.add_child(wrapped("默认上限 240 FPS。开启垂直同步后，帧率也会受显示器刷新率限制。", 17))

func leave():
	var body = ui.open_dialog("离开当前公会", Vector2(610, 310))
	body.add_child(wrapped("联机房间会继续运行；离线对局结束后不会保留进度。"))
	body.add_child(ui.button("确认离开", func():
		ui.close_dialog()
		ui.session.leave_room()
		ui.dirty = true, true, true))

func enter_room(room: Dictionary, role: String):
	var body = ui.open_dialog("加入 " + room.get("name", "公会"), Vector2(630, 340))
	var password = LineEdit.new();password.secret = true;password.placeholder_text = GuildLang.t("房间密码（无密码可留空）");body.add_child(password)
	body.add_child(ui.button("观战" if role == "spectator" else "加入公会", func():
		ui.session.password = password.text
		ui.session.send({"type": "enter_room", "room_id": room.id, "role": role, "password": password.text})
		ui.close_dialog(), true, true))

func create_room():
	var body = ui.open_dialog("创建公会房间", Vector2(710, 780))
	var name = LineEdit.new();name.placeholder_text = GuildLang.t("公会名称");name.text = "旅人的公会";body.add_child(name)
	var password = LineEdit.new();password.placeholder_text = GuildLang.t("房间密码（可选）");password.secret = true;body.add_child(password)
	var count = integer_row(body, "最多玩家", 5, 4);count.min_value = 1;count.name = "RoomMaxPlayers"
	var draw = hero_draw_row(body, 2, "CreateHeroDraw")
	var hint = wrapped("", 18);hint.name = "HeroPoolHint";body.add_child(hint)
	var spectators = toggle(body, "允许观战", true)
	var civ = initial_resource_row(body, "initial_civ", "初始文明", null, 1, 1)
	var miasma = initial_resource_row(body, "initial_miasma", "初始瘴气", null, 40, 0)
	body.add_child(wrapped("不勾选时使用标准初始值；自定义只影响开局，后续照常增减。", 17))
	var create = ui.button("创建", func():
		ui.session.password = password.text
		ui.session.send({"type": "create_room", "room_name": name.text, "password": password.text, "max_players": int(count.value), "allow_spectators": spectators.button_pressed, "options": {"hero_draw": draw.get_selected_id(), "initial_civ": int(civ.amount.value) if civ.enabled.button_pressed else null, "initial_miasma": int(miasma.amount.value) if miasma.enabled.button_pressed else null}})
		ui.close_dialog(), true, true);body.add_child(create)
	var refresh = func(): create.disabled = refresh_hero_draw(draw, hint, int(count.value)) < 1
	count.value_changed.connect( func(_value): refresh.call());refresh.call()

func room_options():
	var body = ui.open_dialog("对局规则", Vector2(1060, 820))
	var values = ui.session.room.get("options", ui.store.catalog.defaults).duplicate(true)
	var list = VBoxContainer.new();body.add_child(ui.scroll(list))
	var map_picker = OptionButton.new()
	for name in ["一般迷宫", "大深度迷宫", "训练迷宫"]: map_picker.add_item(GuildLang.t(name))
	map_picker.select(["normal", "deep", "training"].find(values.get("map_type", "normal")));list.add_child(map_picker)
	var difficulty = OptionButton.new()
	for title in ["初级", "上级", "特级", "超级"]: difficulty.add_item(GuildLang.t(title))
	difficulty.select(["beginner", "advanced", "expert", "super"].find(values.get("solo_difficulty", "beginner")))
	list.add_child(difficulty);difficulty.visible = ui.session.local_mode
	var draw = hero_draw_row(list, int(values.get("hero_draw", 2)), "RoomHeroDraw")
	var hint = wrapped("", 18);hint.name = "HeroPoolHint";list.add_child(hint)
	refresh_hero_draw(draw, hint, int(ui.session.room.get("max_players", 1)), ui.session.room.get("banned_characters", []))
	var first = OptionButton.new();first.add_item(GuildLang.t("随机先手"))
	for i in range(5): first.add_item(GuildLang.t("席位 " + str(i + 1) + " 先手"))
	first.select(0 if str(values.get("start_player", "auto")) == "auto" else int(values.get("start_player", 0)) + 1);list.add_child(first)
	var civ = initial_resource_row(list, "initial_civ", "初始文明", values.get("initial_civ"), 1, 1)
	var miasma = initial_resource_row(list, "initial_miasma", "初始瘴气", values.get("initial_miasma"), 10 * int(ui.session.room.get("max_players", 1)), 0)
	list.add_child(wrapped("不勾选时遵循人数、扩充及单人难度的标准初始值。", 17))
	var switches = {}
	var columns = GridContainer.new();columns.columns = 3;list.add_child(columns)
	for key in ui.store.catalog.option_labels:
		var option = toggle(columns, ui.store.catalog.option_labels[key], values.get(key, false));switches[key] = option
		if ui.session.local_mode and key in ["festival_preparation", "monster_quests", "scouts"]: option.button_pressed = false;option.disabled = true
	var base = integer_row(list, "每次行动基础秒数", 3600, int(values.get("base_seconds", 30)));base.min_value = 1
	var reserve = integer_row(list, "备用时间秒数", 7200, int(values.get("reserve_seconds", 120)))
	var disconnect = integer_row(list, "断线宽限秒数", 3600, int(values.get("disconnect_seconds", 30)));disconnect.min_value = 1
	body.add_child(ui.button("应用规则", func():
		for key in switches: values[key] = switches[key].button_pressed
		refresh_hero_draw(draw, hint, int(ui.session.room.get("max_players", 1)), ui.session.room.get("banned_characters", []))
		values.map_type = ["normal", "deep", "training"][map_picker.selected];values.hero_draw = draw.get_selected_id()
		values.solo_difficulty = ["beginner", "advanced", "expert", "super"][difficulty.selected]
		values.start_player = "auto" if first.selected == 0 else first.selected - 1
		values.base_seconds = int(base.value);values.reserve_seconds = int(reserve.value);values.disconnect_seconds = int(disconnect.value)
		values.initial_civ = int(civ.amount.value) if civ.enabled.button_pressed else null
		values.initial_miasma = int(miasma.amount.value) if miasma.enabled.button_pressed else null
		ui.session.send({"type": "set_options", "options": values});ui.close_dialog(), true, true))

func art_detail(source: String, title: String = "卡牌详情"):
	var body = ui.open_dialog(title, Vector2(1110, 850)); var art = ui.card(source, Vector2(1060, 730));body.add_child(art)

func card_detail(number, playable: bool = false, free: bool = false):
	var data = ui.store.card(number)
	if data.is_empty(): return
	var body = ui.open_dialog(data.get("name", "事件卡"), Vector2(1080, 810))
	var row = HBoxContainer.new();body.add_child(row);row.size_flags_vertical = Control.SIZE_EXPAND_FILL
	row.add_child(ui.card(ui.store.card_face(data), Vector2(435, 670)))
	var info = VBoxContainer.new();info.size_flags_horizontal = Control.SIZE_EXPAND_FILL;row.add_child(info)
	info.add_child(ui.resource("gold", int(data.get("price", 0)), "打出费用", 32))
	info.add_child(wrapped(data.get("ui_summary", data.get("description", "")), 19))
	var conversion = HBoxContainer.new();info.add_child(conversion);conversion.add_child(ui.resource("strength", 1, "抵付力量", 22));conversion.add_child(ui.label("=", 22));conversion.add_child(ui.resource("gold", 5, "金币", 22))
	var me = ui.session.me(); var strength = integer_row(info, "抵付", int(me.get("strength", 0)), 0, "strength")
	if not data.get("can_trans", false) and not me.get("strength_as_gold", false): strength.max_value = 0
	else: strength.max_value = min(strength.max_value, ceili(float(data.get("price", 0)) / 5))
	var double = toggle(info, "薇伊：双倍打出效果与费用", false)
	double.visible = me.get("hero") == "vee_white"
	var needed = int(data.get("consume_piece", 0)); var chosen = []
	if needed > 0:
		info.add_child(ui.label("选择支付的迷宫板块：需要 " + str(needed), 19, ui.GOLD))
		for i in range(me.get("tiles", []).size()):
			var key = me.tiles[i]; var check = CheckBox.new();check.text = GuildLang.t(ui.store.catalog.tiles.get(key, {}).get("name", key));info.add_child(check)
			check.toggled.connect( func(value): if value: chosen.append(i)
			else: chosen.erase(i))
	info.add_spacer(false)
	info.add_child(ui.button("打出这张事件", func():
		var args = {"card": int(number), "strength": int(strength.value)}
		if needed:
			var pieces = []
			for index in chosen: pieces.append(me.tiles[index])
			args.pieces = pieces
		if double.visible: args.double = double.button_pressed
		submit("play", args), ui.session.can_act() and me.get("hand", []).has(number), true))
	info.add_child(ui.cost_button("售卖", "gold", "+1", func(): submit("sell_event", {"card": int(number)}), not me.is_empty() and me.get("hand", []).has(number) and ui.session.role == "player"))

func hero_detail(player: Dictionary):
	var hero = ui.store.catalog.heroes.get(player.hero, {})
	var body = ui.open_dialog(hero.get("name", "看板娘") + " · 成长", Vector2(1100, 760))
	var row = HBoxContainer.new();body.add_child(row)
	for source in hero.get("source", []): row.add_child(ui.card(source, Vector2(335, 270), func(): art_detail(source, hero.name)))
	body.add_child(wrapped(hero.get("description", ""), 23, ui.INK))

func growth(player: Dictionary):
	var body = ui.open_dialog(player.name + " · 序章与成长", Vector2(1130, 810))
	var row = HBoxContainer.new();body.add_child(row)
	for pair in [["gold", "gold", 20], ["strength", "strength", 3], ["pot", "pot", 2], ["territory", "territory", "≥3"], ["cards", "event", "≥8"]]:
		var column = VBoxContainer.new();column.custom_minimum_size.x = 194
		var unlocked = player.get("developed", []).has(pair[0])
		var heart = ui.symbol("affection", 40);heart.modulate.a = 1.0 if unlocked else 0.25;column.add_child(heart)
		column.add_child(ui.resource(pair[1], pair[2], "成长条件", 23))
		column.add_child(ui.label("已解锁" if unlocked else "未解锁", 17));row.add_child(ui.panel(column))
	body.add_child(ui.label("已选择的序章", 23, ui.GOLD))
	var stories = HBoxContainer.new();body.add_child(stories)
	for story in player.get("prologue", []):
		var data = ui.store.catalog.prologues.get(str(int(story)), {})
		stories.add_child(ui.card(data.get("source", ""), Vector2(270, 390), func(): art_detail(data.get("source", ""), data.get("name", "序章"))))
	if stories.get_child_count() == 0: stories.add_child(ui.label("尚未选择序章", 19, ui.MUTED))

func develop():
	var me = ui.session.me(); var body = ui.open_dialog("发展公会 · 选择好感度格", Vector2(760, 630)); var chosen = []; var festivals = {}
	var controlled = 0
	for cell in ui.session.game.board: if cell.get("owner") != null and int(cell.owner) == ui.session.player_id: controlled += 1
	for pair in [["gold", "gold", 20], ["strength", "strength", 3], ["pot", "pot", 2], ["territory", "territory", "≥3"], ["cards", "event", "≥8"]]:
		var id = pair[0]; var line = HBoxContainer.new();body.add_child(line)
		var check = CheckBox.new();check.disabled = me.get("developed", []).has(id);check.button_pressed = check.disabled;line.add_child(check)
		var caption = ui.resource(pair[1], pair[2], "控制区域" if id == "territory" else "已打出的事件" if id == "cards" else "支付费用", 25);line.add_child(caption)
		line.add_child(ui.label("→", 24));line.add_child(ui.symbol("affection", 32))
		check.toggled.connect( func(value): if value: chosen.append(id)
		else: chosen.erase(id))
		if id in ["gold", "strength", "pot"] and int(me.get("festival_tokens", 0)) > 0: festivals[id] = integer_row(body, "庆典碎片抵扣", {"gold": 4, "strength": 3, "pot": 2}[id])
	body.add_child(wrapped("每格获得1好感度、释放1冒险者并抽1事件。已解锁格不能再次使用；资格与费用由服务器核验。"))
	body.add_child(ui.button("确认发展", func():
		if chosen.is_empty(): ui.show_toast("请先选择至少一个未解锁的格子。");return
		var spend = {}
		for id in festivals: if chosen.has(id) and festivals[id].value > 0: spend[id] = int(festivals[id].value)
		submit("develop", {"slots": chosen, "count": chosen.size(), "festival": spend}), true, true))

func potions():
	var body = ui.open_dialog("炼金与秘药", Vector2(1000, 760)); var list = VBoxContainer.new();body.add_child(ui.scroll(list))
	var game = ui.session.game; var me = ui.session.me()
	for key in ui.store.catalog.potions:
		var potion = ui.store.catalog.potions[key]; var row = HBoxContainer.new();list.add_child(ui.panel(row))
		var text = wrapped(potion.get("name", key) + "\n" + potion.get("description", ""), 19, ui.INK);text.size_flags_horizontal = Control.SIZE_EXPAND_FILL;row.add_child(text)
		row.add_child(ui.resource("pot", int(potion.get("cost", 0)), "秘药费用", 23))
		var state = GuildTableView.potion_state(ui, key)
		row.add_child(ui.button("使用" if state == "可用" else state, func(): submit("potion", {"option": key}), state == "可用"))

func hero_ability():
	var me = ui.session.me(); var hero = ui.store.catalog.heroes.get(me.get("hero", ""), {}); var ability = hero.get("ability", {})
	if ability.get("discard_min", 0) > 0:
		choose_hand("看板娘特别行动 · 选择弃牌", int(ability.discard_min), int(ability.get("discard_max", ability.discard_min)), func(cards): submit("ability", {"cards": cards}))
	else: submit("ability")

func choose_hand(title: String, minimum: int, maximum: int, callback: Callable):
	var body = ui.open_dialog(title, Vector2(1090, 790)); var grid = GridContainer.new();grid.columns = 5;body.add_child(ui.scroll(grid)); var selected = []
	var hand = ui.session.me().get("hand", [])
	for i in range(hand.size()):
		var art = ui.card(ui.store.card_face(ui.store.card(hand[i])), Vector2(195, 272))
		art.on_click = func():
			if selected.has(i): selected.erase(i)
			elif selected.size() < maximum: selected.append(i)
			art.selected = selected.has(i);art.queue_redraw()
		grid.add_child(art)
	body.add_child(ui.button("确认所选事件", func():
		if selected.size() < minimum: ui.show_toast("至少选择 " + str(minimum) + " 张事件。");return
		var cards = []
		for i in selected: cards.append(int(hand[i]))
		callback.call(cards), true, true))

func achievements():
	var body = ui.open_dialog("王权与公共任务", Vector2(1150, 820)); var grid = GridContainer.new();grid.columns = 4;body.add_child(ui.scroll(grid))
	var me = ui.session.me()
	for public in [true, false]:
		var keys = ui.session.game.get("public_achievements", []) if public else me.get("achievements", [])
		for key in keys:
			var data = ui.store.catalog.achievements.get(key, {})
			var column = VBoxContainer.new();grid.add_child(column)
			column.add_child(ui.card(data.get("source", ""), Vector2(255, 355), func(): art_detail(data.get("source", ""), data.get("name", "王权"))))
			column.add_child(wrapped(("公共" if public else "私人") + " · " + data.get("name", key), 18, ui.GOLD))
			column.add_child(ui.button("完成王权", func(): claim_achievement(key, public), ui.session.can_act()))
			if not public: column.add_child(ui.cost_button("售卖", "gold", "+3", func(): submit("discard_achievement", {"id": key}), ui.session.role == "player"))
	var quests = ui.session.game.get("quests", [])
	for slot in quests:
		if slot is Dictionary:
			var data = ui.store.catalog.quests.get(str(int(slot.get("card", 0))), {})
			var column = VBoxContainer.new();grid.add_child(column);column.add_child(ui.card(data.get("source", ""), Vector2(255, 355)));column.add_child(wrapped("委托 · " + data.get("name", "") + (" · 已完成" if slot.get("done", false) else ""), 18))

func claim_achievement(key: String, public: bool):
	var data = ui.store.catalog.achievements.get(key, {})
	var body = ui.open_dialog("完成王权：" + data.get("name", key), Vector2(670, 420));body.add_child(wrapped(data.get("description", ""), 22, ui.INK))
	var strength = integer_row(body, "抵付", int(ui.session.me().get("strength", 0)), 0, "strength")
	if not data.get("can_trans", false): strength.max_value = 0
	body.add_child(ui.button("确认完成", func(): submit("achievement", {"id": key, "public": public, "strength": int(strength.value)}), ui.session.can_act(), true))

func market():
	var me = ui.session.me(); var body = ui.open_dialog("资源交换与售卖", Vector2(800, 530))
	body.add_child(wrapped("资源售卖不消耗主要行动，也可用于结算中的筹款。", 20, ui.INK))
	var pot = integer_row(body, "售卖数量", int(me.get("pot", 0)), min(1, int(me.get("pot", 0))), "pot")
	body.add_child(ui.cost_button("兑换 / 每瓶", "gold", int(ui.session.game.get("exchange_rate", 3)), func(): submit("exchange", {"amount": int(pot.value)}), int(me.get("pot", 0)) > 0, true))
	body.add_child(ui.cost_button("售卖手牌 / 每张", "gold", "+1", func(): choose_hand("选择售卖的手牌", 1, 1, func(cards): submit("sell_event", {"card": cards[0]})), not me.get("hand", []).is_empty()))
	body.add_child(ui.cost_button("售卖宝石", "gold", "+3", func(): submit("sell_gem"), int(me.get("gems", 0)) > 0))
	if me.get("strength_as_gold", false):
		var strength = integer_row(body, "优先抵付数量", int(me.get("strength", 0)), int(me.get("gold_payment_strength", 0)), "strength")
		body.add_child(ui.button("设置抵付偏好", func(): submit("payment_preference", {"strength": int(strength.value)})))
	if me.get("hero") == "horn_black": body.add_child(ui.button("切换优先使用秘药 / 板块", func(): submit("horn_preference", {"prefer_pot": not me.get("prefer_pot", false)})))

func expansions():
	var body = ui.open_dialog("扩充行动", Vector2(820, 660)); var options = ui.session.game.get("options", {})
	if options.get("solo", false): body.add_child(ui.cost_button("雇用冒险者", "gold", 15, func(): submit("hire")))
	if options.get("scouts", false): body.add_child(ui.button("派遣侦查队", func(): submit("scout")))
	if options.get("dragon", false): body.add_child(ui.button("讨伐潜行之龙", func(): submit("dragon_hunt")))
	if options.get("monster_quests", false): body.add_child(ui.cost_button("讨伐魔兽", "strength", "2 / 3", func(): submit("monster_hunt")))
	if options.get("forest", false):
		body.add_child(ui.cost_button("净化相邻洞穴", "strength", 2, func(): submit("forest_purify", {"payment": "strength"})))
		body.add_child(ui.button("净化相邻洞穴 / 1庆典", func(): submit("forest_purify", {"payment": "festival"})))
	if body.get_child_count() == 1: body.add_child(wrapped("本局未启用额外的行动扩充。"))

func map_cell(cell: Dictionary):
	var body = ui.open_dialog("迷宫区域 (%s,%s)" % [int(cell.q), int(cell.r)], Vector2(750, 570))
	body.add_child(ui.label("区域声望 %s%s" % [int(cell.region), " · 据点翻倍" if cell.get("base", false) else ""], 26, ui.GOLD))
	var source = cell.get("back_source", "images/piece_png/2.png")
	if cell.get("revealed", false): source = ui.store.catalog.tiles.get(cell.get("loot", ""), {}).get("source", source)
	body.add_child(ui.card(source, Vector2(650, 285)))
	if cell.get("blocked", false): body.add_child(wrapped("封锁区域，不能探索或占领。"));return
	if cell.get("owner") != null and int(cell.owner) == ui.session.player_id:
		body.add_child(ui.cost_button("建设据点", "gold", int(cell.get("build_gold", 15)), func(): submit("build", {"tile": cell.id}), ui.session.can_act() and not cell.get("base", false), true))
	else:
		body.add_child(ui.button("探索这块迷宫", func(): submit("explore", {"tile": cell.id}), ui.session.can_act() and cell.get("eligible_for", []).has(ui.session.player_id), true))
		body.add_child(wrapped("探索会先公开板块，再由服务器计算费用并让你选择支付方式。"))

func confirm_pass():
	var body = ui.open_dialog("让公会休息一会儿", Vector2(650, 300));body.add_child(wrapped("闭店后本轮不再行动。所有玩家闭店后进入生产和下一季。"))
	body.add_child(ui.button("确认闭店", func(): submit("pass"), true, true))

func player_detail(player: Dictionary):
	var body = ui.open_dialog(player.name + " · 公会收藏", Vector2(1160, 830)); var grid = GridContainer.new();grid.columns = 5;body.add_child(ui.scroll(grid))
	for i in range(player.get("played", []).size()):
		var number = int(player.played[i]); var data = ui.store.card(number); var meta = player.get("card_states", [])[i] if i < player.get("card_states", []).size() else {}
		var column = VBoxContainer.new();grid.add_child(column)
		if meta.get("face_down", false): column.add_child(ui.label("背面事件", 20, ui.MUTED))
		else: column.add_child(ui.card(ui.store.card_face(data), Vector2(208, 288), func(): card_detail(number)))
		if int(player.id) == ui.session.player_id and not meta.get("face_down", false) and not data.get("action", {}).is_empty():
			column.add_child(ui.button("特别行动", func(): submit("card_action", {"card": number}), ui.session.can_act() and meta.get("used_round", 0) != ui.session.game.get("round", 1)))
	for key in player.get("tiles", []) + player.get("hero_tiles", []): grid.add_child(ui.card(ui.store.catalog.tiles.get(key, {}).get("source", ""), Vector2(208, 250)))
	for key in player.get("earned_achievements", []): grid.add_child(ui.card(ui.store.catalog.achievements.get(key, {}).get("source", ""), Vector2(208, 288)))
	for key in player.get("private_tiles", {}):
		var tile = ui.store.catalog.tiles.get(player.private_tiles[key], {}); var column = VBoxContainer.new();grid.add_child(column);column.add_child(ui.label("私下查看 " + key, 18));column.add_child(ui.card(tile.get("source", ""), Vector2(208, 250)))

func gallery():
	var body = ui.open_dialog("卡牌图鉴", Vector2(1170, 860)); var search = LineEdit.new();search.placeholder_text = GuildLang.t("搜索卡名、编号或关键词");body.add_child(search)
	var category = OptionButton.new()
	for title in ["事件卡", "看板娘", "王权", "迷宫板块", "委托", "序章"]: category.add_item(GuildLang.t(title))
	body.add_child(category)
	var grid = GridContainer.new();grid.columns = 5;body.add_child(ui.scroll(grid))
	var collections = [ui.store.catalog.cards, ui.store.catalog.heroes, ui.store.catalog.achievements, ui.store.catalog.tiles, ui.store.catalog.quests, ui.store.catalog.prologues]
	var state = {"page": 0, "items": []}
	var page_bar = HBoxContainer.new();body.add_child(page_bar); var page_label = ui.label("", 18, ui.MUTED)
	var redraw = func():
		for child in grid.get_children(): child.queue_free()
		state.page = clamp(int(state.page), 0, max(0, ceili(float(state.items.size()) / 15) - 1))
		for i in range(int(state.page) * 15, min(state.items.size(), (int(state.page) + 1) * 15)):
			var item = state.items[i]
			var column = VBoxContainer.new();grid.add_child(column);column.add_child(ui.card(item.source, Vector2(210, 290), func():
				if category.selected == 0: card_detail(int(item.key))
				else: art_detail(item.source, item.name)))
			column.add_child(wrapped(item.name, 17, ui.INK))
		page_label.text = "%s 张卡 · 第 %s / %s 页" % [state.items.size(), int(state.page) + 1, max(1, ceili(float(state.items.size()) / 15))]
	page_bar.add_child(ui.button("上一页", func(): state.page -= 1;redraw.call()));page_bar.add_child(page_label);page_bar.add_child(ui.button("下一页", func(): state.page += 1;redraw.call()))
	var filter = func():
		state.items = [];state.page = 0
		var collection = collections[category.selected]
		for key in collection:
			var data = collection[key]
			if not data.get("available", true): continue
			var index = data.get("name", "") + data.get("printed_code", "") + data.get("ui_summary", "") + data.get("description", "")
			if not search.text.is_empty() and not search.text in index: continue
			var sources = data.get("source", "")
			if sources is String: sources = [sources]
			if category.selected == 0: sources = [ui.store.card_face(data)]
			for i in range(sources.size()): state.items.append({"key": key, "name": data.get("name", key) + (" / " + data.get("subtitle", "") + " / 等级" + str(i + 1) if category.selected == 1 else ""), "source": sources[i]})
		redraw.call()
	search.text_changed.connect( func(_text): filter.call())
	category.item_selected.connect( func(_index): filter.call())
	filter.call()

func results():
	var body = ui.open_dialog("冒险的终章 · 公会结算", Vector2(940, 780)); var list = VBoxContainer.new();body.add_child(ui.scroll(list))
	for row in ui.session.game.get("scores", []):
		var column = VBoxContainer.new();list.add_child(ui.panel(column));column.add_child(ui.label("第 %s 名 · %s · %s 声望" % [int(row.get("rank", 0)), row.get("name", ""), int(row.get("score", 0))], 27, ui.GOLD))
		var entries = []
		for key in row.get("breakdown", {}): entries.append(key + " " + str(int(row.breakdown[key])))
		column.add_child(wrapped(" · ".join(entries), 18))
	if not ui.session.local_mode and int(ui.session.room.get("host_id", -1)) == ui.session.player_id: body.add_child(ui.button("返回公会准备下一局", func(): ui.session.send({"type": "return_lobby"});ui.close_dialog(), true, true))

func pending(pending: Dictionary):
	var options = pending.get("options", [])
	var body = ui.open_dialog(pending.get("title", "结算卡牌效果"), Vector2(1210, 890) if not options.is_empty() else Vector2(940, 800), "pending")
	ui.pending_id = int(pending.id)
	var selected = []; var min_count = int(pending.get("min", 0)); var max_count = int(pending.get("max", 1))
	var row = HBoxContainer.new();row.size_flags_vertical = Control.SIZE_EXPAND_FILL;body.add_child(row)
	var grid = GridContainer.new();grid.columns = 4
	var choices = VBoxContainer.new();choices.size_flags_horizontal = Control.SIZE_EXPAND_FILL;row.add_child(ui.scroll(choices))
	var counter = ui.label("已选 0 / " + str(max_count) + " · 至少 " + str(min_count) + " 项", 20, ui.GOLD);body.add_child(counter);counter.visible = not options.is_empty()
	var buttons = []
	var select = func(index: int):
		if selected.has(index): selected.erase(index)
		elif max_count == 1: selected.clear();selected.append(index)
		elif selected.size() < max_count: selected.append(index)
		for i in range(buttons.size()):
			if buttons[i] is GuildCardArt: buttons[i].selected = selected.has(i);buttons[i].queue_redraw()
			else: buttons[i].button_pressed = selected.has(i)
		counter.text = "已选 %s / %s · 至少 %s 项" % [selected.size(), max_count, min_count]
	choices.add_child(grid)
	var board_choices = not options.is_empty() and options.all( func(option): return option.get("board", false))
	var choice_map: GuildHexMap
	if board_choices:
		choice_map = GuildHexMap.new();choice_map.store = ui.store;choice_map.motion = ui.prefs.motion;choice_map.custom_minimum_size = Vector2(810, 570)
		choice_map.selection_only = true
		var snapshot = ui.session.game.duplicate(true)
		for i in range(options.size()):
			var option = options[i]; var id = str(int(option.q)) + "," + str(int(option.r));choice_map.option_ids[id] = i
			if not snapshot.board.any( func(cell): return cell.id == id): snapshot.board.append({"id": id, "q": int(option.q), "r": int(option.r), "owner": null, "region": 0, "outer": true})
		choice_map.set_game(snapshot, ui.session.player_id);choices.add_child(choice_map)
		choice_map.cell_clicked.connect( func(cell):
			if not choice_map.option_ids.has(cell.id): return
			select.call(int(choice_map.option_ids[cell.id]));choice_map.chosen_ids = []
			for i in selected: choice_map.chosen_ids.append(str(int(options[i].q)) + "," + str(int(options[i].r)))
			choice_map.queue_redraw())
	for index in range(options.size()):
		if board_choices: continue
		var option = options[index]; var column = VBoxContainer.new();column.custom_minimum_size.x = 197;grid.add_child(column)
		if option.get("image") is String and not option.image.is_empty():
			var art = ui.card(option.image, Vector2(193, 268), func(): select.call(index));column.add_child(art);buttons.append(art)
			column.add_child(wrapped(option.get("label", ""), 16, ui.INK))
		else:
			var choice = ui.button(option.get("label", "选项"), func(): select.call(index));choice.toggle_mode = true;column.add_child(choice);buttons.append(choice)
		if option.has("description"): column.add_child(wrapped(option.description, 15))
	var side = VBoxContainer.new();side.custom_minimum_size.x = 270;row.add_child(side)
	var payment = pending.get("payment", {})
	var strength = integer_row(side, "使用", int(payment.get("strength_max", 0)), 0, "strength")
	var pot = integer_row(side, "使用", int(payment.get("pot_max", 0)), 0, "pot")
	strength.get_parent().visible = int(payment.get("strength_max", 0)) > 0;pot.get_parent().visible = int(payment.get("pot_max", 0)) > 0
	var flash = toggle(side, "使用一闪", false);flash.visible = payment.get("flash", false)
	var lab = toggle(side, "派遣浮空实验室", false);lab.visible = payment.get("lab", false)
	var price_line = HBoxContainer.new();side.add_child(price_line);price_line.add_child(ui.symbol("gold", 35))
	var price = ui.label("", 28, ui.GOLD);price_line.add_child(price)
	price_line.visible = payment.has("gold_base")
	var update_price = func():
		if payment.has("gold_base"):
			var base = int(payment.get("gold_flash", payment.gold_base)) if flash.button_pressed else int(payment.gold_base)
			var tile_strength = selected.size() if payment.get("tiles_as_strength", false) else 0
			price.text = str(max(0, base - 5 * (int(strength.value) + int(pot.value) * int(payment.get("potion_strength", 0)) + tile_strength)))
			var ceiling = int(ceil(float(base - 5 * (int(pot.value) * int(payment.get("potion_strength", 0)) + tile_strength)) / 5))
			strength.max_value = max(0, min(int(payment.get("strength_max", 0)), ceiling))
	strength.value_changed.connect( func(_value): update_price.call());pot.value_changed.connect( func(_value): update_price.call());flash.toggled.connect( func(_value): update_price.call())
	if payment.has("target_image"):
		if options.is_empty():
			choices.add_child(ui.card(payment.target_image, Vector2(560, 530)))
			choices.add_child(wrapped(payment.get("target_name", ""), 24, ui.GOLD))
		else:
			side.add_child(ui.card(payment.target_image, Vector2(260, 270)))
			side.add_child(wrapped(payment.get("target_name", ""), 20, ui.GOLD))
		side.add_child(wrapped("探索费用先按最低10金币计算，再用力量等资源抵付。"))
	side.add_spacer(false)
	side.add_child(ui.button("确认并继续", func():
		if selected.size() < min_count or selected.size() > max_count: ui.show_toast("请选择要求数量的选项。");return
		if not ui.session.can_choose(): ui.show_toast("请等待连接恢复。");return
		ui.session.action("choice", {"choice_id": int(pending.id), "selected": selected, "action": {"strength": int(strength.value), "pot": int(pot.value), "flash": flash.button_pressed, "lab": lab.button_pressed}}), true, true))
	if pending.get("optional", false): side.add_child(ui.button("跳过此效果", func(): ui.session.action("choice", {"choice_id": int(pending.id), "selected": [], "skip": true})))
	side.add_child(ui.button("撤回上一步", func(): ui.session.action("undo"), ui.session.game.get("undo", {}).get("available", false)))
	side.add_child(ui.cost_button("售卖筹款", "pot", 1, func(): ui.session.action("exchange", {"amount": 1}), int(ui.session.me().get("pot", 0)) > 0))
	side.add_child(ui.button("售卖手牌筹款", func(): choose_hand("售卖手牌筹款", 1, 1, func(cards): submit("sell_event", {"card": cards[0]})), not ui.session.me().get("hand", []).is_empty()))
	update_price.call()
