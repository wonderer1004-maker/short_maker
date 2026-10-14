import os,subprocess,sys
from pathlib import Path
root=Path(__file__).resolve().parents[1]
operation=os.environ.get('OPERATION','run')
if operation not in ('run','upload','reconcile','metrics'):raise SystemExit('허용되지 않은 작업')
raise SystemExit(subprocess.call([sys.executable,str(root/'app.py'),operation],cwd=root))
