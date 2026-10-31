class_name GuildCardArt
extends Control

var store: GuildArtStore
var source = ""
var selected = false:
	set(value):
		selected = value;queue_redraw()
var highlight = false:
	set(value):
		highlight = value;queue_redraw()
var interactive = false
var on_click: Callable
var on_hover: Callable
var on_leave: Callable
var motion = true
var tween: Tween

func configure(assets: GuildArtStore, image: String, dimensions: Vector2):
	store = assets;source = image;custom_minimum_size = dimensions
	size = dimensions;mouse_filter = MOUSE_FILTER_STOP if interactive else MOUSE_FILTER_IGNORE
	queue_redraw()

func _ready():
	resized.connect( func(): pivot_offset = size / 2;queue_redraw())
	get_viewport().size_changed.connect(queue_redraw)
	mouse_entered.connect(_hover)
	mouse_exited.connect(_leave)

func _draw():
	if not store or source.is_empty(): return
	var natural = store.natural_size(source)
	var factor = min(size.x / natural.x, size.y / natural.y)
	var area = Rect2((size - natural * factor) / 2, natural * factor)
	var shade = StyleBoxFlat.new();shade.bg_color = Color("070f14")
	shade.shadow_color = Color(0, 0, 0, 0.4);shade.shadow_size = 10;shade.shadow_offset = Vector2(0, 5)
	shade.set_corner_radius_all(7);draw_style_box(shade, area)
	# 卡面一律使用扫描图；card_layouts 仅保留迷宫板块的复合版面。
	var layout = store.layouts.get(source, {}) if store.layouts.has(source) else {}
	if layout.get("kind") == "tile" and layout.get("render_mode") != "native_font_text":
		var paper = store.texture(layout.paper); var atlas = store.texture(layout.atlas)
		if paper: draw_texture_rect(paper, area, false)
		if atlas:
			for part in layout.parts:
				var b = part.box
				draw_texture_rect_region(atlas, Rect2(area.position + Vector2(float(part.x), float(part.y)) * factor, Vector2(float(b[2]), float(b[3])) * factor), Rect2(float(b[0]), float(b[1]), float(b[2]), float(b[3])))
	else:
		var tex = store.texture(source)
		if tex: draw_texture_rect(tex, area, false)
	if selected:
		draw_rect(area, Color(0.1, 0.08, 0.1, 0.58))
		draw_rect(area.grow(3), Color("9f4c50"), false, 4)
		draw_selection_label(area.get_center(), area.size.x)
	elif highlight:
		draw_rect(area, Color(0.93, 0.78, 0.35, 0.10))
		draw_rect(area.grow(4), Color("d4a94a"), false, 5)
		draw_highlight_label(area)

func draw_highlight_label(area: Rect2):
	var font = get_theme_default_font()
	var points = clampi(int(area.size.x * 0.075), 17, 28)
	var text = GuildLang.t("可完成")
	var text_size = font.get_string_size(text, HORIZONTAL_ALIGNMENT_LEFT, -1, points)
	var center = Vector2(area.get_center().x, area.position.y + points + 20)
	var bounds = Rect2(center - Vector2(text_size.x + 30, points + 18) / 2, Vector2(text_size.x + 30, points + 18))
	var badge = StyleBoxFlat.new();badge.bg_color = Color("a8791f");badge.border_color = Color("f6e2ae")
	badge.set_border_width_all(2);badge.set_corner_radius_all(8);draw_style_box(badge, bounds)
	var baseline = center + Vector2(-text_size.x / 2, (font.get_ascent(points) - font.get_descent(points)) / 2)
	draw_string(font, baseline, text, HORIZONTAL_ALIGNMENT_LEFT, -1, points, Color("fffdf7"))

func draw_selection_label(center: Vector2, available_width: float):
	var font = get_theme_default_font()
	var points = clampi(int(available_width * 0.12), 18, 32)
	var text = GuildLang.t("已选择")
	var text_size = font.get_string_size(text, HORIZONTAL_ALIGNMENT_LEFT, -1, points)
	var bounds = Rect2(center - Vector2(text_size.x + 28, points + 24) / 2, Vector2(text_size.x + 28, points + 24))
	var badge = StyleBoxFlat.new();badge.bg_color = Color("874449");badge.border_color = Color("e5ddcd")
	badge.set_border_width_all(2);badge.set_corner_radius_all(6);draw_style_box(badge, bounds)
	var baseline = center + Vector2( - text_size.x / 2, (font.get_ascent(points) - font.get_descent(points)) / 2)
	draw_string(font, baseline, text, HORIZONTAL_ALIGNMENT_LEFT, -1, points, Color("fffdf7"))

func _gui_input(event):
	if interactive and event is InputEventMouseButton and event.button_index == MOUSE_BUTTON_LEFT and event.pressed:
		if on_click.is_valid(): on_click.call()
		accept_event()

func _hover():
	if not interactive: return
	z_index = 5
	if motion:
		if tween: tween.kill()
		tween = create_tween().set_trans(Tween.TRANS_CUBIC).set_ease(Tween.EASE_OUT)
		tween.tween_property(self, "scale", Vector2(1.075, 1.075), 0.16)
	if on_hover.is_valid(): on_hover.call(source)

func _leave():
	z_index = 0
	if tween: tween.kill()
	if motion: create_tween().tween_property(self, "scale", Vector2.ONE, 0.12)
	else: scale = Vector2.ONE
	if on_leave.is_valid(): on_leave.call(source)
