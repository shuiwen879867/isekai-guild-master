extends SceneTree

func _init() -> void:
	var src := Image.load_from_file("res://art/images/tts/pack16.webp")
	print("size=", src.get_width(), "x", src.get_height())
	quit(0)
