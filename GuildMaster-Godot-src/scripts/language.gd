class_name GuildLang
extends RefCounted

# 簡體／繁體顯示切換：只在顯示層轉換（OpenCC STPhrases + STCharacters，Apache-2.0）。

const DATA = "res://data/s2t.json"

static var traditional := false
static var _chars := {}
static var _phrases := {}
static var _max_phrase := 2
static var _loaded := false
static var _simplified := {}
static var _font_cache: FontFile

static func t(text) -> String:
	if not traditional:
		if _simplified.is_empty():
			var table = JSON.parse_string(FileAccess.get_file_as_string("res://data/t2s.json"))
			if table is Dictionary: _simplified = table.get("chars", {})
		var simplified = ""
		for character in str(text): simplified += str(_simplified.get(character, character))
		return simplified
	var value = str(text)
	if value.is_empty():
		return value
	_ensure_loaded()
	if _chars.is_empty():
		return value
	var result := ""
	var index := 0
	var length := value.length()
	while index < length:
		var matched := false
		for size in range(mini(_max_phrase, length - index), 1, -1):
			var chunk = value.substr(index, size)
			if _phrases.has(chunk):
				result += _phrases[chunk]
				index += size
				matched = true
				break
		if not matched:
			var character = value[index]
			result += _chars.get(character, character)
			index += 1
	return result

static func font() -> Font:
	if not traditional:
		return load("res://fonts/SourceHanSansLite.ttf")
	return traditional_font()

static func title_font() -> Font:
	if not traditional:
		return load("res://fonts/ZCOOLKuaiLe-Regular.ttf")
	return traditional_font()

static func traditional_font() -> Font:
	if _font_cache == null:
		var base = load("res://fonts/UoqMunThenKhung.otf")
		if base is FontFile:
			var copy: FontFile = base.duplicate()
			copy.fallbacks = [load("res://fonts/SourceHanSansLite.ttf")]
			_font_cache = copy
		else:
			_font_cache = base
	return _font_cache

static func _ensure_loaded() -> void:
	if _loaded:
		return
	_loaded = true
	var parsed = JSON.parse_string(FileAccess.get_file_as_string(DATA))
	if parsed is Dictionary:
		_chars = parsed.get("chars", {})
		_phrases = parsed.get("phrases", {})
		for key in _phrases:
			_max_phrase = maxi(_max_phrase, str(key).length())
