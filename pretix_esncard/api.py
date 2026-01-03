import logging
import time
from typing import Optional

import requests
from django.conf import settings
from pretix.base.settings import GlobalSettingsObject
from requests import JSONDecodeError, RequestException, Response
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

CACHE_TTL = 300  # seconds

logger = logging.getLogger(__name__)
_cache: dict[str, tuple[float, Optional[dict]]] = {}


class ExternalAPIError(Exception):
    pass


def fetch_card(card_number: str) -> dict | None:
    """
    Fetch card data from the ESNcard API server.

    Returns:
        dict | None: Parsed ESNcard data, or None if the card does not exist.

    Raises:
        ExternalAPIError: If the API request or response is invalid.
    """
    url = f"https://esncard.org/services/1.0/card.json?code={card_number}"
    now = time.time()

    # Return cached result if the ESNcard number was tried recently
    if card_number in _cache:
        ts, cached = _cache[card_number]
        if now - ts < CACHE_TTL:
            return cached

    try:
        response = session.get(url, timeout=(2, 6))
        response.raise_for_status()

    except RequestException as e:
        logger.error(
            "ESNcard API request failed for card %s (URL: %s)",
            card_number,
            url,
            exc_info=True,
        )
        raise ExternalAPIError("Error contacting ESNcard API") from e

    try:
        data = validate_response(response)
    except ExternalAPIError:
        raise

    _cache[card_number] = (now, data)
    return data


def validate_response(response: Response) -> dict | None:
    """
    Validate ESNcard API response

    Returns:
        dict | None: Parsed card data, or None if card does not exist.

    Raises:
        ExternalAPIError: If the response format is invalid.
    """
    try:
        data = response.json()
    except JSONDecodeError as e:
        logger.exception("ESNcard API returned invalid JSON: %r", response.text)
        raise ExternalAPIError("ESNcard API returned invalid JSON") from e

    if not isinstance(data, list):
        logger.exception("Unexpected ESNcard API response type: %r", data)
        raise ExternalAPIError("Unexpected ESNcard API response format")

    # Empty list → card does not exist
    if len(data) == 0:
        return None

    # Exactly one item → valid
    if len(data) == 1:
        item = data[0]
        if not isinstance(item, dict):
            logger.exception("ESNcard API returned non-dict item: %r", item)
            raise ExternalAPIError("Invalid ESNcard API item format")
        return item

    # More than one item → API bug
    logger.exception("ESNcard API returned multiple items: %r", data)
    raise ExternalAPIError("ESNcard API returned multiple items")


def get_cloudflare_token() -> str:
    gs = GlobalSettingsObject()
    return gs.settings.get("esncard_cf_token")


def create_session() -> requests.Session:
    session = requests.Session()

    retries = Retry(
        total=3,
        backoff_factor=0.3,
        status_forcelist=[500, 502, 503, 504],
    )

    session.mount("https://", HTTPAdapter(max_retries=retries))
    session.headers.update(
        {
            "User-Agent": f"Pretix-ESNCard-Validator/1.0 (+{settings.SITE_URL})",
            "Accept": "application/json",
        }
    )

    # Add Cloudflare bypass token if configured, to avoid being blocked
    cf_token = get_cloudflare_token()
    if cf_token:
        session.headers.update({"x-bypass-cf-api": cf_token})

    return session


# Reusable session for all ESNcard lookups
session = create_session()
