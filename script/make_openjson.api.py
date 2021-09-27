# Script to make schema of api
#
# 1. run the app locally
# 2. save as json
#

import requests
import json

# get schema
r = requests.get('http://127.0.0.1:8000/openapi.json')
d = r.json()

# save to file
with open('docs.json', 'w') as f:
    json.dump(d, f, indent=4)



