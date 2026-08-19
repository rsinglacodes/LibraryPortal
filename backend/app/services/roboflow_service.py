"""
Roboflow damage-detection service.
Calls the Roboflow Workflows API with a base64-encoded book image and returns
whether damage was detected plus the list of detected class labels.

This module is intentionally isolated — it does not import anything from the
rest of the application except settings, so it can be tested independently.
"""
from __future__ import annotations

import base64
import logging
from typing import Tuple

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)

_ROBOFLOW_WORKFLOW_URL = (
    "https://detect.roboflow.com/infer/workflows/{workspace}/{workflow_id}"
)

_CONFIDENCE_THRESHOLD = 0.30
_UNDAMAGED_LABELS = {"undamaged", "good", "no_damage", "nodamage", "clean"}


class RoboflowError(Exception):
    """Raised when the Roboflow API call fails for any reason."""


def check_damage(image_bytes: bytes) -> Tuple[bool, list]:
    """
    Send image_bytes to the Roboflow damage-detection workflow.

    Returns:
        (is_damaged, labels)
    Raises:
        RoboflowError on any failure.
    """
    settings = get_settings()

    if not settings.ROBOFLOW_API_KEY:
        raise RoboflowError("ROBOFLOW_API_KEY is not configured on the server.")

    url = _ROBOFLOW_WORKFLOW_URL.format(
        workspace=settings.ROBOFLOW_WORKSPACE,
        workflow_id=settings.ROBOFLOW_WORKFLOW_ID,
    )

    image_b64 = base64.b64encode(image_bytes).decode("utf-8")

    payload = {
        "api_key": settings.ROBOFLOW_API_KEY,
        "inputs": {
            "image": {
                "type": "base64",
                "value": image_b64,
            }
        },
    }

    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(url, json=payload)
    except httpx.RequestError as exc:
        raise RoboflowError(f"Network error contacting Roboflow: {exc}") from exc

    if response.status_code != 200:
        raise RoboflowError(
            f"Roboflow returned HTTP {response.status_code}: {response.text[:400]}"
        )

    try:
        data = response.json()
    except Exception as exc:
        raise RoboflowError(f"Could not parse Roboflow response: {exc}") from exc

    predictions = _extract_predictions(data)
    logger.debug("Roboflow raw predictions: %s", predictions)

    damage_labels = []
    for pred in predictions:
        label = str(pred.get("class", pred.get("class_name", ""))).lower().strip()
        confidence = float(pred.get("confidence", 0.0))
        if confidence >= _CONFIDENCE_THRESHOLD and label not in _UNDAMAGED_LABELS:
            damage_labels.append(label)

    is_damaged = len(damage_labels) > 0

    # Fallback: Check top-level workflow output fields (damage_status / damage_count)
    if not is_damaged and isinstance(data, dict):
        for out in data.get("outputs", []):
            if isinstance(out, dict):
                status_str = str(out.get("damage_status", "")).lower().strip()
                count = out.get("damage_count", 0)
                if (status_str and status_str not in _UNDAMAGED_LABELS and "not" not in status_str and "undamaged" not in status_str) or (isinstance(count, (int, float)) and count > 0):
                    is_damaged = True
                    if not damage_labels:
                        damage_labels.append("damaged")
                    break

    return is_damaged, damage_labels


def _extract_predictions(data) -> list:
    """Recursively extract prediction dicts from Roboflow Workflows response."""
    if isinstance(data, list):
        if data and isinstance(data[0], dict) and "class" in data[0]:
            return data
        result = []
        for item in data:
            result.extend(_extract_predictions(item))
        return result

    if isinstance(data, dict):
        if "predictions" in data and isinstance(data["predictions"], list):
            return data["predictions"]
        if "outputs" in data:
            return _extract_predictions(data["outputs"])
        result = []
        for value in data.values():
            if isinstance(value, (dict, list)):
                result.extend(_extract_predictions(value))
        return result

    return []
