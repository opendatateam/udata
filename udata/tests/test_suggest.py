"""Unit tests for the shared suggest scoring (no database needed)."""

import pytest

from udata.core.suggest import (
    EXACT,
    NO_MATCH,
    PREFIX,
    SUBSTRING,
    WORD,
    best_match_score,
    match_score,
    normalize,
    sorted_suggestions,
)


class NormalizeTest:
    @pytest.mark.parametrize(
        "value,expected",
        [
            ("Paris", "paris"),
            ("Orléans", "orleans"),
            ("Nîmes", "nimes"),
            ("Île-de-France", "ile-de-france"),
            ("Le Grand Paris", "le-grand-paris"),
            ("  Paris  ", "paris"),
            ("", ""),
            (None, ""),
        ],
    )
    def test_normalize(self, value, expected):
        assert normalize(value) == expected


class MatchScoreTest:
    def test_exact(self):
        assert match_score("Paris", "Paris") == EXACT

    def test_exact_is_accent_insensitive(self):
        # The whole point: typing without accents must still match.
        assert match_score("Orléans", "orleans") == EXACT
        assert match_score("Nîmes", "nimes") == EXACT

    def test_exact_is_case_insensitive(self):
        assert match_score("PARIS", "paris") == EXACT

    def test_prefix(self):
        assert match_score("Paris 17e Arrondissement", "paris") == PREFIX

    def test_word_not_prefix(self):
        # "paris" is a whole token but not at the start.
        assert match_score("Le Grand Paris", "paris") == WORD

    def test_substring_is_worse_than_word(self):
        # The Val Parisis case: "paris" is buried inside "parisis", not a word.
        assert match_score("Val Parisis", "paris") == SUBSTRING

    def test_no_match(self):
        assert match_score("Bordeaux", "paris") == NO_MATCH

    def test_ordering_paris_family(self):
        """Exact < prefix < word < substring for the real Paris zones."""
        scores = {
            name: match_score(name, "paris")
            for name in [
                "Paris",
                "Paris 2e Arrondissement",
                "Le Grand Paris",
                "Val Parisis",
            ]
        }
        assert scores["Paris"] < scores["Paris 2e Arrondissement"]
        assert scores["Paris 2e Arrondissement"] < scores["Le Grand Paris"]
        assert scores["Le Grand Paris"] < scores["Val Parisis"]

    def test_multi_token_query(self):
        assert match_score("Grand Paris Seine et Oise", "grand paris") == PREFIX
        assert match_score("Le Grand Paris", "grand paris") == WORD


class BestMatchScoreTest:
    def test_best_across_fields(self):
        # e.g. an org whose acronym matches exactly but whose name only contains it.
        assert best_match_score(["Institut National", "INSEE"], "insee") == EXACT

    def test_empty_fields(self):
        assert best_match_score([], "paris") == NO_MATCH


class SortedSuggestionsTest:
    def test_relegates_substring_below_word(self):
        names = ["Val Parisis", "Le Grand Paris", "Paris"]
        ordered = sorted_suggestions(names, "paris", get_texts=lambda n: n)
        assert ordered == ["Paris", "Le Grand Paris", "Val Parisis"]

    def test_secondary_tiebreak(self):
        # Two exact matches; the secondary key (a level priority) decides.
        items = [
            {"name": "Paris", "level": 1},  # departement
            {"name": "Paris", "level": 0},  # commune -> should come first
        ]
        ordered = sorted_suggestions(
            items,
            "paris",
            get_texts=lambda i: i["name"],
            secondary=lambda i: (i["level"], i["name"]),
        )
        assert [i["level"] for i in ordered] == [0, 1]

    def test_size_cap(self):
        names = ["Paris", "Le Grand Paris", "Val Parisis"]
        ordered = sorted_suggestions(names, "paris", get_texts=lambda n: n, size=2)
        assert ordered == ["Paris", "Le Grand Paris"]


class BlendPopularityTest:
    def test_word_is_merged_into_prefix(self):
        assert best_match_score(["Le Grand Paris"], "paris") == WORD
        assert best_match_score(["Le Grand Paris"], "paris", blend_popularity=True) == PREFIX

    def test_exact_and_substring_are_unaffected(self):
        assert best_match_score(["Paris"], "paris", blend_popularity=True) == EXACT
        assert best_match_score(["Val Parisis"], "paris", blend_popularity=True) == SUBSTRING

    def test_blend_lets_input_order_decide_between_prefix_and_word(self):
        # Input is pre-ordered by popularity: a word match first, a prefix second.
        names = ["Open Data Paris", "Paris tourisme"]  # word, then prefix

        # Strict: the prefix always wins, regardless of popularity.
        strict = sorted_suggestions(names, "paris", get_texts=lambda n: n)
        assert strict == ["Paris tourisme", "Open Data Paris"]

        # Blended: prefix and word share a bucket, so the (stable) input order wins.
        blended = sorted_suggestions(names, "paris", get_texts=lambda n: n, blend_popularity=True)
        assert blended == ["Open Data Paris", "Paris tourisme"]
