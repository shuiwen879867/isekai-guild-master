class_name GuildBannerBox
extends StyleBox

# 橫幅按鈕底圖：兩端裝飾以高度等比縮放（不變形），中段平坦區水平拉伸。
# 標準九宮格在「裝飾佔滿整個高度」的圖上會把端飾拉扁或拆開，因此改為自繪。

var texture: Texture2D
var cap_left: float = 128.0
var cap_right: float = 123.0
var tint: Color = Color.WHITE

static func create(source: Texture2D, tint_color: Color, padding_side: float, padding_y: float) -> GuildBannerBox:
	var box = GuildBannerBox.new()
	box.texture = source
	box.tint = tint_color
	for side in [SIDE_LEFT, SIDE_RIGHT]: box.set_content_margin(side, padding_side)
	for side in [SIDE_TOP, SIDE_BOTTOM]: box.set_content_margin(side, padding_y)
	return box

func _draw(to_canvas_item: RID, rect: Rect2) -> void:
	if texture == null or rect.size.x <= 1.0 or rect.size.y <= 1.0: return
	var tex = texture.get_size()
	if tex.x <= 1.0 or tex.y <= 1.0: return
	var scale = rect.size.y / tex.y
	var total_caps = cap_left + cap_right
	if total_caps * scale > rect.size.x: scale = rect.size.x / total_caps
	var draw_h = tex.y * scale
	var top = rect.position.y + floorf((rect.size.y - draw_h) * 0.5)
	var left_w = cap_left * scale
	var right_w = cap_right * scale
	var mid_w = maxf(0.0, rect.size.x - left_w - right_w)
	var rid = texture.get_rid()
	if left_w > 0.0:
		RenderingServer.canvas_item_add_texture_rect_region(to_canvas_item, Rect2(rect.position.x, top, left_w, draw_h), rid, Rect2(0.0, 0.0, cap_left, tex.y), tint)
	if mid_w > 0.0:
		RenderingServer.canvas_item_add_texture_rect_region(to_canvas_item, Rect2(rect.position.x + left_w, top, mid_w, draw_h), rid, Rect2(cap_left, 0.0, tex.x - total_caps, tex.y), tint)
	if right_w > 0.0:
		RenderingServer.canvas_item_add_texture_rect_region(to_canvas_item, Rect2(rect.position.x + rect.size.x - right_w, top, right_w, draw_h), rid, Rect2(tex.x - cap_right, 0.0, cap_right, tex.y), tint)
