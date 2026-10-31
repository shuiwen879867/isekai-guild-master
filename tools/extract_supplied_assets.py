"""Extract, rectify and record the supplied physical-card screenshots."""
from pathlib import Path
import hashlib
import json
import zipfile
import subprocess
import imageio_ffmpeg
import cv2
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path(r'C:/Users/react/Documents/Tencent Files/2213963916/nt_qq/nt_data/Pic/2026-10/Ori')
FILES = ['7801a68e57a740e97b3e8e0a1c1efd62.png','e700ceed44859d14f1d9d7c5882b0f28.png',
 '324ceb04e247ca0463b80979a690d2e2.png','31a64142845dac90b7a3838091872baf.png',
 '1721c4ee5e2789b7973357a2d6d9c651.png','c4bc72df877143ac5fd87582594bd45f.png',
 '361c9b97f38bbabb5f720606c1bc08bf.png','62d915994a287f4fa852880f20707bcb.png']
# Clockwise corners, starting at the top left. No generative reconstruction.
CROPS = {
 'sif_revised_white_1':(5,[(304,59),(610,68),(611,274),(299,265)]),
 'sif_revised_white_2':(5,[(0,28),(296,35),(292,229),(0,226)]),
 'sif_revised_white_3':(5,[(332,278),(627,284),(627,494),(330,484)]),
 'sif_revised_black_1':(2,[(399,319),(774,325),(774,596),(391,585)]),
 'sif_revised_black_2':(2,[(0,29),(381,40),(381,290),(0,279)]),
 'sif_revised_black_3':(2,[(397,52),(770,55),(771,315),(386,305)]),
 'frida_revised_white_1':(3,[(114,230),(371,240),(386,421),(96,412)]),
 'frida_revised_white_2':(3,[(119,19),(375,31),(383,196),(105,194)]),
 'frida_revised_white_3':(3,[(40,478),(320,485),(326,687),(17,677)]),
 'frida_revised_black_1':(4,[(38,497),(331,504),(330,725),(30,720)]),
 'frida_revised_black_2':(4,[(128,56),(397,62),(405,225),(112,235)]),
 'frida_revised_black_3':(0,[(235,19),(551,14),(555,228),(216,230)]),
 'bell_revised_white_1':(1,[(349,233),(621,234),(621,434),(335,427)]),
 'bell_revised_white_2':(1,[(331,450),(616,462),(616,670),(323,660)]),
 'bell_revised_white_3':(1,[(367,47),(628,48),(632,222),(352,219)]),
 'bell_revised_black_1':(6,[(373,42),(639,41),(638,217),(368,211)]),
 'bell_revised_black_2':(6,[(342,428),(622,435),(628,638),(338,629)]),
 'bell_revised_black_3':(6,[(345,227),(627,230),(625,418),(331,410)]),
 'marta_revised_white_1':(1,[(41,208),(309,210),(310,406),(28,399)]),
 'marta_revised_white_2':(1,[(12,442),(325,448),(323,675),(5,667)]),
 'marta_revised_white_3':(1,[(42,20),(304,21),(306,196),(28,193)]),
 'marta_revised_black_1':(6,[(49,16),(308,18),(306,185),(40,181)]),
 'marta_revised_black_2':(6,[(18,423),(320,431),(318,642),(6,636)]),
 'marta_revised_black_3':(6,[(38,192),(321,201),(316,389),(24,381)]),
 'horn_revised_white_1':(5,[(972,65),(1249,74),(1250,272),(963,263)]),
 'horn_revised_white_2':(2,[(789,315),(1134,318),(1139,601),(776,590)]),
 'horn_revised_white_3':(2,[(791,52),(1106,55),(1121,289),(776,281)]),
 'horn_revised_black_1':(0,[(574,24),(911,28),(918,244),(567,238)]),
 'horn_revised_black_2':(3,[(507,28),(778,34),(785,201),(498,199)]),
 'horn_revised_black_3':(2,[(1177,69),(1537,78),(1564,308),(1170,299)]),
 'horn_five_white_1':(4,[(501,490),(809,501),(813,733),(490,732)]),
 'horn_five_white_2':(4,[(525,29),(805,31),(811,225),(514,217)]),
 'horn_five_white_3':(4,[(498,276),(789,286),(801,479),(484,470)]),
 'lazy_life':(7,[(32,14),(312,17),(315,402),(20,398)]),
}

def main():
    target=ROOT/'GuildMaster-Godot/art/supplied';target.mkdir(parents=True,exist_ok=True)
    manifest=[]
    for key,(index,quad) in CROPS.items():
        path=SOURCE/FILES[index]
        original=Image.open(path).convert('RGB')
        width,height=(560,800) if key=='lazy_life' else (800,570)
        matrix=cv2.getPerspectiveTransform(np.float32(quad),np.float32([(0,0),(width-1,0),(width-1,height-1),(0,height-1)]))
        pixels=cv2.warpPerspective(np.array(original),matrix,(width,height),flags=cv2.INTER_CUBIC)
        destination=target/(key+'.webp');Image.fromarray(pixels).save(destination,'WEBP',quality=94)
        manifest.append(dict(id=key,source=path.name,source_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),corners=quad,
                             output='supplied/'+destination.name,sha256=hashlib.sha256(destination.read_bytes()).hexdigest()))
    (ROOT/'docs/SUPPLIED_ASSETS.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),'utf8')
    voice=ROOT/'GuildMaster-Godot-src/audio/voice/kanban-010';voice.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(Path.home()/'Downloads/kanban-010__settle-win-v2.zip') as archive:
        for entry in archive.infolist():
            if '/' in entry.filename or '\\' in entry.filename or not entry.filename.endswith('.ogg'):raise ValueError('Unexpected voice member')
            (voice/entry.filename).write_bytes(archive.read(entry))
    # The supplied .ogg files contain Opus. Godot's Ogg importer requires
    # Vorbis; convert derivatives and retain the original ZIP untouched.
    for path in voice.glob('*.ogg'):
        if b'OpusHead' not in path.read_bytes()[:100]:continue
        converted=path.with_suffix('.vorbis.ogg')
        subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),'-v','error','-y','-i',str(path),
                        '-c:a','libvorbis','-q:a','5',str(converted)],check=True)
        path.write_bytes(converted.read_bytes());converted.unlink()
    print('Extracted',len(manifest),'card faces and',len(list(voice.glob('*.ogg'))),'voice clips.')

if __name__=='__main__':main()
