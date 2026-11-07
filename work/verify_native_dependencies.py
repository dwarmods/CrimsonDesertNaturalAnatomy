"""Verify vendored UI/JSON source bytes against pinned upstream Git blob IDs."""
from pathlib import Path
import hashlib,json
root=Path(__file__).resolve().parent/'neutral-runtime/vendor'
manifest=json.loads((root/'DEPENDENCIES.json').read_text())
count=0
for library,info in manifest.items():
    for name,wanted in info['files'].items():
        data=(root/library/name).read_bytes()
        actual=hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
        if actual!=wanted:raise SystemExit(f'Upstream source mismatch: {library}/{name}')
        count+=1
print(f'Verified {count} vendored files against pinned upstream Git blob IDs')
