"""Read-only XLSX headers and exact list-validation analysis. No workbook writes."""
import argparse
import json
import posixpath
import re
from zipfile import ZipFile
from xml.etree import ElementTree as ET

from openpyxl import load_workbook
from openpyxl.cell.read_only import EMPTY_CELL
from openpyxl.utils.cell import range_boundaries, get_column_letter

NS = {'m': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
REL = '{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id'


class Reader:
    def __init__(self, path, sheet):
        self.wb = load_workbook(path, read_only=True, data_only=False)
        try:
            self.ws = self.wb[sheet]
            with ZipFile(path) as archive:
                book = ET.fromstring(archive.read('xl/workbook.xml'))
                sheets = book.find('m:sheets', NS)
                index, entry = next((i, e) for i, e in enumerate(sheets) if e.get('name') == sheet)
                links = ET.fromstring(archive.read('xl/_rels/workbook.xml.rels'))
                target = next(e.get('Target') for e in links if e.get('Id') == entry.get(REL))
                target = target.lstrip('/') if target.startswith('/') else posixpath.normpath('xl/' + target)
                xml = ET.fromstring(archive.read(target))
            self.names = {}
            definitions = book.find('m:definedNames', NS)
            if definitions is not None:
                for e in definitions:
                    if e.get('localSheetId') is None:
                        self.names[e.get('name')] = e.text or ''
                for e in definitions:
                    if e.get('localSheetId') == str(index):
                        self.names[e.get('name')] = e.text or ''
            self.rules = []
            for e in xml.findall('m:dataValidations/m:dataValidation', NS):
                if e.get('type') == 'list':
                    formula = e.findtext('m:formula1', '', NS)
                    self.rules.append(dict(sqref=e.get('sqref'), formula=formula,
                                           allow_blank=e.get('allowBlank') in ('1', 'true'), **self.resolve(formula)))
            for e in xml.findall('.//{http://schemas.microsoft.com/office/spreadsheetml/2009/9/main}dataValidation'):
                refs = [child.text for child in e.iter() if child.tag.endswith('}sqref') and child.text]
                formulas = [child.text for child in e.iter() if child.tag.endswith('}f') and child.text]
                self.rules.append(dict(sqref=' '.join(refs), formula=' '.join(formulas),
                                       namespace='x14', allow_blank=e.get('allowBlank') in ('1', 'true'),
                                       **self.unresolved('extended x14 validation requires manual resolution')))
        except Exception:
            self.wb.close()
            raise

    def close(self):
        self.wb.close()

    def resolve(self, formula, seen=None):
        seen = set() if seen is None else seen
        value = formula.strip()
        if value.startswith('='):
            value = value[1:].strip()
        if value.startswith('"') and value.endswith('"'):
            return {'status': 'resolved', 'allowed_values': value[1:-1].split(',')}
        if value in seen:
            return self.unresolved('cyclic named range')
        if value in self.names:
            return self.resolve(self.names[value], seen | {value})
        match = re.fullmatch(r"(?:'((?:[^']|'')+)'|([A-Za-z_][\w .]*))!(\$?[A-Za-z]{1,3}\$?[1-9][0-9]*(?::\$?[A-Za-z]{1,3}\$?[1-9][0-9]*)?)", value)
        if not match:
            return self.unresolved('dynamic, dependent, complex, or unknown formula/name')
        sheet = (match[1] or match[2]).replace("''", "'")
        if sheet not in self.wb.sheetnames:
            return self.unresolved('referenced sheet is missing')
        min_col, min_row, max_col, max_row = range_boundaries(match[3])
        if min_col != max_col and min_row != max_row:
            return self.unresolved('list source must have one row or one column')
        values = []
        for row in self.wb[sheet].iter_rows(min_row=min_row, max_row=max_row, min_col=min_col, max_col=max_col):
            for cell in row:
                if cell.data_type == 'f':
                    return self.unresolved('source range contains formulas; manual review required')
                if cell.value is not None:
                    values.append(cell.value)
        return {'status': 'resolved', 'allowed_values': values}

    @staticmethod
    def unresolved(reason):
        return {'status': 'unresolved', 'allowed_values': None, 'reason': reason}


def inspect_workbook(path, sheet, header_rows=(4, 5)):
    """Return column-keyed header values and every list-DV, including unresolved rules."""
    reader = Reader(path, sheet)
    try:
        headers = {}
        for row_number in header_rows:
            for row in reader.ws.iter_rows(min_row=row_number, max_row=row_number):
                for cell in row:
                    if cell.value is not None:
                        headers.setdefault(get_column_letter(cell.column), {})[f'row{row_number}'] = cell.value
        return {'sheet': sheet, 'syntaxOnly': True, 'header_rows': list(header_rows), 'headers': headers, 'dropdowns': reader.rules}
    finally:
        reader.close()


def validate_dropdowns(path, sheet, first_row, last_row, touched_cells=None):
    """Exact list membership only, including copied values; business-required fields need model review.

    Zero covered/nonempty cells never constitutes a pass. Dynamic rules remain
    unresolved even for empty targets. Coverage counts are rule-cell incidences.
    """
    if type(first_row) is not int or type(last_row) is not int or first_row < 1 or last_row < first_row:
        raise ValueError('row interval must be positive and ordered')
    reader = Reader(path, sheet)
    errors, unresolved, checked, empty, applicable_rules = [], [], 0, 0, 0
    touched = None if touched_cells is None else {str(x).replace('$', '').upper() for x in touched_cells}
    try:
        for rule in reader.rules:
            visited = set()
            applicable = False
            if not rule['sqref']:
                unresolved.append({'cell': None, 'value': None, 'formula': rule['formula'], 'reason': 'validation has no resolvable target range'})
            for ref in rule['sqref'].split():
                c1, r1, c2, r2 = range_boundaries(ref)
                start, end = max(r1, first_row), min(r2, last_row)
                iterator = iter(reader.ws.iter_rows(min_row=start, max_row=end, min_col=c1, max_col=c2)) if start <= end else iter(())
                for row_index in range(start, end + 1):
                    row = next(iterator, (EMPTY_CELL,) * (c2 - c1 + 1))
                    for col_index, cell in enumerate(row, start=c1):
                        coordinate = f'{get_column_letter(col_index)}{row_index}'
                        if coordinate in visited or (touched is not None and coordinate not in touched):
                            continue
                        applicable = True
                        visited.add(coordinate)
                        item = {'cell': coordinate, 'value': cell.value, 'formula': rule['formula']}
                        blank = cell.value is None or cell.value == ''
                        empty += int(blank)
                        checked += int(not blank)
                        if cell.data_type == 'f':
                            unresolved.append(dict(item, reason='cell contains formula; manual review required'))
                        elif rule['status'] == 'unresolved':
                            unresolved.append(dict(item, reason=rule['reason']))
                        elif blank:
                            continue
                        elif not any(type(cell.value) is type(v) and cell.value == v for v in rule['allowed_values']):
                            errors.append(dict(item, allowed_values=rule['allowed_values'], reason='exact dropdown membership mismatch'))
            applicable_rules += int(applicable)
        status = ('unresolved' if unresolved else 'failed' if errors else 'no_list_validation'
                  if checked + empty == 0 else 'no_nonempty_list_cells' if checked == 0 else 'passed')
        return {'valid': status == 'passed', 'syntaxOnly': True, 'status': status,
                'checked': checked, 'nonempty': checked, 'empty': empty,
                'rule_count': len(reader.rules), 'applicable_rule_count': applicable_rules,
                'coverage': {'covered_rule_cells': checked + empty, 'scope': 'requested rows and touched cells; list membership only'},
                'errors': errors, 'unresolved': unresolved}
    finally:
        reader.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['inspect', 'validate'])
    parser.add_argument('path')
    parser.add_argument('--sheet', required=True)
    parser.add_argument('--header-rows', nargs='+', type=int, default=[4, 5])
    parser.add_argument('--first-row', type=int)
    parser.add_argument('--last-row', type=int)
    parser.add_argument('--touched-cells', nargs='*')
    args = parser.parse_args()
    try:
        if args.command == 'inspect':
            result = inspect_workbook(args.path, args.sheet, args.header_rows)
        else:
            result = validate_dropdowns(args.path, args.sheet, args.first_row, args.last_row, args.touched_cells)
    except (OSError, ValueError, KeyError) as exc:
        result = {'valid': False, 'syntaxOnly': True, 'status': 'error', 'errors': [str(exc)]}
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    return 0 if result.get('valid', True) else 1


if __name__ == '__main__':
    raise SystemExit(main())
