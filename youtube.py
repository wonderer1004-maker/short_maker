"""OAuth channel verification, scheduled uploads, ambiguity-safe state."""
import datetime as dt
import json
import os
from core import ROOT, now, save_json, publish_slot

SCOPES=['https://www.googleapis.com/auth/youtube.upload','https://www.googleapis.com/auth/youtube.readonly']

def service(login=False):
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    token=ROOT/'token.json'; creds=None
    if token.exists(): creds=Credentials.from_authorized_user_file(str(token),SCOPES)
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    if not creds or not creds.valid:
        if not login: raise RuntimeError('먼저 python app.py login을 실행하세요.')
        p=ROOT/'client_secret.json'
        if not p.exists(): raise RuntimeError('OAuth 데스크톱 앱 JSON을 client_secret.json으로 저장하세요.')
        creds=InstalledAppFlow.from_client_secrets_file(str(p),SCOPES).run_local_server(port=0)
    token.write_text(creds.to_json(),encoding='utf-8')
    if os.name!='nt': token.chmod(0o600)
    yt=build('youtube','v3',credentials=creds,cache_discovery=False)
    channel=yt.channels().list(part='snippet,contentDetails',mine=True).execute().get('items',[])
    if len(channel)!=1: raise RuntimeError('업로드할 채널 하나를 OAuth에서 선택하세요.')
    channel=channel[0]
    identity=ROOT/'data/channel.json'
    if login:
        save_json(identity, {'id':channel['id'],'title':channel['snippet']['title']})
        print('연결 채널:',channel['snippet']['title'],channel['id'])
    elif not identity.exists() or json.loads(identity.read_text(encoding='utf-8'))['id']!=channel['id']:
        raise RuntimeError('채널이 변경되었습니다. login 명령으로 연결 채널을 확인하세요.')
    return yt,channel

def metadata(c,job,index):
    script=json.loads(job['script'])
    if '_affiliate' in script:
        snap=script['_affiliate']
        desc=(snap['disclosure']+'\n쿠팡 파트너스 또는 알리익스프레스 제휴 활동입니다.\n'
              +snap['source']+' / '+snap['scope']+'\n'+snap['methodology']+'\n'
              +'상품 자료 확인: '+snap['collected_at']+'\n'
              +'판매처 자료 사진·표시가 비교 및 AI 합성 음성. 직접 성능 시험 결과가 아닙니다.\n'
              +'옵션·쿠폰·배송비·세금·재고·가격은 구매 전에 확인하세요.\n'
              +'클릭 가능한 상품 링크는 채널 프로필에서 확인하세요.\n'+c.get('affiliate_portal_url','')+'\n')
        for pair in snap['pairs']:
            comparison=pair.get('assessment')
            if comparison:
                desc+=comparison['price_line']+'\n'+'\n'.join(comparison['features'])+'\n'
                desc+='\n'.join(comparison['source_urls'])+'\n'
            for tag in ('popular','alternative'):
                p=pair[tag]
                desc+=f'{pair["rank"]}위 '+('인기 상품' if tag=='popular' else '동종 대안')+': '+p['name']+' / '+p['price']+'원\n'+p['affiliate_url']+'\n'
        desc=desc[:4400]
    elif '_ranking' in script:
        snap=script['_ranking']
        desc=(f'{snap["source"]} / {snap["category"]}\n순위 갱신: {snap["source_updated_at"]}\n'
              f'확인: {snap["collected_at"]}\n{snap["methodology"]}\n{snap["scope"]}\n'
              f'{snap["price_basis"]}. 가격·재고는 구매 전에 다시 확인하세요.\n'
              '브랜드·판매처 상품 자료 사진과 AI 합성 음성을 사용했습니다. 직접 착용·보온성 실험 결과가 아닙니다.\n'
              '순위 출처: '+snap['source_page']+'\n')
        for p in snap['products']:
            desc+=f'{p["rank"]}위 {p["brand"]} / {p["name"]} / {p["price"]:,}원\n{p["url"]}\n'
    else:
        desc='직접 작성한 구매 체크리스트입니다. 특정 제품의 실험·순위를 주장하지 않습니다.\nAI 합성 음성을 사용했습니다.\n'
    if c.get('affiliate_disclosure'): desc+=c['affiliate_disclosure']+'\n'
    desc+=c['channel_profile_cta']+f'\n\n제작 식별자: shorts-studio:{job["id"]}\n#쇼츠 #상품비교'
    status={'privacyStatus':'private','selfDeclaredMadeForKids':c['made_for_kids'],
            'containsSyntheticMedia':c['contains_synthetic_media']}
    if c['mode']=='scheduled':
        slot=job.get('publish_at')
        if not slot or dt.datetime.fromisoformat(slot.replace('Z','+00:00'))<=now():
            slot=publish_slot(c,index)
        status['publishAt']=slot
    return {'snippet':{'title':script['title']+' #Shorts','description':desc,
                       'categoryId':'26','defaultLanguage':'ko'},'status':status}

def upload(c,store,job,index,yt):
    from googleapiclient.http import MediaFileUpload
    from googleapiclient.errors import HttpError
    if job['status']!='ready': return
    body=metadata(c,job,index)
    file=ROOT/job['video']
    if not file.is_file(): raise RuntimeError('완성 영상이 없습니다.')
    store.update(job['id'],status='uploading',publish_at=body['status'].get('publishAt'),error=None)
    try:
        req=yt.videos().insert(part='snippet,status',body=body,
            media_body=MediaFileUpload(str(file),mimetype='video/mp4',chunksize=8*1024*1024,resumable=True))
        response=None
        while response is None:
            _,response=req.next_chunk(num_retries=3)
        if not response.get('id'): raise RuntimeError('업로드 결과 식별자 없음')
        store.update(job['id'],status='uploaded',youtube_id=response['id'],error=None)
    except Exception as e:
        # Network failures may have committed remotely. Never blindly insert again.
        code=getattr(getattr(e,'resp',None),'status',None)
        if isinstance(e,HttpError) and code in (400,401,403,404):
            state='upload_failed'
        else: state='upload_unknown'
        store.update(job['id'],status=state,error=f'{type(e).__name__}: 업로드 실패. 로그/채널을 확인하세요. HTTP={code}')
        raise RuntimeError('업로드를 중단했습니다. 대시보드 상태를 확인하세요.') from None

def reconcile(store):
    yt,ch=service()
    playlist=ch['contentDetails']['relatedPlaylists']['uploads']; page=None; found={}
    # Scan all uploads; only explicit marker matches can resolve an uncertain upload.
    while True:
        r=yt.playlistItems().list(part='contentDetails',playlistId=playlist,maxResults=50,pageToken=page).execute()
        ids=[v['contentDetails']['videoId'] for v in r.get('items',[])]
        if ids:
            videos=yt.videos().list(part='snippet',id=','.join(ids)).execute().get('items',[])
            for v in videos:
                for j in store.rows():
                    if 'shorts-studio:'+j['id'] in v['snippet'].get('description',''):
                        found[j['id']]=v['id']
        page=r.get('nextPageToken')
        if not page: break
    for id,video in found.items(): store.update(id,status='uploaded',youtube_id=video,error=None)
    print('채널에서 확인된 업로드:',len(found),'미확인 항목은 자동 재업로드하지 않습니다.')

def metrics(store):
    yt,_=service();jobs=[j for j in store.rows() if j['youtube_id']]
    for i in range(0,len(jobs),50):
        group=jobs[i:i+50]; by_id={j['youtube_id']:j for j in group}
        result=yt.videos().list(part='statistics',id=','.join(by_id)).execute()
        for v in result.get('items',[]):
            s=v['statistics']; id=by_id[v['id']]['id']
            with store.db:
                store.db.execute('''INSERT INTO metrics(job_id,views,likes,comments,updated_at) VALUES(?,?,?,?,?)
                  ON CONFLICT(job_id) DO UPDATE SET views=excluded.views,likes=excluded.likes,
                  comments=excluded.comments,updated_at=excluded.updated_at''',
                  (id,int(s.get('viewCount',0)),int(s.get('likeCount',0)),int(s.get('commentCount',0)),now().isoformat()))
