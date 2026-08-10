"""
Market price lookup and kirana catalogue for Dukaan Sathi.

Data source:
  LOCAL — prices_local.json with 60+ common kirana items.
"""

import json
import logging
import os
from pathlib import Path

logger = logging.getLogger("agent.prices")

# ---------------------------------------------------------------------------
# Local catalogue (loaded once at import time)
# ---------------------------------------------------------------------------

_LOCAL_DATA_PATH = Path(__file__).parent / "prices_local.json"

def _load_local_data() -> dict:
    """Load the local fallback price data."""
    try:
        with open(_LOCAL_DATA_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        logger.info("Loaded local price data: %d items", len(data.get("items", [])))
        return data
    except Exception as e:
        logger.error("Failed to load local price data: %s", e)
        return {"items": []}

_LOCAL_CATALOGUE = _load_local_data()

# ---------------------------------------------------------------------------
# Fuzzy item matching
# ---------------------------------------------------------------------------

def _normalize(text: str) -> str:
    """Lowercase, strip, collapse spaces."""
    return " ".join(text.lower().strip().split())

def _find_local_item(query: str) -> dict | None:
    """Find an item in the local catalogue by name/alias fuzzy match."""
    q = _normalize(query)
    items = _LOCAL_CATALOGUE.get("items", [])

    # 1. Exact alias match
    for item in items:
        all_names = [item["name_en"].lower(), item.get("name_hi", "").lower()]
        all_names.extend(a.lower() for a in item.get("aliases", []))
        if q in all_names:
            return item

    # 2. Substring match (e.g., "dal" matches "toor dal")
    for item in items:
        all_names = [item["name_en"].lower()]
        all_names.extend(a.lower() for a in item.get("aliases", []))
        for name in all_names:
            if q in name or name in q:
                return item

    return None

def _find_similar_items(query: str, limit: int = 3) -> list[dict]:
    """Find items with partial name overlap for suggestions."""
    q = _normalize(query)
    results = []
    items = _LOCAL_CATALOGUE.get("items", [])

    for item in items:
        all_names = [item["name_en"].lower()]
        all_names.extend(a.lower() for a in item.get("aliases", []))
        # Check if any word from the query appears in any alias
        query_words = q.split()
        for name in all_names:
            if any(w in name for w in query_words) or any(w in q for w in name.split()):
                results.append(item)
                break
        if len(results) >= limit:
            break

    return results

# ---------------------------------------------------------------------------
# Public functions (called by the agent tools)
# ---------------------------------------------------------------------------

async def check_price(item_name: str) -> str:
    """
    Look up the price of a kirana item locally.
    Returns a natural-language string for the TTS to speak.
    """
    local_item = _find_local_item(item_name)

    if local_item:
        name = local_item.get("name_hi") or local_item["name_en"]
        price = local_item["retail_price"]
        unit_raw = local_item["unit"]
        
        unit = "प्रति किलो" if "kg" in unit_raw else ("प्रति लीटर" if "litre" in unit_raw else unit_raw)
        unit = "प्रति 100 ग्राम" if "100g" in unit_raw else unit

        return (
            f"{name} का रेट अभी लगभग {price} रुपये {unit} है। "
            f"नोट करिए कि यह अनुमानित रेट है, फाइनल रेट दुकानदार कन्फर्म करेंगे।"
        )

    else:
        # Item not found at all
        similar = _find_similar_items(item_name)
        if similar:
            names = ", ".join(item.get("name_hi") or item["name_en"] for item in similar)
            return (
                f"माफ़ कीजिये, मुझे '{item_name}' का रेट नहीं मिला। "
                f"लेकिन इन चीज़ों का रेट मेरे पास है: {names}। "
                f"क्या इनमें से कुछ बताऊँ?"
            )
        return (
            f"माफ़ कीजिये, मुझे '{item_name}' का रेट नहीं मिला। "
            f"मैं आम किराना सामान जैसे आटा, चावल, दाल, चीनी, तेल, और मसालों के रेट बता सकती हूँ।"
        )

async def check_availability(item_name: str) -> str:
    """
    Check whether an item is available in the store catalogue locally.
    Returns a natural-language string for the TTS to speak.
    """
    local_item = _find_local_item(item_name)

    if local_item:
        name = local_item.get("name_hi") or local_item["name_en"]
        price = local_item["retail_price"]
        unit_raw = local_item["unit"]
        
        unit = "प्रति किलो" if "kg" in unit_raw else ("प्रति लीटर" if "litre" in unit_raw else unit_raw)
        unit = "प्रति 100 ग्राम" if "100g" in unit_raw else unit

        return (
            f"हाँ जी, {name} हमारी दुकान में मिलता है। "
            f"इसका रेट लगभग {price} रुपये {unit} है।"
        )

    else:
        similar = _find_similar_items(item_name)
        if similar:
            names_str = ", ".join([item.get("name_hi") or item["name_en"] for item in similar])
            return (
                f"माफ़ कीजिये, '{item_name}' लिस्ट में नहीं है। "
                f"लेकिन हमारे पास यह सामान मिलता है: {names_str}। "
                f"क्या आप इनमें से कुछ लेना चाहेंगे?"
            )
        return (
            f"माफ़ कीजिये, '{item_name}' का स्टॉक शायद नहीं है। "
            f"हम आम तौर पर आटा, चावल, दाल, तेल, डेयरी और मसाले रखते हैं।"
        )
