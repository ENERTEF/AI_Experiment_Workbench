import os
import json

c = get_config()

proxy_json = os.environ.get('PROXY_CONFIG_JSON')
if proxy_json:
    c.ServerProxy.servers = json.loads(proxy_json)