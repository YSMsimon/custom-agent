import requests
from bs4 import BeautifulSoup
from duckduckgo_search import DDGS

def fetch_html(url: str) -> str:
    resp = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
    resp.raise_for_status()
    return resp.text

def fetch_text(url: str) -> str:
    html = fetch_html(url)
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "nav", "footer"]):
        tag.decompose()
    return soup.get_text(separator="\n", strip=True)

def web_search(query: str, max_results: int = 5) -> str:
    with DDGS() as ddgs:
        results = list(ddgs.text(query, max_results=max_results))
    return str(results)   # returns list of {title, href, body}