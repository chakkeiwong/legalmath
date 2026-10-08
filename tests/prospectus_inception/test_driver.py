"""Adversarial checks for the isolated trial transport and evidence admission."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from urllib.request import Request

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from scripts.prospectus_inception import LocalRedirects, check_configuration, save
from scripts.prospectus_inception_verify import validate


class TrialGuards(unittest.TestCase):
    def test_redirect_cannot_send_credentials_to_another_origin(self):
        request = Request("http://127.0.0.1:8123/api", headers={"Authorization": "Basic TEST"})
        handler = LocalRedirects()
        for destination in ("https://example.com/api", "http://127.0.0.1:8124/api", "https://127.0.0.1:8123/api"):
            with self.subTest(destination=destination), self.assertRaisesRegex(ValueError, "outside"):
                handler.redirect_request(request, None, 302, "redirect", {}, destination)
        accepted = handler.redirect_request(request, None, 302, "redirect", {}, "http://127.0.0.1:8123/other")
        self.assertEqual(accepted.full_url, "http://127.0.0.1:8123/other")

    def test_declared_pass_without_sealed_evidence_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            save(folder / "manifest.json", {"status": "SERVER_EXCHANGE_PASS"})
            save(folder / "result.json", {"status": "SERVER_EXCHANGE_PASS", "ui": {
                "status": "TWO_BROWSER_EDITS_PERSISTED", "curation": "TWO_EMPTY_CURATION_EXPORTS_AFTER_OPENING"}})
            with self.assertRaisesRegex(ValueError, "Unsealed"):
                validate(folder, current=False)

    def test_changed_evidence_is_rejected_before_interpretation(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            save(folder / "manifest.json", {"status": "SERVER_EXCHANGE_PASS", "outputs": {"packet.zip": "0"*64}})
            save(folder / "result.json", {"status": "SERVER_EXCHANGE_PASS", "ui": {
                "status": "TWO_BROWSER_EDITS_PERSISTED", "curation": "TWO_EMPTY_CURATION_EXPORTS_AFTER_OPENING"}})
            (folder / "packet.zip").write_bytes(b"replaced export")
            with self.assertRaisesRegex(ValueError, "Evidence changed"):
                validate(folder, current=False)

    def test_metadata_declarations_do_not_override_real_project_settings(self):
        project = json.loads((ROOT / "docs/implementation/prospectus-inception/run-014/project-before.json").read_text())
        project["blind_protocol"] = {"recommendations": False, "premerge": False}
        project["recommenders"] = [{"name": "shared predictions"}]
        with self.assertRaisesRegex(ValueError, "Recommendations"):
            check_configuration(project)
        project["recommenders"] = []
        for preference in project["default-preferences"]:
            if preference["name"] == "annotation/editor/curation-sidebar/manager":
                preference["traits"] = '{"autoMergeCurationSidebar": true}'
        with self.assertRaisesRegex(ValueError, "merge"):
            check_configuration(project)


if __name__ == "__main__":
    unittest.main()
