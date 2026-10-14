import json, os
from pathlib import Path
root=Path(__file__).resolve().parents[1]
raw=os.environ.get('YOUTUBE_TOKEN_JSON','')
channel=os.environ.get('YOUTUBE_CHANNEL_ID','')
if not raw or not channel:raise SystemExit('GitHub Secrets에 OAuth token JSON과 채널 ID를 입력하세요.')
token=json.loads(raw)
if not token.get('refresh_token'):raise SystemExit('갱신 가능한 OAuth 토큰이 필요합니다.')
(root/'token.json').write_text(json.dumps(token),encoding='utf-8')
(root/'token.json').chmod(0o600)
(root/'data').mkdir(exist_ok=True)
(root/'data/channel.json').write_text(json.dumps({'id':channel,'title':'GitHub 연결 채널'}),encoding='utf-8')
c=json.loads((root/'config.example.json').read_text(encoding='utf-8'))
if (os.environ.get('CONTENT_MODE') or 'affiliate')=='affiliate':
    c.update(json.loads((root/'affiliate.config.example.json').read_text(encoding='utf-8')))
    if os.environ.get('AFFILIATE_CONFIG_JSON'):
        supplied=json.loads(os.environ['AFFILIATE_CONFIG_JSON'])
        c['affiliate_platforms']=supplied['affiliate_platforms']
    c['affiliate_portal_url']=os.environ.get('AFFILIATE_PORTAL_URL') or c['affiliate_portal_url']
mode=os.environ.get('PUBLICATION_MODE') or 'scheduled'
if mode not in ('private','scheduled'):raise SystemExit('PUBLICATION_MODE must be private or scheduled')
c['mode']=mode
c['require_review']=False
c['speech_provider']=os.environ.get('SPEECH_PROVIDER') or 'openai'
if c['speech_provider'] not in ('openai','edge'):raise SystemExit('음성 제공자 설정을 확인하세요.')
(root/'config.json').write_text(json.dumps(c,ensure_ascii=False),encoding='utf-8')
print('연결 설정 완료. 공개 설정:',mode,'음성:',c['speech_provider'],'토큰 내용은 출력하지 않습니다.')
