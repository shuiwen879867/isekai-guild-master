"""Verify and stage a complete release, publishing only after deployment passes."""
import argparse
import hashlib
import http.client
import json
import os
from pathlib import Path
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT=Path(__file__).resolve().parents[1]
REPO='shuiwen879867/isekai-guild-master'
TAG='v4.1.0'


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--publish',action='store_true');args=parser.parse_args()
    from validate_voice_assets import validate
    validate()
    manifest_sha=sha(ROOT/'GuildMaster-Godot-src/data/voice_manifest.json')
    package=json.loads((ROOT/'qa/package-bilingual/voice-results.json').read_text('utf8'))
    if not package['passed'] or not package.get('package_passed') or package['manifest_sha256']!=manifest_sha or package['clips']!=1134 or set(package['languages'])!={'ja','zh_CN'}:
        raise RuntimeError('The exported bilingual client has not passed its checks')
    env=dict(os.environ,GIT_TERMINAL_PROMPT='0',GCM_INTERACTIVE='Never')
    credentials=subprocess.run(['git','credential','fill'],input='protocol=https\nhost=github.com\n\n',capture_output=True,text=True,check=True,env=env,timeout=40)
    values=dict(line.split('=',1) for line in credentials.stdout.splitlines() if '=' in line)
    headers={'Authorization':'Bearer '+values['password'],'Accept':'application/vnd.github+json','User-Agent':'GuildMasterRelease/4.1','X-GitHub-Api-Version':'2022-11-28'}
    base='/repos/'+REPO

    def api(path,body=None,method=None,missing_ok=False):
        request=urllib.request.Request('https://api.github.com'+path,data=json.dumps(body,ensure_ascii=False).encode() if body is not None else None,headers=dict(headers,**({'Content-Type':'application/json'} if body is not None else {})),method=method or ('PATCH' if body is not None else 'GET'))
        try:
            with urllib.request.urlopen(request,timeout=45) as response:
                content=response.read();return json.loads(content) if content else None
        except urllib.error.HTTPError as error:
            if missing_ok and error.code==404:return None
            try:message=json.loads(error.read()).get('message','request rejected')
            except ValueError:message='request rejected'
            raise RuntimeError('GitHub HTTP '+str(error.code)+': '+message) from None

    commit=subprocess.run(['git','rev-parse','HEAD'],capture_output=True,text=True,check=True,cwd=ROOT).stdout.strip()
    if api(base+'/commits/main')['sha']!=commit or api(base+'/commits/'+TAG)['sha']!=commit:
        raise RuntimeError('Remote main and release tag must match the verified commit')
    release=api(base+'/releases/tags/'+TAG,missing_ok=True)
    if release is None:
        release=next((item for item in api(base+'/releases?per_page=100') if item['tag_name']==TAG),None)
    if release is None:raise RuntimeError('The prepared draft release was not found')
    release_id=release['id']
    assets=[(ROOT/'dist/GuildMaster-Windows-4.1.0.zip','GuildMaster-Windows-4.1.0.zip','application/zip'),(ROOT/'dist/guild-server-4.1.0.zip','guild-server-4.1.0.zip','application/zip'),(ROOT/'docs/更新日志_4.1.png','update-log-4.1.png','image/png'),(ROOT/'docs/DLC玩法总览.png','dlc-guide-4.1.png','image/png')]
    checksum=ROOT/'qa/SHA256SUMS.txt'
    checksum.write_text(''.join(sha(path)+'  '+name+'\n' for path,name,mime in assets),'ascii')
    assets.append((checksum,'SHA256SUMS.txt','text/plain'))

    def matches(item,path):return item.get('digest')=='sha256:'+sha(path) and item['size']==path.stat().st_size

    if not args.publish:
        api(base+'/releases/'+str(release_id),dict(draft=True,name='异世界公会长 v4.1.0 · 全角色中日双语配音',body=(ROOT/'docs/RELEASE_4_1.md').read_text('utf8')))
        staged=[]
        for path,name,mime in assets:
            current={item['name']:item for item in api(base+'/releases/'+str(release_id)+'/assets')}
            if name in current and matches(current[name],path):
                staged.append((path,name,current[name]));continue
            pending='pending-'+sha(path)[:12]+'-'+name
            item=current.get(pending)
            if item is None or not matches(item,path):
                if item is not None:api(base+'/releases/assets/'+str(item['id']),method='DELETE')
                print('Uploading',name,path.stat().st_size,'bytes',flush=True)
                connection=http.client.HTTPSConnection('uploads.github.com',timeout=240,blocksize=1024*1024)
                try:
                    with path.open('rb') as stream:
                        connection.request('POST',base+'/releases/'+str(release_id)+'/assets?name='+urllib.parse.quote(pending),body=stream,headers=dict(headers,**{'Content-Type':mime,'Content-Length':str(path.stat().st_size)}))
                        response=connection.getresponse();payload=response.read()
                    if response.status!=201:raise RuntimeError('GitHub asset upload failed: '+str(response.status))
                    item=json.loads(payload)
                finally:connection.close()
                if not matches(item,path):raise RuntimeError('Uploaded asset hash differs: '+name)
            staged.append((path,name,item))
            print('Staged and verified',name,flush=True)
        old=[]
        for path,name,item in staged:
            if item['name']==name:continue
            current={entry['name']:entry for entry in api(base+'/releases/'+str(release_id)+'/assets')}
            if name in current:
                previous=current[name]
                api(base+'/releases/assets/'+str(previous['id']),dict(name='superseded-'+str(previous['id'])+'-'+name))
                old.append(previous['id'])
            api(base+'/releases/assets/'+str(item['id']),dict(name=name))
        verified={item['name']:item for item in api(base+'/releases/'+str(release_id)+'/assets')}
        for path,name,mime in assets:
            if name not in verified or not matches(verified[name],path):raise RuntimeError('Final asset verification failed: '+name)
        for identifier in old:api(base+'/releases/assets/'+str(identifier),method='DELETE')
    else:
        deploy=json.loads((ROOT/'qa/deploy-receipt.json').read_text('utf8'))
        if deploy.get('archive_sha256')!=sha(ROOT/'dist/guild-server-4.1.0.zip') or deploy.get('voice_validation',{}).get('manifest_sha256')!=manifest_sha or deploy.get('active')!='active':
            raise RuntimeError('The complete bilingual server has not passed deployment verification')
        current={item['name']:item for item in api(base+'/releases/'+str(release_id)+'/assets')}
        for path,name,mime in assets:
            if name not in current or not matches(current[name],path):raise RuntimeError('Release assets are not ready: '+name)
        api(base+'/releases/'+str(release_id),dict(draft=False,prerelease=False,name='异世界公会长 v4.1.0 · 全角色中日双语配音',body=(ROOT/'docs/RELEASE_4_1.md').read_text('utf8'),make_latest='true'))
    release=api(base+'/releases/'+str(release_id))
    remote={item['name']:item for item in api(base+'/releases/'+str(release_id)+'/assets')}
    receipt=dict(repository='https://github.com/'+REPO,commit=commit,draft=release['draft'],release_url='https://github.com/'+REPO+'/releases/tag/'+TAG,voice_manifest_sha256=manifest_sha,assets=[dict(name=name,url=remote[name]['browser_download_url'],size=remote[name]['size'],sha256=sha(path)) for path,name,mime in assets])
    (ROOT/'qa/publish-receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),'utf8')
    print(json.dumps(receipt,ensure_ascii=False,indent=2),flush=True)


if __name__=='__main__':main()
