"""Separate price differences from sourced, narrowly defined feature advantages."""
import json
import re
from decimal import Decimal
from core import ROOT

def rank_label(platform,rank):
    return ('쿠팡 카테고리 베스트 ' if platform=='coupang' else '알리 최근 판매량순 ')+str(rank)+'위'

def facts(product):
    catalog=json.loads((ROOT/'verified_specs.json').read_text(encoding='utf-8'))
    found=[]
    for entry in catalog:
        if re.search(entry['model_pattern'],product['name'],re.I) and not any(
            t.casefold() in product['name'].casefold() for t in entry.get('exclude',[])):
            found.append(entry)
    return found[0] if len(found)==1 else None

def assessment(pair):
    p,a=pair['popular'],pair['alternative']
    if p['currency']!=a['currency']:raise ValueError('같은 통화 가격만 비교할 수 있습니다.')
    left,right=Decimal(p['price']),Decimal(a['price'])
    gap=abs(left-right)
    if gap==0:price_line='두 상품의 표시가가 같습니다.'
    else:
        side='인기 상품' if left<right else '비교 상품'
        price_line=f'{side}이 표시가 기준 {gap:,.0f}원 더 저렴합니다.'
    pf,af=facts(p),facts(a)
    feature_lines=[];sources=[]
    if pf and af:
        sources=[pf['source_url'],af['source_url']]
        for metric,info in pf.get('metrics',{}).items():
            other=af.get('metrics',{}).get(metric)
            if not other or info['unit']!=other['unit'] or info['basis']!=other['basis']:continue
            x,y=Decimal(str(info['value'])),Decimal(str(other['value']))
            if x==y:continue
            if info.get('better')!=other.get('better') or info.get('better') not in ('higher','lower'):continue
            winner=pf if ((x>y)==(info['better']=='higher')) else af
            feature_lines.append(f'{info["label"]}: {winner["model"]} 우위 ({x:g} 대 {y:g}{info["unit"]}, {info["basis"]}).')
    if not feature_lines:feature_lines=['성능 우위는 확인된 비교 자료가 부족합니다.']
    return {'price_line':price_line,'features':feature_lines[:2],
            'popular_specs':pf,'alternative_specs':af,'source_urls':sources,
            'qualification':'상품 옵션·배송비·쿠폰·세금을 포함한 최종 결제 가격 및 종합 성능 우위는 별도 확인 필요'}
