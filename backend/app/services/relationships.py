"""Deterministic, explainable spatial relationship measurements."""
from math import hypot

def measure(person: list[float], obj: list[float]) -> dict | None:
    px1, py1, px2, py2 = person; ox1, oy1, ox2, oy2 = obj
    pw, ph = max(1.0, px2-px1), max(1.0, py2-py1)
    pcx, pcy = (px1+px2)/2, (py1+py2)/2; ocx, ocy = (ox1+ox2)/2, (oy1+oy2)/2
    distance = hypot(pcx-ocx, pcy-ocy) / max(pw, ph)
    ix1, iy1, ix2, iy2 = max(px1,ox1), max(py1,oy1), min(px2,ox2), min(py2,oy2)
    intersection=max(0.0, ix2-ix1)*max(0.0, iy2-iy1)
    union=pw*ph+max(1.0,ox2-ox1)*max(1.0,oy2-oy1)-intersection
    overlap=intersection/union
    # An association must be local to the body; nearby objects elsewhere in a
    # wide CCTV view are intentionally excluded.
    if distance > 1.25 and overlap < .01: return None
    score=min(1.0, .65 * max(0.0, 1-distance/1.25) + .35 * min(1.0, overlap*4))
    return {"relationship":"associated_with", "score":score, "normalized_distance":distance, "overlap":overlap}
