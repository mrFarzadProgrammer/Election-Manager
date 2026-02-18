import httpx

try:
    r = httpx.get("https://api.telegram.org")
    print("SUCCESS:")
    print(r.text)
except Exception as e:
    print("FAILED:")
    print(e)
