#!/usr/bin/env python3
"""Local PDF image extraction with explicit masks, ICC sidecars and audit records."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from pypdf import PdfReader
from pypdf.generic import IndirectObject


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(*args):
    return subprocess.run(args, check=True, capture_output=True, text=True).stdout


def extract(source, target):
    source = Path(source).resolve()
    target = Path(target).resolve()
    if target.exists():
        raise ValueError('Output already exists; choose a new directory (no overwrite).')
    for tool in ('pdfimages',):
        if not shutil.which(tool):
            raise RuntimeError(f'{tool} is required (Poppler).')
    reader = PdfReader(source)
    if reader.is_encrypted:
        raise ValueError('Encrypted PDF: supply an authorized decrypted copy.')
    listing = run('pdfimages', '-list', str(source))
    rows = []
    for line in listing.splitlines():
        f = line.split()
        if not f or not f[0].isdigit():
            continue
        if len(f) < 16 or not f[10].isdigit() or not f[11].isdigit():
            raise ValueError(f'Unsupported image-list row; manual review required: {line}')
        rows.append(dict(page=int(f[0]), number=int(f[1]), kind=f[2],
                         width=int(f[3]), height=int(f[4]), color=f[5],
                         encoding=f[8], object_id=int(f[10]), generation=int(f[11])))
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=target.parent) as work:
        stage = Path(work)
        run('pdfimages', '-all', str(source), str(stage / 'raw'))
        all_files = list(stage.glob('raw-*'))
        seen = set()
        for row in rows:
            files = [p for p in all_files if re.match(r'raw-(\d+)\.', p.name)
                     and int(re.match(r'raw-(\d+)\.', p.name)[1]) == row['number']]
            if not files:
                raise ValueError(f'No exported file for image {row["number"]}')
            row['files'] = []
            for file in files:
                new = stage / f'page-{row["page"]:04d}-image-{row["number"]:04d}-{row["kind"]}{file.suffix}'
                file.rename(new)
                seen.add(file.name)
                row['files'].append(dict(name=new.name, sha256=sha(new), bytes=new.stat().st_size))
            obj = reader.get_object(IndirectObject(row['object_id'], row['generation'], reader))
            if row['kind'] == 'smask':
                obj = obj.get('/SMask', obj).get_object()
            cs = obj.get('/ColorSpace')
            cs = cs.get_object() if cs is not None else None
            row['pdf_colorspace'] = str(cs)
            row['icc_sidecar'] = None
            if isinstance(cs, list) and cs and str(cs[0]) == '/ICCBased':
                profile = cs[1].get_object().get_data()
                icc = stage / f'image-{row["number"]:04d}.icc'
                icc.write_bytes(profile)
                row['icc_sidecar'] = dict(name=icc.name, sha256=sha(icc))
            row['review_required'] = (row['kind'] != 'image' or
                                      cs not in ('/DeviceRGB', '/DeviceGray') or
                                      obj.get('/Decode') is not None)
        if len(seen) != len(all_files):
            raise ValueError('Unmapped output files; extraction not accepted.')
        pages = [dict(page=n, image_entries=sum(r['page'] == n and r['kind'] == 'image' for r in rows),
                      masks=sum(r['page'] == n and r['kind'] != 'image' for r in rows))
                 for n in range(1, len(reader.pages) + 1)]
        report = dict(source=source.name, source_sha256=sha(source), pages=pages, images=rows,
                      image_entries=sum(p['image_entries'] for p in pages),
                      unique_image_objects=len({(r['object_id'], r['generation']) for r in rows if r['kind'] == 'image'}),
                      review_required=any(r['review_required'] for r in rows),
                      note='Entries follow Poppler listing, not every repeated drawing on a page. Masks are separate. ICC sidecars preserve source profiles; automatic color fidelity is not certified.')
        (stage / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
        (stage / 'source-image-list.txt').write_text(listing)
        with (stage / 'page-counts.csv').open('w', newline='') as out:
            writer = csv.DictWriter(out, fieldnames=['page', 'image_entries', 'masks'])
            writer.writeheader()
            writer.writerows(pages)
        shutil.copytree(stage, target)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('pdf')
    parser.add_argument('output')
    args = parser.parse_args()
    result = extract(args.pdf, args.output)
    print(json.dumps({k: result[k] for k in ('image_entries', 'unique_image_objects', 'review_required')}))
