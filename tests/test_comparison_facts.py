import unittest
from comparison_facts import assessment,rank_label,facts

def p(name,price):return {'name':name,'price':str(price),'currency':'KRW'}

class ComparisonFactsTests(unittest.TestCase):
    def test_price_and_feature_advantages_can_differ(self):
        result=assessment({'popular':p('로지텍 M240',15000),'alternative':p('로지텍 M650',33000)})
        self.assertIn('인기 상품',result['price_line']);self.assertIn('18,000원',result['price_line'])
        self.assertIn('M650',result['features'][0]);self.assertEqual(len(result['source_urls']),2)
    def test_unknown_model_cannot_receive_performance_win(self):
        result=assessment({'popular':p('마우스 미확인 A',15000),'alternative':p('마우스 미확인 B',12000)})
        self.assertIn('비교 상품',result['price_line']);self.assertIn('자료가 부족',result['features'][0])
    def test_same_price_no_price_winner(self):
        self.assertIn('같습니다',assessment({'popular':p('A',100),'alternative':p('B',100)})['price_line'])
    def test_business_variant_excluded(self):
        self.assertIsNone(facts(p('로지텍 M240 비즈니스용',10000)))
    def test_different_currency_rejected(self):
        other=p('B',10);other['currency']='USD'
        with self.assertRaises(ValueError):assessment({'popular':p('A',100),'alternative':other})
    def test_rank_label_does_not_invent_coupang_sales_volume(self):
        self.assertEqual(rank_label('coupang',3),'쿠팡 카테고리 베스트 3위')
        self.assertEqual(rank_label('aliexpress',3),'알리 최근 판매량순 3위')

if __name__=='__main__':unittest.main()
