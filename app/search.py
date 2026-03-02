import json

import requests
from bs4 import BeautifulSoup, SoupStrainer

from app.config import BANDCAMP_SEARCH_URL

_session = requests.Session()

_URL_ENCODE = str.maketrans({
    "+": "%2B",
    " ": "+",
    "&": "%26",
    "=": "%3D",
    "@": "%40",
    "'": "%27",
})


def search_bandcamp(query: str) -> list:
    """Search Bandcamp and return a list of album/track results."""
    encoded = query.translate(_URL_ENCODE)
    try:
        response = _session.get(BANDCAMP_SEARCH_URL + encoded, timeout=10)
        response.raise_for_status()
    except requests.RequestException:
        return []

    soup = BeautifulSoup(response.text, "html.parser", parse_only=SoupStrainer("li"))
    results = soup.find_all(class_="searchresult data-search")

    output = []
    for item in results:
        try:
            summary = json.loads(item["data-search"])
        except (KeyError, json.JSONDecodeError, ValueError):
            try:
                import ast
                summary = ast.literal_eval(item["data-search"])
            except Exception:
                continue

        if summary.get("type") not in ("a", "t"):
            continue

        result_info = item.find(class_="result-info")
        if not result_info:
            continue

        heading = result_info.find(class_="heading")
        subhead = result_info.find(class_="subhead")
        if not heading:
            continue

        title = "**{}** *{}*".format(
            heading.get_text(strip=True),
            " ".join(w for w in subhead.get_text(strip=True).replace("\n", "").split(" ") if w)
            if subhead else "",
        )

        a_tag = item.find("a")
        if not a_tag:
            continue

        url = a_tag["href"].split("?")[0]
        output.append({"url": url, "title": title})

    return output
