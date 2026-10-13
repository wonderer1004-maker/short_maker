# 직장인의 쇼츠 스튜디오 V1

인기 주제 조사 → 원본 대본 → 한국어 AI 내레이션 → 세로 영상·자막·음악 → 검토 → 비공개 또는 예약 업로드 → 성과 기록을 실행하는 Python 프로그램입니다.

**이 파일은 완성 코드입니다. 본인 API 키와 유튜브 OAuth 로그인 전에는 실제 인기 데이터 수집·유료 음성 생성·채널 업로드가 실행되지 않습니다. 이 대화에서 채널 연결이나 실제 게시를 완료한 것은 아닙니다.**

## 처음 시작하기 — Windows PC 권장

1. ZIP을 압축 해제합니다. 한글 안내와 코드를 함께 보관합니다.
2. Python 3.11 이상을 설치합니다. 설치 화면에서 `Add Python to PATH`를 선택합니다.
3. FFmpeg를 설치하고 `ffmpeg`, `ffprobe`를 PATH에 추가합니다. Windows에서는 터미널에서 `winget install Gyan.FFmpeg` 후 터미널을 다시 열 수 있습니다. 공식 배포 안내: https://ffmpeg.org/download.html
4. `START_WINDOWS.bat`를 더블클릭합니다. 필요한 Python 패키지를 설치하고 관리 화면을 엽니다.
5. 관리 화면에서 동봉된 **25초 화면 샘플**을 재생합니다. 샘플은 자막과 자체 합성 배경음악이 있으며, 설명 음성은 없는 디자인 미리보기입니다. 실제 제작에서는 API로 설명 음성이 생성됩니다.
6. 아래 안내에 따라 API 키와 OAuth 파일을 넣습니다.
7. 터미널에서 `.venv\Scripts\python.exe app.py login`을 실행하고 본인 구글 계정과 정확한 유튜브 채널을 선택합니다.
8. 관리 화면의 `인기 후보 50개 수집` 또는 `오늘 영상 제작`을 누릅니다. 작업 중에는 기다린 뒤 페이지를 새로고침합니다.
9. 영상의 사실·자막·발음·사용 권리를 확인하고 `확인 완료 · 업로드 대기`를 누릅니다. `준비 영상 업로드`를 누르면 기본적으로 비공개로 업로드됩니다.
10. 잘 작동하는 것을 확인한 뒤 아래 자동화 설정을 적용합니다.

Android는 영상 관리·유튜브 확인에 사용할 수 있습니다. 이 프로그램의 FFmpeg 작업과 OAuth 최초 연결은 PC에서 하는 것을 권장합니다. 휴대폰에서 주소 하나로 이용하는 공개 웹앱이나 서버 배포를 완료한 버전은 아닙니다. 현재 관리 화면은 실행 중인 PC의 `http://127.0.0.1:8765`입니다.

## 필요한 연결

### 1. YouTube Data API 키

- Google Cloud Console https://console.cloud.google.com/ 에서 새 프로젝트를 만듭니다.
- `API 및 서비스 → 라이브러리 → YouTube Data API v3 → 사용`을 선택합니다.
- `사용자 인증 정보 → 사용자 인증 정보 만들기 → API 키`를 선택합니다.
- 키의 API 제한을 YouTube Data API v3로 설정합니다. 이 키는 조회용입니다. 업로드 권한은 OAuth로 별도 연결합니다.

### 2. YouTube 업로드 OAuth

- 같은 프로젝트의 Google Auth Platform/OAuth 동의 화면을 설정합니다.
- 외부 앱을 테스트 상태로 사용할 경우 본인의 계정을 테스트 사용자로 추가합니다.
- `OAuth 클라이언트 ID`를 만들고 애플리케이션 유형을 **데스크톱 앱**으로 선택합니다.
- JSON을 내려받아 프로그램 폴더에 `client_secret.json`이라는 이름으로 저장합니다.
- `app.py login`에서 `youtube.upload`, `youtube.readonly` 권한을 허용합니다.
- 로그인 결과의 채널 이름·ID를 확인합니다. 업로드 시 이 연결 채널을 다시 검사합니다.
- 테스트 상태 앱의 토큰 유효기간, 계정 인증·업로드 한도, API 할당량 때문에 장기 자동화가 멈출 수 있습니다. 재로그인 또는 Google Cloud의 앱 설정·한도를 확인하세요.
- API 프로젝트의 공개 업로드 조건은 공식 문서와 계정 상태를 확인하세요. 정책·API 문서는 변경될 수 있습니다. 공개 제한이 있는 상태를 프로그램이 우회하지 않습니다.

### 3. OpenAI API 키

- 본인의 API 계정에서 키를 발급받고 API 결제·사용 한도를 설정합니다.
- ChatGPT 구독과 API 사용료는 별도입니다.
- `ENV_EXAMPLE.txt`를 `.env`로 복사한 뒤 본인의 키를 입력합니다.

```dotenv
YOUTUBE_API_KEY=본인_조회용_API_키
OPENAI_API_KEY=본인_AI_API_키
```

키·OAuth JSON·token.json을 GitHub에 올리거나 다른 사람에게 보내지 마세요. ZIP에 실제 키나 채널 로그인 정보는 포함하지 않았습니다.

## 수집 방식과 분석의 정확한 범위

- 기본 분야: 경량패딩·러닝용품·출퇴근 의류.
- 최근 30일의 검색어별 조회수순 후보를 최대 50개씩 조회하고 합칩니다.
- 중복 영상 ID를 제거한 뒤 **수집 후보 중 누적 조회수순 50개**를 보여줍니다.
- 검색 결과가 충분하지 않으면 50개 미만일 수 있습니다. 유튜브 전체의 절대 TOP 50, 전체 쇼츠 순위, 전수조사가 아닙니다.
- `누적 조회수 ÷ 게시 후 경과일`은 평균 속도 참고값이며 최근 24시간 증가량이 아닙니다.
- 원본 영상·음성·대본·썸네일을 내려받거나 분석하지 않습니다. 첫 2초 장면과 실제 영상 구성은 사람이 링크를 열어 조사해야 합니다.
- 인기 제목은 주제 힌트로만 사용합니다. 사실 근거로 사용하지 않습니다.

## 새 영상의 내용과 제품 사진

`catalog.json`은 검증한 주제 자료입니다. 기본 3개는 제품 순위·효능·가격을 주장하지 않는 구매 체크리스트입니다. 진짜 제품 TOP 5를 자동으로 발명하지 않습니다.

제품 비교를 만들려면 다음을 직접 추가하세요.

1. 제품 이름, 확인한 가격, 판매처 URL과 확인 날짜, 실제 실험 결과를 `facts`에 기록합니다.
2. 근거 링크를 `source_urls`에 기록합니다.
3. 직접 촬영한 제품 사진 또는 상업적 편집·게시 권한이 확보된 사진을 `assets/media`에 넣습니다.
4. 해당 brief의 `media`를 `["assets/media/my_product.jpg"]`처럼 설정합니다.
5. 사진 사용 권리를 확보한 뒤 `media_rights_confirmed`를 `true`로 설정합니다. 사실 검토 후 `approved`를 `true`로 설정합니다.

제조사·판매처의 웹페이지 사진은 공개되어 있다는 이유만으로 재사용 권한이 생기지 않습니다. AI 이미지나 자료 화면을 실제 착용·실험 영상으로 표시하지 마세요.

자료가 없으면 직접 그린 설명 카드가 사용됩니다. 카드 템플릿의 테마·확대 효과·장면별 설명은 포함하지만, 실제 제품 촬영이나 고품질 생성형 동영상 제작을 대신하지 않습니다. 비슷한 주제와 카드만 반복하면 시청 성과와 수익화에 불리할 수 있으므로 원본 촬영과 고유한 설명을 보강하세요.

## 기본 운영

`config.example.json`은 최초 참고 설정이며 `START_WINDOWS.bat`가 `config.json`으로 복사합니다. 프로그램은 `config.json`이 있으면 그 파일을 읽습니다.

```json
{
  "daily_videos": 3,
  "publish_hours_kst": [12, 18, 21],
  "mode": "private",
  "require_review": true,
  "daily_run_hour_kst": 7
}
```

위 항목만 **기존 config.json 안에서 수정**하세요. 위 조각으로 파일 전체를 덮어쓰면 다른 필수 설정이 빠집니다.

- `private`: 비공개 업로드, 예약 공개 없음.
- `scheduled`: 비공개 상태로 업로드하고 `publishAt`으로 예약 공개.
- `require_review: true`: 영상 생성 후 검토 대기. 사람이 확인 버튼을 눌러야 업로드 대기에 들어갑니다.
- `require_review: false`: 검증된 catalog의 자료로 생성한 뒤 업로드까지 이어집니다. 자동 사실 검증이나 수익화 보장이 추가되는 것은 아닙니다.
- 생성 후 공개 시각이 이미 지났거나 30분 이내이면 해당 시각을 다음 날로 이동합니다.
- 하루 생성 목표를 채우려면 그날 사용하지 않은 검증 brief와 아직 사용하지 않은 원본 후보가 필요합니다. 부족하면 개수를 줄여 기록하며 동일 대본으로 채우지 않습니다.
- 추천량은 하루 3개입니다. 50개를 설정하려면 공개 시각 목록도 50개로 늘리고 자료·AI 요청 한도·업로드 한도를 확보해야 합니다. 반복 게시가 수익을 늘린다는 보장은 없습니다.

## 자동으로 매일 실행

### 검토형

```bash
python app.py daemon
```

프로그램이 켜져 있으면 한국시간 오전 7시 이후 하루 한 번 실행합니다. 꺼져 있었으면 켠 날 설정 시각 이후 실행합니다. 이 명령이 실행 중인 동안 PC 또는 서버가 켜져 있어야 합니다. 오류 후 비용이 드는 작업을 계속 반복하지 않도록 하루 한 번 자동 시도하고, 수동 재시도는 관리 화면에서 가능합니다.

검토형에서는 영상을 확인한 뒤 `준비 영상 업로드`를 누릅니다. 완전 자동 예약 게시를 원하면 **config.json의 `mode`를 `scheduled`, `require_review`를 `false`**로 바꿉니다. 공개 예약은 실제로 채널에 게시되는 설정입니다. 먼저 비공개 테스트를 권장합니다.

Windows 작업 스케줄러로 매일 실행할 수도 있습니다.

- 프로그램: `프로그램폴더\.venv\Scripts\python.exe`
- 인수: `"프로그램폴더\app.py" run`
- 시작 위치: `프로그램폴더`
- 시간: 매일 오전 7시, PC 시간대 서울
- daemon과 작업 스케줄러 중 한 가지를 사용하세요. 중복 실행은 파일 잠금으로 차단됩니다.

Linux cron 예시: 시스템 시간대가 UTC라면 매일 22:00 UTC가 다음 날 오전 7시 KST입니다.

```cron
0 22 * * * cd /absolute/path/shorts_studio && /absolute/path/shorts_studio/.venv/bin/python app.py run >> /absolute/path/shorts_studio/data/cron.log 2>&1
```

## 예약 업로드·중복 방지

- 영상 ID를 이미 사용했으면 다시 후보로 만들지 않습니다.
- 같은 날 같은 brief로 두 번 작업을 만들지 않습니다.
- 기존 대본과 문자 패턴이 매우 비슷하면 생성물을 거부합니다. 이것은 독창성에 대한 법률·정책 판정이 아닙니다.
- 중단 후 재실행 시 생성된 대본과 장면 음성을 재사용합니다.
- 업로드 결과가 불확실하면 `upload_unknown`으로 멈춥니다. 재실행해도 새 업로드를 시도하지 않습니다.
- `python app.py reconcile`은 본인 업로드 목록의 제작 식별자를 찾아 상태를 복원합니다.
- reconcile 후에도 미확인이면 채널의 최근 업로드와 처리 상태를 직접 확인하세요. 부재를 확인하기 전 상태를 초기화하면 중복 업로드될 수 있습니다. 프로그램에는 불확실 업로드의 강제 자동 초기화를 넣지 않았습니다.
- 명확한 400/401/403/404 오류는 `upload_failed`로 기록합니다. 원인을 수정한 뒤 관리 화면에서 재시도를 준비합니다. 한도 초과는 한도를 우회하지 않습니다.

## 수익 연결과 성과

- 쇼츠 설명·댓글의 일반 URL은 클릭되지 않습니다. 채널 프로필, 쇼핑 상품 태그, 관련 영상 등 지원되는 기능을 사용하세요.
- **상품 태그, 쇼핑 제휴 가입, 관련 영상 연결은 이 프로그램이 자동으로 수행하지 않습니다.** 유튜브 스튜디오에서 직접 설정하세요.
- 제휴·협찬을 한다면 `affiliate_disclosure`와 적절한 유튜브 공개 설정을 사용하세요. 출처 표시는 광고 고지를 대신하지 않습니다.
- `조회수 갱신`은 본인 영상의 조회수·좋아요·댓글 수를 API로 가져옵니다.
- 상품 클릭·구매·총수익·제작비는 대시보드에 수동 입력합니다. 조회수로 수익을 추정해서 실제 수익처럼 표시하지 않습니다.
- 순수익은 입력 수익에서 입력 비용을 뺀 값입니다. 세금 계산은 포함하지 않습니다.
- `성과 CSV 저장` 결과: `data/performance.csv`.
- 시청 유지율·구독 전환·광고수익은 유튜브 스튜디오에서 확인하세요. YouTube Analytics API 연결은 포함하지 않았습니다.
- 주 1회 자세한 비교 영상은 직접 촬영·검증한 자료로 제작합니다. `python app.py weekly`는 최근 쇼츠를 바탕으로 긴 영상 촬영 기획서를 만들며, 긴 영상 자체를 자동 제작하지는 않습니다.

## 비용과 제한

- 기본은 텍스트 모델 `gpt-4o-mini`, 음성 모델 `tts-1`입니다. 계정에서 지원하는 모델로 설정을 변경할 수 있습니다.
- 대본 최대 550자, 장면 4~6개, 실제 음성 포함 영상 20~60초를 검증합니다.
- 유료 AI 요청은 기본 하루 최대 24회입니다. 정상 3개 제작은 대본 3회 + 음성 12~18회 수준입니다. 생성 재시도도 한도에 포함됩니다.
- 이 한도는 **요청 횟수 제한**이며 원화 비용 상한이 아닙니다. API 콘솔의 예산·사용 알림도 설정하세요. 실제 비용은 모델·문자 수·토큰 수에 따라 다릅니다.
- 별도 영상 생성 API, 유료 스톡 영상 다운로드, 음성 복제는 사용하지 않습니다.
- 배경음악은 코드에서 만든 간단한 합성 연주입니다. 유행곡이 아닙니다. 직접 사용 권리를 확보한 음악을 `music_path`와 `music_rights_confirmed`로 설정할 수 있습니다.
- 초과 업로드·API 한도·영상 처리·네트워크·모델 오류는 기록 후 중단될 수 있습니다.
- 게시물 품질, 조회수, 수익, YPP 승인, 쇼핑 자격을 보장하지 않습니다.

## 점검 명령

```bash
python app.py doctor
python app.py demo
python app.py login
python app.py collect
python app.py run
python app.py run --skip-collect
python app.py upload
python app.py metrics
python app.py reconcile
python app.py export
python app.py weekly
python app.py dashboard
python app.py daemon
python -m unittest discover -s tests -v
```

Windows에서는 `python` 대신 `.venv\Scripts\python.exe`를 사용합니다. Linux/macOS에서는 `.venv/bin/python`을 사용합니다.

관리 화면은 로컬 전용이며 사용자 인증을 제공하지 않습니다. 인터넷에 포트를 열거나 공용 서버에서 직접 노출하지 마세요. 외부 서버 운용 시 별도의 인증·HTTPS·백업·비밀 관리가 필요합니다.

## 공식 참고 자료

- YouTube 검색: https://developers.google.com/youtube/v3/docs/search/list
- 영상 업로드: https://developers.google.com/youtube/v3/docs/videos/insert
- 예약 시각·공개 상태: https://developers.google.com/youtube/v3/docs/videos
- 재사용·대량 반복 콘텐츠 수익화 정책: https://support.google.com/youtube/answer/1311392?hl=ko
- 쇼츠 링크: https://support.google.com/youtube/answer/13748639?hl=ko
- 쇼핑 제휴: https://support.google.com/youtube/answer/13376398?hl=ko
- 리믹스: https://support.google.com/youtube/answer/10623810?hl=ko
- 음성 API: https://developers.openai.com/api/reference/resources/audio/subresources/speech/methods/create

## 포함 파일

`app.py` 관리 화면·일일 작업 / `core.py` 상태·후보·대본 / `render.py` 영상 / `youtube.py` 로그인·업로드 / `catalog.json` 검증 자료 / `config.example.json` 설정 / `tests` 회귀 점검 / `output/demo` 화면 샘플.

Python 소스는 MIT License로 제공합니다. 한글 폰트는 Noto Sans KR이며 동봉한 SIL Open Font License를 따릅니다. API 서비스 이용약관과 제3자 자료의 권리는 별도입니다.

GitHub 저장소에서는 용량을 줄이기 위해 폰트와 샘플 MP4를 버전 관리하지 않습니다. 설치 스크립트가 폰트를 내려받고 샘플이 없으면 직접 생성합니다. 폰트는 내려받은 파일의 SHA-256을 확인합니다.
