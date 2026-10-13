"""Persist only upload state, never credentials or generated media."""
import subprocess, pathlib
root=pathlib.Path(__file__).resolve().parents[1]
def git(*args):
 p=subprocess.run(['git',*args],cwd=root,capture_output=True,text=True)
 if p.returncode:raise RuntimeError('상태 저장 실패. GitHub 쓰기 권한과 브랜치를 확인하세요.')
 return p.stdout
p=root/'data/studio.sqlite3'
if p.exists():
 git('add','-f','data/studio.sqlite3')
 if git('diff','--cached','--name-only'):
  git('commit','-m','Persist Shorts processing state [skip ci]')
  git('push','origin','HEAD')
