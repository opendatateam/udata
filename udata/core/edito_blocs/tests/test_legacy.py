from bson import ObjectId

from udata.core.edito_blocs.legacy import upgrade_legacy_blocs


def without_ids(value):
    """Drop the generated `_id`s, which are random."""
    if isinstance(value, list):
        return [without_ids(item) for item in value]
    if isinstance(value, dict):
        return {k: without_ids(v) for k, v in value.items() if k != "_id"}
    return value


def test_each_legacy_bloc_gets_its_own_section():
    blocs = upgrade_legacy_blocs(
        [
            {"_id": "hero", "_cls": "HeroBloc", "title": "Hero"},
            {"_id": "md", "_cls": "MarkdownBloc", "content": "A"},
            {"_id": "links", "_cls": "LinksListBloc", "links": []},
        ]
    )

    assert blocs[0] == {"_id": "hero", "_cls": "HeroBloc", "title": "Hero"}
    assert [bloc["_cls"] for bloc in blocs[1:]] == ["SectionBloc", "SectionBloc"]
    assert blocs[1]["blocs"] == [{"_id": "md", "_cls": "MarkdownBloc", "content": "A"}]
    assert blocs[2]["blocs"] == [{"_id": "links", "_cls": "LinksListBloc", "links": []}]


def test_title_becomes_a_title_bloc():
    blocs = upgrade_legacy_blocs(
        [
            {"_id": "md", "_cls": "MarkdownBloc", "title": "T", "subtitle": "S", "content": "A"},
            {"_id": "explore", "_cls": "ExploreBloc", "title": "Only title", "resource_id": "r"},
        ]
    )

    assert without_ids(blocs) == [
        {
            "_cls": "SectionBloc",
            "blocs": [
                {"_cls": "TitleBloc", "title": "T", "subtitle": "S"},
                {"_cls": "MarkdownBloc", "content": "A"},
            ],
        },
        {
            "_cls": "SectionBloc",
            "blocs": [
                {"_cls": "TitleBloc", "title": "Only title"},
                {"_cls": "ExploreBloc", "resource_id": "r"},
            ],
        },
    ]
    # The converted bloc keeps its id.
    assert blocs[0]["blocs"][1]["_id"] == "md"


def test_subtitle_without_title_becomes_text():
    blocs = upgrade_legacy_blocs(
        [{"_id": "md", "_cls": "MarkdownBloc", "subtitle": "S", "content": "A"}]
    )

    assert without_ids(blocs[0]["blocs"]) == [
        {"_cls": "MarkdownBloc", "content": "S"},
        {"_cls": "MarkdownBloc", "content": "A"},
    ]


def test_blank_title_is_no_title():
    blocs = upgrade_legacy_blocs(
        [{"_id": "md", "_cls": "MarkdownBloc", "title": "  ", "subtitle": " ", "content": "A"}]
    )

    assert without_ids(blocs[0]["blocs"]) == [{"_cls": "MarkdownBloc", "content": "A"}]


def test_lists_become_grids_of_one_bloc_per_object():
    datasets = [ObjectId(), ObjectId()]
    reuse = ObjectId()
    dataservice = ObjectId()

    blocs = upgrade_legacy_blocs(
        [
            {"_id": "1", "_cls": "DatasetsListBloc", "title": "Datasets", "datasets": datasets},
            {"_id": "2", "_cls": "ReusesListBloc", "reuses": [reuse]},
            {"_id": "3", "_cls": "DataservicesListBloc", "dataservices": [dataservice]},
        ]
    )

    assert without_ids(blocs) == [
        {
            "_cls": "SectionBloc",
            "blocs": [
                {"_cls": "TitleBloc", "title": "Datasets"},
                {
                    "_cls": "GridBloc",
                    "cells": [
                        {"width": "1/2", "blocs": [{"_cls": "DatasetBloc", "dataset": d}]}
                        for d in datasets
                    ],
                },
            ],
        },
        {
            "_cls": "SectionBloc",
            "blocs": [
                {
                    "_cls": "GridBloc",
                    "cells": [{"width": "1/3", "blocs": [{"_cls": "ReuseBloc", "reuse": reuse}]}],
                }
            ],
        },
        {
            "_cls": "SectionBloc",
            "blocs": [
                {
                    "_cls": "GridBloc",
                    "cells": [
                        {
                            "width": "1/2",
                            "blocs": [{"_cls": "DataserviceBloc", "dataservice": dataservice}],
                        }
                    ],
                }
            ],
        },
    ]


def test_empty_list_keeps_only_its_title():
    blocs = upgrade_legacy_blocs(
        [
            {"_id": "1", "_cls": "DatasetsListBloc", "title": "Soon", "datasets": []},
            {"_id": "2", "_cls": "ReusesListBloc"},
        ]
    )

    assert without_ids(blocs) == [
        {"_cls": "SectionBloc", "blocs": [{"_cls": "TitleBloc", "title": "Soon"}]},
        {"_cls": "SectionBloc", "blocs": []},
    ]


def test_accordion_content_is_converted():
    dataset = ObjectId()

    blocs = upgrade_legacy_blocs(
        [
            {
                "_id": "acc",
                "_cls": "AccordionListBloc",
                "title": "FAQ",
                "description": "Questions",
                "items": [
                    {
                        "title": "Item",
                        "content": [
                            {
                                "_id": "list",
                                "_cls": "DatasetsListBloc",
                                "title": "In item",
                                "datasets": [dataset],
                            },
                            {"_id": "md", "_cls": "MarkdownBloc", "content": "A"},
                        ],
                    }
                ],
            }
        ]
    )

    assert without_ids(blocs) == [
        {
            "_cls": "SectionBloc",
            "blocs": [
                {"_cls": "TitleBloc", "title": "FAQ", "subtitle": "Questions"},
                {
                    "_cls": "AccordionListBloc",
                    "items": [
                        {
                            "title": "Item",
                            "content": [
                                {"_cls": "TitleBloc", "title": "In item"},
                                {
                                    "_cls": "GridBloc",
                                    "cells": [
                                        {
                                            "width": "1/2",
                                            "blocs": [{"_cls": "DatasetBloc", "dataset": dataset}],
                                        }
                                    ],
                                },
                                {"_cls": "MarkdownBloc", "content": "A"},
                            ],
                        }
                    ],
                },
            ],
        }
    ]


def test_upgrading_twice_gives_the_same_result():
    blocs = upgrade_legacy_blocs(
        [
            {"_id": "hero", "_cls": "HeroBloc", "title": "Hero"},
            {"_id": "1", "_cls": "DatasetsListBloc", "title": "T", "datasets": [ObjectId()]},
        ]
    )

    assert upgrade_legacy_blocs(blocs) == blocs
