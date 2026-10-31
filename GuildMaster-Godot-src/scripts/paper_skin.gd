class_name GuildPaperSkin
extends RefCounted

static func paper(state: String = "paper", padding: int = 16) -> StyleBoxTexture:
	var result = StyleBoxTexture.new();result.texture = load("res://ui/comic/" + state + ".svg")
	for side in [SIDE_LEFT, SIDE_TOP, SIDE_RIGHT, SIDE_BOTTOM]:
		result.set_texture_margin(side, 12);result.set_content_margin(side, padding)
	return result

static func main_frame(padding: int = 0) -> StyleBoxTexture:
	var result = StyleBoxTexture.new();result.texture = load("res://ui/comic/main_frame.svg")
	result.set_texture_margin(SIDE_LEFT, 26);result.set_texture_margin(SIDE_TOP, 24)
	result.set_texture_margin(SIDE_RIGHT, 26);result.set_texture_margin(SIDE_BOTTOM, 24)
	for side in [SIDE_LEFT, SIDE_TOP, SIDE_RIGHT, SIDE_BOTTOM]:
		result.set_content_margin(side, padding)
	return result

static func player_frame(padding: int = 0) -> StyleBoxTexture:
	var result = StyleBoxTexture.new();result.texture = load("res://ui/comic/player_frame.svg")
	result.set_texture_margin(SIDE_LEFT, 35);result.set_texture_margin(SIDE_TOP, 30)
	result.set_texture_margin(SIDE_RIGHT, 35);result.set_texture_margin(SIDE_BOTTOM, 30)
	for side in [SIDE_LEFT, SIDE_TOP, SIDE_RIGHT, SIDE_BOTTOM]:
		result.set_content_margin(side, padding)
	return result

static func banner(state: String = "normal", padding: int = 10) -> StyleBox:
	var pressed = state in ["pressed", "primary_pressed"]
	var source = load("res://ui/buttons/banner_pressed.png" if pressed else "res://ui/buttons/banner_normal.png")
	var tint = Color.WHITE
	match state:
		"hover": tint = Color(1.12, 1.07, 1.0)
		"disabled": tint = Color(0.82, 0.80, 0.78, 0.85)
		"primary": tint = Color(0.74, 0.40, 0.47)
		"primary_hover": tint = Color(0.86, 0.48, 0.55)
		"primary_pressed": tint = Color(0.74, 0.40, 0.47)
	return GuildBannerBox.create(source, tint, maxf(6.0, padding * 0.8), 2.0)

static func primary_state(state: String) -> String:
	return {"normal": "primary", "hover": "primary_hover", "pressed": "primary_pressed", "disabled": "disabled"}.get(state, state)

static func plaque(state: String = "normal", padding: int = 6) -> StyleBox:
	var pressed = state in ["pressed", "primary_pressed"]
	var source = load("res://ui/buttons/plaque_pressed.png" if pressed else "res://ui/buttons/plaque_normal.png")
	var tint = Color.WHITE
	match state:
		"hover": tint = Color(1.12, 1.07, 1.0)
		"disabled": tint = Color(0.82, 0.80, 0.78, 0.85)
		"primary": tint = Color(0.74, 0.40, 0.47)
		"primary_hover": tint = Color(0.86, 0.48, 0.55)
		"primary_pressed": tint = Color(0.74, 0.40, 0.47)
	var box: GuildBannerBox = GuildBannerBox.create(source, tint, maxf(6.0, padding), 2.0)
	box.cap_left = 184.0
	box.cap_right = 172.0
	return box

static func title_font() -> Font:
	return GuildLang.title_font()
