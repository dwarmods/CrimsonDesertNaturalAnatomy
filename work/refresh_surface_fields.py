from pathlib import Path
root=Path(__file__).resolve().parent
for name,marker in [('repair_surface_fields.py','# Replace weak'),('use_metric_smoothing.py',"f=APP/'web/fit.js'")]:
 p=root/name;source=p.read_text().split(marker)[0];exec(compile(source,str(p),'exec'),{'__file__':str(p)})
