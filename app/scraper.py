import asyncio
import json
import random
import ssl
from collections import Counter
from datetime import datetime

import aiohttp
from aiohttp.client_exceptions import InvalidURL
from bs4 import BeautifulSoup, SoupStrainer

from app.config import (
    COLLECTION_ENDPOINT,
    COLLECTION_TOKEN,
    FANS_ENDPOINT,
    MAX_RESULTS,
)


class ScraperError(Exception):
    pass


class InvalidBandcampURL(ScraperError):
    pass


class NoFansFound(ScraperError):
    pass


def _create_ssl_context() -> ssl.SSLContext:
    ctx = ssl.create_default_context()
    ctx.set_alpn_protocols(["http/1.1"])
    return ctx


async def _get_tralbum_info(session: aiohttp.ClientSession, input_url: str) -> tuple:
    """Fetch release metadata and purchaser list from a Bandcamp URL."""
    try:
        async with session.get(input_url) as resp:
            soup_meta = BeautifulSoup(await resp.text(), "html.parser", parse_only=SoupStrainer("meta"))
    except InvalidURL:
        raise InvalidBandcampURL(input_url)

    page_props_tag = soup_meta.find(attrs={"name": "bc-page-properties"})
    if page_props_tag is None:
        raise InvalidBandcampURL(input_url)

    try:
        bc_info = json.loads(page_props_tag["content"])
    except (json.JSONDecodeError, KeyError):
        raise InvalidBandcampURL(input_url)

    url_main = input_url.split("://")[-1].split("/")[0]
    fans_url = f"https://{url_main}{FANS_ENDPOINT}"
    query_title = soup_meta.find(property="og:title")["content"]
    query_tralbum_type = bc_info["item_type"]
    query_tralbum_id = bc_info["item_id"]

    payload = json.dumps({
        "tralbum_type": query_tralbum_type,
        "tralbum_id": str(query_tralbum_id),
        "count": 500,
    })
    async with session.post(fans_url, data=payload) as resp:
        parsed = await resp.json()

    fans = [
        {
            "fan_id": item["fan_id"],
            "mod_date": datetime.strptime(item["mod_date"], "%d %b %Y %H:%M:%S %Z"),
        }
        for item in parsed["results"]
    ]

    album_url = None
    if query_tralbum_type == "t":
        async with session.get(input_url) as resp:
            soup_h3 = BeautifulSoup(await resp.text(), "html.parser", parse_only=SoupStrainer("h3"))
            a_tag = soup_h3.find("a")
            if a_tag:
                album_url = f"https://{url_main}{a_tag['href']}"

    return query_title, query_tralbum_type, query_tralbum_id, fans, album_url


async def _get_fan_tralbums(
    session: aiohttp.ClientSession,
    fan_id: int,
    freshness: int,
    purchase_priority: str,
    query_tralbum_id: int,
    tralbums_per_fan: int,
) -> list:
    payload = json.dumps({
        "fan_id": fan_id,
        "older_than_token": COLLECTION_TOKEN,
        "count": freshness,
    })
    async with session.post(COLLECTION_ENDPOINT, data=payload) as resp:
        parsed = await resp.json()

    desired_keys = (
        "item_type", "tralbum_id", "item_url", "item_title",
        "band_name", "num_streamable_tracks", "is_subscriber_only",
    )
    tralbums = [
        {key: item[key] for key in desired_keys}
        for item in parsed["items"]
    ]
    tralbums = [
        t for t in tralbums
        if t["tralbum_id"] != query_tralbum_id
        and t["num_streamable_tracks"] != 0
        and not t["is_subscriber_only"]
    ]

    if purchase_priority == "top":
        return tralbums
    if purchase_priority == "recent":
        return tralbums[:tralbums_per_fan]
    return random.sample(tralbums, min(tralbums_per_fan, len(tralbums)))


async def _get_tralbum_tags(session: aiohttp.ClientSession, item_url: str) -> list:
    try:
        async with session.get(item_url) as resp:
            soup = BeautifulSoup(await resp.text(), "html.parser", parse_only=SoupStrainer("a"))
            return [item.text for item in soup.find_all(class_="tag")]
    except Exception:
        return []


async def discover(
    bc_url: str,
    prioritise_recent: bool,
    purchase_priority: str,
    variability: int,
    freshness: int,
) -> tuple[list, str, str]:
    """Main entry point: discover related releases for a Bandcamp URL."""
    ssl_context = _create_ssl_context()
    connector = aiohttp.TCPConnector(ssl=ssl_context)

    async with aiohttp.ClientSession(connector=connector) as session:
        query_url = bc_url
        query_title, tralbum_type, tralbum_id, fans, album_url = await _get_tralbum_info(session, bc_url)

        if not fans:
            if tralbum_type == "t" and album_url:
                query_title, tralbum_type, tralbum_id, fans, _ = await _get_tralbum_info(session, album_url)
                if fans:
                    query_url = album_url
                else:
                    raise NoFansFound(bc_url)
            else:
                raise NoFansFound(bc_url)

        fan_count = MAX_RESULTS // variability
        if prioritise_recent:
            selected_fans = fans[:fan_count]
        else:
            selected_fans = random.sample(fans, min(fan_count, len(fans)))

        tralbums_per_fan = MAX_RESULTS // len(selected_fans)

        tasks = [
            _get_fan_tralbums(session, fan["fan_id"], freshness, purchase_priority, tralbum_id, tralbums_per_fan)
            for fan in selected_fans
        ]
        fan_tralbums = await asyncio.gather(*tasks)
        all_tralbums = [item for sublist in fan_tralbums for item in sublist]

        if purchase_priority == "top":
            most_common = Counter(t["tralbum_id"] for t in all_tralbums).most_common(MAX_RESULTS)
            top_ids = {item[0] for item in most_common}
            seen = set()
            deduped = []
            for t in all_tralbums:
                if t["tralbum_id"] in top_ids and t["tralbum_id"] not in seen:
                    deduped.append(t)
                    seen.add(t["tralbum_id"])
            all_tralbums = deduped

        tag_tasks = [_get_tralbum_tags(session, t["item_url"]) for t in all_tralbums]
        tags_per_tralbum = await asyncio.gather(*tag_tasks)
        for tralbum, tags in zip(all_tralbums, tags_per_tralbum):
            tralbum["tags"] = tags

        return all_tralbums, query_title, query_url
