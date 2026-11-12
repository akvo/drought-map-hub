"""Sync GeoNode raster metadata to the drought monitoring portal.

Runs after the GeoTiffs are uploaded to GeoNode: reads back the raster
resources GeoNode now holds and pushes their metadata to every configured
hub, which upserts by geonode_id. Each resource is pushed to two hub
endpoints:

  - POST /api/v1/rasters            -> the core Raster asset (authoritative;
                                       present on every hub, geonode module or
                                       not). Its result decides success.
  - POST /api/v1/geonode/publications -> the optional GeoNode metadata cache.
                                       Best-effort: a 404 means the hub runs
                                       with the geonode module off, which is
                                       expected, not a failure.

Several hubs (staging, production) can read the same GeoNode, so both env
vars accept a comma-separated list.
"""
import os
import sys
from datetime import datetime

import requests

geonode_url = os.getenv("GEONODE_URL")
username = os.getenv("GEONODE_USERNAME")
password = os.getenv("GEONODE_PASSWORD")
hub_url = os.getenv("DROUGHTMAP_HUB_URL")
hub_api_key = os.getenv("DROUGHTMAP_HUB_API_KEY")

VERIFY = True
REQUEST_TIMEOUT = (10, 60)
PAGE_SIZE = 20

CATEGORIES = [
    "cdi-raster-map",
    "spi-raster-map",
    "esi-raster-map",
    "evi2-raster-map",
    "sm-raster-map",
]

# Hub payload field -> GeoNode resource field. Optional on both sides; the
# hub rejects empty strings for its URL fields, so blanks are dropped.
OPTIONAL_FIELDS = {
    "detail_url": "detail_url",
    "embed_url": "embed_url",
    "thumbnail_url": "thumbnail_url",
    "download_url": "download_url",
    "file_size": "filesize",
}


def parse_targets():
    """Pair each hub URL with its API key. Returns a list of (url, key).

    Both env vars are comma-separated and positional, so the counts have to
    match exactly: zipping a short list would silently send one server's key
    to another server's host. Refuse the whole run instead.
    """
    urls = [u.strip().rstrip("/") for u in (hub_url or "").split(",")]
    keys = [k.strip() for k in (hub_api_key or "").split(",")]
    urls = [u for u in urls if u]
    keys = [k for k in keys if k]
    if not urls or not keys:
        return []
    if len(urls) != len(keys):
        raise SystemExit(
            f"DROUGHTMAP_HUB_URL lists {len(urls)} host(s) but "
            f"DROUGHTMAP_HUB_API_KEY lists {len(keys)} key(s). Refusing to "
            "sync: a mismatch would send one portal's key to another host."
        )
    return list(zip(urls, keys))


def fetch_resources(category, page):
    """Return one page of GeoNode raster resources for a category."""
    url = (
        f"{geonode_url}/api/v2/resources"
        f"?filter{{category.identifier}}={category}"
        f"&filter{{subtype}}=raster"
        f"&page={page}&page_size={PAGE_SIZE}&sort[]=-date"
    )
    response = requests.get(
        url,
        auth=(username, password),
        verify=VERIFY,
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    return response.json()


def build_payload(resource, category):
    """Map a GeoNode resource onto the hub push payload, or None if unusable."""
    geonode_id = resource.get("pk")
    date_str = resource.get("date") or ""
    try:
        year_month = datetime.strptime(date_str[:10], "%Y-%m-%d").date()
    except ValueError:
        print(f"Skipping resource {geonode_id}: bad date '{date_str}'")
        return None
    if not geonode_id or not resource.get("title"):
        print(f"Skipping resource {geonode_id}: missing id or title")
        return None

    payload = {
        "geonode_id": geonode_id,
        "category": category,
        "title": resource.get("title"),
        "year_month": year_month.replace(day=1).isoformat(),
    }
    for field, source in OPTIONAL_FIELDS.items():
        value = resource.get(source)
        if value:
            payload[field] = value
    return payload


def push_publication(payload, target):
    """Push one resource to one hub. Returns True on success.

    The core Raster endpoint is authoritative; the GeoNode cache endpoint is
    best-effort (a 404 means the geonode module is off on that hub).
    """
    url, api_key = target
    headers = {"X-API-Key": api_key}

    res = requests.post(
        f"{url}/api/v1/rasters",
        json=payload,
        headers=headers,
        verify=VERIFY,
        timeout=REQUEST_TIMEOUT,
    )
    if res.status_code not in (200, 201):
        print(
            f"Raster push to {url} failed for "
            f"geonode_id={payload['geonode_id']}: "
            f"{res.status_code} {res.text}"
        )
        return False

    gn = requests.post(
        f"{url}/api/v1/geonode/publications",
        json=payload,
        headers=headers,
        verify=VERIFY,
        timeout=REQUEST_TIMEOUT,
    )
    if gn.status_code not in (200, 201, 404):
        print(
            f"GeoNode cache push to {url} failed for "
            f"geonode_id={payload['geonode_id']}: "
            f"{gn.status_code} {gn.text}"
        )
    return True


def sync_category(category, targets):
    """Push every raster in a category to every hub. Returns (ok, failed)."""
    synced = failed = 0
    page = 1
    while True:
        try:
            data = fetch_resources(category, page)
        except requests.exceptions.RequestException as e:
            print(f"Failed to fetch {category} page {page}: {e}")
            return synced, failed + 1

        resources = data.get("resources") or []
        if not resources:
            break

        for resource in resources:
            payload = build_payload(resource, category)
            if not payload:
                continue
            # One hub being down must not skip the others: every target is
            # attempted and the failures are counted, not raised.
            for target in targets:
                try:
                    ok = push_publication(payload, target)
                except requests.exceptions.RequestException as e:
                    print(
                        f"Push to {target[0]} failed for "
                        f"{payload['geonode_id']}: {e}"
                    )
                    ok = False
                synced += ok
                failed += not ok

        if page * PAGE_SIZE >= data.get("total", 0):
            break
        page += 1

    print(f"{category}: {synced} pushed, {failed} failed.")
    return synced, failed


def main():
    targets = parse_targets()
    if not targets:
        # ponytail: opt-in step — deployments without a hub just skip it.
        print(
            "DROUGHTMAP_HUB_URL/DROUGHTMAP_HUB_API_KEY not set, "
            "skipping portal sync."
        )
        return

    hosts = ", ".join(url for url, _ in targets)
    print(f"Syncing GeoNode metadata to {len(targets)} portal(s): {hosts}")

    total_failed = 0
    for category in CATEGORIES:
        _, failed = sync_category(category, targets)
        total_failed += failed

    if total_failed:
        print(f"\n=== Portal sync finished with {total_failed} failure(s) ===")
        sys.exit(1)
    print("\n=== Portal sync completed ===")


if __name__ == "__main__":
    main()
