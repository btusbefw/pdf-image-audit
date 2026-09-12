# PDF image extraction audit sample

Independent synthetic technical demonstration by CDRXRX. Not client work or a claimed completed contract.

Run `python extract.py input.pdf new-output-directory` with Python, pypdf and Poppler (`pdfimages`) installed. No network calls. Existing output directories are rejected; encrypted or unrecognized inventory rows fail explicitly.

## Verified demonstration

The three-page synthetic PDF has two unique image objects, three page image entries and one separate soft mask. Page3 has no images. Both extracted JPEG entries match the original JPEG byte for byte. Decoded RGB pixels and alpha mask match the synthetic RGBA input exactly. `python verify.py` reruns extraction and these assertions, including overwrite rejection.

Outputs include per-page CSV counts, JSON inventory, original Poppler inventory, output checksums, and native JPEG/JPX formats where Poppler supports them. Embedded ICCBased profiles are retained as sidecars when present, with checksums; this fixture does not certify ICC handling.

## Honest limits

This is a tested extraction component, not a universal archival-fidelity certificate. Counts are Poppler image entries, not every rendering occurrence of an object on the same page. Transparency masks remain separate, not merged. Indexed/CMYK/ICCBased/Decode cases are flagged for review. Inline images not represented by a regular indirect object fail rather than silently disappear. Vector graphics are not raster images. Color profile interpretation, compound filter chains, JBIG2/CCITT sidecars, and unusual encodings need representative-file verification before delivery. No invented DPI or missing ICC profile.

No customer data included. Copyright CDRXRX; demonstration and source may be inspected for evaluation.
