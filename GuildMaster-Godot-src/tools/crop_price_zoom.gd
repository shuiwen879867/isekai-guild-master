extends SceneTree

func _init() -> void:
	var src := Image.load_from_file("res://art/images/tts/pack16.webp")
	if src == null:
		push_error("cannot load pack16")
		quit(1)
		return
	# index 12 (card 332) at [719,0], index 18 (card 338) at [719,1024]
	var crops := {332: Rect2i(721, 8, 210, 210), 338: Rect2i(721, 1032, 210, 210), 331: Rect2i(2, 8, 210, 210)}
	for cid: int in crops:
		var box: Rect2i = crops[cid]
		var img := Image.create(box.size.x, box.size.y, false, src.get_format())
		img.blit_rect(src, box, Vector2i.ZERO)
		img.resize(630, 630, Image.INTERPOLATE_NEAREST)
		print(cid, " saved ", img.save_png("res://.autoconverted/price_%d.png" % cid))
	quit(0)
