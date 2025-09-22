import requests
import pandas as pd
import logging
from typing import Dict, Any, List, Tuple
from . import config

# Setup logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# --- Private HTTP Helpers (diadaptasi dari es.py) ---
def _es_post(
    index: str, path: str, body: Dict[str, Any], timeout: int = 60
) -> Dict[str, Any]:
    """Sends a POST request to Elasticsearch."""
    try:
        url = f"{config.ES_URL}/{index}{path}"
        logger.debug(f"POST to {url} with body: {body}")
        r = requests.post(url, json=body, timeout=timeout)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Error on POST to {url}: {e}")
        raise


# --- Public Functions ---
def ping() -> Tuple[bool, str]:
    """Checks connection to Elasticsearch."""
    try:
        r = requests.get(config.ES_URL, timeout=5)
        r.raise_for_status()
        info = r.json()
        version = info.get("version", {}).get("number", "unknown")
        logger.info(f"Successfully connected to Elasticsearch v{version}")
        return True, f"Connected to ES v{version}"
    except requests.exceptions.RequestException as e:
        msg = f"Failed to connect to ES at {config.ES_URL}. Error: {e}"
        logger.error(msg)
        return False, msg


def get_all_data(index: str, size: int = 1000) -> pd.DataFrame:
    """
    Fetches all data from an index using the scroll API via requests.
    This is the equivalent of the old `fetch_all_data`.
    """
    all_hits = []
    try:
        # Initial search
        body = {"size": size, "query": {"match_all": {}}}
        path = "/_search?scroll=1m"
        data = _es_post(index, path, body)

        scroll_id = data.get("_scroll_id")
        hits = data.get("hits", {}).get("hits", [])
        all_hits.extend(hits)

        # Scrolling
        while scroll_id and len(hits) > 0:
            scroll_body = {"scroll": "1m", "scroll_id": scroll_id}
            # Note: The scroll API endpoint is different, it doesn't need an index
            scroll_data = requests.post(
                f"{config.ES_URL}/_search/scroll", json=scroll_body, timeout=30
            ).json()

            scroll_id = scroll_data.get("_scroll_id")
            hits = scroll_data.get("hits", {}).get("hits", [])
            all_hits.extend(hits)

        if not all_hits:
            logger.warning(f"No documents found in index '{index}'.")
            return pd.DataFrame()

        source_docs = [doc["_source"] for doc in all_hits]
        logger.info(
            f"Successfully fetched {len(source_docs)} documents from '{index}'."
        )
        return pd.DataFrame(source_docs)

    except Exception as e:
        logger.error(f"Failed to get all data from index '{index}': {e}")
        return pd.DataFrame()
