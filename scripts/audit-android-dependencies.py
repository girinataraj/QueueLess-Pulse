"""Audit resolved Android runtime Maven packages via OSV, with no exclusions."""
import json
from pathlib import Path
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
packages = json.loads((ROOT/'evidence/android/runtime-packages.json').read_text())
assert packages and all(item['name'] and item['version'] for item in packages)
pending = [(index, {'package':{'ecosystem':'Maven','name':item['name']}, 'version':item['version']})
           for index,item in enumerate(packages)]
findings = []
while pending:
    request = urllib.request.Request('https://api.osv.dev/v1/querybatch',
        data=json.dumps({'queries':[query for _,query in pending]}).encode(),
        headers={'Content-Type':'application/json'},method='POST')
    with urllib.request.urlopen(request,timeout=30) as response:
        results = json.load(response)['results']
    assert len(results)==len(pending), 'Incomplete security response'
    next_page = []
    for (index,query),result in zip(pending,results):
        for advisory in result.get('vulns',[]):
            findings.append({**packages[index], 'advisory':advisory['id']})
        if result.get('next_page_token'):
            next_page.append((index,{**query,'page_token':result['next_page_token']}))
    pending = next_page
report = {'source':'https://api.osv.dev/v1/querybatch','resolved_maven_packages':len(packages),
          'known_vulnerabilities':findings,'advisory_exclusions':[]}
(ROOT/'evidence/android/runtime-advisories.json').write_text(json.dumps(report,indent=2)+'\n')
if findings:
    print(json.dumps(findings,indent=2))
    raise SystemExit('Android runtime dependency audit failed')
print('PASS:',len(packages),'resolved Android runtime Maven packages; no known OSV advisories or exclusions')
