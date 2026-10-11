"""Scan the tracked index and complete Git history with a pinned Gitleaks binary."""
import hashlib
import io
import os
import platform
import subprocess
import tarfile
import tempfile
import urllib.request
import zipfile
from pathlib import Path

VERSION='8.30.1'
ASSETS={
    'Windows':('windows_x64.zip','d29144deff3a68aa93ced33dddf84b7fdc26070add4aa0f4513094c8332afc4e'),
    'Linux':('linux_x64.tar.gz','551f6fc83ea457d62a0d98237cbad105af8d557003051f41f3e7ca7b3f2470eb'),
}

def git(*args):
    return subprocess.check_output(['git',*args])

def main():
    root=Path(__file__).resolve().parents[1]
    os.chdir(root)
    evidence=root/'evidence';evidence.mkdir(exist_ok=True)
    temporary=root/'.tmp';temporary.mkdir(exist_ok=True)
    suffix,expected=ASSETS[platform.system()]
    name=f'gitleaks_{VERSION}_{suffix}'
    with urllib.request.urlopen(f'https://github.com/gitleaks/gitleaks/releases/download/v{VERSION}/{name}',timeout=60) as response:
        archive=response.read()
    if hashlib.sha256(archive).hexdigest()!=expected:
        raise SystemExit('Secret scanner download failed checksum verification')
    with tempfile.TemporaryDirectory(prefix='secret-scan-',dir=temporary) as folder:
        scratch=Path(folder).resolve()
        binary=scratch/('gitleaks.exe' if platform.system()=='Windows' else 'gitleaks')
        if platform.system()=='Windows':
            with zipfile.ZipFile(io.BytesIO(archive)) as bundle:binary.write_bytes(bundle.read('gitleaks.exe'))
        else:
            with tarfile.open(fileobj=io.BytesIO(archive),mode='r:gz') as bundle:binary.write_bytes(bundle.extractfile('gitleaks').read())
            binary.chmod(0o755)
        index=scratch/'index';index.mkdir()
        paths=git('ls-files','-z').decode().split('\0')
        forbidden=[]
        for path in filter(None,paths):
            parts=Path(path).parts
            if any(p in ('QueueLess_MVP','.venv','.tmp','node_modules','instance','evidence','test-results','playwright-report','.gradle','build') for p in parts) or path=='seed.py' or Path(path).suffix in ('.db','.sqlite','.sqlite3','.pem','.key','.p12','.pfx','.jks','.keystore','.apk','.aab') or (Path(path).name.startswith('.env') and path!='.env.example') or path=='mobile/android/local.properties':
                forbidden.append(path);continue
            target=(index/path).resolve()
            if not target.is_relative_to(index):raise SystemExit('Invalid tracked path')
            target.parent.mkdir(parents=True,exist_ok=True)
            target.write_bytes(git('show',':'+path))
        if forbidden:raise SystemExit('Forbidden tracked release paths: '+', '.join(forbidden))
        for command,source,report,extra in [('dir',index,'secrets-index.json',[]),('git',root,'secrets-history.json',['--log-opts=--all'])]:
            subprocess.run([str(binary),command,str(source),'--redact=100','--no-banner','--report-format','json','--report-path',str(evidence/report),*extra],check=True)
    print('PASS: tracked release paths, Gitleaks index and complete Git history. No scanner rules disabled.')

if __name__=='__main__':main()
