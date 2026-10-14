"""Use only the ranking section actually advertised by MUSINSA's public page.
No search-sort guesses, price sorting, CAPTCHA bypass, or invented rankings.
"""
import datetime as dt
import hashlib
import json
import re
import urllib.parse
import urllib.request
from pathlib import Path
from core import ROOT, now, save_json

PAGE='https://www.musinsa.com/main/musinsa/ranking'
HOSTS={'www.musinsa.com','client.musinsa.com','api.musinsa.com','image.msscdn.net'}

def fetch(url, binary=False):
    parsed=urllib.parse.urlsplit(url)
    if parsed.scheme!='https' or parsed.hostname not in HOSTS or parsed.username:
        raise ValueError('허용되지 않은 랭킹 출처 URL')
    req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0','Accept':'application/json,text/html,*/*'})
    with urllib.request.urlopen(req,timeout=40) as r:
        if urllib.parse.urlsplit(r.url).hostname not in HOSTS:raise ValueError('출처 이동 확인 필요')
        data=r.read(12*1024*1024+1)
    if len(data)>12*1024*1024:raise ValueError('출처 파일이 너무 큽니다.')
    return data if binary else data.decode('utf-8')

def walk(v):
    if isinstance(v,dict):
        yield v
        for x in v.values():yield from walk(x)
    elif isinstance(v,list):
        for x in v:yield from walk(x)

def discover():
    html=fetch(PAGE)
    match=re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>',html,re.S)
    if not match:raise ValueError('랭킹 페이지 구조 변경. 임의 순위로 대체하지 않습니다.')
    d=json.loads(match.group(1))
    stores=d['props']['pageProps']['data']['store']
    store=next(s for s in stores if s['code']=='musinsa')
    advertised=next(x for x in walk(store) if x.get('type')=='ranking')
    data=json.loads(fetch(advertised['bffWebApi']))
    tabs=next(x for x in data['data']['modules'] if x.get('type')=='TAB_OUTLINED')
    root=next(x for x in tabs['tabs'] if x.get('params',{}).get('sectionId')=='199'
              and isinstance(x.get('text'),dict) and x['text'].get('text')=='전체')
    categories={x['text']['text']:x['params'] for x in walk(root)
        if isinstance(x.get('text'),dict) and x.get('params',{}).get('categoryCode')}
    return tabs['apiUrl'],categories

def extract(payload,category,category_code,clock=None,max_age_hours=24):
    modules=payload['data']['modules'];clock=clock or now()
    info=next(m['information'] for m in modules if m.get('type')=='QUERY_UPDATEDAT')
    explanation=info.get('additionalInformation',{}).get('text','')
    if not all(word in explanation for word in ('매출','조회수','후기')):
        raise ValueError('인기순위 산정 기준이 확인되지 않습니다.')
    stamp=dt.datetime.fromtimestamp(int(info['updatedAt'])/1000,dt.timezone.utc)
    age=(clock-stamp).total_seconds()/3600
    if age < -.5 or age>max_age_hours:raise ValueError('랭킹이 오래되었거나 확인 시각이 잘못되었습니다.')
    products={}
    for module in modules:
        if module.get('type')!='MULTICOLUMN':continue
        for item in module.get('items',[]):
            if item.get('type')!='PRODUCT_COLUMN':continue
            rank=item.get('image',{}).get('rank')
            if type(rank) is not int or rank not in range(1,6):continue
            event=item['image']['onClickLike']['eventLog']['ga4']['payload']
            if event.get('item_category_id')!=category_code or event.get('applied_tab')!='ranking_cat':
                raise ValueError('다른 카테고리 또는 신상·급상승 랭킹입니다.')
            info_item=item['info'];id=str(item['id'])
            if not id.isdigit() or event.get('item_id')!=id:raise ValueError('상품 식별자 불일치')
            image=item['image']['url']
            if urllib.parse.urlsplit(image).hostname!='image.msscdn.net':raise ValueError('상품 사진 출처 변경')
            p=dict(rank=rank,id=id,brand=info_item['brandName'],name=info_item['productName'],
                   price=int(event['price']),image_url=image,url='https://www.musinsa.com/products/'+id)
            if not p['brand'] or not p['name'] or p['price']<=0:raise ValueError('상품 정보 누락')
            if rank in products and products[rank]!=p:raise ValueError('중복 순위가 서로 다릅니다.')
            products[rank]=p
    if sorted(products)!=[1,2,3,4,5] or len({p['id'] for p in products.values()})!=5:
        raise ValueError('1~5위를 모두 확인하지 못했습니다.')
    return dict(category=category,category_code=category_code,source='무신사 카테고리 상품 랭킹',
                methodology=explanation,source_updated_at=stamp.isoformat(),collected_at=clock.isoformat(),
                source_page=PAGE,products=[products[i] for i in range(1,6)],
                scope='해당 쇼핑몰의 상품 인기순위. 브랜드 전체·국내 전체 판매량 순위 아님.',
                price_basis='쿠폰·회원 추가할인 전 표시가')

def collect_category(c,category,discovery=None):
    template,categories=discovery or discover()
    if category not in categories:raise ValueError('해당 카테고리가 출처에 없습니다.')
    params=categories[category];url=template
    for k,v in params.items():url=url.replace('{'+k+'}',v)
    if '{' in url:raise ValueError('랭킹 주소 구조 변경')
    payload=json.loads(fetch(url))
    snapshot=extract(payload,category,params['categoryCode'],max_age_hours=c.get('ranking_max_age_hours',24))
    snapshot['source_api']=url
    folder=ROOT/'data/rankings'/params['categoryCode'];folder.mkdir(parents=True,exist_ok=True)
    save_json(folder/(now().date().isoformat()+'.json'),snapshot)
    return snapshot

def fingerprint(snapshot):
    stable=[(p['rank'],p['id'],p['price']) for p in snapshot['products']]
    return hashlib.sha256(json.dumps(stable).encode()).hexdigest()[:24]

def assets(snapshot,folder):
    from PIL import Image
    folder.mkdir(parents=True,exist_ok=True)
    paths=[]
    for p in snapshot['products']:
        path=folder/(p['id']+'.jpg')
        if not path.exists():
            data=fetch(p['image_url'],binary=True)
            temp=path.with_suffix('.download');temp.write_bytes(data)
            try:
                with Image.open(temp) as im:
                    if im.mode in ('RGBA','LA') or 'transparency' in im.info:
                        rgba=im.convert('RGBA');bg=Image.new('RGBA',rgba.size,'white')
                        im=Image.alpha_composite(bg,rgba)
                    im.convert('RGB').save(path,quality=95)
            finally:temp.unlink(missing_ok=True)
        paths.append(path)
    return paths

def make_script(snapshot):
    category=snapshot['category'];stamp=snapshot['source_updated_at'][:10]
    title=f'{category} 인기 TOP 5 | 무신사 {stamp}'
    intro=f'무신사 {category} 상품 인기순위, 상위 다섯 개를 확인해 보세요.'
    scenes=[dict(heading='인기 TOP 5',narration=intro)]
    for p in reversed(snapshot['products']):
        # No LLM-generated performance claims or fake tests. Keep name recognisable.
        name=p['name']
        spoken=re.sub(r'_[A-Z0-9]+$','',name)
        spoken=re.sub(r'\[[^\]]*\]|\([^)]*\)','',spoken).strip()[:60]
        scenes.append(dict(heading=p['brand'],narration=f'{p["rank"]}위, {p["brand"]}. {spoken}. 쿠폰 전 표시가는 {p["price"]:,}원입니다.'))
    scenes.append(dict(heading='출처와 시각 확인',narration='매출, 조회수, 후기수를 반영한 무신사 상품 랭킹입니다. 가격과 재고는 구매 전에 다시 확인하세요.'))
    return dict(title=title[:90],scenes=scenes,_ranking=snapshot)

def run_popularity(c,store):
    from editorial import render_ranking
    from app import upload_ready
    day=now().date().isoformat();discovery=discover()
    failures=[]
    for category in c['ranking_categories'][:c['daily_videos']]:
        try:
            snapshot=collect_category(c,category,discovery)
            source='popularity:'+snapshot['category_code']+':'+fingerprint(snapshot)
            if not c.get('skip_unchanged_rankings',True):source+=':'+day
            existing=next((j for j in store.rows() if j['source_id']==source),None)
            if existing and existing['status'] not in ('draft','generation_failed'):continue
            id=existing['id'] if existing else store.add(day,source,'rank:'+snapshot['category_code'])
            if not id:continue
            job=store.get(id)
            script=json.loads(job['script']) if job['script'] else make_script(snapshot)
            store.update(id,script=json.dumps(script,ensure_ascii=False))
            file,seconds=render_ranking(c,store,id,script['_ranking'],script)
            store.update(id,status='review' if c['require_review'] else 'ready',video=file,error=None)
            save_json(ROOT/'output'/id/'provenance.json',script['_ranking'])
            print('인기순위 영상 완성:',category,seconds,'초',flush=True)
        except Exception as e:
            if 'id' in locals() and id and store.get(id) and store.get(id)['status'] in ('draft','generation_failed'):
                store.update(id,status='generation_failed',error='인기순위 또는 영상 생성 실패: '+type(e).__name__)
            failures.append(category);print('수집/제작 실패:',category,type(e).__name__,flush=True)
        finally:id=None
    upload_ready(c,store)
    if failures:raise RuntimeError('일부 인기순위 영상 제작 실패. 가격순으로 대체하지 않았습니다.')
