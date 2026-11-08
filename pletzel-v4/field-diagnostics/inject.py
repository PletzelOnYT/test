#!/usr/bin/env python3
"""Inject opt-in Mac diagnostics into an existing Pletzel standalone HTML.

Preserves exact original HTML byte sequence, with one new inline script after
<head>. This never recompiles the game or changes its WASM bytes.
"""
from pathlib import Path
import hashlib
import sys
if len(sys.argv) != 4:
    raise SystemExit("usage: inject.py <existing-standalone.html> <field-diagnostics.js> <output.html>")
source, overlay, out = map(Path, sys.argv[1:])
src, js = source.read_bytes(), overlay.read_bytes()
marker = b"<head>\n"
assert src.count(marker) == 1 and b"pletzel-field-diagnostics-v1" not in src
tag = b'<script id="pletzel-field-diagnostics-v1">\n' + js + b"\n</script>\n"
result = src.replace(marker, marker+tag, 1)
assert result.replace(marker+tag, marker, 1) == src
out.write_bytes(result)
for label, data in (("engine-original",src),("diagnostics-js",js),("field-html",result)):
    print(label, len(data), hashlib.sha256(data).hexdigest())
