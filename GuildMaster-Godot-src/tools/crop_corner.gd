extends SceneTree

func _init() -> void:
	var src := Image.load_from_file("res://art/images/tts/pack16.webp")
	if src == null:
		push_error("cannot load pack16")
		quit(1)
		return
	# bottom-right corner of cards 331 [0,0] and 332 [719,0]
	var crops := {331: Rect2i(0 + 430, 0 + 760, 289, 264), 332: Rect2i(719 + 430, 0 + 760, 289, 264)}
	for cid: int in crops:
		var box: Rect2i = crops[cid]
		var img := Image.create(box.size.x, box.size.y, false, src.get_format())
		img.blit_rect(src, box, Vector2i.ZERO)
		img.resize(578, 528, Image.INTERPOLATE_LANCZOS)
		print(cid, " saved ", img.save_png("res://.autoconverted/corner_%d.png" % cid))
	quit(0)
