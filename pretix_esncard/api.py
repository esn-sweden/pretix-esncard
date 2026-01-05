import logging
import requests
import time
from django.conf import settings
from pretix.base.settings import GlobalSettingsObject
from pydantic import ValidationError
from requests import JSONDecodeError, RequestException
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from pretix_esncard.models import ESNCard, ESNCardResponse


class ExternalAPIError(Exception):
    pass


CACHE_TTL = 300  # seconds

logger = logging.getLogger(__name__)
_cache: dict[str, tuple[float, ESNCard | None]] = {}
_session = None


def fetch_card(card_number: str) -> ESNCard | None:
    """
    Fetch card data from the ESNcard API server.

    Returns:
        ESNCard | None: Parsed ESNcard data, or None if the card does not exist.

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
        response = get_session().get(url, timeout=(2, 6))
        response.raise_for_status()
        data = response.json()
    except (RequestException, JSONDecodeError) as e:
        logger.error(
            "ESNcard API request failed for card %s (URL: %s) with error: %s",
            card_number,
            url,
            e,
        )
        raise ExternalAPIError("Error contacting ESNcard API")

    try:
        esncards = ESNCardResponse.model_validate(data).root
    except ValidationError as e:
        logger.error("API returned incorrect data model: %s", e.json())
        raise ExternalAPIError("API returned wrongly formatted data")

    esncard = esncards[0] if esncards else None
    _cache[card_number] = (now, esncard)
    return esncard


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


def get_session():
    global _session
    if _session is None:
        _session = create_session()
    return _session
