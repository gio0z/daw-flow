"""Unit tests for Document Quality rubric registry loading and strict structural validation.

Verifies `load_rubric` in `scripts.doc_quality` against canonical registry invariants:
- Strict top-level keys: exact `{"schema_version", "common", "kinds"}`
- `schema_version` must be integer 1
- `common`: array of exactly 5 criteria objects with exact keys `{"id", "question"}`
- `common` IDs: unique and exactly matching `COMMON_CRITERIA_IDS` (DQ-01..DQ-05)
- `kinds`: object containing exactly the 13 canonical kind keys
- Each kind: array of exactly 3 criteria objects with exact keys `{"id", "question"}`
- Kind IDs: unique and exactly matching `{kind}-01`, `{kind}-02`, `{kind}-03`
- Non-blank questions across all criteria; no semantic wording pinning
- Rejection of malformed JSON, unreadable files, extra keys, missing keys, duplicate IDs
"""

from __future__ import annotations

import copy
import json
import pathlib
import tempfile
import unittest

from scripts.doc_quality import CANONICAL_KINDS, COMMON_CRITERIA_IDS, load_rubric


class TestDocRubricRegistry(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.project_root = pathlib.Path(__file__).resolve().parents[1]
        cls.canonical_path = cls.project_root / "references" / "document-quality-rubric.json"
        with open(cls.canonical_path, "r", encoding="utf-8") as f:
            cls.canonical_data = json.load(f)

    def write_disposable_rubric(self, data: dict | list | str | bytes) -> pathlib.Path:
        if isinstance(data, bytes):
            tmp = tempfile.NamedTemporaryFile(mode="wb", suffix=".json", delete=False)
            tmp.write(data)
        else:
            tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8")
            if isinstance(data, (dict, list)):
                json.dump(data, tmp)
            else:
                tmp.write(data)
        tmp.close()
        tmp_path = pathlib.Path(tmp.name)
        self.addCleanup(lambda: tmp_path.unlink(missing_ok=True))
        return tmp_path

    def test_canonical_rubric_accepted_with_meaningful_invariants(self) -> None:
        rubric, findings = load_rubric(self.canonical_path)
        self.assertEqual(findings, [])
        self.assertIsNotNone(rubric)
        assert rubric is not None

        # Verify top-level structure
        self.assertEqual(rubric.get("schema_version"), 1)
        self.assertEqual(set(rubric.keys()), {"schema_version", "common", "kinds"})

        # Verify common criteria invariants
        common = rubric.get("common", [])
        self.assertEqual(len(common), 5)
        common_ids = [c["id"] for c in common]
        self.assertEqual(len(common_ids), len(set(common_ids)))
        self.assertEqual(set(common_ids), set(COMMON_CRITERIA_IDS))
        for c in common:
            self.assertEqual(set(c.keys()), {"id", "question"})
            self.assertTrue(isinstance(c["question"], str) and c["question"].strip() != "")

        # Verify kinds invariants
        kinds = rubric.get("kinds", {})
        self.assertEqual(set(kinds.keys()), set(CANONICAL_KINDS))
        self.assertEqual(len(kinds), 13)
        for k in CANONICAL_KINDS:
            k_items = kinds[k]
            self.assertEqual(len(k_items), 3)
            expected_ids = {f"{k}-01", f"{k}-02", f"{k}-03"}
            actual_ids = [item["id"] for item in k_items]
            self.assertEqual(len(actual_ids), len(set(actual_ids)))
            self.assertEqual(set(actual_ids), expected_ids)
            for item in k_items:
                self.assertEqual(set(item.keys()), {"id", "question"})
                self.assertTrue(isinstance(item["question"], str) and item["question"].strip() != "")

    def test_valid_synthetic_minimal_rubric_accepted(self) -> None:
        synthetic = {
            "schema_version": 1,
            "common": [{"id": cid, "question": f"Question for {cid}"} for cid in COMMON_CRITERIA_IDS],
            "kinds": {
                k: [{"id": f"{k}-0{idx}", "question": f"Criteria {idx} for {k}"} for idx in (1, 2, 3)]
                for k in CANONICAL_KINDS
            },
        }
        path = self.write_disposable_rubric(synthetic)
        rubric, findings = load_rubric(path)
        self.assertEqual(findings, [])
        self.assertIsNotNone(rubric)

    def test_missing_and_unreadable_file_rejected(self) -> None:
        non_existent = self.project_root / "references" / "non_existent_rubric.json"
        rubric, findings = load_rubric(non_existent)
        self.assertIsNone(rubric)
        self.assertIn("rubric_missing", [f["code"] for f in findings])

        unreadable = self.write_disposable_rubric(b"\xff\xfe\x00\x00\x80\x81")
        rubric, findings = load_rubric(unreadable)
        self.assertIsNone(rubric)
        self.assertIn("rubric_unreadable", [f["code"] for f in findings])

        malformed = self.write_disposable_rubric("{ invalid json: [ }")
        rubric, findings = load_rubric(malformed)
        self.assertIsNone(rubric)
        self.assertIn("rubric_malformed", [f["code"] for f in findings])

        root_list = self.write_disposable_rubric([{"schema_version": 1}])
        rubric, findings = load_rubric(root_list)
        self.assertIsNone(rubric)
        self.assertIn("rubric_invalid_type", [f["code"] for f in findings])

    def test_strict_top_level_keys_rejected(self) -> None:
        data = copy.deepcopy(self.canonical_data)
        data["extra_metadata"] = "prohibited"
        path = self.write_disposable_rubric(data)
        rubric, findings = load_rubric(path)
        self.assertIsNone(rubric)
        self.assertIn("rubric_extra_key", [f["code"] for f in findings])

        for required_key in ["schema_version", "common", "kinds"]:
            sub_data = copy.deepcopy(self.canonical_data)
            del sub_data[required_key]
            path = self.write_disposable_rubric(sub_data)
            rubric, findings = load_rubric(path)
            self.assertIsNone(rubric)
            self.assertIn("rubric_missing_key", [f["code"] for f in findings])

    def test_schema_version_variants_rejected(self) -> None:
        for invalid_version in [2, 0, -1, "1", True, False, None, 1.0]:
            data = copy.deepcopy(self.canonical_data)
            data["schema_version"] = invalid_version
            path = self.write_disposable_rubric(data)
            rubric, findings = load_rubric(path)
            self.assertIsNone(rubric)
            self.assertIn("rubric_invalid_schema_version", [f["code"] for f in findings])

    def test_common_array_type_and_counts_rejected(self) -> None:
        data = copy.deepcopy(self.canonical_data)
        data["common"] = {"DQ-01": "not a list"}
        path = self.write_disposable_rubric(data)
        rubric, findings = load_rubric(path)
        self.assertIsNone(rubric)
        self.assertIn("rubric_missing_common", [f["code"] for f in findings])

        # 4 items instead of 5
        data = copy.deepcopy(self.canonical_data)
        data["common"] = data["common"][:4]
        path = self.write_disposable_rubric(data)
        rubric, findings = load_rubric(path)
        self.assertIsNone(rubric)
        self.assertIn("rubric_common_count_invalid", [f["code"] for f in findings])

        # 6 items instead of 5
        data = copy.deepcopy(self.canonical_data)
        data["common"].append({"id": "DQ-06", "question": "Extra criterion"})
        path = self.write_disposable_rubric(data)
        rubric, findings = load_rubric(path)
        self.assertIsNone(rubric)
        self.assertIn("rubric_common_count_invalid", [f["code"] for f in findings])

    def test_common_item_schema_and_keys_rejected(self) -> None:
        # Item not a dict
        data = copy.deepcopy(self.canonical_data)
        data["common"][0] = "string criterion"
        path = self.write_disposable_rubric(data)
        rubric, findings = load_rubric(path)
        self.assertIsNone(rubric)
        self.assertIn("rubric_common_item_invalid", [f["code"] for f in findings])

        # Extra key in common criterion
        data = copy.deepcopy(self.canonical_data)
        data["common"][0]["extra_property"] = True
        path = self.write_disposable_rubric(data)
        rubric, findings = load_rubric(path)
        self.assertIsNone(rubric)
        self.assertIn("rubric_common_item_extra_key", [f["code"] for f in findings])

        # Missing id in common criterion
        data = copy.deepcopy(self.canonical_data)
        del data["common"][0]["id"]
        path = self.write_disposable_rubric(data)
        rubric, findings = load_rubric(path)
        self.assertIsNone(rubric)
        self.assertIn("rubric_common_item_missing_key", [f["code"] for f in findings])

        # Missing question in common criterion
        data = copy.deepcopy(self.canonical_data)
        del data["common"][0]["question"]
        path = self.write_disposable_rubric(data)
        rubric, findings = load_rubric(path)
        self.assertIsNone(rubric)
        self.assertIn("rubric_common_item_missing_key", [f["code"] for f in findings])

    def test_common_ids_duplicate_and_invalid_rejected(self) -> None:
        # Non-string id
        data = copy.deepcopy(self.canonical_data)
        data["common"][0]["id"] = 101
        path = self.write_disposable_rubric(data)
        rubric, findings = load_rubric(path)
        self.assertIsNone(rubric)
        self.assertIn("rubric_common_id_invalid", [f["code"] for f in findings])

        # Duplicate ID
        data = copy.deepcopy(self.canonical_data)
        data["common"][1]["id"] = "DQ-01"
        path = self.write_disposable_rubric(data)
        rubric, findings = load_rubric(path)
        self.assertIsNone(rubric)
        self.assertIn("rubric_common_id_duplicate", [f["code"] for f in findings])

        # Unknown / mismatched ID
        data = copy.deepcopy(self.canonical_data)
        data["common"][4]["id"] = "DQ-99"
        path = self.write_disposable_rubric(data)
        rubric, findings = load_rubric(path)
        self.assertIsNone(rubric)
        self.assertIn("rubric_common_mismatch", [f["code"] for f in findings])

    def test_common_question_blank_or_non_string_rejected(self) -> None:
        for invalid_q in ["", "   ", "\t\n", None, 123, False]:
            data = copy.deepcopy(self.canonical_data)
            data["common"][0]["question"] = invalid_q
            path = self.write_disposable_rubric(data)
            rubric, findings = load_rubric(path)
            self.assertIsNone(rubric)
            self.assertIn("rubric_common_question_invalid", [f["code"] for f in findings])

    def test_kinds_structure_and_keys_rejected(self) -> None:
        # Kinds not a dict
        data = copy.deepcopy(self.canonical_data)
        data["kinds"] = ["blueprint", "brd"]
        path = self.write_disposable_rubric(data)
        rubric, findings = load_rubric(path)
        self.assertIsNone(rubric)
        self.assertIn("rubric_missing_kinds", [f["code"] for f in findings])

        # Unknown kind in kinds object
        data = copy.deepcopy(self.canonical_data)
        data["kinds"]["unknown_extra_kind"] = [
            {"id": "unknown_extra_kind-01", "question": "Q1"},
            {"id": "unknown_extra_kind-02", "question": "Q2"},
            {"id": "unknown_extra_kind-03", "question": "Q3"},
        ]
        path = self.write_disposable_rubric(data)
        rubric, findings = load_rubric(path)
        self.assertIsNone(rubric)
        self.assertIn("rubric_unknown_kind", [f["code"] for f in findings])

        # Missing kind in kinds object
        data = copy.deepcopy(self.canonical_data)
        del data["kinds"]["roadmap"]
        path = self.write_disposable_rubric(data)
        rubric, findings = load_rubric(path)
        self.assertIsNone(rubric)
        self.assertIn("rubric_missing_kind", [f["code"] for f in findings])

    def test_kind_criteria_array_and_counts_rejected(self) -> None:
        # Kind items not a list
        data = copy.deepcopy(self.canonical_data)
        data["kinds"]["blueprint"] = "not a list"
        path = self.write_disposable_rubric(data)
        rubric, findings = load_rubric(path)
        self.assertIsNone(rubric)
        self.assertIn("rubric_kind_missing", [f["code"] for f in findings])

        # Kind count == 2 instead of 3
        data = copy.deepcopy(self.canonical_data)
        data["kinds"]["blueprint"] = data["kinds"]["blueprint"][:2]
        path = self.write_disposable_rubric(data)
        rubric, findings = load_rubric(path)
        self.assertIsNone(rubric)
        self.assertIn("rubric_kind_count_invalid", [f["code"] for f in findings])

        # Kind count == 4 instead of 3
        data = copy.deepcopy(self.canonical_data)
        data["kinds"]["blueprint"].append({"id": "blueprint-04", "question": "Fourth"})
        path = self.write_disposable_rubric(data)
        rubric, findings = load_rubric(path)
        self.assertIsNone(rubric)
        self.assertIn("rubric_kind_count_invalid", [f["code"] for f in findings])

    def test_kind_item_schema_and_keys_rejected(self) -> None:
        # Kind item not a dict
        data = copy.deepcopy(self.canonical_data)
        data["kinds"]["blueprint"][0] = "not a dict"
        path = self.write_disposable_rubric(data)
        rubric, findings = load_rubric(path)
        self.assertIsNone(rubric)
        self.assertIn("rubric_kind_item_invalid", [f["code"] for f in findings])

        # Extra key in kind criterion
        data = copy.deepcopy(self.canonical_data)
        data["kinds"]["blueprint"][0]["extra_key"] = 99
        path = self.write_disposable_rubric(data)
        rubric, findings = load_rubric(path)
        self.assertIsNone(rubric)
        self.assertIn("rubric_kind_item_extra_key", [f["code"] for f in findings])

        # Missing id in kind criterion
        data = copy.deepcopy(self.canonical_data)
        del data["kinds"]["blueprint"][0]["id"]
        path = self.write_disposable_rubric(data)
        rubric, findings = load_rubric(path)
        self.assertIsNone(rubric)
        self.assertIn("rubric_kind_item_missing_key", [f["code"] for f in findings])

        # Missing question in kind criterion
        data = copy.deepcopy(self.canonical_data)
        del data["kinds"]["blueprint"][0]["question"]
        path = self.write_disposable_rubric(data)
        rubric, findings = load_rubric(path)
        self.assertIsNone(rubric)
        self.assertIn("rubric_kind_item_missing_key", [f["code"] for f in findings])

    def test_kind_ids_duplicate_and_invalid_rejected(self) -> None:
        # Non-string id in kind
        data = copy.deepcopy(self.canonical_data)
        data["kinds"]["blueprint"][0]["id"] = 1
        path = self.write_disposable_rubric(data)
        rubric, findings = load_rubric(path)
        self.assertIsNone(rubric)
        self.assertIn("rubric_kind_id_invalid", [f["code"] for f in findings])

        # Duplicate ID in kind
        data = copy.deepcopy(self.canonical_data)
        data["kinds"]["blueprint"][1]["id"] = "blueprint-01"
        path = self.write_disposable_rubric(data)
        rubric, findings = load_rubric(path)
        self.assertIsNone(rubric)
        self.assertIn("rubric_kind_id_duplicate", [f["code"] for f in findings])

        # Unknown / mismatched IDs in kind
        data = copy.deepcopy(self.canonical_data)
        data["kinds"]["blueprint"][2]["id"] = "blueprint-99"
        path = self.write_disposable_rubric(data)
        rubric, findings = load_rubric(path)
        self.assertIsNone(rubric)
        self.assertIn("rubric_kind_ids_mismatch", [f["code"] for f in findings])

    def test_kind_question_blank_or_non_string_rejected(self) -> None:
        for invalid_q in ["", "   ", "\t\n", None, 456, True]:
            data = copy.deepcopy(self.canonical_data)
            data["kinds"]["blueprint"][0]["question"] = invalid_q
            path = self.write_disposable_rubric(data)
            rubric, findings = load_rubric(path)
            self.assertIsNone(rubric)
            self.assertIn("rubric_kind_question_invalid", [f["code"] for f in findings])


if __name__ == "__main__":
    unittest.main()
