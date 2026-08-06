import os
import requests

headers = {
    "Authorization": f"Bearer {os.environ['GITHUB_TOKEN']}",
    "Accept": "application/vnd.github+json",
}

r = requests.get(
    "https://api.github.com/user",
    headers=headers,
)

print(r.headers.get("X-OAuth-Scopes"))