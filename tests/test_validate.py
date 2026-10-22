import copy
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('validator', ROOT / 'scripts' / 'validate.py')
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)


class ValidationTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads((ROOT / 'assets' / 'trial-example.json').read_text(encoding='utf-8'))

    def test_valid_draft_still_needs_human_review(self):
        result = validator.validate(self.data)
        self.assertEqual(result['errors'], [])
        self.assertEqual(result['status'], 'MECHANICAL_PASS_REVIEW_REQUIRED')

    def test_scene_cover_has_no_overlay_text(self):
        self.data['gallery'][0]['overlay_text'] = ['Great gift']
        self.assertTrue(any('overlay_text' in x for x in validator.validate(self.data)['errors']))

    def test_unconfirmed_print_region_is_rejected(self):
        self.data['product']['print_region']['confirmed'] = False
        self.assertTrue(any('print_region' in x for x in validator.validate(self.data)['errors']))

    def test_title_and_five_bullets(self):
        self.data['listing']['title'] = 'x' * 76
        self.data['listing']['bullets'].pop()
        errors = validator.validate(self.data)['errors']
        self.assertTrue(any('title' in x for x in errors))
        self.assertTrue(any('bullets' in x for x in errors))

    def test_claim_requires_confirmed_fact(self):
        self.data['gallery'][1]['fact_ids'] = ['waterproof']
        self.assertTrue(any('waterproof' in x for x in validator.validate(self.data)['errors']))

    def test_contact_and_html_rejected(self):
        self.data['listing']['description'] = '<b>Visit https://example.com</b>'
        self.assertGreaterEqual(len(validator.validate(self.data)['errors']), 2)

    def test_unknown_limits_never_claim_full_compliance(self):
        self.data['rules']['bullet_max'] = None
        self.data['rules']['description_max'] = None
        result = validator.validate(self.data)
        self.assertEqual(result['errors'], [])
        self.assertTrue(any('bullet_max' in x for x in result['warnings']))


if __name__ == '__main__':
    unittest.main()
