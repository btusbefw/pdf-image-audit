import tempfile
from pathlib import Path
from PIL import Image
from extract import extract

here = Path(__file__).resolve().parent
fixture = here / 'evidence'
with tempfile.TemporaryDirectory() as work:
    out = Path(work) / 'extracted'
    report = extract(fixture / 'fixture.pdf', out)
    assert report['image_entries'] == 3
    assert report['unique_image_objects'] == 2
    assert [(p['image_entries'], p['masks']) for p in report['pages']] == [(2, 1), (1, 0), (0, 0)]
    for name in ['page-0001-image-0000-image.jpg', 'page-0002-image-0003-image.jpg']:
        assert (out / name).read_bytes() == (fixture / 'native.jpg').read_bytes()
    rgba = Image.open(fixture / 'alpha.png')
    assert Image.open(out / 'page-0001-image-0001-image.png').tobytes() == rgba.convert('RGB').tobytes()
    assert Image.open(out / 'page-0001-image-0002-smask.png').tobytes() == rgba.getchannel('A').tobytes()
    assert report['review_required']
    try:
        extract(fixture / 'fixture.pdf', out)
    except ValueError:
        pass
    else:
        raise AssertionError('Existing directory was not protected')
print('PASS: counts, native JPEG bytes, RGB pixels, alpha pixels, review flag and overwrite protection')
