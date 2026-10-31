import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = json.loads((ROOT / 'release.json').read_text('utf8'))
VERSION = CONFIG['version']
REVISION = CONFIG['revision']
TAG = 'v' + VERSION
