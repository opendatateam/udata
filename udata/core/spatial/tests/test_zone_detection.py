from udata.core.spatial.zone_detection import detect_zone, geom_to_bbox, iou


class IouTest:
    def test_identical_boxes(self):
        assert iou([0, 0, 10, 10], [0, 0, 10, 10]) == 1.0

    def test_no_overlap(self):
        assert iou([0, 0, 1, 1], [5, 5, 6, 6]) == 0.0

    def test_partial_overlap(self):
        # [0,0,10,10] vs [5,5,15,15]: intersection 5x5=25, union 100+100-25=175
        assert iou([0, 0, 10, 10], [5, 5, 15, 15]) == 25 / 175

    def test_touching_edges_no_overlap(self):
        assert iou([0, 0, 5, 5], [5, 0, 10, 5]) == 0.0

    def test_contained_box(self):
        # [0,0,10,10] fully contains [2,2,8,8]: intersection = area of smaller box
        assert iou([0, 0, 10, 10], [2, 2, 8, 8]) == 36 / 100


class DetectZoneTest:
    def test_no_zones(self):
        assert detect_zone([0, 0, 10, 10], {}) is None

    def test_skips_malformed_bboxes(self):
        # e.g. GeoZone.bbox defaults to [] rather than being absent
        zones = {"empty": [], "malformed": [0, 0, 10], "ok": [0, 0, 10, 10]}
        assert detect_zone([0, 0, 10, 10], zones) == ["ok"]

    def test_all_malformed_returns_none(self):
        assert detect_zone([0, 0, 10, 10], {"empty": []}) is None

    def test_match_above_threshold(self):
        zones = {"a": [0, 0, 10, 10], "b": [100, 100, 110, 110]}
        assert detect_zone([0, 0, 10, 10], zones) == ["a"]

    def test_no_match_below_threshold(self):
        zones = {"a": [0, 0, 10, 10]}
        # 25/175 overlap is well below the 0.8 threshold
        assert detect_zone([5, 5, 15, 15], zones) is None

    def test_picks_best_of_multiple_candidates(self):
        zones = {
            "exact": [0, 0, 10, 10],
            "close": [1, 1, 11, 11],
        }
        assert detect_zone([0, 0, 10, 10], zones) == ["exact"]

    def test_custom_threshold(self):
        zones = {"a": [0, 0, 10, 10]}
        assert detect_zone([5, 5, 15, 15], zones, threshold=0.1) == ["a"]

    def test_exact_tie_returns_all_matching_zones(self):
        # e.g. a region and a department sharing identical geometry (DOM-TOM)
        zones = {
            "fr:region:03": [0, 0, 10, 10],
            "fr:departement:972": [0, 0, 10, 10],
            "unrelated": [100, 100, 110, 110],
        }
        assert sorted(detect_zone([0, 0, 10, 10], zones)) == ["fr:departement:972", "fr:region:03"]


class GeomToBboxTest:
    def test_multipolygon(self):
        geom = {
            "type": "MultiPolygon",
            "coordinates": [
                [[[102.0, 2.0], [103.0, 2.0], [103.0, 3.0], [102.0, 3.0], [102.0, 2.0]]]
            ],
        }
        assert geom_to_bbox(geom) == [102.0, 2.0, 103.0, 3.0]

    def test_multiple_polygons_takes_envelope(self):
        geom = {
            "type": "MultiPolygon",
            "coordinates": [
                [[[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0], [0.0, 0.0]]],
                [[[10.0, 10.0], [11.0, 10.0], [11.0, 11.0], [10.0, 11.0], [10.0, 10.0]]],
            ],
        }
        assert geom_to_bbox(geom) == [0.0, 0.0, 11.0, 11.0]

    def test_empty_coordinates(self):
        assert geom_to_bbox({"type": "MultiPolygon", "coordinates": []}) is None
