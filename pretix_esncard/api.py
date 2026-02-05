import logging
import requests
import time
from django.conf import settings
from pretix.base.settings import GlobalSettingsObject
from pydantic import ValidationError
from requests import JSONDecodeError, RequestException, Session
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from pretix_esncard.models import CardStatus, ESNCard, ESNCardResponse

from . import __version__


class ExternalAPIError(Exception):
    pass


CACHE_TTL = 300  # seconds

logger = logging.getLogger(__name__)
_cache: dict[str, tuple[float, ESNCard | None]] = {}
_session: Session | None = None


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
            logger.debug("Using cached data for card %s", card_number)
            return cached

    try:
        response = get_session().get(url, timeout=(2, 6))
        response.raise_for_status()
        data = response.json()
    except (RequestException, JSONDecodeError) as e:
        status = getattr(e.response, "status_code", None)
        body = getattr(e.response, "text", None)
        logger.error(
            "ESNcard API request failed for card %s (URL: %s). Status: %s. Error: %s. Body: %s",
            card_number,
            url,
            status,
            e,
            body,
        )
        raise ExternalAPIError("Error contacting ESNcard API")

    try:
        esncards = ESNCardResponse.model_validate(data).root
    except ValidationError as e:
        logger.error(
            "API returned invalid data for card %s (URL: %s). Validation error: %s. Raw response: %s",
            card_number,
            url,
            e.json(),
            data,
        )
        raise ExternalAPIError("API returned wrongly formatted data")

    esncard = esncards[0] if esncards else None

    # Don't cache unregistered cards, to allow the status to refresh quickly after registration.
    if esncard is None or esncard.status != CardStatus.AVAILABLE:
        _cache[card_number] = (now, esncard)
    return esncard


def get_cloudflare_token() -> str | None:
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
            "User-Agent": f"Pretix-ESNCard-Validator/{__version__} (+{settings.SITE_URL})",
            "Accept": "application/json",
        }
    )

    # Add Cloudflare bypass token if configured, to avoid being blocked
    cf_token = get_cloudflare_token()
    session.cf_token = cf_token
    if cf_token:
        session.headers.update({"x-bypass-cf-api": cf_token})

    return session


def get_session():
    global _session
    current_token = get_cloudflare_token()

    # Create a new session if the Cloudflare token has changed
    if _session is None or getattr(_session, "cf_token", None) != current_token:
        _session = create_session()

    return _session
