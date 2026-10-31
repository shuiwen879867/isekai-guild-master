"""Local UI adapter; uses the unchanged engine/session with the existing framing."""
import argparse
import json
from pathlib import Path
import secrets
import select
import socket
import struct
import time

from guild_network import _Decoder,_encode
from guild_session import Session

def serve(endpoint):
    listener=socket.socket();listener.bind(('127.0.0.1',0));listener.listen(1)
    token=secrets.token_urlsafe(32)
    endpoint.write_text(json.dumps(dict(port=listener.getsockname()[1],token=token)),encoding='utf-8')
    listener.settimeout(30)
    connection,_=listener.accept();listener.close()
    connection.setblocking(False)
    decoder=_Decoder();session=Session();authenticated=False;out=bytearray();revision=-1
    session.saves_dir_ref=str(endpoint.parent / 'saves')
    (endpoint.parent / 'saves').mkdir(parents=True, exist_ok=True)
    try:
        while True:
            read,write,_=select.select([connection],[connection] if out else [],[],.04)
            if read:
                data=connection.recv(65536)
                if not data:break
                for message in decoder.feed(data):
                    try:
                        if not authenticated:
                            if message.get('type')!='local_hello' or not secrets.compare_digest(message.get('token',''),token):
                                return
                            authenticated=True
                            out.extend(_encode(dict(type='welcome',player_id=0,role='player',is_host=True)))
                        elif message['type']=='local_lobby':session.local_lobby(message.get('name','公会长'),message.get('options'))
                        elif message['type']=='action':session.action(message['action'].pop('type'),**message['action'])
                        elif message['type']=='save_game':session.save_game(message.get('name',''))
                        elif message['type']=='rename_players':session.rename_players(message.get('names',{}))
                        elif message['type']=='load_game':session.load_game(message.get('name',''))
                        elif message['type']=='leave_room':session.leave_room()
                        elif message['type']=='local_quit':return
                        else:session.lobby(message['type'],**{k:v for k,v in message.items() if k!='type'})
                        if session.toast:
                            out.extend(_encode(dict(type='notice',message=session.toast)));session.toast=''
                    except (ValueError,KeyError,TypeError) as exc:
                        out.extend(_encode(dict(type='error',message=str(exc))))
            session.tick()
            if authenticated and session.revision!=revision:
                revision=session.revision
                if session.room is not None:session.room['saves']=session.saves()
                out.extend(_encode(dict(type='snapshot',room=session.room,game=session.game)))
            if write and out:
                try:sent=connection.send(out);del out[:sent]
                except BlockingIOError:pass
    finally:
        connection.close();session.close();endpoint.unlink(missing_ok=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--endpoint',required=True,type=Path)
    serve(parser.parse_args().endpoint)
