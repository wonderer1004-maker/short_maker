# 쇼츠 자동 제작·업로드

인기 후보 조사 → 원본 구매 체크리스트 대본 → 한국어 AI 음성·자막·음악 → 하루 3개 쇼츠 → 비공개 업로드 또는 예약 공개.

## 먼저 할 일

현재 저장소가 Public이면 **Settings → General → Danger Zone → Change repository visibility → Private**로 변경하세요. 이 버전은 실행 상태 DB가 외부에 공개되지 않도록 비공개 저장소에서만 자동 작업을 허용합니다. Public 상태에서는 자동 실행이 중단됩니다.

1. [GitHub 실행 안내](GITHUB_START.md)에 따라 API 키와 OAuth 토큰을 GitHub Secrets에 등록합니다.
2. Settings → Actions → General → Workflow permissions에서 Read and write permissions를 허용합니다.
3. Actions → Daily original Shorts → Run workflow로 비공개 테스트를 합니다.
4. 비공개 영상의 내용과 실제 업로드를 확인합니다.
5. 예약 공개를 원하면 Actions Variables에 `PUBLICATION_MODE=scheduled`를 설정합니다. 미등록 기본값은 `private`입니다.

자동 작업은 매일 한국시간 오전 7시 17분에 실행을 요청합니다. GitHub 대기열 때문에 정확한 실행 시각은 보장되지 않습니다. PC는 꺼져 있어도 됩니다. 최초 YouTube OAuth 로그인은 PC에서 해야 합니다.

## 필요한 Secrets

| 이름 | 값 |
|---|---|
| `YOUTUBE_API_KEY` | 조회용 YouTube Data API 키 |
| `OPENAI_API_KEY` | 대본·음성 생성용 API 키 |
| `YOUTUBE_TOKEN_JSON` | PC에서 `app.py login` 후 생성한 token.json 전체 내용 |
| `YOUTUBE_CHANNEL_ID` | PC의 data/channel.json 안의 id 값 |

키와 토큰을 코드, README, 이슈 또는 채팅으로 보내지 마세요.

## 주의할 범위

- 전체 유튜브 TOP 50이 아니라 설정한 검색어·기간의 API 후보 중 조회수순 50개입니다.
- 원본 영상·대사·음악을 복제하지 않습니다. 기본 자료는 구매 체크리스트 3개입니다.
- 실제 제품 비교를 하려면 확인한 사실과 상업적 사용 권리가 있는 촬영 자료를 추가해야 합니다.
- 상품 태그·관련 영상·제휴 프로그램 연결은 유튜브 스튜디오에서 직접 설정합니다.
- 생성물은 Actions Artifact에서 7일 동안 다운로드할 수 있습니다.
- API 비용, GitHub 실행 시간·저장 공간 한도, YouTube 채널 업로드 한도가 적용됩니다.
- 코드 테스트는 완료했지만 본인 키·로그인으로 실제 외부 연결 테스트를 완료해야 합니다.
- 원본 촬영 없이 비슷한 카드 영상을 반복하면 수익화와 시청 성과에 불리할 수 있습니다. 수익은 보장되지 않습니다.

[상세 설치·사용 안내](README_KO.md) · [검증 범위](VERIFICATION.md) · [초기 자료](catalog.json) · [실행 설정](config.example.json)

## PC에서 실행

`START_WINDOWS.bat` 또는 `bash start.sh`를 실행합니다. 관리 화면은 로컬 PC 전용이며 GitHub Pages에서 실행되는 사이트는 아닙니다.
