# GitHub에서 실행하기

이 폴더의 내용물을 비공개 GitHub 저장소의 최상위에 올립니다. `.github/workflows/daily-shorts.yml`을 포함해야 합니다. shorts_studio 폴더 아래에 중첩해 올리지 마세요.

1. GitHub에서 새 **Private** 저장소를 만듭니다.
2. 이 패키지의 파일들을 저장소 최상위에 올립니다. .github 폴더도 포함합니다. git push 또는 GitHub 웹 파일 업로드를 사용합니다.
3. Settings → Secrets and variables → Actions → New repository secret에서 다음을 등록합니다.
   - YOUTUBE_API_KEY: 조회용 YouTube Data API 키
   - OPENAI_API_KEY: AI 대본·음성 API 키
   - YOUTUBE_TOKEN_JSON: PC에서 app.py login 후 만들어진 token.json의 전체 내용
   - YOUTUBE_CHANNEL_ID: PC의 data/channel.json에 있는 id 값
4. OAuth 최초 로그인은 PC에서 해야 합니다. README_KO.md를 따르세요. 토큰 파일을 저장소 코드로 올리지 말고 Secrets에만 등록합니다. 테스트 상태 OAuth 앱은 토큰 만료로 재로그인이 필요할 수 있습니다.
5. Settings → Actions → General → Workflow permissions에서 Read and write permissions를 허용합니다. 상태 DB를 저장하기 위해 필요합니다.
6. Actions → Daily original Shorts → Run workflow를 눌러 비공개 테스트를 실행합니다.
7. 작업 완료 후 Actions의 Artifacts에서 완성 영상을 다운로드하고, 유튜브 스튜디오에서 비공개 업로드를 확인합니다.
8. 예약 공개를 원하면 Actions의 Variables에 PUBLICATION_MODE=scheduled를 등록합니다. 미등록 시 private입니다. 이 설정은 자동 게시를 실행합니다.

매일 오전 7시 17분 한국시간 실행을 요청합니다. GitHub의 작업 대기열 상황에 따라 실행이 늦거나 누락될 수 있습니다. 정확한 시각 보장 서비스는 아닙니다.

기본 하루 3개. 자료와 후보가 부족하면 덜 제작할 수 있습니다. GitHub runner에서 관리 화면 서버를 켜지 않습니다. GitHub Pages로 Python·FFmpeg를 실행할 수는 없습니다.

업로드 전후 상태를 저장소에 기록하여 다음 실행에서도 중복을 막습니다. 원격 저장 실패 시 작업을 중단합니다. 불확실 업로드는 자동 재시도하지 않습니다. 비공개 저장소만 허용합니다. 브랜치 보호가 봇의 직접 쓰기를 막으면 실행할 수 없습니다. 코드 수정과 실행이 동시에 일어나 push 충돌이 생기면 업로드 작업을 중단하고 상태를 확인하세요.

생성 영상은 Actions Artifact에 7일 보관합니다. 상태 DB는 저장소에 남지만 음성·영상 파일은 다음 runner에 복원되지 않습니다. 실패한 제작은 음성을 다시 생성하면서 추가 비용이 들 수 있습니다. GitHub 실행 시간·저장 공간과 AI API 요금은 별도입니다. Google/YouTube 토큰을 다른 사람에게 보내지 마세요.
