"""Validate the review-only Blueprint against Render's authoritative schema."""
import json
from pathlib import Path
import urllib.request
import yaml
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
with urllib.request.urlopen('https://render.com/schema/render.yaml.json',timeout=30) as response:
    schema = json.load(response)
blueprint = yaml.safe_load((ROOT/'render.staging.yaml').read_text())
errors = list(Draft202012Validator(schema).iter_errors(blueprint))
def concise(error):
    if error.context:
        return [line for child in error.context for line in concise(child)]
    return [str(list(error.absolute_path))+': '+error.message]
if errors:
    for error in errors:
        for line in concise(error)[:12]: print(line)
    raise SystemExit(1)
service = blueprint['services'][0]
database = blueprint['databases'][0]
assert len(blueprint['services']) == len(blueprint['databases']) == 1
assert service['name'] == 'queueless-pulse-staging' and service['autoDeployTrigger']=='off'
assert database['name']=='queueless-pulse-staging-db' and database['ipAllowList']==[]
assert database['databaseName']=='queueless_pulse_staging'
assert {item['key'] for item in service['envVars']} >= {'APP_STAGE','STAGING_DATABASE_NAME','DATABASE_URL','SECRET_KEY','DEMO_MODE','DEMO_ACCESS_USER','DEMO_ACCESS_PASSWORD','PUBLIC_BASE_URL','TRUSTED_HOSTS'}
(ROOT/'evidence').mkdir(exist_ok=True)
(ROOT/'evidence/staging-blueprint.json').write_text(json.dumps({'official_schema':'passed','isolated_resources':'passed','deployed':False},indent=2))
print('PASS: official Render schema and separate-resource safety checks; not deployed')
