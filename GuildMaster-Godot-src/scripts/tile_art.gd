class_name GuildTileArt
extends GuildCardArt

func _draw():
	if not store or source.is_empty(): return
	var edge = min(size.x, size.y) * 0.88
	var texture = store.tile_texture(source, clamp(int(edge), 160, 750))
	if texture == null: return
	draw_set_transform(size / 2, - PI / 6, Vector2.ONE)
	draw_texture_rect(texture, Rect2( - Vector2.ONE * edge / 2, Vector2.ONE * edge), false)
	draw_set_transform(Vector2.ZERO)
	if selected:
		var outline = PackedVector2Array()
		for i in range(7): outline.append(size / 2 + Vector2(cos(i * PI / 3 - PI / 2), sin(i * PI / 3 - PI / 2)) * edge * 0.54)
		draw_colored_polygon(outline, Color(0.1, 0.08, 0.1, 0.58))
		draw_polyline(outline, Color("9f4c50"), 3, true)
		draw_selection_label(size / 2, edge)
