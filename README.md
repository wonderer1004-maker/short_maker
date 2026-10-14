# 실제 인기순위 쇼츠 자동 제작 · 예약 업로드 V3

승인한 크림색 제품 중심 디자인으로 **실제 상품 사진 · 인기순위 · 가격 · 한국어 AI 설명 · 배경음악**을 넣어 YouTube에 예약 공개합니다.

## 순위 기준

무신사 공개 랭킹 페이지의 **전체 상품 랭킹**에서 카테고리를 선택하고, 실제 순위 1~5를 그대로 사용합니다. 신상·급상승·검색 추천순·가격순을 인기순위로 바꾸지 않습니다.

출처 설명은 **매출·조회수·후기수를 반영한 상품 랭킹**입니다. 브랜드·제품명을 함께 표시하지만 **브랜드 자체 순위나 대한민국 전체 판매량 순위는 아닙니다.** 같은 브랜드의 제품이 함께 포함될 수 있습니다. 이전 가격순 샘플의 5개 브랜드를 고정하지 않습니다.

순위 출처와 갱신 시각을 영상에 표시합니다. 1~5위·카테고리·산정 설명·최신성을 확인하지 못하면 게시를 중단합니다. 플랫폼 데이터 구조가 바뀌면 수집 코드를 수정해야 할 수 있습니다.

## 매일 운영

- 한국시간 오전 7시 17분 GitHub Actions 실행 요청.
- 기본 카테고리: 경량 패딩/패딩 베스트, 플리스/뽀글이, 니트/스웨터.
- 하루 최대 3편. TOP 5 소개 → 5위부터 1위 → 요약표.
- 1080×1920, 30fps, 크림색 화면, 상품 사진, 가격과 확인 시각.
- 한국어 음성과 자체 합성 음악. 설명할 때 음악이 작아집니다.
- 기본 예약 공개 시각: 12시·18시·21시 KST. 늦으면 다음 날로 이동.
- 순위·제품·가격이 같으면 중복 영상을 만들지 않습니다. 변화가 없거나 수집이 실패하면 3편보다 적게 게시될 수 있습니다.
- 결과가 불확실한 업로드는 자동 재시도하지 않습니다.

## GitHub 활성화

1. 저장소를 **Private**로 바꿉니다. 상태 DB 보호를 위해 Public에서는 작업을 차단합니다.
2. Settings → Secrets and variables → Actions에 아래 Secrets를 등록합니다.
3. Settings → Actions → General → Workflow permissions를 Read and write permissions로 설정합니다.
4. 첫 테스트는 Variables에 `PUBLICATION_MODE=private`를 넣고 Actions → Daily original Shorts → Run workflow를 실행합니다.
5. 확인 후 `PUBLICATION_MODE=scheduled`로 설정하면 예약 공개까지 자동으로 실행합니다.

**V3의 PUBLICATION_MODE 미등록 기본값은 scheduled입니다. 실제 공개 설정입니다. 비공개 테스트에는 private를 명시하세요.** 키·OAuth 로그인 정보가 없으면 실제 업로드를 실행할 수 없습니다.

| Secret | 값 |
|---|---|
| `YOUTUBE_TOKEN_JSON` | PC에서 app.py login 후 생성한 token.json 전체 내용 |
| `YOUTUBE_CHANNEL_ID` | PC의 data/channel.json 안의 id |
| `OPENAI_API_KEY` | 기본 한국어 설명 음성 API 키 |
| `YOUTUBE_API_KEY` | 기존 유튜브 주제 조사용. 상품 랭킹 수집에는 불필요 |

최초 YouTube OAuth 로그인은 PC에서 해야 합니다. 키와 토큰을 코드·이슈·채팅에 올리지 마세요. [설정 상세](GITHUB_START.md).

Actions Variables의 `SPEECH_PROVIDER` 기본값은 `openai`입니다. `edge`도 선택할 수 있지만 비공식 클라이언트 서비스 변경으로 실패할 수 있습니다. 상시 운용 기본값은 OpenAI입니다. 인기 영상 설명은 확인한 상품명·순위·가격으로 구성하여 AI가 성능·사용 경험을 만들어내지 않습니다.

## 결과 확인

Actions Artifact에서 영상과 출처 자료를 7일간 다운로드할 수 있습니다. 파일은 `output/<작업ID>/short.mp4`와 같은 폴더의 `provenance.json`입니다.

업로드 결과가 불확실하면 Run workflow의 operation에서 `reconcile`을 선택해 채널의 실제 업로드를 확인합니다. `metrics`로 조회수도 갱신할 수 있습니다.

API 비용, GitHub 실행 시간·저장 공간, 채널 업로드 한도가 적용됩니다. 요청 횟수 제한은 원화 비용 상한이 아닙니다. GitHub 예약 실행은 지연·누락될 수 있습니다.

상품 자료 사진은 상품 식별·비교 화면이며 직접 착용·보온성 실험·브랜드 협찬을 주장하지 않습니다. 공개·수익화 운용에 사용할 이미지의 권리와 플랫폼 정책을 확인하세요. 상품 태그·관련 영상·제휴 고지는 유튜브 스튜디오에서 직접 설정합니다. 수익·조회수·수익화 승인은 보장하지 않습니다.

## PC / 미리보기

```bash
python scripts/install_font.py
python app.py ranking-preview
python app.py run
python app.py dashboard
python -m unittest discover -s tests -v
```

`ranking-preview`는 첫 카테고리의 실제 인기순위 영상을 만들고 채널에는 올리지 않습니다. 음성 제공자가 OpenAI이면 API 키가 필요합니다.

기존 체크리스트는 `content_mode=checklist`로 선택합니다. [구버전 안내](README_KO.md)는 V1/V2 설명이며 공개 기본값·인기 영상 운영은 이 V3 안내가 우선합니다.
