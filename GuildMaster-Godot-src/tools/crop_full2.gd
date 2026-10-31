extends SceneTree

func _init() -> void:
	var src := Image.load_from_file("res://art/images/tts/pack16.webp")
	if src == null:
		push_error("cannot load pack16")
		quit(1)
		return
	var crops := {332: Rect2i(719, 0, 720, 1024), 338: Rect2i(719, 1024, 720, 1024)}
	for cid: int in crops:
		var box: Rect2i = crops[cid]
		var img := Image.create(box.size.x, box.size.y, false, src.get_format())
		img.blit_rect(src, box, Vector2i.ZERO)
		print(cid, " saved ", img.save_png("res://.autoconverted/full_%d.png" % cid))
	quit(0)
