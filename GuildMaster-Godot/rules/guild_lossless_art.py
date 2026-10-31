"""Pixel-identical encodings of the original tile scans; no layout changes."""

LOSSLESS_IMAGE_MAP = {
    'images/piece_png/%s.png' % number: 'images/piece_webp/%s.webp' % number
    for number in range(1, 23)
}


def original_art_source(source):
    return LOSSLESS_IMAGE_MAP.get(source, source) if isinstance(source, str) else source
