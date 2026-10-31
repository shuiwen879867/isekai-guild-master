class_name GuildPortrait
extends TextureRect

var on_click: Callable

func _ready():
	expand_mode = TextureRect.EXPAND_IGNORE_SIZE;stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	clip_contents = true;mouse_filter = Control.MOUSE_FILTER_STOP;mouse_default_cursor_shape = Control.CURSOR_POINTING_HAND

func _gui_input(event):
	if event is InputEventMouseButton and event.button_index == MOUSE_BUTTON_LEFT and event.pressed:
		if on_click.is_valid(): on_click.call()
		accept_event()
