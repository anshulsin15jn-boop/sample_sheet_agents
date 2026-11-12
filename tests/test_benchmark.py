"""Tests for GEO header parsing, the cohort view, mapping application, grading, and the rule baseline."""
import gzip
import io

from src.cohort import all_cohorts, apply_mapping, row_view, sample_key
from src.geo import parse_expert_trait_row, parse_header
from src.grading import grade
from src.rules import label_value, rule_answer

HEADER = """!Series_title\t"A study of asthma"
!Sample_title\t"asthma 1"\t"asthma 2"\t"healthy 1"
!Sample_geo_accession\t"GSM1"\t"GSM2"\t"GSM3"
!Sample_source_name_ch1\t"blood"\t"blood"\t"blood"
!Sample_characteristics_ch1\t"disease state: asthma"\t"disease state: asthma"\t"disease state: control"
!Sample_characteristics_ch1\t"age: 30"\t"age: 41"\t"age: 52"
"""


def toy_cohort(labels=None):
    p = parse_header(HEADER)
    return {"cohort_id": "GSE0", "trait": "Asthma", **p,
            "labels": labels or {"GSM1": 1, "GSM2": 1, "GSM3": 0},
            "valid_rows": ["title", "char_0"]}


def test_parse_header_rows_and_order():
    p = parse_header(HEADER)
    assert p["series_title"] == "A study of asthma"
    assert p["samples"] == ["GSM1", "GSM2", "GSM3"]
    assert [r["row_id"] for r in p["rows"]] == ["title", "source", "char_0", "char_1"]
    assert p["rows"][2]["values"][2] == "disease state: control"


def test_parse_header_pads_short_rows():
    p = parse_header(HEADER + '!Sample_characteristics_ch1\t"x: 1"\n')
    assert p["rows"][-1]["values"] == ["x: 1", "", ""]


def test_expert_trait_row_parsing():
    assert parse_expert_trait_row("trait_row = 2  # note\nage_row = 1") == 2
    assert parse_expert_trait_row("trait_row = 0\ntrait_row = None\n") is None
    assert parse_expert_trait_row("x = 1") == "unparsed"


def test_apply_mapping_and_unknowns():
    c = toy_cohort()
    preds = apply_mapping(c, "char_0", {"disease state: asthma": "disease",
                                        "disease state: control": "control"})
    assert preds == {"GSM1": 1, "GSM2": 1, "GSM3": 0}
    preds = apply_mapping(c, "char_0", {"disease state: asthma": "Disease "})   # case and space tolerant
    assert preds == {"GSM1": 1, "GSM2": 1, "GSM3": None}
    preds = apply_mapping(c, "char_0", {"disease state: control": "unsure"})
    assert preds["GSM3"] is None
    assert set(apply_mapping(c, "no_such_row", {}).values()) == {None}


def test_grade_perfect_partial_and_abstain():
    c = toy_cohort()
    full = {"disease state: asthma": "disease", "disease state: control": "control"}
    g = grade(c, "char_0", full)
    assert g["accuracy"] == 1 and g["macro_f1"] == 1 and g["solved"] and g["row_correct"]
    g = grade(c, "char_0", {"disease state: asthma": "disease"})
    assert abs(g["accuracy"] - 2 / 3) < 1e-9 and abs(g["coverage"] - 2 / 3) < 1e-9
    assert g["selective_accuracy"] == 1.0 and not g["solved"]
    g = grade(c, "char_0", full, cannot_determine=True)
    assert g["coverage"] == 0 and g["selective_accuracy"] is None and not g["row_correct"]


def test_grade_wrong_direction_gives_zero():
    c = toy_cohort()
    g = grade(c, "char_0", {"disease state: asthma": "control", "disease state: control": "disease"})
    assert g["accuracy"] == 0 and g["macro_f1"] == 0


def test_long_rows_collapse_digits_but_numeric_rows_stay():
    row = {"row_id": "title", "name": "sample title",
           "values": [f"patient {i}" for i in range(40)] + [f"control {i}" for i in range(40)]}
    v = row_view(row)
    assert v["collapsed"] and v["values"] == ["patient #", "control #"]
    assert sample_key(row, "patient 17") == "patient #"
    num = {"row_id": "char_0", "name": "x", "values": [f"cag length: {i}" for i in range(15, 70)]}
    v = row_view(num)
    assert not v["collapsed"] and len(v["values"]) == 55 and v["values"][0] == "cag length: 15"


def test_rule_labels():
    assert label_value("disease state: control", "Asthma") == "control"
    assert label_value("tissue: adjacent non-tumor", "Liver Cancer") == "control"
    assert label_value("diagnosis: adult-onset asthma", "Asthma") == "disease"
    assert label_value("asthma status: Yes", "Asthma") == "disease"
    assert label_value("asthma status: No", "Asthma") == "control"
    assert label_value("hd genotype: HD", "Huntingtons Disease") == "unknown"
    assert label_value("disease: Huntington's disease", "Huntingtons Disease") == "disease"


def test_rule_answer_on_toy():
    a = rule_answer(toy_cohort())
    assert a["row"] == "char_0" and not a["cannot_determine"]
    assert grade(toy_cohort(), a["row"], a["mapping"])["accuracy"] == 1


def test_built_benchmark_is_consistent():
    cs = all_cohorts()
    assert len(cs) == 50 and sum(c["split"] == "dev" for c in cs) == 10
    for c in cs:
        assert set(c["labels"]) <= set(c["samples"])
        assert set(c["labels"].values()) == {0, 1}
        assert all(len(r["values"]) == len(c["samples"]) for r in c["rows"])
        assert c["valid_rows"], c["cohort_id"]
