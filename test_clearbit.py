import urllib.request
import json
import urllib.parse

company = "Skyroot Aerospace"
url = f"https://autocomplete.clearbit.com/v1/companies/suggest?query={urllib.parse.quote(company)}"
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
try:
    with urllib.request.urlopen(req) as response:
        data = json.loads(response.read())
        print(json.dumps(data, indent=2))
except Exception as e:
    print(e)
