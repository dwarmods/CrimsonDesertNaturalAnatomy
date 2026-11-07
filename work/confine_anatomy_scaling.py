from pathlib import Path
import json
APP=Path(__file__).resolve().parent.parent/'outputs/Kliff-Body-Editor';f=APP/'web/assets/body.json';a=json.loads(f.read_text());r=next(m for m in a['meshes'] if m['editable']);region=set(r['region']);r['anatomyScaleWeights']=[1 if i in region else 0 for i in range(len(r['weights']))];f.write_text(json.dumps(a,separators=(',',':')))
f=APP/'web/fit.js';s=f.read_text().replace('value+weights[i]*((value-pivot[a])*(scales[a]-1)+offsets[a])', 'value+region.anatomyScaleWeights[i]*(value-pivot[a])*(scales[a]-1)+weights[i]*offsets[a]');f.write_text(s)
f=APP/'fit.py';s=f.read_text().replace('value+w*((value-pivot[a])*(scales[a]-1)+offsets[a])', "value+region['anatomyScaleWeights'][i]*(value-pivot[a])*(scales[a]-1)+w*offsets[a]");f.write_text(s)
