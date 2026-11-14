#!/usr/bin/env python3
"""Add optional Mac browser issue capture to native standalone HTML (no WASM modifications)."""
from pathlib import Path
import hashlib,sys
if len(sys.argv)!=4:
    raise SystemExit("usage: inject_mac_diagnostics.py <compiled.html> <opt-in.js> <output.html>")
src_path,js_path,out_path=map(Path,sys.argv[1:])
src=src_path.read_bytes()
js=js_path.read_bytes()
marker=b"<head>\n"
assert src.count(marker)==1,"Unexpected standalone HTML head"
assert b"pletzel-field-diagnostics-v1" not in src,"Diagnostics already injected"
tag=b'<script id="pletzel-field-diagnostics-v1">\n'+js+b'\n</script>\n'
out=src.replace(marker,marker+tag,1)
assert out.replace(marker+tag,marker,1)==src,"Original native game HTML must be identical"
out_path.write_bytes(out)
for label,data in (("original-game",src),("diagnostics-js",js),("mac-field-game",out)):
    print(label,len(data),hashlib.sha256(data).hexdigest())
