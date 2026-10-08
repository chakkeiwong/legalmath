"""Source fidelity failures that a successful HTTP import must not conceal.

Run with the optional Cassis sidecar: python -m unittest discover -s
tests/prospectus_inception.
"""
import io
import json
from pathlib import Path
import sys
import unittest
import warnings
import zipfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from legalmath.prospectus.successor import annotation_xmi as exchange


class InceptionExchange(unittest.TestCase):
    def setUp(self):
        self.packet = json.loads((ROOT / "docs/implementation/prospectus-adoption/phases/A3/attempt-004/annotation-input.json").read_text())
        self.raw, self.types = exchange.encode(self.packet)

    def restore(self, raw=None):
        return exchange.decode(raw or self.raw, self.packet["source"], self.packet["text"], types=self.types)

    def mutate(self, function):
        cas = exchange.load_export(self.raw, self.types)
        function(cas)
        return cas.to_xmi().encode()

    def test_unicode_discontinuous_duplicate_text_roundtrip(self):
        self.assertEqual(exchange.normalized(self.packet), exchange.normalized(self.restore()))

    def test_actual_server_zip_uses_its_own_type_system(self):
        raw = io.BytesIO()
        with zipfile.ZipFile(raw, "w") as archive:
            archive.writestr("reader.xmi", self.raw)
            archive.writestr("TypeSystem.xml", self.types)
        result = exchange.decode(raw.getvalue(), self.packet["source"], self.packet["text"])
        self.assertEqual(exchange.normalized(result), exchange.normalized(self.packet))

    def test_changed_label_is_recovered_as_an_edit(self):
        def edit(cas):
            next(a for a in cas.select(exchange.SPAN) if a.groupId == "exception").label = "changed"
        packet = self.restore(self.mutate(edit))
        self.assertEqual(next(g for g in packet["groups"] if g["id"] == "exception")["label"], "changed")
        self.assertNotEqual(exchange.normalized(packet), exchange.normalized(self.packet))

    def test_missing_source_identity_is_not_reconstructed(self):
        with self.assertRaisesRegex(ValueError, "source identity"):
            self.restore(self.mutate(lambda cas: cas.remove(next(iter(cas.select(exchange.IDENTITY))))))

    def test_changed_source_hash_rejects_export(self):
        with self.assertRaisesRegex(ValueError, "edition"):
            self.restore(self.mutate(lambda cas: setattr(next(iter(cas.select(exchange.IDENTITY))), "sourceSHA", "f"*64)))

    def test_changed_text_rejects_export(self):
        with self.assertRaisesRegex(ValueError, "text changed"):
            self.restore(self.mutate(lambda cas: setattr(cas, "sofa_string", cas.sofa_string.replace("No loss", "A  loss"))))

    def test_wrong_quote_rejects_export(self):
        with self.assertRaisesRegex(ValueError, "evidence span"):
            self.restore(self.mutate(lambda cas: setattr(next(iter(cas.select(exchange.SPAN))), "quote", "invented")))

    def test_lost_group_piece_cannot_pass_by_shared_label(self):
        with self.assertRaisesRegex(ValueError, "group member"):
            self.restore(self.mutate(lambda cas: cas.remove(next(a for a in cas.select(exchange.SPAN) if a.piece == 1))))

    def test_lost_discontinuity_link_is_detected(self):
        with self.assertRaisesRegex(ValueError, "group links"):
            self.restore(self.mutate(lambda cas: cas.remove(next(a for a in cas.select(exchange.RELATION) if a.kind == exchange.GROUP_LINK))))

    def test_wrong_relation_endpoint_is_detected(self):
        def redirect(cas):
            edge = next(a for a in cas.select(exchange.RELATION) if a.kind != exchange.GROUP_LINK)
            edge.Dependent = next(a for a in cas.select(exchange.SPAN) if a.piece == 1)
        with self.assertRaisesRegex(ValueError, "target|group heads"):
            self.restore(self.mutate(redirect))

    def test_conflicting_group_labels_are_not_silently_collapsed(self):
        with self.assertRaisesRegex(ValueError, "conflicting labels"):
            self.restore(self.mutate(lambda cas: setattr(next(a for a in cas.select(exchange.SPAN) if a.piece == 1), "label", "different")))

    def test_semantic_relation_change_survives_reimport(self):
        def change(cas):
            next(a for a in cas.select(exchange.RELATION) if a.kind != exchange.GROUP_LINK).kind = "condition"
        actual = self.restore(self.mutate(change))
        self.assertEqual(actual["relations"][0]["kind"], "condition")
        self.assertNotEqual(exchange.normalized(actual), exchange.normalized(self.packet))

    def test_display_span_movement_cannot_change_cited_offsets_silently(self):
        with self.assertRaisesRegex(ValueError, "Display span"):
            self.restore(self.mutate(lambda cas: setattr(next(iter(cas.select(exchange.SPAN))), "end", 2)))

    def test_whitespace_is_preserved_in_source_span_separately_from_display(self):
        cas = exchange.load_export(self.raw, self.types)
        first = next(a for a in cas.select(exchange.SPAN) if a.groupId == "definition" and a.piece == 0)
        self.assertEqual(first.end, 1)
        self.assertEqual(first.sourceEnd, 3)
        self.assertEqual(first.quote, "😀 ")
        self.assertEqual(exchange.normalized(self.restore()), exchange.normalized(self.packet))


if __name__ == "__main__":
    unittest.main()
