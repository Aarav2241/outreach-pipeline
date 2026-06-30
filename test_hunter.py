import urllib.request
import json
import urllib.parse

API_KEY = "8af6a5eb95001abba7a41644b5dbf56085c63068"
domain = "infosys.com"

url = f"https://api.hunter.io/v2/domain-search?domain={domain}&api_key={API_KEY}"
try:
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    response = urllib.request.urlopen(req)
    data = json.loads(response.read())
    print("SUCCESS")
    print(json.dumps(data['data']['emails'][:2], indent=2))
except Exception as e:
    print("FAILED:", e)
