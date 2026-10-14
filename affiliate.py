"""Official affiliate catalog adapters; no scraping or invented sales figures."""
import datetime as dt
import hashlib
import hmac
import html
import json
import os
import re
import urllib.parse as up
import urllib.request as ur
import urllib.error
from decimal import Decimal
from core import ROOT, now, save_json

DISCLOSURE = '제휴 링크를 통한 구매 시 일정 수수료를 받을 수 있습니다.'

def safe_url(url, domains):
    p=up.urlsplit(url)
    if p.scheme!='https' or p.username or p.password or p.port not in (None,443):
        raise ValueError('HTTPS 상품 주소가 필요합니다.')
    if not any(p.hostname==d or (p.hostname or '').endswith('.'+d) for d in domains):
        raise ValueError('허용되지 않은 상품 주소입니다.')
    return url

def request(url, headers=None, body=None):
    req=ur.Request(url,headers=headers or {},data=body)
    # Authentication failures are not retried and signed URLs never enter logs.
    try:
        with ur.urlopen(req,timeout=40) as r:
            data=r.read(8*1024*1024+1)
            if len(data)>8*1024*1024:raise ValueError('응답 크기 초과')
            return json.loads(data)
    except Exception:
        raise RuntimeError('제휴 API 요청 실패: 키·API 권한·요청 제한을 확인하세요.') from None

def required(name):
    value=os.environ.get(name,'')
    if not value:raise ValueError(name+' 설정이 필요합니다.')
    return value

def coupang_signature(method,path,query,access,secret,date):
    digest=hmac.new(secret.encode(),(date+method+path+query).encode(),hashlib.sha256).hexdigest()
    return f'CEA algorithm=HmacSHA256, access-key={access}, signed-date={date}, signature={digest}'

class Coupang:
    name='쿠팡'
    methodology='쿠팡 파트너스 카테고리 베스트 API 반환 순서. 국내 전체 판매량 순위 아님.'
    def call(self,path,params=None,body=None):
        path='/v2/providers/affiliate_open_api/apis/openapi'+path
        q=up.urlencode(params or {})
        date=dt.datetime.now(dt.timezone.utc).strftime('%y%m%dT%H%M%SZ')
        auth=coupang_signature('POST' if body is not None else 'GET',path,q,
             required('COUPANG_ACCESS_KEY'),required('COUPANG_SECRET_KEY'),date)
        x=request('https://api-gateway.coupang.com'+path+('?' +q if q else ''),
            {'Authorization':auth,'Content-Type':'application/json'},
            json.dumps(body).encode() if body is not None else None)
        if str(x.get('rCode'))!='0':raise RuntimeError('쿠팡 파트너스 응답 오류')
        return x['data']
    def normalize(self,p):
        return validate_product({'id':str(p['productId']),'name':p['productName'],
            'price':str(p['productPrice']),'currency':'KRW','image':p['productImage'],
            'url':p['productUrl'],'affiliate_url':p['productUrl']},'coupang')
    def top(self,c):
        category=str(c['category_id'])
        if not category.isdigit():raise ValueError('쿠팡 카테고리 번호 필요')
        return [self.normalize(p) for p in self.call('/products/bestcategories/'+category,{'limit':10})]
    def search(self,keyword,c):
        x=self.call('/products/search',{'keyword':keyword,'limit':10})
        return [self.normalize(p) for p in x.get('productData',[])]
    def links(self,products):
        # Require API-issued affiliate links instead of constructing a referral suffix.
        x=self.call('/v1/deeplink',body={'coupangUrls':[p['url'] for p in products]})
        mapping={v['originalUrl']:v['shortenUrl'] for v in x}
        for p in products:
            p['affiliate_url']=safe_url(mapping[p['url']],['coupang.com'])

def top_signature(params,secret):
    joined=''.join(k+str(params[k]) for k in sorted(params) if k!='sign' and str(params[k]))
    return hashlib.md5((secret+joined+secret).encode()).hexdigest().upper()

class AliExpress:
    name='알리익스프레스'
    methodology='제휴 Hot Product API 최근 판매량 내림차순. 설정한 검색·카테고리 범위이며 집계 기간은 API 미공개.'
    def call(self,method,params):
        # Documented TOP HTTPS gateway and GMT+8 timestamp; no guessed sync signature.
        x={'method':method,'app_key':required('ALI_APP_KEY'),'sign_method':'md5',
           'timestamp':dt.datetime.now(dt.timezone(dt.timedelta(hours=8))).strftime('%Y-%m-%d %H:%M:%S'),
           'format':'json','v':'2.0',**{k:str(v) for k,v in params.items() if v!=''}}
        x['sign']=top_signature(x,required('ALI_APP_SECRET'))
        response=request('https://eco.taobao.com/router/rest',
            {'Content-Type':'application/x-www-form-urlencoded'},up.urlencode(x).encode())
        result=response.get(method.replace('.','_')+'_response',{}).get('resp_result',{})
        if str(result.get('resp_code'))!='200':raise RuntimeError('알리 제휴 API 응답 오류: 앱 권한 확인 필요')
        return result['result']
    def normalize(self,p):
        url=p['promotion_link']
        if url.startswith('http://s.click.aliexpress.com/'):url='https://'+url[7:]
        x={'id':str(p['product_id']),'name':p['product_title'],
           'price':p['target_sale_price'],'currency':p['target_sale_price_currency'],
           'image':p['product_main_image_url'],'url':p['product_detail_url'],
           'affiliate_url':url,'volume':int(p['lastest_volume']),
           'category':str(p['second_level_category_id'])}
        return validate_product(x,'aliexpress')
    def query(self,method,c,keywords):
        result=self.call(method,{'tracking_id':required('ALI_TRACKING_ID'),
            'target_currency':'KRW','target_language':'KO','ship_to_country':'KR',
            'page_size':50,'page_no':1,'sort':'LAST_VOLUME_DESC',
            'keywords':keywords,'category_ids':c.get('category_id','')})
        return [self.normalize(p) for p in result.get('products',{}).get('product',[])]
    def top(self,c):
        products=self.query('aliexpress.affiliate.hotproduct.query',c,c.get('keyword',''))
        volumes=[p['volume'] for p in products]
        if volumes!=sorted(volumes,reverse=True):raise ValueError('API 판매량 정렬 검증 실패')
        return products[:10]
    def search(self,keyword,c):return self.query('aliexpress.affiliate.product.query',c,keyword)
    def links(self,products):pass  # promotion_link already contains the requested tracking_id.

def validate_product(p,platform):
    domains=['coupang.com'] if platform=='coupang' else ['aliexpress.com']
    safe_url(p['url'],domains);safe_url(p['affiliate_url'],domains)
    safe_url(p['image'],['coupangcdn.com','coupang.com'] if platform=='coupang' else ['alicdn.com'])
    price=Decimal(str(p['price']))
    if not price.is_finite() or price<=0 or p['currency']!='KRW':raise ValueError('확인된 원화 가격 필요')
    if not p['id'].isdigit() or not str(p['name']).strip():raise ValueError('상품 식별 정보 없음')
    p['price']=str(price);p['name']=str(p['name'])[:250]
    return p

def type_rule(name,rules):
    matches=[r for r in rules if any(t.casefold() in name.casefold() for t in r['aliases'])
        and not any(t.casefold() in name.casefold() for t in r.get('exclude',[]))]
    if len(matches)!=1:raise ValueError('상품 종류를 명확하게 판별할 수 없습니다. 비교 규칙을 추가하세요.')
    return matches[0]

def choose_alternative(p,candidates,rule):
    valid=[]
    for a in candidates:
        if a['id']==p['id']:continue
        if re.sub(r'\W','',a['name'].casefold())==re.sub(r'\W','',p['name'].casefold()):continue
        if not any(t.casefold() in a['name'].casefold() for t in rule['aliases']):continue
        if any(t.casefold() in a['name'].casefold() for t in rule.get('exclude',[])):continue
        if p.get('category') and p['category']!=a.get('category'):continue
        ratio=Decimal(a['price'])/Decimal(p['price'])
        if Decimal('0.4')<=ratio<=Decimal('2.5'):valid.append(a)
    if not valid:raise ValueError('동종 대체 상품이 없습니다. 해당 플랫폼 제작을 중단합니다.')
    return min(valid,key=lambda a:abs(Decimal(a['price'])-Decimal(p['price'])))

def collect(platform,c):
    adapter=Coupang() if platform=='coupang' else AliExpress()
    products=adapter.top(c)
    if len(products)!=10 or len({p['id'] for p in products})!=10:
        raise ValueError('중복 없는 실제 TOP10이 필요합니다. 순위를 임의로 채우지 않습니다.')
    pairs=[];cache={}
    for rank,p in enumerate(products,1):
        rule=type_rule(p['name'],c['comparison_rules'])
        if rule['keyword'] not in cache:cache[rule['keyword']]=adapter.search(rule['keyword'],c)
        a=choose_alternative(p,cache[rule['keyword']],rule)
        pairs.append({'rank':rank,'popular':dict(p),'alternative':dict(a),'type':rule['label']})
    adapter.links([p for pair in pairs for p in (pair['popular'],pair['alternative'])])
    snap={'platform':platform,'source':adapter.name,'collected_at':now().isoformat(),
        'methodology':adapter.methodology,'scope':c.get('label','설정 카테고리'),
        'category_id':str(c.get('category_id','')),'keyword':c.get('keyword',''),
        'source_api':('https://partners.coupang.com/openapi/apidoc' if platform=='coupang'
            else 'https://open.alitrip.com/docs/api.htm?apiId=45794'),
        'disclosure':DISCLOSURE,'pairs':pairs}
    save_json(ROOT/'data/affiliate'/platform/(now().date().isoformat()+'.json'),snap)
    return snap

def price(p):return f'{Decimal(p["price"]):,.0f}원'

def make_script(snapshot,index,c):
    spans=[(0,3),(3,6),(6,10)];start,end=spans[index]
    snap={**snapshot,'pairs':snapshot['pairs'][start:end]}
    scenes=[{'narration':f'{snapshot["source"]} 인기 목록, {start+1}위부터 {end}위입니다. 제휴 링크 구매 시 수수료를 받을 수 있습니다.'}]
    for pair in snap['pairs']:
        p,a=pair['popular'],pair['alternative']
        scenes.append({'narration':f'{pair["rank"]}위, {p["name"][:32]}. 표시 가격 {price(p)}. 같은 종류의 {a["name"][:32]}는 {price(a)}입니다. 옵션과 배송비는 구매 전에 확인하세요.'})
    scenes.append({'narration':'성능 실험 결과가 아닌 판매처 자료 비교입니다. 상품 링크는 채널 프로필에서 확인하세요.'})
    return {'title':f'{snapshot["source"]} {snapshot["scope"]} 인기 {start+1}~{end}위 가격 비교'[:85],
            'scenes':scenes,'_affiliate':snap}

def portal(snapshots,c):
    cards=[]
    for snap in snapshots:
        cards.append('<!-- snapshot:'+hashlib.sha256(json.dumps(snap,sort_keys=True,ensure_ascii=False).encode()).hexdigest()+' -->')
        for pair in snap['pairs']:
            products=[]
            for tag in ('popular','alternative'):
                p=pair[tag];url=safe_url(p['affiliate_url'],['coupang.com','aliexpress.com'])
                products.append('<div><b>'+('인기 상품' if tag=='popular' else '동종 대안')+'</b><p>'+html.escape(p['name'])+'</p><strong>'+price(p)+'</strong><p><a rel="sponsored noopener" target="_blank" href="'+html.escape(url,quote=True)+'">판매처에서 확인</a></p></div>')
            cards.append('<article><h2>'+html.escape(snap['source'])+' '+str(pair['rank'])+'위 · '+html.escape(pair['type'])+'</h2><div class="pair">'+''.join(products)+'</div><small>'+html.escape(snap['collected_at'])+' 확인 · '+html.escape(snap['methodology'])+'</small></article>')
    content='<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>오늘의 상품 비교</title><style>body{max-width:980px;margin:auto;padding:24px;background:#f7f4ee;color:#292c2e;font:17px/1.6 sans-serif}article{background:white;border-radius:24px;padding:24px;margin:24px 0}.pair{display:grid;grid-template-columns:1fr 1fr;gap:24px}a{display:inline-block;background:#667553;color:white;padding:12px 20px;border-radius:12px;text-decoration:none}small{color:#706b62}.notice{background:#ebe3d5;padding:20px;border-radius:16px}@media(max-width:600px){.pair{grid-template-columns:1fr}}</style><h1>오늘의 인기 상품 비교</h1><p class="notice">'+DISCLOSURE+' 쿠팡 파트너스 및 알리익스프레스 제휴 활동입니다.</p><p>판매처 표시 가격 비교입니다. 옵션·배송비·세금·쿠폰·가격·재고는 구매 전에 확인하세요. 직접 성능 시험 결과가 아닙니다.</p>'+''.join(cards)+'</html>'
    out=ROOT/'output/affiliate-links';out.mkdir(parents=True,exist_ok=True)
    (out/'index.html').write_text(content,encoding='utf-8')
    return content

def publish_portal(content,c):
    # Render publishes only site/, while state and credentials remain private.
    dest=ROOT/'site/index.html';dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(content,encoding='utf-8')
    if os.environ.get('SHORTS_CHECKPOINT')=='1':
        import subprocess,sys
        subprocess.run([sys.executable,str(ROOT/'scripts/checkpoint.py')],check=True)
        hook=required('RENDER_DEPLOY_HOOK')
        safe_url(hook,['api.render.com'])
        if not up.urlsplit(hook).path.startswith('/deploy/'):
            raise ValueError('Render 배포 Hook 주소가 필요합니다.')
        try:
            with ur.urlopen(ur.Request(hook,data=b'',method='POST'),timeout=30):pass
        except Exception:raise RuntimeError('상품 페이지 배포 요청 실패') from None
    else:
        raise RuntimeError('로컬에서 생성한 site/index.html을 연결한 Render 저장소에 게시하세요.')


def verify_portal(c,script):
    url=safe_url(c.get('affiliate_portal_url',''),['onrender.com'])
    try:
        with ur.urlopen(url,timeout=30) as r:body=r.read(2*1024*1024).decode()
    except Exception:raise RuntimeError('공개 상품 페이지 확인 실패. GitHub Pages 설정을 확인하세요.') from None
    for pair in script['_affiliate']['pairs']:
        for p in (pair['popular'],pair['alternative']):
            if html.escape(p['affiliate_url'],quote=True) not in body:raise RuntimeError('최신 제휴 링크 게시 대기 중입니다. 다시 실행하세요.')
    fingerprint=hashlib.sha256(json.dumps(script['_affiliate'],sort_keys=True,ensure_ascii=False).encode()).hexdigest()
    if 'snapshot:'+fingerprint not in body:raise RuntimeError('영상과 상품 페이지 자료가 다릅니다. 게시 완료 후 다시 실행하세요.')

def run_affiliate(c,store):
    from comparison_render import render_comparison
    from app import upload_ready
    if c.get('speech_provider','openai')=='openai':required('OPENAI_API_KEY')
    if not c['require_review']:
        safe_url(required('RENDER_DEPLOY_HOOK'),['api.render.com'])
        safe_url(c.get('affiliate_portal_url',''),['onrender.com'])
    snapshots=[];errors=[];day=now().date().isoformat()
    for platform,pc in c['affiliate_platforms'].items():
        if not pc.get('enabled'):continue
        try:
            snap=collect(platform,pc);snapshots.append(snap)
            for index in range(3):
                brief=f'affiliate:{platform}:{index}'
                existing=next((j for j in store.rows() if j['day']==day and j['brief_id']==brief),None)
                if existing and existing['status'] not in ('draft','generation_failed'):continue
                jid=existing['id'] if existing else store.add(day,f'{brief}:{day}',brief)
                script=json.loads(existing['script']) if existing and existing['script'] else make_script(snap,index,c)
                store.update(jid,script=json.dumps(script,ensure_ascii=False))
                try:
                    path,seconds=render_comparison(c,store,jid,script)
                    save_json(ROOT/'output'/jid/'provenance.json',script['_affiliate'])
                    store.update(jid,video=path,status='review' if c['require_review'] else 'ready',error=None)
                except Exception:
                    store.update(jid,status='generation_failed',error='상품 비교 영상 제작 실패')
                    raise
        except Exception as e:
            errors.append(platform+': '+type(e).__name__);print(platform,'수집/제작 중단:',type(e).__name__,flush=True)
    # Include current ready snapshots from persisted jobs if an API temporarily fails.
    snapshots=[]
    for j in store.rows():
        if j['day']==day and j['script']:
            s=json.loads(j['script']).get('_affiliate')
            if s and j['status'] in ('ready','review','uploaded'):snapshots.append(s)
    if snapshots:
        content=portal(snapshots,c)
        if not c['require_review']:publish_portal(content,c)
        upload_ready(c,store)
    if errors:raise RuntimeError('; '.join(errors))
