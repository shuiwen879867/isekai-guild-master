shader_type canvas_item;
render_mode unshaded;

// --- 背景圖片與基礎參數 ---
uniform sampler2D bg_texture : source_color, filter_linear_mipmap;
uniform vec2 canvas_size = vec2(1920.0, 1080.0);
uniform vec2 texture_size = vec2(1024.0, 571.0);
uniform float clock = 0.0;
uniform bool home = true;

// --- 畫面氛圍微調 ---
uniform float vignette_strength : hint_range(0.0, 1.0) = 0.35;
uniform float overlay_darkness : hint_range(0.0, 1.0) = 0.10;

void fragment() {
	// 保持比例置中填滿 (Aspect cover centered)
	float canvas_aspect = canvas_size.x / max(1.0, canvas_size.y);
	float tex_aspect = texture_size.x / max(1.0, texture_size.y);

	vec2 uv = UV;
	if (canvas_aspect > tex_aspect) {
		float scale = tex_aspect / canvas_aspect;
		uv.y = (uv.y - 0.5) * scale + 0.5;
	} else {
		float scale = canvas_aspect / tex_aspect;
		uv.x = (uv.x - 0.5) * scale + 0.5;
	}

	vec4 tex_color = texture(bg_texture, uv);
	vec3 color = tex_color.rgb;

	// 微幅整體壓暗，襯托前景淺色文字與卡牌
	color *= (1.0 - overlay_darkness);

	// 電影感暗角（Vignette）
	vec2 v_uv = (UV - 0.5) * 2.0;
	float vignette = clamp(1.0 - dot(v_uv, v_uv) * (vignette_strength * 0.4), 0.0, 1.0);
	color *= vignette;

	COLOR = vec4(color, 1.0);
}