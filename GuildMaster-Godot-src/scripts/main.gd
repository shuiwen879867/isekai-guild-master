extends Control

const PHASES = {"draft": "开局轮抽", "research": "情报收集", "action": "公会行动", "final": "最终行动", "finished": "终局结算"}
const GOLD = Color("874449")
const INK = Color("343133")
const MUTED = Color("6b6460")
var store = GuildArtStore.new()
var session = GuildSession.new()
var prefs = {"name": "公会长", "address": "guanpeng666.cn", "port": 6677, "sounds": true, "sound_volume": 0.65, "voices": true, "voice_volume": 0.85, "voice_language": "ja", "layout": "classic", "motion": true, "hints": true, "frame_limit": 240, "vsync": false, "language": "zh_CN"}
var voice: GuildVoice
var content: Control
var modal_layer: Control
var toast_label: Label
var preview_panel: PanelContainer
var preview_art: GuildCardArt
var backdrop: GuildBackdrop
var sound: AudioStreamPlayer
var dirty = true
var last_signature = ""
var hover_source = ""
var last_hover_source = ""
var alt_zoom = false
var selected_research = []
var selection_scroll_states = {}
var research_packet = ""
var dialog: Control
var pending_id = -1
var modal_key = ""
var last_feedback = -1
var last_phase = ""
var last_round = -1
var last_view_player = -1
var last_quest_report = -1
var toast_serial = 0
var connect_form = {}
var game_clock: Label
var dialogs: GuildRenpyDialogs
var debug_mode = false
var selected_tile = ""
var package_check: GuildPackageCheck
var renpy_reference = {}
var hand_page = 0
var player_clocks = []
var choice_states = {}
var browsing_character = ""
var home_portrait = ""
var hover_dimensions = Vector2(100, 140)
var hover_magnification = 2.5
var final_notice: Control
var final_notice_serial = 0
var feedback_scope = ""
var last_action_count = -1

func rerender():
	dirty = true;last_signature = ""

func undo():
	var state = session.game.get("undo", {})
	if state.get("available", false): session.action("undo", {"undo_id": state.get("id")})

func _ready():
	renpy_reference = JSON.parse_string(FileAccess.get_file_as_string("res://data/renpy_layout_reference.json"))
	_load_preferences();GuildLang.traditional = str(prefs.language) == "zh_TW";_apply_frame_settings();_build_theme();session.rules_catalog = store.catalog;add_child(session)
	DisplayServer.window_set_title(GuildLang.t("异世界公会长 · Godot"))
	backdrop = GuildBackdrop.new();add_child(backdrop);backdrop.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT);backdrop.motion = prefs.motion
	content = Control.new();add_child(content);content.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	modal_layer = Control.new();add_child(modal_layer);modal_layer.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT);modal_layer.mouse_filter = Control.MOUSE_FILTER_IGNORE;modal_layer.z_index = 30
	preview_panel = PanelContainer.new();add_child(preview_panel);preview_panel.z_index = 80;preview_panel.mouse_filter = MOUSE_FILTER_IGNORE;preview_panel.hide()
	preview_art = GuildCardArt.new();preview_panel.add_child(preview_art)
	toast_label = Label.new();add_child(toast_label);toast_label.z_index = 100;toast_label.hide();toast_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER;toast_label.mouse_filter = MOUSE_FILTER_IGNORE
	toast_label.add_theme_stylebox_override("normal", GuildPaperSkin.paper("paper", 18))
	toast_label.add_theme_font_size_override("font_size", 21)
	dialogs = GuildRenpyDialogs.new();dialogs.ui = self
	_setup_audio()
	voice = GuildVoice.new();add_child(voice);voice.setup(self)
	session.changed.connect( func(): dirty = true)
	session.notice.connect(show_toast)
	session.connected.connect( func(): show_toast("公会连接成功。" if session.local_mode else "服务器已确认连接。"))
	resized.connect(_position_preview)
	resized.connect(_position_final_notice)
	_render()
	var args = OS.get_cmdline_user_args()
	debug_mode = args.has("--ui-test")
	if args.has("--verify-package"):
		package_check = GuildPackageCheck.new();package_check.run(self);return
	if args.has("--demo") or debug_mode: call_deferred("_start_demo")

func _build_theme():
	var style = Theme.new();style.default_font = GuildLang.font();style.default_font_size = 20
	for type in ["Label", "Button", "CheckButton", "CheckBox", "OptionButton", "LineEdit", "SpinBox", "PopupMenu"]:
		for state in ["font_color", "font_hover_color", "font_pressed_color", "font_focus_color"]: style.set_color(state, type, INK)
		style.set_color("font_disabled_color", type, Color("8c877e"))
	for state in ["normal", "hover", "pressed", "disabled"]: style.set_stylebox(state, "Button", GuildPaperSkin.banner(state, 46))
	style.set_stylebox("focus", "Button", box(Color.TRANSPARENT, GOLD, 0, 4))
	for type in ["OptionButton", "CheckButton", "CheckBox"]:
		for state in ["normal", "hover", "pressed", "disabled"]: style.set_stylebox(state, type, GuildPaperSkin.paper(state, 10))
		style.set_stylebox("focus", type, box(Color.TRANSPARENT, GOLD, 0, 4))
	for type in ["PanelContainer", "PopupMenu", "TooltipPanel"]: style.set_stylebox("panel", type, GuildPaperSkin.paper("paper", 20))
	style.set_color("font_color", "TooltipLabel", INK)
	style.set_stylebox("normal", "LineEdit", GuildPaperSkin.paper("paper", 13))
	style.set_stylebox("focus", "LineEdit", GuildPaperSkin.paper("hover", 13))
	for type in ["CheckBox", "CheckButton"]:
		style.set_icon("checked", type, load("res://ui/comic/checked.svg"));style.set_icon("unchecked", type, load("res://ui/comic/unchecked.svg"))
	var rail = box(Color("b4afb1"), Color("b4afb1"), 0, 2)
	style.set_stylebox("slider", "HSlider", rail);style.set_stylebox("grabber_area", "HSlider", box(GOLD, GOLD, 0, 2))
	for state in ["grabber", "grabber_highlight", "grabber_disabled"]: style.set_icon(state, "HSlider", load("res://ui/comic/knob.svg"))
	for type in ["VScrollBar", "HScrollBar"]:
		style.set_stylebox("scroll", type, box(Color("d7d0c9"), Color("d7d0c9"), 0, 1))
		for state in ["grabber", "grabber_highlight", "grabber_pressed"]: style.set_stylebox(state, type, box(INK, INK, 0, 1))
	style.set_constant("separation", "VBoxContainer", 12);style.set_constant("separation", "HBoxContainer", 12)
	theme = style

func box(fill: Color, border: Color, radius: int = 12, padding: int = 16) -> StyleBoxFlat:
	var result = StyleBoxFlat.new();result.bg_color = fill;result.border_color = border
	result.set_border_width_all(1);result.set_corner_radius_all(radius)
	result.content_margin_left = padding;result.content_margin_right = padding;result.content_margin_top = padding;result.content_margin_bottom = padding
	return result

func label(text: String, points: int = 20, color: Color = INK) -> Label:
	var node = Label.new();node.text = GuildLang.t(text);node.add_theme_font_size_override("font_size", points);node.add_theme_color_override("font_color", color)
	if points >= 27: node.add_theme_font_override("font", GuildPaperSkin.title_font())
	return node

func button(text: String, callback: Callable, enabled: bool = true, primary: bool = false) -> Button:
	var node = Button.new();node.text = GuildLang.t(text);node.custom_minimum_size.y = 46;node.disabled = not enabled
	node.mouse_default_cursor_shape = CURSOR_POINTING_HAND
	if primary:
		for state in ["normal", "hover", "pressed"]: node.add_theme_stylebox_override(state, GuildPaperSkin.banner(GuildPaperSkin.primary_state(state), 46))
		for state in ["font_color", "font_hover_color", "font_pressed_color"]: node.add_theme_color_override(state, Color("fffdf7"))
	node.pressed.connect( func(): play_sound("click");callback.call())
	node.mouse_entered.connect( func():
		if not prefs.motion or node.disabled: return
		node.create_tween().tween_property(node, "modulate", Color(0.94, 0.91, 0.86), 0.12))
	node.mouse_exited.connect( func(): node.create_tween().tween_property(node, "modulate", Color.WHITE, 0.12))
	return node

func symbol(kind: String, points: int = 32) -> TextureRect:
	return picture(load("res://ui/symbols/" + kind + ".png"), points)

func picture(texture: Texture2D, points: int = 32) -> TextureRect:
	var node = TextureRect.new();node.texture = texture
	node.custom_minimum_size = Vector2(points, points);node.expand_mode = TextureRect.EXPAND_IGNORE_SIZE;node.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	node.mouse_filter = MOUSE_FILTER_IGNORE;return node

func resource(kind: String, value, help: String, points: int = 25) -> HBoxContainer:
	var row = HBoxContainer.new();row.tooltip_text = GuildLang.t(help);row.mouse_filter = MOUSE_FILTER_STOP
	row.add_theme_constant_override("separation", 6)
	row.add_child(symbol(kind, points + 7));row.add_child(label(str(value), points, INK));return row

func box_button(text: String, callback: Callable, enabled: bool = true, primary: bool = false) -> Button:
	var node = button(text, callback, enabled, primary)
	for state in ["normal", "hover", "pressed", "disabled"]: node.add_theme_stylebox_override(state, GuildPaperSkin.paper(GuildPaperSkin.primary_state(state) if primary else state, 10))
	return node

func step_button(label: String, callback: Callable, enabled: bool = true) -> Button:
	# 所有加减步进钮：统一 46×46 方形与 plaque 样式。
	var node = button(label, callback, enabled)
	node.custom_minimum_size = Vector2(46, 46)
	for state in ["normal", "hover", "pressed", "disabled"]: node.add_theme_stylebox_override(state, GuildPaperSkin.plaque(state, 8))
	return node

func symbol_button(kind: String, help: String, callback: Callable, enabled: bool = true) -> Button:
	var node = button("", callback, enabled);node.custom_minimum_size = Vector2(66, 52);node.tooltip_text = GuildLang.t(help)
	for state in ["normal", "hover", "pressed", "disabled"]: node.add_theme_stylebox_override(state, GuildPaperSkin.paper(state, 6))
	var picture = symbol(kind, 32);node.add_child(picture);picture.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	picture.offset_left = 15;picture.offset_right = -15;picture.offset_top = 10;picture.offset_bottom = -10
	if not enabled: picture.modulate.a = 0.3
	return node

func art_button(source: String, help: String, callback: Callable, enabled: bool = true) -> Button:
	var node = button("", callback, enabled);node.custom_minimum_size = Vector2(75, 58);node.tooltip_text = GuildLang.t(help)
	for state in ["normal", "hover", "pressed", "disabled"]: node.add_theme_stylebox_override(state, GuildPaperSkin.paper(state, 6))
	var art = GuildCardArt.new();art.configure(store, source, Vector2(48, 43));node.add_child(art);art.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	art.offset_left = 12;art.offset_right = -12;art.offset_top = 8;art.offset_bottom = -8
	if not enabled: art.modulate.a = 0.3
	return node

func cost_button(title: String, kind: String, value, callback: Callable, enabled: bool = true, primary: bool = false) -> Button:
	var node = button("", callback, enabled, primary);node.tooltip_text = GuildLang.t(title)
	var line = HBoxContainer.new();line.mouse_filter = MOUSE_FILTER_IGNORE;node.add_child(line);line.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	line.offset_left = 16;line.offset_right = -16;line.offset_top = 8;line.offset_bottom = -8
	var caption = label(title, 18, Color("fffdf7") if primary else INK);caption.size_flags_horizontal = Control.SIZE_EXPAND_FILL;caption.mouse_filter = MOUSE_FILTER_IGNORE;line.add_child(caption)
	line.add_child(symbol(kind, 27));line.add_child(label(str(value), 21, Color("fffdf7") if primary else INK))
	node.custom_minimum_size.x = caption.get_minimum_size().x + 96
	return node

func panel(child: Control, padding: int = 20) -> PanelContainer:
	var node = PanelContainer.new();node.add_theme_stylebox_override("panel", GuildPaperSkin.paper("paper", padding));node.add_child(child);return node

func scroll(child: Control, dimensions: Vector2 = Vector2.ZERO) -> ScrollContainer:
	var node = ScrollContainer.new();node.custom_minimum_size = dimensions;node.size_flags_horizontal = Control.SIZE_EXPAND_FILL;node.size_flags_vertical = Control.SIZE_EXPAND_FILL
	node.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED;node.add_child(child);child.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	return node

func preserve_selection_scroll(scroller: ScrollContainer, context: String, packet: String):
	if selection_scroll_states.get(context, {}).get("packet", "") != packet:
		selection_scroll_states[context] = {"packet": packet, "vertical": 0}
	_restore_selection_scroll.call_deferred(scroller, selection_scroll_states[context])

func _restore_selection_scroll(scroller: ScrollContainer, state: Dictionary):

	await get_tree().process_frame
	await get_tree().process_frame
	if not is_instance_valid(scroller) or not scroller.is_inside_tree(): return
	scroller.scroll_vertical = int(state.vertical)
	scroller.get_v_scroll_bar().value_changed.connect( func(value): state.vertical = int(value))

func card(source: String, dimensions: Vector2 = Vector2(150, 208), callback: Callable = Callable(), magnification: float = 2.5) -> GuildCardArt:
	var art = GuildTileArt.new() if store.layouts.get(source, {}).get("kind") == "tile" else GuildCardArt.new()
	art.interactive = true;art.motion = prefs.motion;art.on_click = callback
	art.on_click = func():
		if callback.is_valid(): play_sound("card");callback.call()
	art.on_hover = func(image): hover_dimensions = dimensions;hover_magnification = magnification;hover_source = image;last_hover_source = image;_update_preview()
	art.on_leave = func(image):
		if hover_source == image: hover_source = ""
		if not alt_zoom: preview_panel.hide()
	art.configure(store, source, dimensions)
	return art

func _load_preferences():
	var config = ConfigFile.new()
	if config.load("user://preferences.cfg") == OK:
		for key in prefs: prefs[key] = config.get_value("preferences", key, prefs[key])

func save_preferences():
	var config = ConfigFile.new()
	for key in prefs: config.set_value("preferences", key, prefs[key])
	config.save("user://preferences.cfg")
	backdrop.motion = prefs.motion
	_apply_audio()
	if is_instance_valid(voice): voice.apply_settings()
	_apply_frame_settings()

func apply_language(persist: bool = false):
	prefs.language = "zh_TW" if str(prefs.get("language", "zh_CN")) == "zh_TW" else "zh_CN"
	GuildLang.traditional = prefs.language == "zh_TW"
	if persist: save_preferences()
	_build_theme()
	DisplayServer.window_set_title(GuildLang.t("异世界公会长 · Godot"))

func set_language(code: String):
	prefs.language = "zh_TW" if str(code) == "zh_TW" else "zh_CN"
	apply_language(true)
	rerender()

func _apply_frame_settings():
	var limit = int(prefs.frame_limit)
	if limit not in [0, 60, 120, 144, 240]: limit = 240
	prefs.frame_limit = limit
	Engine.max_fps = limit
	DisplayServer.window_set_vsync_mode(DisplayServer.VSYNC_ENABLED if prefs.vsync else DisplayServer.VSYNC_DISABLED)

func _setup_audio():
	for bus in ["SFX"]:
		if AudioServer.get_bus_index(bus) < 0: AudioServer.add_bus();AudioServer.set_bus_name(AudioServer.bus_count - 1, bus)
	sound = AudioStreamPlayer.new();sound.bus = "SFX";sound.max_polyphony = 4;add_child(sound)
	_apply_audio()

func _apply_audio():
	if sound == null: return
	AudioServer.set_bus_volume_db(AudioServer.get_bus_index("SFX"), linear_to_db(max(0.0001, float(prefs.sound_volume))))
	AudioServer.set_bus_mute(AudioServer.get_bus_index("SFX"), not prefs.sounds)

func play_sound(kind: String = "click"):
	if not prefs.sounds: return
	var path = "res://audio/guild_" + kind + ".wav"
	if ResourceLoader.exists(path): sound.stream = load(path);sound.play()

func _process(_delta):
	# 单人 / 多人各有一版印刷卡面（face_variants.solo）；模式变化时重建画面。
	var wanted_mode = "multi"
	if not session.game.is_empty() and bool(session.game.get("options", {}).get("solo", false)):
		wanted_mode = "solo"
	if store.mode != wanted_mode: store.mode = wanted_mode;dirty = true
	var alt = Input.is_key_pressed(KEY_ALT)
	if alt != alt_zoom:
		alt_zoom = alt;_update_preview()
	if preview_panel.visible: _position_preview()
	if dirty:
		dirty = false
		var copy = session.game.duplicate(true);copy.erase("clock")

		var signature = JSON.stringify([session.room, copy, session.rooms, session.active, session.synchronized, session.directory, session.room_connected, session.role, session.player_id])
		if signature != last_signature: last_signature = signature;_render();dialogs.refresh_snapshot()
	if is_instance_valid(game_clock):
		var banks = session.game.get("clock")
		var timebank = banks.get(str(session.player_id), {}) if banks is Dictionary else {}
		game_clock.text = ("基础 %ss / 备用 %ss" % [int(timebank.get("base", 0)), int(timebank.get("reserve", 0))]) if not timebank.is_empty() else ""
	var banks = session.game.get("clock", {});banks = banks if banks is Dictionary else {}
	for item in player_clocks:
		if is_instance_valid(item.label) and banks.has(item.id): item.label.text = "%ss + %ss" % [int(banks[item.id].base), int(banks[item.id].reserve)]

func _input(event):
	if event is InputEventKey and event.pressed and not event.echo:
		if event.keycode == KEY_ESCAPE:
			if modal_key == "pending": dialogs.settings();return
			if dialog: close_dialog()
			else: dialogs.settings()
		elif event.keycode == KEY_F11:
			get_window().mode = Window.MODE_WINDOWED if get_window().mode == Window.MODE_FULLSCREEN else Window.MODE_FULLSCREEN

func _update_preview():
	if not alt_zoom: preview_panel.hide();return
	var source = hover_source
	if alt_zoom and source.is_empty() and preview_panel.visible: source = last_hover_source
	if source.is_empty(): preview_panel.hide();return
	var is_tile = store.layouts.get(source, {}).get("kind") == "tile"
	if (preview_art is GuildTileArt) != is_tile:
		preview_panel.remove_child(preview_art);preview_art.queue_free()
		preview_art = GuildTileArt.new() if is_tile else GuildCardArt.new();preview_panel.add_child(preview_art)
	var natural = store.natural_size(source)
	var height = min(1000.0, size.y - 80)
	var width = height * natural.x / natural.y
	if alt_zoom: width = 760
	if width > size.x - 80: width = size.x - 80;height = width * natural.y / natural.x
	preview_art.configure(store, source, Vector2(width, height));preview_panel.reset_size()
	preview_panel.show();_position_preview()

func _position_preview():
	if not is_instance_valid(preview_panel) or not preview_panel.visible: return
	if alt_zoom: preview_panel.position = (size - preview_panel.size) / 2
	else:
		var pointer = get_global_mouse_position()
		preview_panel.position = Vector2(clamp(pointer.x - preview_panel.size.x - 20, 16, size.x - preview_panel.size.x - 16), clamp(pointer.y - preview_panel.size.y - 16, 16, size.y - preview_panel.size.y - 16))

func show_toast(message: String):
	toast_serial += 1; var serial = toast_serial
	toast_label.text = GuildLang.t(message);toast_label.show();toast_label.reset_size();toast_label.position = Vector2((size.x - toast_label.size.x) / 2, 25)
	toast_label.modulate.a = 0
	if prefs.motion: create_tween().tween_property(toast_label, "modulate:a", 1.0, 0.16)
	else: toast_label.modulate.a = 1
	get_tree().create_timer(4.5).timeout.connect( func(): if serial == toast_serial: toast_label.hide())

func _hide_final_notice():
	final_notice_serial += 1
	if is_instance_valid(final_notice): final_notice.queue_free()
	final_notice = null

func _position_final_notice():
	if is_instance_valid(final_notice):
		final_notice.size.x = minf(1040, size.x - 64)
		final_notice.position = Vector2((size.x - final_notice.size.x) / 2, size.y * 0.35 - final_notice.size.y / 2)

func _show_final_notice():
	_hide_final_notice()
	var serial = final_notice_serial
	var body = VBoxContainer.new();body.add_theme_constant_override("separation", 20)
	final_notice = panel(body, 32);final_notice.name = "FinalNotice";final_notice.z_index = 90;final_notice.mouse_filter = MOUSE_FILTER_IGNORE
	add_child(final_notice)
	for item in [["最终阶段开始", 52, GOLD], ["文明与瘴气相邻。每位公会长最多再行动两次。", 28, INK], ["金币产能最多减少20，取得等量金币。", 24, MUTED]]:
		var text = label(item[0], item[1], item[2]);text.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER;text.mouse_filter = MOUSE_FILTER_IGNORE;body.add_child(text)
	final_notice.size = Vector2(minf(1040, size.x - 64), 240);_position_final_notice()
	get_tree().create_timer(6.0).timeout.connect( func(): if serial == final_notice_serial: _hide_final_notice())

func _sync_game_feedback():
	var game = session.game; var phase = game.get("phase", ""); var feedback = game.get("feedback", {})
	var scope = session.room_id; var event_id = int(feedback.get("id", 0)); var round_number = int(game.get("round", 1)); var actions = int(game.get("action_count", 0))
	var was_scope = feedback_scope; var was_phase = last_phase
	if not was_phase.is_empty() and was_scope == scope:
		if phase == "final" and was_phase != "final": play_sound("final");_show_final_notice()
		elif last_feedback != event_id: play_sound(feedback.get("kind", "card"));show_toast(feedback.get("message", ""))
		elif was_phase != phase or last_round != round_number: play_sound("season")
		elif last_action_count != actions: play_sound("card")
	feedback_scope = scope;last_feedback = event_id;last_phase = phase;last_round = round_number;last_action_count = actions
	# 客座模式：行动席换人时弹公告，确认后继续（终局结算不再弹）。
	var seat = int(game.view_player) if game.get("view_player") != null else -1
	if session.local_mode and phase != "finished" and seat >= 0 and last_view_player >= 0 and seat != last_view_player and modal_key != "seat":
		dialogs.seat_change(seat)
	last_view_player = seat
	# 公会委托板：每季结算后弹出完成公告。
	var report = game.get("quest_report", {})
	var report_serial = int(report.get("serial", 0)) if report is Dictionary else 0
	if was_scope == scope and not was_phase.is_empty() and report_serial > 0 and report_serial != last_quest_report and modal_key != "quest_report":
		dialogs.quest_report(report)
	last_quest_report = report_serial

func open_dialog(title: String, dimensions: Vector2 = Vector2(1020, 760), key: String = "") -> VBoxContainer:
	close_dialog(false);modal_key = key
	var shade = ColorRect.new();shade.color = Color(0, 0, 0, 0.68);modal_layer.add_child(shade);shade.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	dialog = shade
	var container = PanelContainer.new();container.add_theme_stylebox_override("panel", GuildPaperSkin.player_frame(20));shade.add_child(container);container.size = dimensions;container.position = (size - dimensions) / 2
	var body = VBoxContainer.new();container.add_child(body)
	var header = HBoxContainer.new();body.add_child(header)
	var heading = label(title, 28, GOLD);heading.size_flags_horizontal = Control.SIZE_EXPAND_FILL;header.add_child(heading)
	if key != "pending": header.add_child(button("关闭", close_dialog))
	if prefs.motion:
		container.modulate.a = 0;container.position.y += 16
		var tween = create_tween().set_parallel(true);tween.tween_property(container, "modulate:a", 1.0, 0.18);tween.tween_property(container, "position:y", container.position.y - 16, 0.18)
	return body

func close_dialog(restore_pending: bool = true):
	if dialog: dialog.queue_free();dialog = null
	modal_key = "";pending_id = -1;hover_source = "";last_hover_source = "";preview_panel.hide()
	if restore_pending: rerender()

func _render():
	if is_instance_valid(voice): voice.sync()
	if session.game.is_empty():
		_hide_final_notice();last_phase = "";last_feedback = -1;last_round = -1;last_action_count = -1;feedback_scope = "";last_view_player = -1;last_quest_report = -1
	elif session.game.get("phase") == "finished" and last_phase != "finished":
		_hide_final_notice()
		if modal_key != "settings": close_dialog(false)
	for child in content.get_children(): content.remove_child(child);child.queue_free()
	hover_source = "";preview_panel.hide()
	var freshly_home = session.game.is_empty() and session.room.is_empty() and not session.directory
	if freshly_home and not backdrop.home: home_portrait = ""
	backdrop.home = freshly_home;backdrop.queue_redraw()
	if session.game.is_empty(): selection_scroll_states.clear()
	if session.game.is_empty() and not session.room.is_empty(): GuildRenpyShell.room(self, content);return
	if session.game.is_empty() and not session.directory: GuildRenpyShell.home(self, content);return
	if not session.game.is_empty():
		_render_game(content)
		_sync_game_feedback()
		var current_pending = session.game.get("pending")
		if current_pending is Dictionary and int(current_pending.player) == session.player_id:
			if modal_key not in ["market", "settings", "payment_preference", "seat"] and pending_id != int(current_pending.id): dialogs.pending(current_pending)
		elif modal_key == "pending": close_dialog()
		return
	var margin = MarginContainer.new();content.add_child(margin);margin.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	for side in ["left", "right", "top", "bottom"]: margin.add_theme_constant_override("margin_" + side, 24)
	var root = VBoxContainer.new();margin.add_child(root)
	backdrop.home = session.game.is_empty() and session.room.is_empty() and not session.directory;backdrop.queue_redraw()
	var header = HBoxContainer.new();root.add_child(panel(header, 10))
	var brand = label("异世界公会长", 28, GOLD);brand.size_flags_horizontal = Control.SIZE_EXPAND_FILL;header.add_child(brand)
	if session.game.is_empty(): header.add_child(label("GUILD MASTER", 14, MUTED))
	else:
		header.add_child(button("公会记录", func(): dialogs.game_log()))
		header.add_child(button("撤回", func(): session.action("undo"), session.game.get("undo", {}).get("available", false)))
		header.add_child(art_button(store.catalog.achievements.royal133.source, "王权", func(): dialogs.achievements()))
		header.add_child(symbol_button("gold", "售牌", func(): dialogs.market(), session.role == "player"))
	header.add_child(button("图鉴", func(): dialogs.gallery()))
	header.add_child(button("设置", func(): dialogs.settings()))
	if not session.room.is_empty() or session.directory: header.add_child(button("离开", func(): dialogs.leave()))
	if not session.game.is_empty(): _render_game(root)
	elif not session.room.is_empty(): _render_room(root)
	elif session.directory: _render_directory(root)
	else: _render_home(root)
	var pending = session.game.get("pending")
	if pending is Dictionary and int(pending.player) == session.player_id:
		if modal_key != "seat" and pending_id != int(pending.id): dialogs.pending(pending)
	elif modal_key == "pending": close_dialog()

func _render_home(root: VBoxContainer):
	var center = HBoxContainer.new();center.size_flags_vertical = Control.SIZE_EXPAND_FILL;root.add_child(center)
	center.add_theme_constant_override("separation", 48)
	var menu = VBoxContainer.new();menu.custom_minimum_size.x = 460;center.add_child(menu);menu.add_spacer(false)
	menu.add_child(label("异世界公会长", 56, Color("fffdf7")))
	menu.add_child(label("一张委托，开启你的冒险。", 22, Color("fffdf7")))
	var actions = VBoxContainer.new();actions.custom_minimum_size.x = 450
	menu.add_child(panel(actions))
	actions.add_child(label("准备出发", 29, GOLD))
	var name_input = LineEdit.new();name_input.placeholder_text = GuildLang.t("公会长昵称");name_input.text = prefs.name;actions.add_child(name_input)
	var address_input = LineEdit.new();address_input.placeholder_text = GuildLang.t("服务器地址");address_input.text = prefs.address;actions.add_child(address_input)
	var port_input = SpinBox.new();port_input.min_value = 1;port_input.max_value = 65535;port_input.value = prefs.port;actions.add_child(port_input)
	actions.add_child(button("连接游玩服务器", func():
		prefs.name = name_input.text;prefs.address = address_input.text;prefs.port = int(port_input.value);save_preferences()
		session.connect_server(prefs.address, prefs.port, prefs.name);show_toast("正在连接服务器…"), true, true))
	actions.add_child(button("离线单人挑战", func(): prefs.name = name_input.text;save_preferences();session.start_local(prefs.name);show_toast("正在准备离线公会…")))
	actions.add_child(label("Alt 放大卡片 · Esc 设置 · F11 全屏", 16, MUTED))
	menu.add_spacer(false)
	var story = VBoxContainer.new();story.size_flags_horizontal = Control.SIZE_EXPAND_FILL;center.add_child(story);story.add_spacer(false)
	var sheet = VBoxContainer.new();sheet.add_child(label("本日开张！", 36, GOLD))
	var hero = store.catalog.heroes.hainie_red
	sheet.add_child(card(hero.source[0], Vector2(750, 410), func(): dialogs.art_detail(hero.source[0], hero.name)))
	var showcase = HBoxContainer.new();sheet.add_child(showcase)
	for number in [1, 50, 78]: showcase.add_child(card(store.card_face(store.card(number)), Vector2(180, 235), func(): dialogs.card_detail(number)))
	var frame = panel(sheet);story.add_child(frame);story.add_spacer(false)

func _render_directory(root: VBoxContainer):
	var sheet = VBoxContainer.new(); var frame = panel(sheet, 22);frame.size_flags_vertical = Control.SIZE_EXPAND_FILL;root.add_child(frame)
	var bar = HBoxContainer.new();sheet.add_child(bar)
	var heading = label("旅人的公会大厅", 34, GOLD);heading.size_flags_horizontal = Control.SIZE_EXPAND_FILL;bar.add_child(heading)
	bar.add_child(button("刷新", func(): session.send({"type": "list_rooms"})))
	bar.add_child(button("创建公会房间", func(): dialogs.create_room(), true, true))
	var rooms_box = VBoxContainer.new();sheet.add_child(scroll(rooms_box))
	if session.rooms.is_empty(): rooms_box.add_child(label("暂时没有房间。创建一间公会，邀请伙伴加入。", 22, MUTED))
	for room in session.rooms:
		var row = HBoxContainer.new();rooms_box.add_child(panel(row))
		var info = VBoxContainer.new();info.size_flags_horizontal = Control.SIZE_EXPAND_FILL;row.add_child(info)
		info.add_child(label(room.get("name", "公会"), 26, GOLD));info.add_child(label("房间 %s · %s / %s 人%s" % [room.get("id", ""), str(room.get("player_count", room.get("players", 0))), str(room.get("max_players", 4)), " · 已开始" if room.get("started", false) else " · 等待冒险"], 17, MUTED))
		row.add_child(button("加入", func(): dialogs.enter_room(room, "player")))
		row.add_child(button("观战", func(): dialogs.enter_room(room, "spectator"), room.get("allow_spectators", true)))

func _render_room(root: VBoxContainer):
	var room = session.room
	root.add_child(label(room.get("name", "旅人的公会"), 34, GOLD))
	root.add_child(label("等待伙伴准备 · 房间 " + session.room_id if not room.get("drafting", false) else "命运的相遇 · 选择你的看板娘", 18, MUTED))
	if room.get("drafting", false):
		var choices = HBoxContainer.new();root.add_child(scroll(choices))
		for character in room.get("hero_offers", []):
			var identity = store.catalog.characters.get(character, {})
			var column = VBoxContainer.new();choices.add_child(panel(column));column.custom_minimum_size.x = 250
			column.add_child(label(identity.get("name", character), 27, GOLD))
			for variant in ["white", "black"]:
				var hero_key = identity.get("variants", {}).get(variant, "")
				var hero = store.catalog.heroes.get(hero_key, {})
				if hero.is_empty() or not hero.get("available", false): continue
				column.add_child(card(hero.source[0], Vector2(230, 165), func(): voice.play_event(hero_key, "intro");dialogs.art_detail(hero.source[0], hero.name)))
				column.add_child(button("选择" + ("白版" if variant == "white" else "黑版"), func(): session.send({"type": "set_hero", "character": character, "variant": variant}), true, true))
		return
	var seats = HBoxContainer.new();root.add_child(seats)
	for player in room.get("players", []):
		var seat = VBoxContainer.new();seat.custom_minimum_size.x = 220;seats.add_child(panel(seat))
		seat.add_child(label(player.name, 25, GOLD));seat.add_child(label("已准备" if player.get("ready", false) else "等待准备", 20, Color("8eb69b") if player.get("ready", false) else MUTED))
		seat.add_child(label("在线" if player.get("connected", true) else "等待重新连接", 17, MUTED))
		if int(room.get("host_id", -1)) == session.player_id and int(player.id) != session.player_id:
			seat.add_child(button("移出房间", func(): session.send({"type": "kick", "target_id": int(player.id)})))
	var rule_text = store.catalog.option_labels
	var enabled = []
	for key in rule_text: if room.get("options", {}).get(key, false): enabled.append(rule_text[key])
	root.add_child(label("规则：" + " · ".join(enabled), 18, MUTED))
	root.add_spacer(false)
	var bar = HBoxContainer.new();root.add_child(bar)
	if not session.local_mode: bar.add_child(button("准备 / 取消准备", func():
		var mine = {}
		for p in room.players: if int(p.id) == session.player_id: mine = p
		session.send({"type": "ready", "ready": not mine.get("ready", false)}), session.role == "player"))
	if int(room.get("host_id", -1)) == session.player_id:
		bar.add_child(button("修改对局规则", func(): dialogs.room_options()))
		bar.add_child(button("开始冒险", func(): session.send({"type": "start"}), true, true))
	_chat(root)

func _render_game(root: Control):
	GuildTableView.draw(self, root)

func _render_hand(root: VBoxContainer, me: Dictionary, phase: String):
	var bar = HBoxContainer.new();root.add_child(panel(bar, 8))
	var heading = label("你的手牌", 20, GOLD);heading.size_flags_horizontal = Control.SIZE_EXPAND_FILL;bar.add_child(heading)
	bar.add_child(label("悬浮预览 · 按住 Alt 放大 · 点击查看与打出", 15, MUTED))
	var cards = me.get("hand", [])
	if phase == "research": cards = me.get("offered", []);heading.text = "情报收集 · 选择保留的事件"
	elif phase == "draft": cards = me.get("draft_cards", []);heading.text = "开局轮抽 · 选择一张保留"
	var signature = JSON.stringify(cards) + phase
	var new_packet = signature != research_packet
	if new_packet: research_packet = signature;selected_research = []
	var strip = HBoxContainer.new();strip.add_theme_constant_override("separation", 14)
	var scroller = ScrollContainer.new();scroller.name = "HandStrip";scroller.custom_minimum_size.y = 180;scroller.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_AUTO;scroller.vertical_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED;root.add_child(scroller);scroller.add_child(strip)
	for index in range(cards.size()):
		var number = int(cards[index]); var data = store.card(number)
		var art = card(store.card_face(data), Vector2(112, 158), func():
			if phase in ["research", "draft"]:
				if selected_research.has(index): selected_research.erase(index)
				else:
					if phase == "draft": selected_research = []
					selected_research.append(index)
				_render()
			else: dialogs.card_detail(number))
		art.selected = selected_research.has(index);strip.add_child(art)
		if new_packet and prefs.motion:
			art.modulate.a = 0;art.scale = Vector2(0.94, 0.94)
			var deal = art.create_tween().set_parallel(true).set_trans(Tween.TRANS_CUBIC).set_ease(Tween.EASE_OUT)
			deal.tween_property(art, "modulate:a", 1.0, 0.22).set_delay(index * 0.025)
			deal.tween_property(art, "scale", Vector2.ONE, 0.26).set_delay(index * 0.025)
	if cards.is_empty(): strip.add_child(label("暂无手牌", 18, MUTED))
	if session.role == "spectator": heading.text = "观战 · 私人手牌不显示"
	elif phase == "research":
		var chosen = []
		for index in selected_research: chosen.append(int(cards[index]))
		var free = int(me.get("research_free", 0)); var total = 0 if session.game.get("round", 1) == 1 and me.get("research_initial_free", false) else max(0, chosen.size() - free) * 3
		bar.add_child(cost_button("保留 %s 张" % chosen.size(), "gold", total, func(): session.action("research", {"cards": chosen}), not me.get("researched", false), true))
		if session.game.get("round", 1) == 1 and not me.get("mulligan_done", false): bar.add_child(button("更换所选起始牌", func(): session.action("mulligan", {"cards": chosen}), chosen.size() <= 5))
	elif phase == "draft":
		bar.add_child(button("确认轮抽选择", func(): session.action("draft_pick", {"index": int(selected_research[0]), "draft_step": int(session.game.draft_step)}), selected_research.size() == 1 and me.get("draft_choice") == null, true))

func _chat(root: VBoxContainer):
	if session.local_mode: return
	var row = HBoxContainer.new();root.add_child(row)
	var input = LineEdit.new();input.placeholder_text = GuildLang.t("和公会伙伴说些什么…");input.size_flags_horizontal = Control.SIZE_EXPAND_FILL;row.add_child(input)
	var submit = func():
		if not input.text.strip_edges().is_empty(): session.send({"type": "chat", "message": input.text});input.clear()
	row.add_child(button("发送", submit));input.text_submitted.connect( func(_value): submit.call())

func _start_demo():

	if FileAccess.file_exists("res://data/demo.json"):
		var state = GuildSession.normalize(JSON.parse_string(FileAccess.get_file_as_string("res://data/demo.json")))
		session.set_process(false)
		session.game = state.game;session.room = state.room;session.player_id = 0;session.role = "player";session.active = true;dirty = true
		session.synchronized = true;session.room_connected = true

func stop_audio():
	if is_instance_valid(sound): sound.stop();sound.stream = null
	if is_instance_valid(voice): voice.stop()

func _exit_tree():
	session.close();stop_audio()
