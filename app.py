#!/usr/bin/env python3
import argparse
import csv
import datetime as dt
import html
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import time
import urllib.parse
import webbrowser
from core import ROOT, Store, config, collect, select_brief, generate, now, save_json, run_lock
from render import render

def load_catalog():
    entries=json.loads((ROOT/'catalog.json').read_text(encoding='utf-8'))
    if len({x['id'] for x in entries})!=len(entries): raise ValueError('중복 brief id')
    for b in entries:
        if not b.get('facts') or not b.get('keywords'): raise ValueError('facts와 keywords가 필요합니다.')
    return entries

def run_daily(c,store,skip_collect=False):
    if c.get('content_mode')=='popularity':
        from popularity import run_popularity
        return run_popularity(c,store)
    day=now().date().isoformat()
    if skip_collect:
        videos=json.loads((ROOT/'data/candidates.json').read_text(encoding='utf-8'))['videos']
    else:
        videos=collect(c)
    catalog=load_catalog()
    existing=[j for j in store.rows() if j['day']==day]
    used={j['brief_id'] for j in existing}
    source_used={j['source_id'] for j in store.rows()}
    needed=max(0,c['daily_videos']-len(existing))
    for v in videos:
        if not needed: break
        if v['id'] in source_used: continue
        b=select_brief(v,catalog,used)
        if not b: continue
        id=store.add(day,v['id'],b['id'])
        if id: used.add(b['id']);needed-=1
    brief_map={b['id']:b for b in catalog};video_map={v['id']:v for v in videos}
    for job in store.rows():
        if job['day']!=day or job['status'] not in ('draft','generation_failed'): continue
        brief=brief_map[job['brief_id']]
        video=video_map.get(job['source_id'],{'title':brief['topic']})
        if not brief.get('approved'): continue
        try:
            if job['script']:
                script=json.loads(job['script'])
            else:
                script=generate(c,store,brief,video)
                store.update(job['id'],script=json.dumps(script,ensure_ascii=False))
            path,seconds=render(c,store,job['id'],script,brief)
            store.update(job['id'],video=path,status='review' if c['require_review'] else 'ready',error=None)
            save_json(ROOT/'output'/job['id']/'provenance.json',{
                'source_video_url':'https://www.youtube.com/watch?v='+job['source_id'],
                'analysis_scope':'메타데이터 주제 힌트만 사용; 원본 영상·음성 미사용',
                'brief':brief,'script':script,'duration_seconds':seconds,'created_at':now().isoformat()})
        except Exception as e:
            store.update(job['id'],status='generation_failed',error=f'{type(e).__name__}: 생성 실패. 설정·요청 한도·자료·대본을 확인하세요.')
            print(job['id'],'생성 실패:',type(e).__name__,flush=True)
            # Do not continuously retry potentially billable HTTP operations.
            if isinstance(e, (RuntimeError, OSError)): break
    if needed: print(f'오늘 {needed}개 부족: 새 후보 또는 검증된 catalog 항목을 추가하세요.',flush=True)
    upload_ready(c,store)

def upload_ready(c,store):
    from youtube import service, upload
    if not (ROOT/'token.json').exists():
        print('채널 로그인 전입니다. 완성 영상은 로컬에 저장됩니다.',flush=True);return
    day=now().date().isoformat()
    # Include ready backlog; enforce per-local-day upload attempts and successes.
    rows=store.rows()
    uploaded_today=store.db.execute("SELECT COUNT(*) FROM jobs WHERE status='uploaded' AND id IN (SELECT job_id FROM upload_events WHERE day=?)",(day,)).fetchone()[0]
    left=max(0,c['daily_videos']-uploaded_today)
    ready=sorted([j for j in rows if j['status']=='ready'],key=lambda j:j['created_at'])[:left]
    if not ready: return
    # Unknown upload state anywhere blocks inserts until reconciliation.
    if any(j['status'] in ('uploading','upload_unknown') for j in rows):
        print('확인되지 않은 업로드가 있어 중단합니다. reconcile을 실행하세요.',flush=True);return
    yt,_=service()
    for i,job in enumerate(ready,uploaded_today):
        script=json.loads(job['script']) if job.get('script') else {}
        if '_ranking' in script:
            updated=dt.datetime.fromisoformat(script['_ranking']['source_updated_at'])
            if (now()-updated).total_seconds()>c.get('ranking_max_age_hours',24)*3600:
                store.update(job['id'],status='rank_stale',error='순위가 오래되어 게시하지 않았습니다.')
                continue
        if not job.get('video') or not (ROOT/job['video']).is_file():
            if os.environ.get('SHORTS_CHECKPOINT')!='1':
                raise RuntimeError('완성 영상이 없습니다. 제작 파일을 복원하세요.')
            script=json.loads(job['script'])
            if '_ranking' in script:
                from editorial import render_ranking
                path,_=render_ranking(c,store,job['id'],script['_ranking'],script)
            else:
                brief=next(b for b in load_catalog() if b['id']==job['brief_id'])
                path,_=render(c,store,job['id'],script,brief)
            store.update(job['id'],video=path)
            job=store.get(job['id'])
        script=json.loads(job['script']) if job.get('script') else {}
        if '_ranking' in script:
            updated=dt.datetime.fromisoformat(script['_ranking']['source_updated_at'])
            if (now()-updated).total_seconds()>c.get('ranking_max_age_hours',24)*3600:
                store.update(job['id'],status='rank_stale',error='순위가 오래되어 게시하지 않았습니다.')
                continue
        with store.db: store.db.execute('INSERT OR IGNORE INTO upload_events VALUES(?,?,?)',(job['id'],day,now().isoformat()))
        upload(c,store,job,i,yt)
        print('업로드 완료:',job['id'],flush=True)

def init_store():
    s=Store()
    s.db.execute('CREATE TABLE IF NOT EXISTS upload_events(job_id TEXT PRIMARY KEY,day TEXT NOT NULL,attempt_at TEXT NOT NULL)')
    s.db.commit();return s

DEMO_SCRIPT={
 'title':'경량패딩 구매 전 확인할 세 가지',
 'scenes':[
  {'heading':'경량패딩, 뭘 확인할까요?', 'narration':'브랜드 이름만 보고 고르기 전에, 매장에서 직접 확인할 항목을 정리해 보세요.'},
  {'heading':'01 · 라벨부터 확인', 'narration':'충전재 구성과 세탁 방법을 확인하세요. 충전재 비율과 충전량은 서로 다른 항목으로 구분해서 봅니다.'},
  {'heading':'02 · 함께 입어보기', 'narration':'출퇴근용이라면 실제로 입을 겉옷과 함께 착용해 보세요. 팔을 움직였을 때 당기는 부분이 있는지 확인합니다.'},
  {'heading':'03 · 모르는 정보는 질문', 'narration':'충전량 정보가 없다면 판매처에 문의하세요. 확인하지 않은 보온성을 제품 순위처럼 단정하지 않습니다.'},
  {'heading':'내 용도에 맞게 선택', 'narration':'이 영상은 제품 실험이 아닌 구매 체크리스트입니다. 궁금한 비교 항목을 댓글로 알려주세요.'}
 ]}

def demo(c,store):
    path,sec=render(c,store,'demo',DEMO_SCRIPT,load_catalog()[0],demo=True)
    save_json(ROOT/'output/demo/script.json',DEMO_SCRIPT)
    print('화면 샘플 생성:',path,sec,'초 · 내레이션 없음 · 업로드 대상 아님')

def ranking_preview(c,store):
    from popularity import collect_category,make_script
    from editorial import render_ranking
    snapshot=collect_category(c,c['ranking_categories'][0])
    script=make_script(snapshot)
    path,sec=render_ranking(c,store,'ranking_preview',snapshot,script)
    save_json(ROOT/'output/ranking_preview/provenance.json',snapshot)
    print('인기순위 미리보기:',path,sec,'초. 채널 업로드하지 않았습니다.')

def export(store):
    path=ROOT/'data/performance.csv'
    rows=store.db.execute('''SELECT j.id,j.day,j.brief_id,j.youtube_id,
       m.views,m.likes,m.comments,m.clicks,m.orders,m.revenue,m.cost,
       (COALESCE(m.revenue,0)-COALESCE(m.cost,0)) AS net_profit
       FROM jobs j LEFT JOIN metrics m ON j.id=m.job_id''').fetchall()
    with path.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.writer(f);w.writerow(['job_id','day','topic','youtube_id','views','likes','comments',
            'clicks','orders','revenue_krw_manual','cost_krw_manual','net_profit_krw'])
        w.writerows([tuple(x) for x in rows])
    print('내보내기:',path)

def weekly(store):
    cutoff=(now().date()-dt.timedelta(days=7)).isoformat()
    jobs=[j for j in store.rows() if j['day']>=cutoff and j['script']]
    catalog={b['id']:b for b in load_catalog()}
    lines=['# 주간 비교 영상 촬영 기획서', '', '목표: 5~10분. 실제 제품·자료를 직접 확인한 뒤 제작합니다.',
           '이 파일은 촬영 계획이며 검증 결과나 완성 영상이 아닙니다.', '',
           '## 구성', '1. 시청자의 구매 고민과 비교 기준 소개 (30초)',
           '2. 가격·확인 날짜·판매처·비교 조건 공개 (1분)',
           '3. 직접 촬영한 착용·사용·측정 장면과 결과 (3~5분)',
           '4. 사용 목적별 선택과 확인하지 못한 항목 (1분)',
           '5. 협찬·제휴 관계 공개, 구매 경로 안내 (30초)', '', '## 이번 주 주제 후보']
    for j in jobs[:10]:
        script=json.loads(j['script']); b=catalog.get(j['brief_id'],{})
        lines+=['', '### '+script['title'], '직접 확인할 기준:']
        lines+=['- '+f for f in b.get('facts',[])]
        lines+=['촬영 필요: 실제 제품 라벨, 착용·사용 모습, 비교 조건, 판매처·가격 확인일.',
                '원본 자료 없는 결과·순위·가격은 작성하지 않습니다.']
    if not jobs:lines+=['', '최근 완성 대본이 없습니다. 첫 영상 제작 후 다시 실행하세요.']
    lines+=['', '## 게시 후 연결', '유튜브 스튜디오에서 해당 쇼츠의 관련 영상에 이 긴 영상을 연결합니다.',
            '상품 태그·제휴 링크·광고 공개 설정은 자격과 실제 계약에 맞게 설정합니다.']
    path=ROOT/'data'/f'weekly_{now().date().isoformat()}.md'
    path.write_text('\n'.join(lines),encoding='utf-8');print('주간 기획서:',path)

def doctor(c):
    import shutil
    for name in ('ffmpeg','ffprobe'):
        print(name, 'OK' if shutil.which(c[name]) else '설치 필요')
    print('한글 폰트:', 'OK' if (ROOT/c['font_path']).exists() else '없음')
    for key in ('YOUTUBE_API_KEY','OPENAI_API_KEY'): print(key,'설정됨' if os.environ.get(key) else '미설정')
    print('OAuth JSON:',(ROOT/'client_secret.json').exists(),'채널 로그인:',(ROOT/'token.json').exists())
    print('실행 설정:',c['mode'],'검토:',c['require_review'],'일일 영상:',c['daily_videos'])

def dashboard(c,port):
    csrf=secrets.token_urlsafe(32)
    state={'process':None,'log':None}
    def esc(x): return html.escape(str(x or ''))
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args): pass
        def send(self,data,kind='text/html; charset=utf-8',code=200):
            body=data.encode() if isinstance(data,str) else data
            self.send_response(code);self.send_header('Content-Type',kind)
            self.send_header('Content-Length',str(len(body)))
            self.send_header('X-Content-Type-Options','nosniff')
            self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(body)
        def host_ok(self):
            return self.headers.get('Host') in (f'127.0.0.1:{port}',f'localhost:{port}')
        def do_GET(self):
            if not self.host_ok():return self.send('Invalid host',code=403)
            parsed=urllib.parse.urlsplit(self.path)
            if parsed.path.startswith('/video/'):
                relative=urllib.parse.unquote(parsed.path[len('/video/'):])
                p=(ROOT/'output'/relative).resolve()
                if not p.is_relative_to((ROOT/'output').resolve()) or p.suffix!='.mp4' or not p.is_file():
                    return self.send('Not found',code=404)
                # HTML5 Range requests allow seeking without loading an entire large file.
                size=p.stat().st_size;start=0;end=size-1;status=200
                raw=self.headers.get('Range','')
                if raw.startswith('bytes='):
                    try:
                        a,b=raw[6:].split('-',1);start=int(a);end=min(int(b) if b else end,end)
                        if not 0<=start<=end<size:raise ValueError()
                        status=206
                    except ValueError:return self.send('Invalid range',code=416)
                self.send_response(status);self.send_header('Content-Type','video/mp4')
                self.send_header('Accept-Ranges','bytes');self.send_header('Content-Length',str(end-start+1))
                if status==206:self.send_header('Content-Range',f'bytes {start}-{end}/{size}')
                self.end_headers()
                with p.open('rb') as f:
                    f.seek(start);remaining=end-start+1
                    while remaining:
                        chunk=f.read(min(65536,remaining));self.wfile.write(chunk);remaining-=len(chunk)
                return
            if parsed.path!='/':return self.send('Not found',code=404)
            s=init_store();jobs=s.rows();c=config()
            running=state['process'] is not None and state['process'].poll() is None
            form=lambda cmd,label,id='':f'<form method="post"><input type="hidden" name="csrf" value="{csrf}"><input type="hidden" name="cmd" value="{cmd}"><input type="hidden" name="id" value="{esc(id)}"><button>{label}</button></form>'
            buttons=''.join(form(cmd,label) for cmd,label in [('collect','인기 후보 50개 수집'),('run','오늘 영상 제작'),('upload','준비 영상 업로드'),('metrics','조회수 갱신'),('export','성과 CSV 저장'),('weekly','주간 긴 영상 기획서'),('reconcile','업로드 확인')])
            cards=''
            for j in jobs:
                script=json.loads(j['script']) if j['script'] else {}
                video=''
                if j['video']:
                    relative=str(Path(j['video']).relative_to('output')).replace('\\','/')
                    video=f'<video controls preload="metadata" src="/video/{urllib.parse.quote(relative)}"></video>'
                action=form('approve','확인 완료 · 업로드 대기',j['id']) if j['status']=='review' else ''
                if j['status']=='upload_failed':action+=form('retry-upload','실패한 업로드 재시도 준비',j['id'])
                metrics=s.db.execute('SELECT * FROM metrics WHERE job_id=?',(j['id'],)).fetchone()
                m=dict(metrics) if metrics else {}
                performance=f'''<form method="post" class="finance"><input type="hidden" name="csrf" value="{csrf}"><input type="hidden" name="cmd" value="finance"><input type="hidden" name="id" value="{esc(j['id'])}">
                    <label>수익(원)<input name="revenue" type="number" min="0" step="0.01" value="{m.get('revenue',0)}"></label>
                    <label>비용(원)<input name="cost" type="number" min="0" step="0.01" value="{m.get('cost',0)}"></label>
                    <label>상품 클릭<input name="clicks" type="number" min="0" value="{m.get('clicks',0)}"></label>
                    <label>구매 건수<input name="orders" type="number" min="0" value="{m.get('orders',0)}"></label><button>성과 저장</button></form>'''
                narr=' '.join(x['narration'] for x in script.get('scenes',[]))
                link=f'<a href="https://youtu.be/{esc(j["youtube_id"])}" target="_blank" rel="noopener">유튜브 확인</a>' if j['youtube_id'] else ''
                cards+=f'<article>{video}<div><small>{esc(j["day"])} · {esc(j["status"])}</small><h2>{esc(script.get("title",j["brief_id"]))}</h2><p>{esc(narr)}</p><p class="error">{esc(j["error"])}</p><p>조회수 {m.get("views",0) or 0} · 순수익 {(m.get("revenue",0) or 0)-(m.get("cost",0) or 0):,.0f}원</p>{action}{link}{performance}</div></article>'
            candidates=ROOT/'data/candidates.json';table=''
            if candidates.exists():
                candidate=json.loads(candidates.read_text(encoding='utf-8'))
                table='<p>'+esc(candidate['scope'])+'</p><table><tr><th>순위</th><th>주제 참고 영상</th><th>조회수</th><th>누적 조회수÷경과일*</th></tr>'
                for v in candidate['videos']:
                    table+=f'<tr><td>{v["rank"]}</td><td><a href="{esc(v["url"])}" target="_blank" rel="noopener">{esc(v["title"])}</a></td><td>{v["views"]:,}</td><td>{v["average_views_per_day"]:,}</td></tr>'
                table+='</table><p>*최근 24시간 증가량이 아닙니다. 원본 영상 내용을 분석한 결과도 아닙니다.</p>'
            log=ROOT/'data/dashboard.log'
            lines=log.read_text(encoding='utf-8',errors='replace')[-1500:] if log.exists() else ''
            sample='<video controls preload="metadata" src="/video/demo/short.mp4"></video>' if (ROOT/'output/demo/short.mp4').exists() else ''
            content=f'''<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>쇼츠 스튜디오</title>
            <style>body{{background:#0b1424;color:#eaf0ff;font:16px system-ui;margin:0}}main{{max-width:1120px;margin:auto;padding:28px}}h1{{font-size:36px}}h2{{font-size:22px}}small,.muted{{color:#a7bdd4}}.badge{{color:#60ecc4}}button{{background:#63e7c0;border:0;padding:13px 19px;border-radius:10px;font-weight:bold;cursor:pointer}}.buttons{{display:flex;gap:12px;flex-wrap:wrap}}article{{display:flex;gap:24px;background:#172339;padding:22px;border-radius:18px;margin:22px 0}}video{{width:190px;max-height:340px;border-radius:14px}}article>div{{flex:1}}p{{line-height:1.7}}a{{color:#a3d1ff}}.error{{color:#ffb7b7}}input{{display:block;max-width:130px;background:#243854;color:white;border:1px solid #3e5774;border-radius:6px;padding:8px}}.finance{{display:flex;gap:12px;flex-wrap:wrap;align-items:end;margin-top:20px}}label{{font-size:12px}}table{{width:100%;border-collapse:collapse}}td,th{{text-align:left;padding:12px;border-bottom:1px solid #29405f}}pre{{white-space:pre-wrap;background:#172339;padding:15px}}@media(max-width:650px){{article{{display:block}}video{{width:100%;max-height:480px}}h1{{font-size:28px}}}}</style>
            <main><small>ORIGINAL SHORTS WORKFLOW</small><h1>직장인의 쇼츠 스튜디오</h1><p class="badge">{'실제 상품 인기순위 수집' if c.get('content_mode')=='popularity' else '유튜브 후보 50개 분석'} → 하루 최대 {c['daily_videos']}개 새 영상 → {'비공개 업로드' if c['mode']=='private' else '예약 공개'} → 성과 기록</p>
            <p>채널: {esc(c['channel_name'])} · 검토 {'사용' if c['require_review'] else '생략'} · {'작업 실행 중' if running else '대기 중'}</p>
            <p class="muted">업로드 전 영상·사실·사용 권리를 확인하세요. 상품 태그와 관련 영상은 유튜브 스튜디오에서 연결합니다. 광고수익·구매 전환은 수동 입력입니다.</p>
            <div class="buttons">{buttons}</div><h2>제작 목록</h2>{cards or '<p>오늘 영상 제작을 누르세요. API 연결 전에는 아래 화면 샘플을 확인할 수 있습니다.</p>'}
            <details><summary>화면 샘플 · 실제 음성은 API 연결 후 생성</summary>{sample}</details><h2>인기 후보 분석</h2>{table or '<p>아직 수집하지 않았습니다.</p>'}<details><summary>작업 기록</summary><pre>{esc(lines)}</pre></details>
            <p>자동 작업: 별도 터미널에서 python app.py daemon 실행. 결과 확인은 페이지 새로고침.</p></main></html>'''
            s.db.close();self.send(content)
        def do_POST(self):
            if not self.host_ok():return self.send('Invalid host',code=403)
            origin=self.headers.get('Origin')
            if origin and origin not in (f'http://127.0.0.1:{port}',f'http://localhost:{port}'):
                return self.send('Invalid origin',code=403)
            n=int(self.headers.get('Content-Length','0'))
            if n>8192:return self.send('Too large',code=413)
            form=urllib.parse.parse_qs(self.rfile.read(n).decode())
            get=lambda k:form.get(k,[''])[0]
            if not secrets.compare_digest(get('csrf'),csrf):return self.send('Invalid token',code=403)
            cmd=get('cmd');id=get('id');s=init_store()
            if cmd in ('approve','retry-upload','finance'):
                job=s.get(id)
                if not job:return self.send('Not found',code=404)
                try:
                    with run_lock():
                        if cmd=='approve' and job['status']=='review':s.update(id,status='ready',error=None)
                        elif cmd=='retry-upload' and job['status']=='upload_failed':s.update(id,status='ready',error=None)
                        elif cmd=='finance':
                            revenue,cost=float(get('revenue')),float(get('cost'));clicks,orders=int(get('clicks')),int(get('orders'))
                            if min(revenue,cost,clicks,orders)<0 or not all(__import__('math').isfinite(x) for x in (revenue,cost)):raise ValueError()
                            with s.db:
                                s.db.execute('''INSERT INTO metrics(job_id,revenue,cost,clicks,orders) VALUES(?,?,?,?,?) ON CONFLICT(job_id) DO UPDATE SET
                                  revenue=excluded.revenue,cost=excluded.cost,clicks=excluded.clicks,orders=excluded.orders''',(id,revenue,cost,clicks,orders))
                except (ValueError,RuntimeError):return self.send('작업 중 또는 입력 오류',code=409)
            elif cmd in ('collect','run','upload','metrics','export','weekly','reconcile'):
                if state['process'] and state['process'].poll() is None:return self.send('작업 실행 중입니다.',code=409)
                if state['log']:state['log'].close()
                state['log']=(ROOT/'data/dashboard.log').open('a',encoding='utf-8')
                state['process']=subprocess.Popen([sys.executable,str(ROOT/'app.py'),cmd],cwd=ROOT,stdout=state['log'],stderr=state['log'])
            else:return self.send('Unknown command',code=400)
            s.db.close();self.send_response(303);self.send_header('Location','/');self.end_headers()
    server=ThreadingHTTPServer(('127.0.0.1',port),Handler)
    print(f'관리 화면: http://127.0.0.1:{port}',flush=True)
    webbrowser.open(f'http://127.0.0.1:{port}')
    server.serve_forever()

def main():
    parser=argparse.ArgumentParser(description='원본 쇼츠 제작·예약 업로드 프로그램')
    parser.add_argument('command',choices=['doctor','demo','ranking-preview','login','collect','run','upload','metrics','export','weekly','reconcile','dashboard','daemon'])
    parser.add_argument('--port',type=int,default=8765)
    parser.add_argument('--skip-collect',action='store_true')
    args=parser.parse_args();c=config();s=init_store()
    if args.command=='dashboard':dashboard(c,args.port);return
    if args.command=='daemon':
        print('매일 한국시간 설정 시각 이후 실행. PC/서버가 켜져 있어야 합니다.',flush=True)
        while True:
            c=config();stamp=ROOT/'data/last_daily_run.txt';today=now().date().isoformat()
            if now().hour>=c['daily_run_hour_kst'] and (not stamp.exists() or stamp.read_text()!=today):
                try:
                    with run_lock():run_daily(c,s)
                    stamp.write_text(today)
                except Exception as e:
                    print('자동 작업 실패:',type(e).__name__,'설정을 확인하세요.',flush=True)
                    # Avoid repeated paid attempts: one daily automatic attempt, manual retry available.
                    stamp.write_text(today)
            time.sleep(30)
    else:
        with run_lock():
            if args.command=='doctor':doctor(c)
            elif args.command=='demo':demo(c,s)
            elif args.command=='ranking-preview':ranking_preview(c,s)
            elif args.command=='collect':collect(c)
            elif args.command=='run':run_daily(c,s,args.skip_collect)
            elif args.command=='upload':upload_ready(c,s)
            elif args.command=='login':
                from youtube import service
                service(login=True)
            elif args.command=='metrics':
                from youtube import metrics
                metrics(s)
            elif args.command=='reconcile':
                from youtube import reconcile
                reconcile(s)
            elif args.command=='export':export(s)
            elif args.command=='weekly':weekly(s)

if __name__=='__main__':
    try:main()
    except KeyboardInterrupt:print('종료했습니다.')
    except Exception as e:
        # URLs can contain API keys. Never dump request URLs or credential contents.
        print('작업 실패:',type(e).__name__,'설정과 관리 화면의 상태를 확인하세요.',file=sys.stderr)
        sys.exit(1)
