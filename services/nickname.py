import random
import os

import requests
from bs4 import BeautifulSoup


def fetch_random_nickname():
    """Fetch a random anime-style nickname from the external site."""
    try:
        url = os.environ.get('NICKNAME_URL', 'https://www.qmsjmfb.com/erciyuan.php')
        resp = requests.get(url, timeout=5)
        resp.encoding = resp.apparent_encoding
        soup = BeautifulSoup(resp.text, 'html.parser')
        names = [li.get_text(strip=True) for li in soup.find_all('li') if li.get_text(strip=True)]
        if names:
            nickname = random.choice(names)
            # Truncate to 24 chars if needed
            return nickname[:24]
    except Exception:
        pass
    # Fallback
    return '匿名用户_' + os.urandom(3).hex()
