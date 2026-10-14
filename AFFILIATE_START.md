# 쿠팡 + 알리 상품 비교 쇼츠 V4

하루에 **쿠팡 3편 + 알리 3편, 총 최대 6편**을 제작합니다. 각 플랫폼 TOP10의 모든 상품을 동종 대안과 비교하며, 1~3위 / 4~6위 / 7~10위로 나눕니다. 1080×1920 화면, 판매처 제공 실제 사진, 표시 가격, 한국어 설명, 자체 합성 배경음악, 제휴 표시가 포함됩니다.

## 순위와 비교 범위

- 쿠팡: 파트너스 **카테고리 베스트 API 반환 순서**. 정확한 판매 수량이나 국내 전체 판매순위라고 주장하지 않습니다. 기본 예시는 가전·디지털 카테고리(1016)입니다.
- 알리: 제휴 **Hot Product API 최근 판매량 내림차순**. 기본 예시는 무선 마우스 검색 범위이며 알리 전체 순위가 아닙니다. 집계 기간은 API가 제공하지 않습니다. 판매량 정렬이 맞는지 응답을 검증합니다.
- 대안: 설정한 동종 상품 키워드, 다른 상품 ID와 다른 상품명, 원화 표시가 0.4~2.5배 범위. 알리는 동일한 2차 카테고리도 요구합니다. 이 기준은 완전히 다른 모델임을 보증하지 않으므로 초기 영상을 직접 확인하고 비교 규칙을 조정하세요.
- 비교 근거: 판매처 상품명·상품 사진·표시 가격. 옵션·배송비·세금·쿠폰 포함 실결제 가격이나 성능 우열을 추정하지 않습니다. 배터리·보온성·사용 후기·직접 시험 결과를 만들어내지 않습니다.
- 실제 고유 상품 10개 또는 동종 대안을 찾지 못하면 해당 플랫폼 제작을 중단합니다. 미지원 상품 종류는 비교 규칙을 추가해야 합니다. 키·계정 권한으로 실응답 구조가 달라지면 어댑터 수정이 필요할 수 있습니다.

## 최초 설정

1. `short_maker` 저장소를 **Private**로 전환합니다. 작업 상태 DB를 저장하므로 Public에서는 제작 워크플로가 차단됩니다.
2. 쿠팡 파트너스 및 알리 Affiliate 계정을 승인받고, **제휴 API 권한**을 활성화합니다. 쿠팡 판매자용 API 키는 사용하지 않습니다. 유튜브 채널과 상품 페이지를 각 제휴 계정의 홍보 채널로 등록·확인하세요. 프로그램은 계정 승인이나 API 권한을 대신 발급하지 않습니다.
3. GitHub Settings → Secrets and variables → Actions → Secrets에 아래 키를 등록합니다. 키·토큰을 채팅·코드·이슈에 붙여넣지 마세요.

| Secret | 내용 |
|---|---|
| YOUTUBE_TOKEN_JSON | PC에서 `python app.py login` 후 생성한 token.json 전체 |
| YOUTUBE_CHANNEL_ID | data/channel.json의 id |
| OPENAI_API_KEY | 한국어 설명 음성 생성 |
| COUPANG_ACCESS_KEY | 쿠팡 파트너스 Access Key |
| COUPANG_SECRET_KEY | 쿠팡 파트너스 Secret Key |
| ALI_APP_KEY | 공식 TOP 게이트웨이 사용 권한이 있는 알리 제휴 앱 키 |
| ALI_APP_SECRET | 해당 앱 Secret |
| ALI_TRACKING_ID | 알리 Affiliate 추적 ID |
| RENDER_DEPLOY_HOOK | Render 상품 사이트 Settings의 Deploy Hook URL |

4. Render에서 이 저장소의 정적 사이트를 연결합니다. `render.yaml`로 배포하면 **site/**만 공개하며 코드·DB·토큰은 공개 디렉터리에 포함하지 않습니다. GitHub가 Private이면 Render GitHub 앱에 저장소 접근 권한을 유지하세요. Render 자동 배포는 끕니다. 상품 페이지를 갱신한 뒤 Deploy Hook으로만 배포하므로 작업 상태 저장마다 재배포되지 않습니다. Render 사이트 Settings → Deploy Hook 주소를 GitHub RENDER_DEPLOY_HOOK Secret에 등록하세요. 정적 사이트는 Render 무료 옵션을 사용하지만 계정별 사용량 제한이 적용됩니다.
5. Actions → Variables를 아래와 같이 설정합니다.

| Variable | 값 |
|---|---|
| CONTENT_MODE | affiliate (GitHub 기본값) |
| AFFILIATE_PORTAL_URL | Render의 실제 https://…onrender.com 주소 |
| PUBLICATION_MODE | 최초 테스트는 private, 검토 후 scheduled |
| AFFILIATE_CONFIG_JSON | 선택 사항. affiliate.config.example.json의 affiliate_platforms를 포함하는 JSON. 카테고리·검색어·동종 비교 규칙을 변경할 때 사용 |

6. YouTube Studio → 채널 맞춤설정 → 프로필 링크에 Render 상품 페이지 URL을 등록합니다. **쇼츠 설명과 댓글의 URL은 클릭되지 않습니다.** 영상은 채널 프로필로 안내합니다. 링크 페이지에는 제휴 고지와 인기 상품/동종 대안의 실제 제휴 링크가 표시됩니다.
7. GitHub Settings → Actions → General → Workflow permissions → **Read and write permissions**. Actions → Daily original Shorts → Run workflow의 operation을 **run**으로 선택합니다. 첫 작업은 상품 페이지 배포를 기다리며 업로드가 중단될 수 있습니다. 페이지가 공개되면 **upload**로 다시 실행하면 음성을 다시 제작하지 않고 업로드합니다.

## 자동 운영 시간 (한국시간)

- 07:17: 상품 수집·6편 제작 요청·상품 페이지 갱신·업로드.
- 08:17: 링크 페이지가 배포되었는지 다시 확인한 뒤 준비된 영상 업로드. 새 영상·음성을 만들지 않습니다.
- 예약 공개 슬롯: 11:00, 12:00, 15:00, 18:00, 20:00, 21:00. 늦은 슬롯은 다음 날로 이동합니다.
- 각 영상의 제휴 링크와 자료 지문이 공개 페이지에 모두 있는지 확인하며, 24시간이 지난 상품 자료는 게시하지 않습니다. 불확실한 업로드는 자동 재삽입하지 않고 reconcile로 확인합니다.
- 정상 제작이 끝난 영상은 같은 날 재실행해도 다시 제작하지 않습니다. 실패한 작업만 재개합니다. 매일 같은 순위가 반복되면 영상도 비슷해질 수 있습니다. 실제 변화가 적을 때에는 자동 실행을 줄여 콘텐츠 품질을 검토하세요.
- API/음성/GitHub 실행 비용과 채널 업로드 한도가 적용됩니다. 제휴 링크 클릭·주문·확정 수익은 각 제휴 대시보드에서 확인합니다. 자동 제작이 수익이나 YouTube 수익화 승인을 보장하지 않습니다.

## PC에서 설정/검토

```bash
python -m pip install -r requirements.txt
python scripts/install_font.py
python app.py affiliate-setup
# config.json의 카테고리·규칙·affiliate_portal_url 설정
# ENV_EXAMPLE.txt를 .env로 복사해 본인의 키 설정
python app.py doctor
python app.py run
python app.py dashboard
```

PC 기본 require_review=true는 영상을 검토 목록에만 저장합니다. 실제 자동 공개는 GitHub에서 설정합니다. `output/<작업ID>/short.mp4`, `provenance.json`, `output/affiliate-links/index.html`을 확인할 수 있습니다.

## 검증 상태

코드 테스트는 API 서명·응답 검증·TOP10 분할·대안 필터·링크 고지를 확인합니다. **현재 실제 제휴 API 호출과 YouTube 업로드는 계정 키가 없어 검증하지 못했습니다.** 공식 API 어댑터와 파이프라인을 구현했으며, 계정 연결 후 비공개 테스트가 필요합니다.

## 공식 자료

- https://partners.coupang.com/openapi/apidoc
- https://open.alitrip.com/docs/api.htm?apiId=45794
- https://open.alitrip.com/docs/doc.htm?articleId=101617&docType=1&treeId=796
- https://support.google.com/youtube/answer/13748639
- https://render.com/docs/static-sites
- https://render.com/docs/deploy-hooks

무신사 V3 모드는 GitHub CONTENT_MODE=popularity로 유지할 수 있습니다. 로컬 config.json의 content_mode=popularity를 사용할 수도 있습니다.
