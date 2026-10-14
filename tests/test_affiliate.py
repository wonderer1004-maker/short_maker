import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import affiliate as a

def product(i=1,name='무선 마우스 모델 A',cost='12000'):
    return {'id':str(i),'name':name,'price':cost,'currency':'KRW',
        'url':f'https://www.coupang.com/vp/products/{i}',
        'affiliate_url':f'https://link.coupang.com/a/{i}',
        'image':f'https://thumbnail.coupangcdn.com/{i}.jpg'}

RULE={'label':'무선 마우스','keyword':'무선 마우스','aliases':['무선 마우스'],'exclude':['케이스','거치대']}

class AffiliateTests(unittest.TestCase):
    def test_coupang_signs_exact_path_and_query(self):
        import hmac
        expected=hmac.new(b's',b'260101T010101ZGET/patha=1',hashlib.sha256).hexdigest()
        self.assertTrue(a.coupang_signature('GET','/path','a=1','k','s','260101T010101Z').endswith(expected))
    def test_top_signature_sorted_and_excludes_sign(self):
        self.assertEqual(a.top_signature({'b':'2','a':'1','sign':'ignored'},'s'),hashlib.md5(b'sa1b2s').hexdigest().upper())
    def test_https_and_host_restrictions(self):
        for url in ['http://coupang.com/a','https://coupang.com.evil.com/a','https://user@coupang.com/a','https://127.0.0.1/a']:
            with self.assertRaises(ValueError):a.safe_url(url,['coupang.com'])
    def test_non_krw_and_nonfinite_price_rejected(self):
        for field,value in [('currency','USD'),('price','NaN'),('price','0')]:
            p=product();p[field]=value
            with self.assertRaises(ValueError):a.validate_product(p,'coupang')
    def test_accessory_is_not_main_product(self):
        with self.assertRaises(ValueError):a.type_rule('무선 마우스 케이스',[RULE])
    def test_ambiguous_type_stops(self):
        with self.assertRaises(ValueError):a.type_rule('무선 마우스 키보드',[RULE,{**RULE,'aliases':['키보드']}])
    def test_alternative_same_id_or_same_name_rejected(self):
        with self.assertRaises(ValueError):a.choose_alternative(product(),[product(),product(2)],RULE)
    def test_different_kind_and_accessory_rejected(self):
        with self.assertRaises(ValueError):a.choose_alternative(product(),[product(2,'유선 키보드'),product(3,'무선 마우스 거치대')],RULE)
    def test_extreme_price_ratio_rejected(self):
        with self.assertRaises(ValueError):a.choose_alternative(product(),[product(2,'무선 마우스 모델 B','100')],RULE)
    def test_alternative_closest_valid_price(self):
        self.assertEqual(a.choose_alternative(product(),[product(2,'무선 마우스 모델 B','13000'),product(3,'무선 마우스 모델 C','18000')],RULE)['id'],'2')
    def test_preserves_top10_and_searches_type_once(self):
        tops=[product(i,f'무선 마우스 모델 {i}') for i in range(1,11)]
        with patch.object(a.Coupang,'top',return_value=tops),patch.object(a.Coupang,'search',return_value=[product(99,'무선 마우스 모델 Z')]) as search,patch.object(a.Coupang,'links'),patch.object(a,'save_json'):
            snap=a.collect('coupang',{'category_id':'1016','comparison_rules':[RULE]})
        self.assertEqual([p['popular']['id'] for p in snap['pairs']],[str(i) for i in range(1,11)])
        search.assert_called_once()
    def test_missing_or_duplicate_top10_stops(self):
        for rows in [[product()]*10,[product()]*9]:
            with patch.object(a.Coupang,'top',return_value=rows):
                with self.assertRaises(ValueError):a.collect('coupang',{'comparison_rules':[RULE]})
    def test_three_videos_cover_every_rank_once(self):
        snap={'platform':'coupang','source':'쿠팡','scope':'범위','collected_at':'2026-10-14T00:00:00+00:00','methodology':'API 반환 순서','disclosure':a.DISCLOSURE,'pairs':[{'rank':i,'popular':product(i),'alternative':product(i+20,'무선 마우스 모델 B'),'type':'무선 마우스'} for i in range(1,11)]}
        scripts=[a.make_script(snap,i,{}) for i in range(3)]
        self.assertEqual([p['rank'] for s in scripts for p in s['_affiliate']['pairs']],list(range(1,11)))
        self.assertEqual([len(s['scenes']) for s in scripts],[5,5,6])
    def test_portal_escapes_title_and_discloses(self):
        snap={'platform':'coupang','source':'쿠팡','collected_at':'now','methodology':'order','pairs':[{'rank':1,'type':'마우스','popular':product(1,'<script>'), 'alternative':product(2)}]}
        with tempfile.TemporaryDirectory() as tmp,patch.object(a,'ROOT',Path(tmp)):
            page=a.portal([snap],{})
            self.assertNotIn('<script>',page);self.assertIn('&lt;script&gt;',page)
            self.assertIn(a.DISCLOSURE,page);self.assertIn('rel="sponsored noopener"',page)
    def test_ali_cannot_silently_convert_dollars(self):
        raw={'product_id':1,'product_title':'mouse','target_sale_price':'10','target_sale_price_currency':'USD','product_main_image_url':'https://ae01.alicdn.com/a.jpg','product_detail_url':'https://www.aliexpress.com/item/1.html','promotion_link':'https://s.click.aliexpress.com/e/a','lastest_volume':3,'second_level_category_id':1}
        with self.assertRaises(ValueError):a.AliExpress().normalize(raw)

if __name__=='__main__':unittest.main()
