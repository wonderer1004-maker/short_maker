"""Download the open-licensed font without storing a large binary in Git."""
import hashlib
from pathlib import Path
import urllib.request

ROOT=Path(__file__).resolve().parents[1]
DEST=ROOT/'assets/fonts/NotoSansKR.ttf'
EXPECTED='194018e6b2b293a7964f037b25c0249ce1418bc9ab3c971060a03aa57861e252'
URL='https://raw.githubusercontent.com/google/fonts/main/ofl/notosanskr/NotoSansKR%5Bwght%5D.ttf'

if not DEST.exists():
    DEST.parent.mkdir(parents=True,exist_ok=True)
    with urllib.request.urlopen(URL,timeout=120) as r:data=r.read()
    if hashlib.sha256(data).hexdigest()!=EXPECTED:
        raise SystemExit('폰트 원본이 변경되었습니다. 확인 후 해시를 갱신하세요.')
    DEST.write_bytes(data)
print('한글 폰트 준비 완료')
