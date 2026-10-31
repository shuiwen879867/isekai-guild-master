class_name GuildBackdrop
extends Control

var clock = 0.0
var motion = true
var home = true
var bg_texture: Texture2D

func _ready():
	mouse_filter = MOUSE_FILTER_IGNORE
	bg_texture = preload("res://ui/background.png")
	var shader_material = ShaderMaterial.new()
	shader_material.shader = preload("res://ui/backdrop.gdshader")
	shader_material.set_shader_parameter("bg_texture", bg_texture)
	if bg_texture:
		shader_material.set_shader_parameter("texture_size", bg_texture.get_size())
	material = shader_material
	resized.connect(queue_redraw)

func _process(delta):
	if motion:
		clock += delta
		if material:
			material.set_shader_parameter("clock", clock)

func _draw():
	if not material: return
	material.set_shader_parameter("canvas_size", size)
	material.set_shader_parameter("home", home)
	if bg_texture:
		material.set_shader_parameter("texture_size", bg_texture.get_size())
	draw_rect(Rect2(Vector2.ZERO, size), Color.WHITE)
