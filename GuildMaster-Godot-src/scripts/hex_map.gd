class_name GuildHexMap
extends Control

signal cell_clicked(cell: Dictionary)
signal cell_hovered(cell: Dictionary)
var store: GuildArtStore
var game = {}
var player_id = -1
var hovered = ""
var points = {}
var step = 76.0
var motion = true
var pulse = 0.0
var selection_only = false
var option_ids = {}
var chosen_ids = []
var renpy_geometry = false
var owner_colors = [Color("d99487"), Color("d9bd77"), Color("84abc6"), Color("8ab9a2"), Color("baa4d3")]
# 迷宫未揭示格的同心色环（外→内），一般迷宫／大深度迷宫各一套（2026-10 依实体版面配色）。
var ring_colors = {
	"deep": {1: Color("b1a97f"), 2: Color("7d8a5f"), 3: Color("6e8c91"), 4: Color("5b5245")},
	"normal": {1: Color("c3b184"), 2: Color("dd8a5f"), 3: Color("a57a8c")},
}
var boss_fill = Color("6e5238")
var blocked_fill = Color("3a3733")
var blocked_star = Color("f2efe8")
var animated_outlines = []
var hit_polygons = {}
var pulse_layer: Control
var cached_viewport: SubViewport
var cached_painter: Control

class PulseLayer extends Control:
	var map_owner
	func _draw():
		if is_instance_valid(map_owner): map_owner.draw_pulse(self)

class StaticLayer extends Control:
	var map_owner
	func _draw():
		if is_instance_valid(map_owner): map_owner.draw_static(self)

func _ready():
	mouse_filter = MOUSE_FILTER_STOP
	cached_viewport = SubViewport.new();cached_viewport.transparent_bg = true;cached_viewport.disable_3d = true;cached_viewport.handle_input_locally = false;add_child(cached_viewport)
	cached_painter = StaticLayer.new();cached_painter.map_owner = self;cached_painter.mouse_filter = MOUSE_FILTER_IGNORE;cached_viewport.add_child(cached_painter)
	pulse_layer = PulseLayer.new();pulse_layer.map_owner = self;pulse_layer.mouse_filter = MOUSE_FILTER_IGNORE;add_child(pulse_layer)
	resized.connect(queue_redraw)
	mouse_exited.connect( func(): hovered = "";queue_redraw())

func _process(delta):
	if motion:
		pulse += delta
		if is_instance_valid(pulse_layer): pulse_layer.queue_redraw()

func draw_pulse(canvas: Control):
	if not motion: return
	var color = Color("874449").lerp(Color("bd7b78"), 0.5 + sin(pulse * 2) * 0.15)
	for outline in animated_outlines:
		if outline.id != hovered and not chosen_ids.has(outline.id): canvas.draw_polyline(outline.points, color, 3, true)

func set_game(snapshot: Dictionary, pid: int):
	game = snapshot;player_id = pid;queue_redraw()

func polygon(center: Vector2, radius: float) -> PackedVector2Array:
	var vertices = PackedVector2Array()
	for i in range(6): vertices.append(center + Vector2(cos(deg_to_rad(i * 60 - 90)), sin(deg_to_rad(i * 60 - 90))) * radius)
	return vertices

func star_polygon(center: Vector2, radius: float) -> PackedVector2Array:
	var vertices = PackedVector2Array()
	for i in range(10):
		var angle = deg_to_rad(i * 36.0 - 90.0);var reach = radius if i % 2 == 0 else radius * 0.42
		vertices.append(center + Vector2(cos(angle), sin(angle)) * reach)
	return vertices

func _draw():
	if not is_instance_valid(cached_viewport): return
	cached_viewport.size = Vector2i(maxi(1, ceili(size.x)), maxi(1, ceili(size.y)));cached_painter.size = size
	cached_painter.queue_redraw();cached_viewport.render_target_update_mode = SubViewport.UPDATE_ONCE
	draw_texture_rect(cached_viewport.get_texture(), Rect2(Vector2.ZERO, Vector2(cached_viewport.size)), false)

func draw_static(canvas: Control):
	var cells = game.get("board", [])
	if cells.is_empty(): return
	var xmin = 100.0; var xmax = -100.0; var ymin = 100.0; var ymax = -100.0
	for cell in cells:
		xmin = min(xmin, float(cell.q) + float(cell.r) / 2);xmax = max(xmax, float(cell.q) + float(cell.r) / 2)
		ymin = min(ymin, float(cell.r));ymax = max(ymax, float(cell.r))
	step = min(92.0, min((size.x - 36) / (xmax - xmin + 1.25), (size.y - 36) / ((ymax - ymin) * 0.866 + 1.3)))
	if renpy_geometry: step = min(110.0, min((size.x - 12) / (xmax - xmin + 1.1), (size.y - 12) / ((ymax - ymin) * 0.866 + 1.25)))
	var origin = Vector2(size.x / 2 - step * (xmin + xmax) / 2, size.y / 2 - step * 0.866 * (ymin + ymax) / 2)
	var font = get_theme_default_font()
	var rules = game.get("rules", {});if not rules is Dictionary: rules = {}
	var options = rules.get("options", {});if not options is Dictionary: options = {}
	var rings = ring_colors.get("deep", {}) if str(options.get("map_type", "normal")) == "deep" else ring_colors.get("normal", {})
	points = {};hit_polygons = {};animated_outlines = []
	var fills = []
	var unrevealed = {}
	for cell in cells:
		var p = origin + Vector2(step * (float(cell.q) + float(cell.r) / 2), step * 0.866 * float(cell.r));points[cell.id] = p
		var poly = polygon(p, step * 0.55);hit_polygons[cell.id] = poly
		var face_down = cell.get("owner") == null and not cell.get("revealed", false) and not cell.get("blocked", false) and not cell.get("outer", false)
		unrevealed[cell.id] = face_down
		var fill = Color("e5ddcd")
		if cell.get("blocked", false): fill = blocked_fill
		elif cell.get("owner") != null: fill = owner_colors[int(cell.owner) % 5].lightened(0.7)
		else:
			# 2026-10-26 复修：缝隙环色不应只属于已翻开格。未翻面／魔王格的背面板块图
			# 漂浮在底色之上（六角羽化边留出缝隙），底色给区域内圈/外圈对应的环色，
			# 缝隙即呈现环色；背面贴图本身仍是不透明上层，不会被颜色遮罩。
			var region = int(cell.get("region", 0))
			if rings.has(region): fill = Color(rings[region].r, rings[region].g, rings[region].b, 0.5)
		if cell.id == hovered: fill = Color(fill.r, fill.g, fill.b, 1.0).lightened(0.25)
		if chosen_ids.has(cell.id): fill = Color(fill.r, fill.g, fill.b, 1.0).lightened(0.4)
		fills.append([poly, fill])
	# 第一层：先画完所有底色，后面的格子才不会盖住已绘制格子的板块图。
	for entry in fills: canvas.draw_colored_polygon(entry[0], entry[1])
	# 第二层：未揭示格的背面板块图；用引擎算好的 back_source（一般＝piece_png/2、魔王＝87/88/17、变动＝tts/083）。
	# 不能用 cell.image——变动格 image=1083 没有对应版面会整体消失；魔王共用 image=17 会让 2/4 星误用 3 星背面。
	# 缺图时给木纹保底色，绝不再落回平底色环外观。
	for cell in cells:
		if not unrevealed.get(cell.id, false): continue
		var p = points[cell.id]
		var back = store.tile_texture(str(cell.get("back_source", "images/piece_png/2.png")))
		if back:
			canvas.draw_set_transform(p, - PI / 6, Vector2.ONE)
			canvas.draw_texture_rect(back, Rect2( - Vector2.ONE * step * 0.43, Vector2.ONE * step * 0.86), false)
			canvas.draw_set_transform(Vector2.ZERO)
		else: canvas.draw_colored_polygon(hit_polygons[cell.id], Color("c9b795"))
	# 第三层：边线（向内加粗）与格内内容。区域色环一律画在第一层底色上（含未翻面格），
	# 背面板块图作为不透明上层漂浮其上，缝隙透出环色，贴图本体不被颜色遮罩；
	# 区域辨识另由靠下的分数六角点承担。
	for cell in cells:
		var p = points[cell.id]
		var eligible = option_ids.has(cell.id) if selection_only else cell.get("eligible_for", []).has(player_id)
		var border = Color("302f31")
		if cell.get("owner") != null: border = owner_colors[int(cell.owner) % 5]
		if eligible: border = Color("874449").lerp(Color("bd7b78"), 0.6)
		if cell.id == hovered: border = Color("9f4c50")
		if chosen_ids.has(cell.id): border = Color("c9982e")
		var width = 4.0 if eligible or cell.id == hovered else 3.0
		var inset = polygon(p, maxf(8.0, step * 0.55 - width / 2.0));inset.append(inset[0])
		canvas.draw_polyline(inset, border, width, true)
		if eligible: animated_outlines.append({"id": cell.id, "points": inset})
		if cell.get("blocked", false):
			draw_icon(canvas, "star", p, step * 0.3);continue
		if cell.get("outer", false): canvas.draw_string(font, p + Vector2(-8, 7), "+", HORIZONTAL_ALIGNMENT_LEFT, -1, 22, Color("bd1630"));continue
		if cell.get("owner") != null:
			var color = owner_colors[int(cell.owner) % 5]
			var token = store.adventurer_token(int(cell.owner), cell.get("base", false))
			if token: canvas.draw_texture_rect(token, Rect2(p - Vector2(step * 0.285, step * 0.33), Vector2.ONE * step * 0.57), false)
			else: canvas.draw_circle(p, step * 0.23, color)
			var caption = GuildLang.t("据点 ×2" if cell.get("base", false) else "营地")
			var text_size = clampi(int(step * 0.15), 10, 14)
			canvas.draw_string(font, p + Vector2( - font.get_string_size(caption, HORIZONTAL_ALIGNMENT_LEFT, -1, text_size).x / 2, step * 0.36), caption, HORIZONTAL_ALIGNMENT_LEFT, -1, text_size, Color("343133"))
		elif cell.get("revealed", false):
			# 已揭示格：绘制板块图（漂在底色之上，保持清晰）。
			var art_source = str(store.catalog.tiles.get(str(cell.get("loot", "")), {}).get("source", ""))
			var tex = store.tile_texture(art_source) if not art_source.is_empty() else null
			if tex:
				canvas.draw_set_transform(p, - PI / 6, Vector2.ONE)
				canvas.draw_texture_rect(tex, Rect2( - Vector2.ONE * step * 0.43, Vector2.ONE * step * 0.86), false)
				canvas.draw_set_transform(Vector2.ZERO)
		elif cell.get("boss", false): canvas.draw_string(font, p + Vector2(-18, step * 0.27), GuildLang.t("魔王"), HORIZONTAL_ALIGNMENT_LEFT, -1, 15, Color("fffdf7"))
		# 潜行之龙站在任何一格都要可见——引擎允许龙潜入未翻开板块（_dragon_toward 的邻居筛选
		# 不排除 revealed），但旧实现只在「已揭示」分支里画龙，龙踏上未翻面格会整只消失，直到下次移动才回来。
		if not cell.get("blocked", false) and not cell.get("outer", false):
			var dragon = game.get("dragon", {})
			if dragon is Dictionary and dragon.get("active", false) and str(dragon.get("tile", "")) == str(cell.get("id", "")):
				draw_dragon(canvas, p, int(dragon.get("eggs", 0)))
		if cell.get("forest", false): canvas.draw_circle(p + Vector2( - step * 0.25, - step * 0.24), 5, Color("7da58d"))
		# 区域分数：靠下方一排小实心六角形（数量＝区域编号）；浅色格用黑色，深色背面用浅色。
		var score_region = int(cell.get("region", 0))
		if score_region > 0:
			var dark_cell = unrevealed.get(cell.id, false) or cell.get("boss", false)
			var spacing = 11.0;var dot_row = p.y + step * (0.42 if cell.get("owner") != null else 0.33)
			var dot_x0 = p.x - (score_region - 1) * spacing / 2.0
			for i in range(score_region):
				draw_icon(canvas, "dot_light" if dark_cell else "dot_dark", Vector2(dot_x0 + i * spacing, dot_row), 4.5)
	if is_instance_valid(pulse_layer): pulse_layer.queue_redraw()

func draw_dragon(canvas: Control, p: Vector2, eggs: int):
	var head = store.texture("images/ui/dragon head.png")
	var egg = store.texture("images/ui/dragon egg.png")
	var center = p + Vector2(0, - step * 0.045)
	var radius = step * 0.285
	canvas.draw_circle(center, radius, Color("f7f0e2"))
	canvas.draw_arc(center, radius, 0, TAU, 40, Color("343133"), 2, true)
	if head:
		var head_size = step * 0.46
		canvas.draw_texture_rect(head, Rect2(center - Vector2(head_size, head_size) / 2, Vector2(head_size, head_size)), false)
	if egg and eggs > 0:
		var egg_size = step * 0.19
		for i in range(eggs):
			var offset = Vector2((i - (eggs - 1) * 0.5) * (egg_size + 3), step * 0.36)
			canvas.draw_texture_rect(egg, Rect2(p + offset - Vector2(egg_size, egg_size) / 2, Vector2(egg_size, egg_size)), false)

var icon_cache = {}

func icon(key: String) -> Texture2D:
	if icon_cache.has(key): return icon_cache[key]
	# 玩家自订图标优先：把 PNG 放到 art/images/icons/star.png｜dot_dark.png｜dot_light.png 即生效。
	var custom = store.texture("images/icons/%s.png" % key)
	if custom:
		icon_cache[key] = custom;return custom
	# Godot 2D 的 draw_colored_polygon 没有抗锯齿（MSAA 不作用于 canvas 绘制指令），
	# 因此先用 6 倍超取样光栅化，再以 Lanczos 缩回 1 倍，边缘自然带 alpha 羽化，放大缩小都平滑。
	var px = 96;var ss = 6
	var shape = star_polygon(Vector2(px / 2.0, px / 2.0), px / 2.0 - 2.0)
	var color = Color("f2efe8")
	if key.begins_with("dot"):
		color = Color("1c1a1e") if key == "dot_dark" else Color("f2efe8")
		shape = polygon(Vector2(px / 2.0, px / 2.0), px / 2.0 - 2.0)
	var big = px * ss
	var img = Image.create(big, big, false, Image.FORMAT_RGBA8)
	var scaled = PackedVector2Array()
	for vertex in shape: scaled.append(vertex * ss)
	var count = scaled.size()
	for y in range(big):
		var spans = []
		for i in range(count):
			var a = scaled[i];var b = scaled[(i + 1) % count]
			if (a.y > y) != (b.y > y): spans.append(a.x + (b.x - a.x) * (y + 0.5 - a.y) / (b.y - a.y))
		spans.sort()
		for k in range(0, spans.size(), 2):
			var x0 = maxi(0, int(floor(spans[k])));var x1 = mini(big, int(ceil(spans[k + 1])))
			for x in range(x0, x1): img.set_pixel(x, y, color)
	img.resize(px, px, Image.INTERPOLATE_LANCZOS)
	var baked = ImageTexture.create_from_image(img)
	icon_cache[key] = baked
	return baked

# 以贴图绘制图标：vertex_radius 与向量版的图形顶点半径一致，位置为图形中心。
func draw_icon(canvas: Control, key: String, center: Vector2, vertex_radius: float):
	var tex = icon(key)
	if tex == null: return
	var side = vertex_radius * 2.0 * 96.0 / 92.0
	canvas.draw_texture_rect(tex, Rect2(center - Vector2.ONE * side / 2.0, Vector2.ONE * side), false)

func _gui_input(event):
	if event is InputEventMouseMotion:
		var previous = hovered;hovered = ""
		for key in points:
			if Geometry2D.is_point_in_polygon(event.position, hit_polygons[key]):
				hovered = key;break
		if previous != hovered:
			for cell in game.get("board", []):
				if cell.id == hovered: cell_hovered.emit(cell)
			queue_redraw()
	elif event is InputEventMouseButton and event.button_index == MOUSE_BUTTON_LEFT and event.pressed:
		for cell in game.get("board", []):
			if hit_polygons.has(cell.id) and Geometry2D.is_point_in_polygon(event.position, hit_polygons[cell.id]):
				cell_clicked.emit(cell);accept_event();break
