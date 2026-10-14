import datetime as dt
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from core import Store, KST, select_brief, publish_slot, validate_script, config
from app import DEMO_SCRIPT
from youtube import metadata, upload

class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.store=Store(Path(self.tmp.name)/'db.sqlite3')
        self.c=config()
        self.c['content_mode']='checklist'
    def tearDown(self):
        self.store.db.close();self.tmp.cleanup()
    def test_source_is_never_added_twice_even_next_day(self):
        self.assertTrue(self.store.add('2026-10-14','source-a','brief-a'))
        self.assertIsNone(self.store.add('2026-10-15','source-a','brief-b'))
    def test_daily_brief_not_duplicated(self):
        self.store.add('2026-10-14','source-a','brief-a')
        self.assertIsNone(self.store.add('2026-10-14','source-b','brief-a'))
    def test_same_brief_can_have_new_source_next_day(self):
        self.store.add('2026-10-14','source-a','brief-a')
        self.assertTrue(self.store.add('2026-10-15','source-b','brief-a'))
    def test_billable_request_cap_is_atomic_and_persists(self):
        self.store.reserve_request(1)
        with self.assertRaises(RuntimeError):self.store.reserve_request(1)
        self.assertEqual(self.store.db.execute('SELECT requests FROM usage').fetchone()[0],1)
    def test_keyword_matching_and_verified_brief_required(self):
        catalog=[{'id':'a','approved':False,'keywords':['패딩']},
                 {'id':'b','approved':True,'keywords':['러닝']}]
        self.assertIsNone(select_brief({'title':'패딩 인기'},catalog,set()))
        self.assertEqual(select_brief({'title':'러닝 신발'},catalog,set())['id'],'b')
        self.assertIsNone(select_brief({'title':'러닝 신발'},catalog,{'b'}))
    def test_past_schedule_moves_to_tomorrow_in_kst(self):
        t=dt.datetime(2026,10,14,13,tzinfo=KST)
        slot=publish_slot(self.c,0,t)
        self.assertEqual(slot,'2026-10-15T03:00:00Z')
    def test_slot_has_safety_margin(self):
        t=dt.datetime(2026,10,14,11,45,tzinfo=KST)
        self.assertEqual(publish_slot(self.c,0,t),'2026-10-15T03:00:00Z')
    def test_duplicate_script_rejected(self):
        old=' '.join(s['narration'] for s in DEMO_SCRIPT['scenes'])
        with self.assertRaises(ValueError):validate_script(DEMO_SCRIPT,self.c,[old])
    def test_valid_script(self):
        self.assertEqual(validate_script(DEMO_SCRIPT,self.c)['title'],DEMO_SCRIPT['title'])
    def test_private_upload_has_no_publish_at(self):
        job={'id':'abc','script':json.dumps(DEMO_SCRIPT),'publish_at':None}
        body=metadata(self.c,job,0)
        self.assertEqual(body['status']['privacyStatus'],'private')
        self.assertNotIn('publishAt',body['status'])
    def test_scheduled_upload_stays_private_until_slot(self):
        self.c['mode']='scheduled'
        body=metadata(self.c,{'id':'abc','script':json.dumps(DEMO_SCRIPT),'publish_at':None},0)
        self.assertEqual(body['status']['privacyStatus'],'private')
        self.assertIn('publishAt',body['status'])
    def test_upload_marker_added_for_reconciliation(self):
        body=metadata(self.c,{'id':'job123','script':json.dumps(DEMO_SCRIPT),'publish_at':None},0)
        self.assertIn('shorts-studio:job123',body['snippet']['description'])
    def test_disallow_sql_field_injection(self):
        with self.assertRaises(ValueError):self.store.update('abc',**{'status=1; DROP TABLE jobs; --':'x'})
    def test_ready_backlog_uploads_limited_and_unknown_blocks(self):
        import app
        self.store.db.execute('CREATE TABLE upload_events(job_id TEXT PRIMARY KEY,day TEXT,attempt_at TEXT)')
        (Path(self.tmp.name)/'short.mp4').write_bytes(b'test video')
        for n in range(5):
            id=self.store.add('2026-10-13',f's{n}',f'b{n}')
            self.store.update(id,status='ready',video='short.mp4')
        with patch('app.ROOT',Path(self.tmp.name)),patch('youtube.service',return_value=(object(),{})),patch('youtube.upload') as mocked:
            (Path(self.tmp.name)/'token.json').write_text('{}')
            app.upload_ready(self.c,self.store)
            self.assertEqual(mocked.call_count,3)
            self.store.update(self.store.rows()[0]['id'],status='upload_unknown')
            mocked.reset_mock();app.upload_ready(self.c,self.store)
            mocked.assert_not_called()
    def test_network_error_leaves_unknown_and_never_reinserts(self):
        from unittest.mock import Mock
        id=self.store.add('2026-10-14','source','brief')
        file=Path(self.tmp.name)/'short.mp4';file.write_bytes(b'test video')
        self.store.update(id,status='ready',script=json.dumps(DEMO_SCRIPT),video='short.mp4')
        yt=Mock();yt.videos.return_value.insert.return_value.next_chunk.side_effect=OSError('lost response')
        with patch('youtube.ROOT',Path(self.tmp.name)):
            with self.assertRaises(RuntimeError):upload(self.c,self.store,self.store.get(id),0,yt)
            self.assertEqual(self.store.get(id)['status'],'upload_unknown')
            yt.reset_mock();upload(self.c,self.store,self.store.get(id),0,yt)
            yt.videos.assert_not_called()
    def test_success_records_remote_id(self):
        from unittest.mock import Mock
        id=self.store.add('2026-10-14','source','brief')
        (Path(self.tmp.name)/'short.mp4').write_bytes(b'test video')
        self.store.update(id,status='ready',script=json.dumps(DEMO_SCRIPT),video='short.mp4')
        yt=Mock();yt.videos.return_value.insert.return_value.next_chunk.return_value=(None,{'id':'REMOTE123'})
        with patch('youtube.ROOT',Path(self.tmp.name)):upload(self.c,self.store,self.store.get(id),0,yt)
        self.assertEqual(self.store.get(id)['youtube_id'],'REMOTE123')
        self.assertEqual(self.store.get(id)['status'],'uploaded')
    def test_run_daily_is_idempotent_without_second_paid_generation(self):
        import app
        self.store.db.execute('CREATE TABLE upload_events(job_id TEXT PRIMARY KEY,day TEXT,attempt_at TEXT)')
        videos=[{'id':str(n),'title':topic} for n,topic in enumerate(['경량패딩','러닝','출퇴근'])]
        with patch('app.collect',return_value=videos),patch('app.generate',return_value=DEMO_SCRIPT) as gen,patch('app.render',return_value=('output/test.mp4',30)),patch('app.upload_ready'):
            app.run_daily(self.c,self.store)
            self.assertEqual(gen.call_count,3)
            app.run_daily(self.c,self.store)
            self.assertEqual(gen.call_count,3)
            self.assertEqual(len(self.store.rows()),3)
    def test_quota_error_is_failed_not_unknown(self):
        from unittest.mock import Mock
        from googleapiclient.errors import HttpError
        import httplib2
        id=self.store.add('2026-10-14','source','brief')
        (Path(self.tmp.name)/'short.mp4').write_bytes(b'test video')
        self.store.update(id,status='ready',script=json.dumps(DEMO_SCRIPT),video='short.mp4')
        yt=Mock();yt.videos.return_value.insert.return_value.next_chunk.side_effect=HttpError(httplib2.Response({'status':'403'}),b'{"error":{"message":"quota exceeded"}}')
        with patch('youtube.ROOT',Path(self.tmp.name)):
            with self.assertRaises(RuntimeError):upload(self.c,self.store,self.store.get(id),0,yt)
        self.assertEqual(self.store.get(id)['status'],'upload_failed')

if __name__=='__main__':unittest.main()
