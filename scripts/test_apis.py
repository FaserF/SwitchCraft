
import requests

def test_api(name, url, params):
    try:
        print(f"Testing {name}...")
        resp = requests.get(url, params=params, timeout=10)
        print(f"Status: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            if isinstance(data, list):
                print(f"Result count: {len(data)}")
                print(f"First 3: {[x.get('PackageName', x.get('Name', x.get('name', ''))) for x in data[:3]]}")
            elif 'apps' in data:
                print(f"Result count: {len(data['apps'])}")
                print(f"First 3: {[x.get('name', '') for x in data['apps'][:3]]}")
            else:
                print(f"Unknown structure keys: {data.keys()}")
        else:
            print(f"Response: {resp.text[:100]}")
    except Exception as e:
        print(f"Error: {e}")
    print("-" * 20)

# 1. Original
test_api("Winget-Pkg-API", "https://winget-pkg-api.onrender.com/api/v1/search", {"q": "Google"})

# 2. Winstall (Likely failed)
test_api("Winstall", "https://api.winstall.app/apps/search", {"q": "Google"})

# 3. Azure Function (Community)
test_api("Azure Community API", "https://func-winget-api.azurewebsites.net/api/DoSearch", {"query": "Google"})
