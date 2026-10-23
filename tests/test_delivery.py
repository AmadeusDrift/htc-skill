import importlib.util
import json
from pathlib import Path
import tempfile
import subprocess
import sys
import unittest
import zipfile

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('delivery', ROOT / 'scripts' / 'gallery_delivery.py')
delivery = importlib.util.module_from_spec(spec)
spec.loader.exec_module(delivery)


class DeliveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.data = {'product_id': 'DEMO', 'canvas': [20, 20],
                     'slots': [{'id': f'{i:02}', 'role': 'scene' if i == 1 else 'detail'} for i in range(1, 8)],
                     'shared_images': {}, 'variants': []}
        for n, color in enumerate(['red', 'green', 'blue', 'yellow'], 1):
            variant = {'id': f'A{n:03}', 'images': {}}
            for i in range(1, 8):
                slot = f'{i:02}'
                if slot in ['03', '05']:
                    relative = f'shared/{slot}.png'
                    self.data['shared_images'][slot] = relative
                else:
                    relative = f"{variant['id']}/{slot}.png"
                    variant['images'][slot] = relative
                path = self.root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                if not path.exists(): Image.new('RGB', (20, 20), 'white' if slot in ['03', '05'] else color).save(path)
            self.data['variants'].append(variant)
        template = self.root / 'master.psd'
        template.write_bytes(b'FROZEN TEST FIXTURE')
        self.data['templates'] = [{'path': 'master.psd', 'sha256': delivery.sha256(template)}]
        self.manifest = self.root / 'delivery.json'
        self.save()

    def tearDown(self): self.temp.cleanup()

    def save(self): self.manifest.write_text(json.dumps(self.data), encoding='utf-8')

    def test_manifest_in_work_folder_resolves_product_root(self):
        self.manifest = self.root / '工作资料' / 'delivery.json'
        self.manifest.parent.mkdir()
        self.data['project_root'] = '..'
        self.save()
        self.assertEqual(delivery.inspect(self.manifest)['delivered_image_count'], 28)
        self.data['variants'][0]['images']['01'] = '../outside.png'
        self.save()
        with self.assertRaisesRegex(ValueError, 'escapes project'):
            delivery.inspect(self.manifest)

    def test_manifest_rejects_arbitrary_project_root(self):
        self.data['project_root'] = '../..'
        self.save()
        with self.assertRaisesRegex(ValueError, 'project_root'):
            delivery.load_manifest(self.manifest)

    def test_overview_cache_stays_in_work_folder(self):
        self.data['preview_cache_dir'] = '工作资料/预览缓存'
        self.save()
        output = self.root / 'A001' / '总览.jpg'
        self.assertFalse(delivery.make_overview(self.manifest, 'A001', output)['reused'])
        self.assertFalse(output.with_name(output.name + '.inputs.json').exists())
        self.assertEqual(len(list((self.root / '工作资料/预览缓存').glob('*.json'))), 1)
        self.assertTrue(delivery.make_overview(self.manifest, 'A001', output)['reused'])
        self.data['preview_cache_dir'] = '../outside'
        self.save()
        with self.assertRaisesRegex(ValueError, 'escapes project'):
            delivery.make_overview(self.manifest, 'A001', output)

    def test_shared_images_make_four_complete_sets(self):
        result = delivery.inspect(self.manifest)
        self.assertEqual(result['variant_count'], 4)
        self.assertEqual(result['images_per_set'], 7)
        self.assertEqual(result['delivered_image_count'], 28)
        self.assertEqual(result['status'], 'FILES_VERIFIED_VISUAL_REVIEW_REQUIRED')

    def test_missing_variant_image_is_rejected(self):
        (self.root / 'A002/07.png').unlink()
        with self.assertRaisesRegex(ValueError, 'Missing'):
            delivery.inspect(self.manifest)

    def test_changed_frozen_psd_is_rejected(self):
        (self.root / 'master.psd').write_bytes(b'CHANGED')
        with self.assertRaisesRegex(ValueError, 'hash'):
            delivery.inspect(self.manifest)

    def test_path_escape_is_rejected(self):
        self.data['shared_images']['03'] = '../outside.png'; self.save()
        with self.assertRaisesRegex(ValueError, 'project'):
            delivery.inspect(self.manifest)

    def test_duplicate_variant_id_is_rejected(self):
        self.data['variants'][1]['id'] = 'A001'; self.save()
        with self.assertRaisesRegex(ValueError, 'unique'):
            delivery.inspect(self.manifest)

    def test_mismatched_canvas_is_rejected(self):
        Image.new('RGB', (21, 20)).save(self.root / 'A001/01.png')
        with self.assertRaisesRegex(ValueError, 'canvas'):
            delivery.inspect(self.manifest)

    def test_slot_grid_preserves_four_artworks_without_generation(self):
        output = self.root / 'grid.png'
        result = delivery.make_grid(self.manifest, '07', output)
        self.assertFalse(result['reused'])
        with Image.open(output) as grid:
            self.assertEqual(grid.size, (40, 40))
            self.assertEqual([grid.getpixel(p) for p in [(10, 10), (30, 10), (10, 30), (30, 30)]],
                             [(255, 0, 0), (0, 128, 0), (0, 0, 255), (255, 255, 0)])
        self.assertTrue(delivery.make_grid(self.manifest, '07', output)['reused'])

    def test_existing_preview_from_different_inputs_is_not_overwritten(self):
        output = self.root / 'grid.png'
        delivery.make_grid(self.manifest, '07', output)
        Image.new('RGB', (20, 20), 'black').save(self.root / 'A001/07.png')
        with self.assertRaisesRegex(ValueError, 'overwrite'):
            delivery.make_grid(self.manifest, '07', output)

    def test_pack_includes_shared_images_in_each_complete_set_and_reuses(self):
        output = self.root / 'sets.zip'
        delivery.pack(self.manifest, output)
        with zipfile.ZipFile(output) as archive:
            self.assertEqual(len(archive.namelist()), 28)
            self.assertIsNone(archive.testzip())
            self.assertEqual(archive.read('A001/03.png'), archive.read('A004/03.png'))
            self.assertFalse(any('\\' in name for name in archive.namelist()))
        self.assertTrue(delivery.pack(self.manifest, output)['reused'])

    def test_overview_does_not_require_other_variant_outputs_ready(self):
        (self.root / 'A004/07.png').unlink()
        self.assertTrue(Path(delivery.make_overview(self.manifest, 'A001', self.root / 'overview.jpg')['path']).is_file())

    def test_reordered_variants_do_not_reuse_old_grid(self):
        output = self.root / 'grid.png'; delivery.make_grid(self.manifest, '07', output)
        self.data['variants'].reverse(); self.save()
        with self.assertRaisesRegex(ValueError, 'overwrite'):
            delivery.make_grid(self.manifest, '07', output)

    def test_reordered_slots_do_not_reuse_old_overview(self):
        output = self.root / 'overview.png'; delivery.make_overview(self.manifest, 'A001', output)
        self.data['slots'].reverse(); self.save()
        with self.assertRaisesRegex(ValueError, 'overwrite'):
            delivery.make_overview(self.manifest, 'A001', output)

    def test_preview_sidecar_cannot_overwrite_manifest(self):
        collision = self.root / 'grid.png.inputs.json'
        collision.write_text(self.manifest.read_text(), encoding='utf-8')
        original = collision.read_bytes()
        with self.assertRaisesRegex(ValueError, 'conflict|overwrite'):
            delivery.make_grid(collision, '07', self.root / 'grid.png')
        self.assertEqual(collision.read_bytes(), original)

    def test_unowned_sidecar_is_not_overwritten(self):
        sidecar = self.root / 'grid.png.inputs.json'; sidecar.write_text('important unrelated note', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'overwrite'):
            delivery.make_grid(self.manifest, '07', self.root / 'grid.png')
        self.assertEqual(sidecar.read_text(), 'important unrelated note')

    def test_single_variant_can_be_packaged_while_other_set_is_incomplete(self):
        (self.root / 'A004/07.png').unlink()
        output = self.root / 'first.zip'
        self.assertEqual(delivery.pack(self.manifest, output, 'A001')['images'], 7)
        with zipfile.ZipFile(output) as archive:self.assertEqual(len(archive.namelist()), 7)

    def test_first_set_delivery_allows_other_variant_mapping_to_be_incomplete(self):
        self.data['variants'][3]['images'].pop('07'); self.save()
        self.assertEqual(delivery.pack(self.manifest, self.root / 'first.zip', 'A001')['images'], 7)
        self.assertTrue(Path(delivery.make_overview(self.manifest, 'A001', self.root / 'first.jpg')['path']).exists())

    def test_cli_inspect_honors_variant_selection(self):
        (self.root / 'A004/07.png').unlink()
        result = subprocess.run([sys.executable, str(ROOT / 'scripts/gallery_delivery.py'), 'inspect',
                                 str(self.manifest), '--variant', 'A001'], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(json.loads(result.stdout)['variant_count'], 1)


if __name__ == '__main__': unittest.main()
