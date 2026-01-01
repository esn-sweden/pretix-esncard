import logging

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

# Reusable session for all ESNcard lookups
session = requests.Session()

retries = Retry(
    total=3,
    backoff_factor=0.3,
    status_forcelist=[500, 502, 503, 504],
)

session.mount("https://", HTTPAdapter(max_retries=retries))


class ExternalAPIError(Exception):
    pass


def fetch_card(card_number: str) -> dict:
    url = f"https://esncard.org/services/1.0/card.json?code={card_number}"

    try:
        response = session.get(url, timeout=3)
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

    return data
