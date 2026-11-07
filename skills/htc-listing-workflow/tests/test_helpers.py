import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile
from xml.sax.saxutils import escape

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))


def fixture(path, extended=False):
    """Minimal XLSX authored as XML, never via openpyxl writers."""
    cells = {'A4': 'Attribute', 'A5': 'color_name', 'A6': 'COLOR',
             'A7': 'color', 'A8': ' COLOR ', 'B6': 'Red', 'C6': 'Blue',
             'D6': 'anything', 'E6': ' COLOR ', 'F6': 'Red', 'G6': 'Red', 'H6': 'anything'}
    def xml_cells(items):
        rows = {}
        for coord, value in items.items():
            row = ''.join(c for c in coord if c.isdigit())
            rows.setdefault(row, []).append(f'<c r="{coord}" t="inlineStr"><is><t xml:space="preserve">{escape(value)}</t></is></c>')
        return ''.join(f'<row r="{r}">{"".join(c)}</row>' for r, c in rows.items())
    ns = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'
    rules = [('A6:A9', '&quot;COLOR,BLUE&quot;'), ('B6', 'Palette'),
             ('C6', "'Lookup Values'!$A$1:$A$2"), ('D6:D7', 'INDIRECT(A6)'),
             ('E6', '&quot; COLOR ,BLUE&quot;'), ('F6', 'Alias'), ('G6', 'LocalPalette'), ('H6', 'INDEX(Palette,1)')]
    with ZipFile(path, 'w') as z:
        z.writestr('[Content_Types].xml', '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/><Override PartName="/xl/worksheets/sheet2.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/></Types>')
        z.writestr('_rels/.rels', '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>')
        z.writestr('xl/workbook.xml', f'<workbook xmlns="{ns}" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Listing" sheetId="1" r:id="rId1"/><sheet name="Lookup Values" sheetId="2" r:id="rId2"/></sheets><definedNames><definedName name="Palette">\'Lookup Values\'!$A$1:$A$2</definedName><definedName name="Alias">Palette</definedName><definedName name="LocalPalette" localSheetId="0">Palette</definedName></definedNames></workbook>')
        z.writestr('xl/_rels/workbook.xml.rels', '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/><Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet2.xml"/></Relationships>')
        dvs = ''.join(f'<dataValidation type="list" sqref="{ref}"><formula1>{formula}</formula1></dataValidation>' for ref, formula in rules)
        ext = '<extLst><ext uri="test"><x14:dataValidations xmlns:x14="http://schemas.microsoft.com/office/spreadsheetml/2009/9/main" xmlns:xm="http://schemas.microsoft.com/office/excel/2006/main"><x14:dataValidation type="list"><x14:formula1><xm:f>INDIRECT(A6)</xm:f></x14:formula1><xm:sqref>I6</xm:sqref></x14:dataValidation></x14:dataValidations></ext></extLst>' if extended else ''
        z.writestr('xl/worksheets/sheet1.xml', f'<worksheet xmlns="{ns}"><sheetData>{xml_cells(cells)}</sheetData><dataValidations count="{len(rules)}">{dvs}</dataValidations>{ext}</worksheet>')
        z.writestr('xl/worksheets/sheet2.xml', f'<worksheet xmlns="{ns}"><sheetData>{xml_cells({"A1": "Red", "A2": "Blue"})}</sheetData></worksheet>')


class InputTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('input_gate'), 'input gate implementation missing')
        import input_gate
        self.mod = input_gate
        self.data = dict(schema_version='htc-listing-v1', mode='single', source_dir='images', start_sku='SKU001', listing_workbook=None, cloud_links_workbook=None, title_template='Product {关键词}', output_dir='同级新目录', template_rows=None, product_info={})

    def test_first_sku_inclusive_and_padding(self):
        self.assertEqual(self.mod.next_skus('SKU009', 3), ['SKU009', 'SKU010', 'SKU011'])

    def test_explicit_no_listing_is_valid(self):
        self.assertTrue(self.mod.validate_request(self.data)['valid'])

    def test_missing_or_bad_title_fails(self):
        del self.data['title_template']
        self.assertIn('title_template', self.mod.validate_request(self.data)['missing'])
        self.data['title_template'] = 'Product'
        self.assertFalse(self.mod.validate_request(self.data)['valid'])

    def test_parent_child_requires_grouping(self):
        self.data['mode'] = 'parent-child'
        self.assertFalse(self.mod.validate_request(self.data)['valid'])
        self.data['grouping'] = dict(sale_mode='children individually', parent_file='p.jpg', children=[dict(file='left.jpg', suffix='A'), dict(file='middle.jpg', suffix='B'), dict(file='right.jpg', suffix='C')])
        self.assertTrue(self.mod.validate_request(self.data)['valid'])

    def test_nullable_fields_must_be_explicit(self):
        del self.data['listing_workbook']
        self.assertFalse(self.mod.validate_request(self.data)['valid'])

    def test_schema_numeric_and_suffix_guards(self):
        for field, bad in [('schema_version', 'v2'), ('start_sku', 'SKU'), ('title_limit', True), ('keyword_limit', 0)]:
            data = dict(self.data, **{field: bad})
            self.assertFalse(self.mod.validate_request(data)['valid'], field)
        self.data.update(mode='parent-child', grouping={'parent_file': 'p.jpg', 'children': [{'file': 'a.jpg', 'suffix': 'A'}, {'file': 'b.jpg', 'suffix': 'A'}]})
        self.assertFalse(self.mod.validate_request(self.data)['valid'])

    def test_bad_grouping_with_path_checks_returns_errors(self):
        self.data.update(mode='parent-child', grouping={'children': None})
        self.assertFalse(self.mod.validate_request(self.data, check_paths=True)['valid'])

    def test_template_rows_object(self):
        self.data['template_rows'] = {'sheet': '模板', 'first_row': 7, 'last_row': 10}
        self.assertTrue(self.mod.validate_request(self.data)['valid'])
        self.data['template_rows']['last_row'] = 6
        self.assertFalse(self.mod.validate_request(self.data)['valid'])

    def test_explicit_placeholders_rejected_without_english_false_positives(self):
        for field, value in [('source_dir', '填写图片目录绝对路径'), ('title_template', '填写英文标题模板，使用{关键词}占位'), ('output_dir', '<output_dir>'), ('source_dir', 'TODO')]:
            self.assertFalse(self.mod.validate_request(dict(self.data, **{field: value}))['valid'], value)
        self.assertTrue(self.mod.validate_request(dict(self.data, title_template='Fill Your Home with Art {关键词}'))['valid'])

    def test_grouping_conflicts_sale_mode_and_unsafe_paths(self):
        grouping = dict(parent_file='p.jpg', children=[{'file': 'a.jpg', 'suffix': 'A'}], sale_mode='children individually')
        self.assertFalse(self.mod.validate_request(dict(self.data, grouping=grouping))['valid'])
        self.data.update(mode='parent-child', grouping=grouping)
        del grouping['sale_mode']
        self.assertIn('grouping.sale_mode', self.mod.validate_request(self.data)['missing'])
        grouping['sale_mode'] = 'children individually'
        for filename in ['p.jpg', '../a.jpg', 'C:/a.jpg', '/a.jpg', 'sub/../../a.jpg']:
            grouping['children'][0]['file'] = filename
            self.assertFalse(self.mod.validate_request(self.data)['valid'], filename)
        grouping['children'][0]['file'] = 'a.jpg'
        for suffix in ['A ', 'A/', 'A:', 'A?', 'A.']:
            grouping['children'][0]['suffix'] = suffix
            self.assertFalse(self.mod.validate_request(self.data)['valid'], suffix)

    def test_numbered_groups_checked_individually(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as temp:
            root = Path(temp)
            for name in ['001', '002']:
                (root / name).mkdir()
                for file in ['p.jpg', 'left.jpg', 'right.jpg']:
                    (root / name / file).write_bytes(b'fixture')
            self.data.update(source_dir=str(root), mode='parent-child', grouping=dict(unit='每个编号文件夹一组', sale_mode='children individually', parent_file='p.jpg', children=[{'file': 'left.jpg', 'suffix': 'A'}, {'file': 'right.jpg', 'suffix': 'C'}]))
            self.assertTrue(self.mod.validate_request(self.data, check_paths=True)['valid'])
            (root / '002' / 'right.jpg').unlink()
            result = self.mod.validate_request(self.data, check_paths=True)
            self.assertFalse(result['valid'])
            self.assertTrue(any('002/right.jpg' in error for error in result['errors']))

    def test_paths_must_be_absolute_and_output_must_be_new(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as temp:
            self.data['source_dir'] = temp
            self.assertTrue(self.mod.validate_request(self.data, check_paths=True)['valid'])
            for target in [temp, '.', 'relative-new-output']:
                result = self.mod.validate_request(dict(self.data, output_dir=target), check_paths=True)
                self.assertFalse(result['valid'], target)
            result = self.mod.validate_request(dict(self.data, source_dir='.'), check_paths=True)
            self.assertFalse(result['valid'])
            result = self.mod.validate_request(dict(self.data, output_dir=str(Path(temp) / 'new')), check_paths=True)
            self.assertTrue(result['valid'])

    def test_result_explicitly_states_syntax_only(self):
        self.assertTrue(self.mod.validate_request(self.data)['syntaxOnly'])


class WorkbookTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('workbook_rules'), 'workbook rules implementation missing')
        import workbook_rules
        self.mod = workbook_rules
        self.temp = tempfile.TemporaryDirectory(dir=Path(__file__).parent)
        self.path = Path(self.temp.name) / 'template.xlsx'
        fixture(self.path)

    def tearDown(self):
        self.temp.cleanup()

    def test_exact_literal_and_preserved_whitespace(self):
        result = self.mod.validate_dropdowns(self.path, 'Listing', 6, 8)
        self.assertEqual({x['cell'] for x in result['errors']}, {'A7', 'A8'})
        self.assertEqual({x['cell'] for x in result['unresolved']}, {'D6', 'D7', 'H6'})
        self.assertFalse(result['valid'])

    def test_named_crosssheet_recursive_and_headers(self):
        result = self.mod.inspect_workbook(self.path, 'Listing')
        self.assertEqual(result['headers']['A']['row4'], 'Attribute')
        self.assertEqual(result['headers']['A']['row5'], 'color_name')
        for rule in result['dropdowns']:
            if rule['sqref'] in ('B6', 'C6', 'F6', 'G6'):
                self.assertEqual(rule['allowed_values'], ['Red', 'Blue'])

    def test_touched_copied_values_still_checked(self):
        result = self.mod.validate_dropdowns(self.path, 'Listing', 6, 8, touched_cells=['A7'])
        self.assertEqual([x['cell'] for x in result['errors']], ['A7'])
        self.assertEqual(result['unresolved'], [])

    def test_inspection_never_changes_workbook_bytes(self):
        before = self.path.read_bytes()
        self.mod.inspect_workbook(self.path, 'Listing')
        self.mod.validate_dropdowns(self.path, 'Listing', 6, 8)
        self.assertEqual(self.path.read_bytes(), before)

    def test_zero_checked_never_claims_validation_pass(self):
        result = self.mod.validate_dropdowns(self.path, 'Listing', 8, 8, touched_cells=['B8'])
        self.assertFalse(result['valid'])
        self.assertEqual(result['status'], 'no_list_validation')
        result = self.mod.validate_dropdowns(self.path, 'Listing', 6, 6, touched_cells=['A6'])
        self.assertTrue(result['valid'])
        self.assertEqual(result['status'], 'passed')
        self.assertTrue(result['syntaxOnly'])
        result = self.mod.validate_dropdowns(self.path, 'Listing', 7, 7, touched_cells=['D7'])
        self.assertFalse(result['valid'])
        self.assertEqual(result['unresolved'][0]['cell'], 'D7')
        self.assertEqual(result['nonempty'], 0)
        self.assertEqual(result['empty'], 1)
        result = self.mod.validate_dropdowns(self.path, 'Listing', 9, 9, touched_cells=['A9'])
        self.assertFalse(result['valid'])
        self.assertEqual(result['status'], 'no_nonempty_list_cells')
        self.assertEqual(result['coverage']['covered_rule_cells'], 1)

    def test_extended_validation_is_reported_unresolved(self):
        fixture(self.path, extended=True)
        result = self.mod.inspect_workbook(self.path, 'Listing')
        self.assertTrue(any(rule['sqref'] == 'I6' and rule['status'] == 'unresolved' for rule in result['dropdowns']))
        result = self.mod.validate_dropdowns(self.path, 'Listing', 6, 6, touched_cells=['I6'])
        self.assertFalse(result['valid'])
        self.assertEqual(result['unresolved'][0]['cell'], 'I6')


if __name__ == '__main__':
    unittest.main()
