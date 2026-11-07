"""Validate the explicit HTC request; never infer a starting SKU from old rows."""
import argparse
import json
import re
from pathlib import Path, PureWindowsPath


def _placeholder(value):
    return isinstance(value, str) and bool(re.search(r'填写|待填|请填|示例路径|(?i:\bTODO\b)|<[^<>]*>', value))


def _safe_relative(value):
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        return False
    path = PureWindowsPath(value)
    return not path.drive and not path.root and '..' not in path.parts and value not in ('.', '')


def next_skus(start, count):
    match = re.fullmatch(r'(.*?)([0-9]+)', start) if isinstance(start, str) else None
    if not match or not isinstance(count, int) or isinstance(count, bool) or count < 0:
        raise ValueError('start must end in digits and count must be a nonnegative integer')
    prefix, number = match.groups()
    return [prefix + str(int(number) + i).zfill(len(number)) for i in range(count)]


def validate_request(data, check_paths=False):
    """Syntax/path gate only; semantic grouping and business-required fields need model review."""
    errors, missing = [], []
    if not isinstance(data, dict):
        return {'valid': False, 'syntaxOnly': True, 'errors': ['request must be a JSON object'], 'missing': ['structured_request']}
    required = ('schema_version', 'mode', 'source_dir', 'start_sku', 'listing_workbook',
                'cloud_links_workbook', 'title_template', 'output_dir')
    missing = [key for key in required if key not in data]
    for key in required:
        if _placeholder(data.get(key)):
            errors.append(f'{key} contains an unfilled placeholder')
    if data.get('schema_version') != 'htc-listing-v1':
        errors.append('schema_version must be htc-listing-v1')
    if data.get('mode') not in ('single', 'parent-child'):
        errors.append('mode must be single or parent-child')
    for key in ('source_dir', 'output_dir'):
        if not isinstance(data.get(key), str) or not data[key].strip():
            errors.append(f'{key} must be nonempty')
    try:
        next_skus(data.get('start_sku'), 1)
    except ValueError as exc:
        errors.append(str(exc))
    title = data.get('title_template')
    if not isinstance(title, str) or '{关键词}' not in title:
        errors.append('title_template must contain {关键词}')
    for key, default in (('title_limit', 100), ('keyword_limit', 15)):
        value = data.get(key, default)
        if type(value) is not int or value <= 0:
            errors.append(f'{key} must be a positive integer')
    # No normalization is applied to keyword strings: spaces are retained.
    if data.get('keyword_spaces', 'preserve') != 'preserve':
        errors.append('keyword_spaces must be preserve')
    for key in ('listing_workbook', 'cloud_links_workbook'):
        value = data.get(key)
        if value is not None and (not isinstance(value, str) or not value.strip()):
            errors.append(f'{key} must be a path or explicit null')
    if not isinstance(data.get('product_info', {}), dict):
        errors.append('product_info must be an object')
    rows = data.get('template_rows')
    if isinstance(rows, dict):
        first, last = rows.get('first_row'), rows.get('last_row')
        if (not isinstance(rows.get('sheet'), str) or not rows['sheet'].strip()
                or _placeholder(rows['sheet']) or type(first) is not int or type(last) is not int
                or first < 1 or last < first):
            errors.append('template_rows requires sheet and an ordered positive first_row/last_row interval')
    elif rows is not None and (not isinstance(rows, list) or any(type(x) is not int or x < 1 for x in rows)):
        errors.append('template_rows must be null, a sheet/first_row/last_row object, or positive row numbers')
    if type(data.get('zip', False)) is not bool:
        errors.append('zip must be boolean')
    grouping = data.get('grouping')
    if data.get('mode') == 'single' and grouping is not None:
        errors.append('single mode requires null or absent grouping')
    if data.get('mode') == 'parent-child':
        if not isinstance(grouping, dict):
            missing.append('grouping')
        else:
            sale_mode = grouping.get('sale_mode')
            if 'sale_mode' not in grouping:
                missing.append('grouping.sale_mode')
            elif not isinstance(sale_mode, str) or not sale_mode.strip() or _placeholder(sale_mode):
                errors.append('grouping.sale_mode must explicitly describe the selling arrangement')
            parent = grouping.get('parent_file')
            if not _safe_relative(parent) or _placeholder(parent):
                errors.append('grouping.parent_file must be a safe nonempty relative path')
            children = grouping.get('children')
            if not isinstance(children, list) or not children:
                errors.append('grouping.children must be a nonempty list')
            else:
                suffixes, files = [], []
                for child in children:
                    if not isinstance(child, dict) or any(not isinstance(child.get(k), str) or not child[k].strip() for k in ('file', 'suffix')):
                        errors.append('each child requires nonempty file and suffix')
                    else:
                        suffixes.append(child['suffix'])
                        files.append(child['file'])
                        if not _safe_relative(child['file']) or _placeholder(child['file']):
                            errors.append(f'unsafe child file: {child["file"]}')
                        suffix = child['suffix']
                        if suffix != suffix.strip() or suffix.endswith('.') or re.search(r'[<>:"/\\|?*\x00-\x1f]', suffix) or _placeholder(suffix):
                            errors.append(f'invalid child suffix: {suffix}')
                if len(set(suffixes)) != len(suffixes) or len(set(files)) != len(files):
                    errors.append('child files and suffixes must be unique')
                identities = [str(PureWindowsPath(file)).casefold() for file in files]
                if len(set(identities)) != len(identities) or (isinstance(parent, str) and str(PureWindowsPath(parent)).casefold() in identities):
                    errors.append('parent and child files must all be distinct')
    if check_paths:
        source = data.get('source_dir')
        for key in ('source_dir', 'listing_workbook', 'cloud_links_workbook'):
            value = data.get(key)
            if isinstance(value, str) and not Path(value).is_absolute():
                errors.append(f'{key} must be an absolute path')
        output = data.get('output_dir')
        if isinstance(output, str) and output != '同级新目录':
            if not Path(output).is_absolute():
                errors.append('output_dir must be an absolute path or 同级新目录')
            if isinstance(source, str) and Path(output).resolve() == Path(source).resolve():
                errors.append('output_dir must differ from source_dir')
            if Path(output).exists():
                errors.append('output_dir already exists; choose a new version directory')
        if isinstance(source, str) and not Path(source).is_dir():
            errors.append('source_dir does not exist or is not a directory')
        for key in ('listing_workbook', 'cloud_links_workbook'):
            value = data.get(key)
            if isinstance(value, str) and not Path(value).is_file():
                errors.append(f'{key} does not exist or is not a file')
        if isinstance(grouping, dict) and isinstance(source, str):
            children = grouping.get('children')
            children = children if isinstance(children, list) else []
            files = [grouping.get('parent_file')] + [c.get('file') for c in children if isinstance(c, dict)]
            root = Path(source)
            groups = [root]
            if grouping.get('unit') == '每个编号文件夹一组':
                groups = sorted((p for p in root.iterdir() if p.is_dir() and re.fullmatch(r'[0-9]+', p.name)), key=lambda p: p.name) if root.is_dir() else []
                if not groups:
                    errors.append('grouping: no numbered folders found in source_dir')
            for group in groups:
                for name in files:
                    if not _safe_relative(name):
                        continue
                    candidate = group.joinpath(*PureWindowsPath(name).parts)
                    display = f'{group.name}/{name}' if group != root else name
                    if not candidate.resolve().is_relative_to(group.resolve()):
                        errors.append(f'grouping file escapes its group: {display}')
                    elif not candidate.is_file():
                        errors.append(f'grouping file does not exist: {display}')
    return {'valid': not errors and not missing, 'syntaxOnly': True, 'errors': errors, 'missing': missing}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--request', required=True, help='UTF-8 JSON request file')
    parser.add_argument('--check-paths', action='store_true')
    args = parser.parse_args()
    try:
        result = validate_request(json.loads(Path(args.request).read_text(encoding='utf-8-sig')), args.check_paths)
    except (OSError, ValueError) as exc:
        result = {'valid': False, 'syntaxOnly': True, 'errors': [str(exc)], 'missing': []}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result['valid'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
