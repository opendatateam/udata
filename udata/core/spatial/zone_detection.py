"""
Bbox-based zone detection.

Matches a dataset's spatial geometry against zone bounding boxes using
Intersection over Union (IoU) scoring. Pure Python, no geospatial dependencies.
"""

from geojson.utils import coords

IOU_THRESHOLD = 0.8


def iou(bbox, zone_bbox):
    """Intersection over Union between two [minx, miny, maxx, maxy] boxes."""
    minx1, miny1, maxx1, maxy1 = bbox
    minx2, miny2, maxx2, maxy2 = zone_bbox

    iw = max(0, min(maxx1, maxx2) - max(minx1, minx2))
    ih = max(0, min(maxy1, maxy2) - max(miny1, miny2))
    intersection = iw * ih

    area1 = (maxx1 - minx1) * (maxy1 - miny1)
    area2 = (maxx2 - minx2) * (maxy2 - miny2)
    union = area1 + area2 - intersection

    return intersection / union if union > 0 else 0.0


def detect_zone(bbox, zones):
    """
    Return the ids of the best-matching zone(s) for `bbox`, or None.

    Ties (exactly equal top score, e.g. a region and a department sharing
    identical geometry) are all returned rather than arbitrarily picking one.
    Ids are sorted, so the result doesn't depend on the order of `zones`.

    bbox: [minx, miny, maxx, maxy]
    zones: {zone_id: [minx, miny, maxx, maxy]}
    """
    scores = {
        zone_id: iou(bbox, zone_bbox)
        for zone_id, zone_bbox in zones.items()
        if zone_bbox and len(zone_bbox) == 4
    }
    if not scores:
        return None
    best_score = max(scores.values())
    if best_score < IOU_THRESHOLD:
        return None
    return sorted(zone_id for zone_id, score in scores.items() if score == best_score)


def geom_to_bbox(geom):
    """Compute the [minx, miny, maxx, maxy] envelope of a GeoJSON geometry dict."""
    points = list(coords(geom))
    if not points:
        return None
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    return [min(xs), min(ys), max(xs), max(ys)]
