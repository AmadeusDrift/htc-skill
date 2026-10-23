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

    def test_seven_image_plan_is_accepted(self):
        while len(self.data['gallery']) < 7:
            item = copy.deepcopy(self.data['gallery'][1])
            item['id'] = str(len(self.data['gallery']) + 1)
            self.data['gallery'].append(item)
        self.assertEqual(validator.validate(self.data)['errors'], [])

    def test_short_gallery_is_rejected(self):
        self.data['gallery'] = self.data['gallery'][:3]
        self.assertTrue(any('gallery' in e for e in validator.validate(self.data)['errors']))

    def test_product_info_can_be_reviewed_before_print_region_and_gallery(self):
        self.data['validation_stage'] = 'product-info'
        self.data['product']['print_region'] = {'confirmed': False}
        self.data.pop('gallery')
        self.data['listing'].pop('description')
        self.assertEqual(validator.validate(self.data)['errors'], [])

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

    def test_product_specific_gallery_roles_are_supported(self):
        for item, role in zip(self.data['gallery'][1:], ['benefit', 'function', 'detail', 'size', 'scene', 'use']):
            item['role'] = role
        self.assertEqual(validator.validate(self.data)['errors'], [])

    def test_modern_design_plan_requires_buying_reason_and_composition(self):
        self.data['gallery_strategy'] = {'buyer_profile': 'Travelers'}
        self.data['gallery'][1].pop('composition', None)
        result = validator.validate(self.data)
        self.assertTrue(any('core_buying_reason' in x for x in result['errors']))
        self.assertTrue(any('composition' in x for x in result['errors']))

    def test_frozen_templates_require_first_set_review_and_hashes(self):
        self.data['workflow'] = {'template_state': 'frozen', 'variant_method': 'smart-object-only'}
        errors = validator.validate(self.data)['errors']
        self.assertTrue(any('first_set_review' in x for x in errors))
        self.assertTrue(any('template_hashes' in x for x in errors))

    def test_explicit_delegation_can_replace_intermediate_pause(self):
        self.data['workflow'] = {
            'template_state': 'frozen', 'variant_method': 'smart-object-only',
            'first_set_review': {'status': 'delegated', 'evidence': 'User: do not pause', 'ai_visual_review': True},
            'template_hashes': {'master.psd': 'a' * 64},
        }
        self.assertEqual(validator.validate(self.data)['errors'], [])

    def test_delegation_is_not_a_fake_user_visual_approval(self):
        self.data['workflow'] = {
            'template_state': 'frozen', 'variant_method': 'smart-object-only',
            'first_set_review': {'status': 'delegated', 'evidence': 'User: do not pause'},
            'template_hashes': {'master.psd': 'a' * 64},
        }
        self.assertTrue(any('ai_visual_review' in x for x in validator.validate(self.data)['errors']))

    def test_variant_stage_cannot_use_scene_redraw(self):
        self.data['workflow'] = {
            'template_state': 'frozen', 'variant_method': 'imagegen-per-variant',
            'first_set_review': {'status': 'approved', 'evidence': 'Approved final set'},
            'template_hashes': {'master.psd': 'a' * 64},
        }
        self.assertTrue(any('variant_method' in x for x in validator.validate(self.data)['errors']))

    def test_delegated_visual_placement_is_separate_from_manufacturing_confirmation(self):
        self.data['product']['print_region'] = {
            'description': 'Visual exterior area', 'confirmed': False, 'manufacturing_confirmed': False,
            'placement_review': {'status': 'delegated', 'evidence': 'User delegated placement'},
        }
        self.assertEqual(validator.validate(self.data)['errors'], [])

    def test_new_schema_cannot_omit_design_strategy(self):
        self.data['schema_version'] = '0.4'; self.data.pop('gallery_strategy')
        self.assertTrue(any('gallery_strategy' in x for x in validator.validate(self.data)['errors']))

    def test_user_requested_gallery_count_can_differ_from_seven(self):
        self.data['images_per_set'] = 6
        self.data['images_per_set_source'] = 'User explicitly requested six images'
        self.data['gallery'] = self.data['gallery'][:6]
        self.assertEqual(validator.validate(self.data)['errors'], [])

    def test_changed_count_needs_user_request_record(self):
        self.data['images_per_set'] = 6
        self.data['gallery'] = self.data['gallery'][:6]
        self.assertTrue(any('images_per_set_source' in x for x in validator.validate(self.data)['errors']))

    def test_exported_stage_requires_a_frozen_template_state(self):
        self.data['workflow'] = {'stage': 'variants_exported', 'template_state': 'draft'}
        self.assertTrue(any('frozen' in x for x in validator.validate(self.data)['errors']))

    def test_unknown_template_state_cannot_bypass_frozen_checks(self):
        self.data['workflow'] = {'template_state': 'variants_exported'}
        self.assertTrue(any('template_state' in x for x in validator.validate(self.data)['errors']))

    def test_title_template_keeps_fixed_product_name_after_variable_print_phrase(self):
        self.data['title_template'] = {'print_phrase': 'Blue Botanical', 'fixed_product_name': 'Zipper Wallet'}
        self.data['listing']['title'] = 'Blue Botanical Zipper Wallet'
        self.assertEqual(validator.validate(self.data)['errors'], [])
        self.data['listing']['title'] = 'Blue Botanical Coin Purse'
        self.assertTrue(any('title_template' in x for x in validator.validate(self.data)['errors']))

    def test_title_template_requires_both_parts(self):
        for field in ('print_phrase', 'fixed_product_name'):
            with self.subTest(field=field):
                self.data['title_template'] = {'print_phrase': 'Botanical', 'fixed_product_name': 'Wallet'}
                self.data['title_template'][field] = ''
                self.assertTrue(any('title_template' in x for x in validator.validate(self.data)['errors']))

    def test_no_implicit_editorial_length_targets(self):
        self.data['rules']['bullet_max'] = None
        self.data['rules']['description_max'] = None
        self.data['rules'].pop('bullet_target', None)
        self.data['rules'].pop('description_target', None)
        self.data['listing']['bullets'][0] = 'Feature ' + 'x' * 270
        self.data['listing']['description'] = 'x' * 1100
        result = validator.validate(self.data)
        self.assertEqual(result['errors'], [])
        self.assertFalse(any('exceeds editorial target' in x for x in result['warnings']))

    def test_configured_official_field_limits_are_enforced_at_boundary(self):
        self.data.pop('title_template', None)
        self.data['rules']['title_max'] = 75
        self.data['rules']['bullet_max'] = 300
        self.data['rules']['description_max'] = 2000
        self.data['listing']['title'] = 'x' * 75
        self.data['listing']['bullets'][0] = 'x' * 300
        self.data['listing']['description'] = 'x' * 2000
        self.assertEqual(validator.validate(self.data)['errors'], [])
        self.data['listing']['title'] += 'x'
        self.data['listing']['bullets'][0] += 'x'
        self.data['listing']['description'] += 'x'
        errors = validator.validate(self.data)['errors']
        for field in ('title_max', 'bullet_max', 'description_max'):
            self.assertTrue(any(field in x for x in errors))


if __name__ == '__main__':
    unittest.main()
