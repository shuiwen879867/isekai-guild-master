class_name GuildArtStore
extends RefCounted

var catalog = {}
var layouts = {}
var textures = {}
var tiles = {}
var texture_order = []
var mode: String = "multi"

func card_face(data: Dictionary) -> String:
	"""Face for this game mode; falls back to the base (multiplayer) print."""
	var source = str(data.get("source", ""))
	if mode == "solo":
		var variants = data.get("face_variants", {})
		if variants is Dictionary:
			var solo = str(variants.get("solo", ""))
			if not solo.is_empty(): return solo
	return source

func remember(source: String, value: Texture2D) -> Texture2D:
	textures[source] = value;texture_order.append(source)
	while texture_order.size() > 64: textures.erase(texture_order.pop_front())
	return value

func _init():
	catalog = JSON.parse_string(FileAccess.get_file_as_string("res://data/catalog.json"))
	layouts = JSON.parse_string(FileAccess.get_file_as_string("res://data/card_layouts.json"))

func texture(source: String) -> Texture2D:
	if source.is_empty(): return null
	if textures.has(source): return textures[source]
	var atlas = catalog.atlas.get(source)
	if atlas is Dictionary:
		var base = texture(atlas.path)
		if base == null: return null
		var result = AtlasTexture.new();result.atlas = base
		var box = atlas.box;result.region = Rect2(float(box[0]), float(box[1]), float(box[2]), float(box[3]))
		return remember(source, result)


	var root = ProjectSettings.globalize_path("res://") if OS.has_feature("editor") else OS.get_executable_path().get_base_dir()
	var path = root.path_join("art").path_join(source)
	if not FileAccess.file_exists(path) and source.begins_with("images/"):
		path = root.path_join("art").path_join(source.trim_prefix("images/"))
	if not FileAccess.file_exists(path): return null
	var bitmap = Image.load_from_file(path)
	if bitmap == null or bitmap.is_empty(): return null
	var result = ImageTexture.create_from_image(bitmap)
	return remember(source, result)

func natural_size(source: String) -> Vector2:
	if layouts.has(source): return Vector2(float(layouts[source].width), float(layouts[source].height))
	var tex = texture(source)
	return tex.get_size() if tex else Vector2(720, 1024)

func card(number) -> Dictionary: return catalog.cards.get(str(int(number)), {})

func portrait(hero_key: String, affection: int = 0) -> Texture2D:
	var dedicated = texture("images/portraits/" + hero_key + ".webp")
	if dedicated != null: return dedicated
	var hero = catalog.heroes.get(hero_key, {})
	var source = hero.get("portrait", "")
	if not source.is_empty(): return texture(source)
	var sources = hero.get("source", [])
	if sources.is_empty(): return null
	source = sources[min(sources.size() - 1, 2 if affection >= 5 else 1 if affection >= 2 else 0)]
	var key = "portrait:" + source
	if textures.has(key): return textures[key]
	var base = texture(source)
	if base == null: return null
	var image_size = base.get_size(); var result = AtlasTexture.new();result.atlas = base

	var area = Rect2(0.135, 0.065, 0.33, 0.825) if hero.get("variant") == "black" else Rect2(0.025, 0.055, 0.45, 0.845)
	result.region = Rect2(area.position * image_size, area.size * image_size)
	return remember(key, result)

func portrait_bust(hero_key: String, affection: int = 0) -> Texture2D:
	var dedicated = texture("images/portraits/" + hero_key + ".webp")
	if dedicated == null: return portrait(hero_key, affection)
	var key = "bust:" + hero_key
	if textures.has(key): return textures[key]
	var size = dedicated.get_size()
	var result = AtlasTexture.new();result.atlas = dedicated
	result.region = Rect2(size.x * 0.20, size.y * 0.03, size.x * 0.60, size.y * 0.57)
	return remember(key, result)

func adventurer_token(player_id: int, is_base: bool = false) -> Texture2D:
	var key = ("base:" if is_base else "adventurer:") + str(posmod(player_id, 5))
	if textures.has(key): return textures[key]
	var source = "images/ui/base_atlas.png" if is_base else "images/ui/" + ["red", "yellow", "blue", "green", "white"][posmod(player_id, 5)] + ".png"
	var base = texture(source)
	if base == null: return null
	var bitmap = base.get_image()
	if is_base: bitmap = bitmap.get_region(Rect2i([16, 445, 875, 1304, 1733][posmod(player_id, 5)], 144, 420, 420))
	bitmap.convert(Image.FORMAT_RGBA8);bitmap.resize(96, 96, Image.INTERPOLATE_LANCZOS)
	for y in range(96):
		for x in range(96):
			if Vector2(x + 0.5, y + 0.5).distance_to(Vector2(48, 48)) > 47: bitmap.set_pixel(x, y, Color.TRANSPARENT)
	return remember(key, ImageTexture.create_from_image(bitmap))

func tile_texture(source: String, resolution: int = 160) -> Texture2D:
	var key = source + "@" + str(resolution)
	if tiles.has(key): return tiles[key]
	var image: Image
	if layouts.has(source):
		var spec = layouts[source]
		var paper = texture(spec.paper); var atlas = texture(spec.atlas)
		if not paper or not atlas: return null
		image = paper.get_image();image.convert(Image.FORMAT_RGBA8)
		image.resize(int(spec.width), int(spec.height), Image.INTERPOLATE_BILINEAR)
		var glyphs = atlas.get_image();glyphs.convert(Image.FORMAT_RGBA8)
		for part in spec.parts:
			var box = part.box
			image.blend_rect(glyphs, Rect2i(int(box[0]), int(box[1]), int(box[2]), int(box[3])), Vector2i(int(part.x), int(part.y)))
	else:
		var tex = texture(source)
		if not tex: return null
		image = tex.get_image();image.convert(Image.FORMAT_RGBA8)
	image.resize(resolution, resolution, Image.INTERPOLATE_LANCZOS)
	# 六角遮罩貼齊原圖描邊外緣：左右尖端 ±0.5、上下平邊 ±0.446、斜邊 |x|+0.565|y| = 0.5，
	# 與板塊圖自身的六角形一致（避免左上/右下露白邊、右上/左下被切）；邊緣 2px 羽化。
	var feather = 2.0 / float(resolution)
	for y in range(resolution):
		for x in range(resolution):
			var px = abs(float(x) / float(resolution - 1) - 0.5); var py = abs(float(y) / float(resolution - 1) - 0.5)
			var over = maxf(py - 0.446, px + 0.565 * py - 0.5)
			if over > 0.0:
				image.set_pixel(x, y, Color.TRANSPARENT)
			elif over > -feather:
				var pixel = image.get_pixel(x, y);pixel.a *= clampf(-over / feather, 0.0, 1.0);image.set_pixel(x, y, pixel)
	var result = ImageTexture.create_from_image(image);tiles[key] = result
	while tiles.size() > 64: tiles.erase(tiles.keys()[0])
	return result
