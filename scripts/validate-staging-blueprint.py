"""Validate the free-only review proposal against Render's authoritative schema."""
import json
from pathlib import Path
import urllib.request
import yaml
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
with urllib.request.urlopen('https://render.com/schema/render.yaml.json',timeout=30) as response:
    schema = json.load(response)
blueprint = yaml.safe_load((ROOT/'render.free-staging.yaml').read_text())
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
assert len(blueprint['services']) == 1 and not blueprint.get('databases')
assert service['name'] == 'queueless-pulse-staging-free'
assert service['plan'] == 'free' and service['autoDeployTrigger'] == 'off'
assert not any(key in service for key in ('disk', 'scaling', 'previews', 'numInstances'))
assert {item['key'] for item in service['envVars']} >= {'APP_STAGE','STAGING_DATABASE_NAME','DATABASE_URL','SECRET_KEY','DEMO_MODE','STAGING_AUTH_MODE','OWNER_REGISTRATION_ENABLED','PUBLIC_BASE_URL','TRUSTED_HOSTS'}
env = {item['key']: item for item in service['envVars']}
assert env['STAGING_AUTH_MODE']['value'] == 'application'
assert env['OWNER_REGISTRATION_ENABLED']['value'] == 'false'
assert not {'DEMO_ACCESS_USER','DEMO_ACCESS_PASSWORD'} & env.keys()
assert env['DATABASE_URL'] == {'key': 'DATABASE_URL', 'sync': False}
assert env['STAGING_DATABASE_NAME']['value'] == 'queueless_pulse_staging'
assert not any('fromDatabase' in item or 'fromService' in item for item in service['envVars'])
(ROOT/'evidence').mkdir(exist_ok=True)
(ROOT/'evidence/free-staging-blueprint.json').write_text(json.dumps({'official_schema':'passed','free_only_resources':'passed','database_provisioned':False,'deployed':False},indent=2))
print('PASS: official Render schema, free-only service and isolated external database input; not deployed')
