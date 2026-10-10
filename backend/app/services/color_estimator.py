"""Fast, deterministic clothing-colour evidence from a person crop.

This is deliberately not a replacement for a vision model.  It measures the
dominant non-background pixels in the upper/lower garment zones and returns
``unknown`` when the crop is too small, dark or visually mixed.  Keeping this
separate from Qwen/PP-Human makes colour retrieval cheap and repeatable.
"""
from __future__ import annotations

import cv2
import numpy as np


def _colour_name(hue: float, saturation: float, value: float) -> str:
    if value < 55:
        return "black"
    if saturation < 32:
        return "white" if value > 185 else "gray"
    if hue < 8 or hue >= 172:
        return "red"
    if hue < 19:
        return "orange" if value > 100 else "brown"
    if hue < 35:
        return "yellow"
    if hue < 86:
        return "green"
    if hue < 132:
        return "blue"
    if hue < 156:
        return "purple"
    return "pink"


def _dominant_colour(region: np.ndarray) -> tuple[str, float]:
    if region.size == 0 or region.shape[0] < 12 or region.shape[1] < 12:
        return "unknown", 0.0
    hsv = cv2.cvtColor(region, cv2.COLOR_BGR2HSV)
    pixels = hsv.reshape(-1, 3)
    # Near-neutral clothing is still useful (black/white/gray); reject only
    # pixels which are too dark to contain a reliable hue/value measurement.
    pixels = pixels[pixels[:, 2] >= 28]
    if len(pixels) < 80:
        return "unknown", 0.0
    bins: dict[str, int] = {}
    for h, s, v in pixels:
        label = _colour_name(float(h), float(s), float(v))
        bins[label] = bins.get(label, 0) + 1
    label, count = max(bins.items(), key=lambda item: item[1])
    purity = count / len(pixels)
    # Mixed scenes, exposed skin and occlusion must not become a false colour.
    return (label, round(purity, 3)) if purity >= 0.30 else ("unknown", round(purity, 3))


def estimate_clothing_colours(person_bgr: np.ndarray) -> dict[str, object]:
    """Estimate visible upper/lower clothing colour from a BGR person crop."""
    if person_bgr is None or person_bgr.ndim != 3:
        return {"upper_color": "unknown", "lower_color": "unknown", "confidence": 0.0}
    height, width = person_bgr.shape[:2]
    if min(height, width) < 32:
        return {"upper_color": "unknown", "lower_color": "unknown", "confidence": 0.0}
    # Exclude the head, feet and lateral background.  The split is intentionally
    # conservative: it is evidence for visible clothing, not a body parser.
    left, right = int(width * 0.18), max(int(width * 0.82), int(width * 0.18) + 1)
    upper = person_bgr[int(height * 0.24):int(height * 0.58), left:right]
    lower = person_bgr[int(height * 0.58):int(height * 0.91), left:right]
    upper_name, upper_confidence = _dominant_colour(upper)
    lower_name, lower_confidence = _dominant_colour(lower)
    return {
        "upper_color": upper_name,
        "lower_color": lower_name,
        "confidence": round((upper_confidence + lower_confidence) / 2, 3),
        "upper_color_confidence": upper_confidence,
        "lower_color_confidence": lower_confidence,
    }
