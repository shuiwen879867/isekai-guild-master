extends SceneTree

func _init() -> void:
	var src := Image.load_from_file("res://art/images/tts/pack16.webp")
	if src == null:
		push_error("cannot load pack16")
		quit(1)
		return
	# D-014 card at [2158,0,720,1024]; zoom into the price circle area.
	var box := Rect2i(2160, 8, 210, 210)
	var img := Image.create(box.size.x, box.size.y, false, src.get_format())
	img.blit_rect(src, box, Vector2i.ZERO)
	img.resize(630, 630, Image.INTERPOLATE_NEAREST)
	var err := img.save_png("res://.autoconverted/card334_price_zoom.png")
	print("zoom saved ", err)
	# Also D-015 price circle for comparison (two red icons).
	var box2 := Rect2i(2880, 8, 210, 210)
	var img2 := Image.create(box2.size.x, box2.size.y, false, src.get_format())
	img2.blit_rect(src, box2, Vector2i.ZERO)
	img2.resize(630, 630, Image.INTERPOLATE_NEAREST)
	print("zoom2 saved ", img2.save_png("res://.autoconverted/card315_price_zoom.png"))
	quit(0)
