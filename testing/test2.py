import requests
try:
    response = requests.get("https://api.themoviedb.org")
    print(f"Connection successful! Status code: {response.status_code}")
except Exception as e:
    print(f"Connection failed: {e}")