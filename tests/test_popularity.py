import copy
import datetime as dt
import json
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from popularity import extract,fingerprint,make_script,fetch
from core import KST
from youtube import metadata

def fixture():
    stamp=dt.datetime(2026,10,14,9,tzinfo=KST)
    modules=[{'type':'QUERY_UPDATEDAT','information':{'updatedAt':int(stamp.timestamp()*1000),
               'additionalInformation':{'text':'매출, 조회수, 후기수를 반영한 상품 랭킹입니다.'}}}]
    items=[]
    for rank,price in enumerate([98000,50000,70000,29000,90000],1):
        id=str(rank+100)
        items.append({'type':'PRODUCT_COLUMN','id':id,'image':{'rank':rank,'url':'https://image.msscdn.net/'+id+'.jpg',
          'onClickLike':{'eventLog':{'ga4':{'payload':{'item_category_id':'002027','item_id':id,'price':price,'applied_tab':'ranking_cat'}}}}},
          'info':{'brandName':'브랜드'+str(rank),'productName':'패딩'+str(rank)}})
    modules.append({'type':'MULTICOLUMN','items':items})
    return {'data':{'modules':modules}},stamp

class PopularityTests(unittest.TestCase):
    def test_does_not_reorder_by_price(self):
        p,t=fixture();s=extract(p,'경량 패딩/패딩 베스트','002027',clock=t)
        self.assertEqual([x['price'] for x in s['products']],[98000,50000,70000,29000,90000])
    def test_missing_rank_stops(self):
        p,t=fixture();p['data']['modules'][1]['items'].pop()
        with self.assertRaises(ValueError):extract(p,'패딩','002027',clock=t)
    def test_wrong_category_stops(self):
        p,t=fixture();p['data']['modules'][1]['items'][0]['image']['onClickLike']['eventLog']['ga4']['payload']['item_category_id']='000'
        with self.assertRaises(ValueError):extract(p,'패딩','002027',clock=t)
    def test_new_arrival_rank_is_not_popularity(self):
        p,t=fixture();p['data']['modules'][1]['items'][0]['image']['onClickLike']['eventLog']['ga4']['payload']['applied_tab']='ranking_theme_new'
        with self.assertRaises(ValueError):extract(p,'패딩','002027',clock=t)
    def test_stale_rank_stops(self):
        p,t=fixture()
        with self.assertRaises(ValueError):extract(p,'패딩','002027',clock=t+dt.timedelta(hours=25))
    def test_methodology_required(self):
        p,t=fixture();p['data']['modules'][0]['information']['additionalInformation']['text']='가격이 저렴한 순'
        with self.assertRaises(ValueError):extract(p,'패딩','002027',clock=t)
    def test_duplicate_products_rejected(self):
        p,t=fixture();a=p['data']['modules'][1]['items'];a[1]['id']=a[0]['id'];a[1]['image']['onClickLike']['eventLog']['ga4']['payload']['item_id']=a[0]['id']
        with self.assertRaises(ValueError):extract(p,'패딩','002027',clock=t)
    def test_fingerprint_ignores_timestamp_but_tracks_changes(self):
        p,t=fixture();s=extract(p,'패딩','002027',clock=t);other=copy.deepcopy(s);other['collected_at']='tomorrow'
        self.assertEqual(fingerprint(s),fingerprint(other));other['products'][0]['price']+=100
        self.assertNotEqual(fingerprint(s),fingerprint(other))
    def test_countdown_follows_real_rank(self):
        p,t=fixture();s=extract(p,'패딩','002027',clock=t);script=make_script(s)
        self.assertEqual(len(script['scenes']),7)
        self.assertTrue(script['scenes'][1]['narration'].startswith('5위'))
        self.assertTrue(script['scenes'][5]['narration'].startswith('1위'))
    def test_rank_upload_description_has_source_and_avoids_price_rank_claim(self):
        p,t=fixture();s=extract(p,'패딩','002027',clock=t);script=make_script(s)
        c={'mode':'private','made_for_kids':False,'contains_synthetic_media':False,'channel_profile_cta':'저장하세요'}
        d=metadata(c,{'id':'test','script':json.dumps(script)},0)['snippet']['description']
        self.assertIn('매출, 조회수, 후기수',d);self.assertIn('무신사',d);self.assertNotIn('가격순',d)
    def test_external_url_is_rejected_before_fetch(self):
        with self.assertRaises(ValueError):fetch('http://127.0.0.1/secrets')
    def test_rank_zero_cannot_be_promoted_to_first(self):
        p,t=fixture();p['data']['modules'][1]['items'][0]['image']['rank']=0
        with self.assertRaises(ValueError):extract(p,'패딩','002027',clock=t)
    def test_future_timestamp_rejected(self):
        p,t=fixture()
        with self.assertRaises(ValueError):extract(p,'패딩','002027',clock=t-dt.timedelta(hours=2))

if __name__=='__main__':unittest.main()
