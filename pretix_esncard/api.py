import logging
import time

import requests
from django.conf import settings
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

CACHE_TTL = 300  # seconds

logger = logging.getLogger(__name__)
_cache: dict[str, tuple[float, dict]] = {}


class ExternalAPIError(Exception):
    pass


def fetch_card(card_number: str) -> dict:
    """Fetches card data from the ESNcard API server

    Implements a cache and raises ExternalAPIError if the operation fails
    """
    url = f"https://esncard.org/services/1.0/card.json?code={card_number}"
    now = time.time()

    # Return cached result if the ESNcard number was tried recently
    if card_number in _cache:
        ts, data = _cache[card_number]
        if now - ts < CACHE_TTL:
            return data

    try:
        response = session.get(url, timeout=(2, 6))
        response.raise_for_status()
        data = response.json()

    except Exception as e:
        logger.exception("ESNcard API request failed for card %s", card_number)
        raise ExternalAPIError(f"Unexpected error contacting ESNcard API: {e}")

    # Normalize: Make sure the API returns exactly one dict (ESNcard item)
    if isinstance(data, list):
        if len(data) == 1:
            data = data[0]
        else:
            raise ExternalAPIError(f"Unexpected list length from API: {len(data)}")

    if not isinstance(data, dict):
        raise ExternalAPIError(f"Unexpected API response type: {type(data)}")

    _cache[card_number] = (now, data)
    return data


def create_session() -> requests.Session:
    session = requests.Session()

    retries = Retry(
        total=3,
        backoff_factor=0.3,
        status_forcelist=[500, 502, 503, 504],
    )

    session.mount("https://", HTTPAdapter(max_retries=retries))
    session.headers.update(
        {"User-Agent": f"Pretix-ESNCard-Validator/1.0 (+{settings.SITE_URL})"}
    )
    session.headers.update(
        {
            "Accept": "application/json",
        }
    )

    return session


# Reusable session for all ESNcard lookups
session = create_session()
