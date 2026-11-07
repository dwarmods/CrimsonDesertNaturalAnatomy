"""Refresh hashes of tracked source files, excluding this manifest itself."""
from pathlib import Path
import hashlib,json,subprocess
root=Path(__file__).resolve().parent.parent
names=subprocess.check_output(['git','ls-files','-z'],cwd=root).decode().split('\0')
manifest={name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in sorted(names)
          if name and name!='SOURCE-SHA256.json' and (root/name).is_file()}
(root/'SOURCE-SHA256.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
print(f'Updated {len(manifest)} source hashes')
