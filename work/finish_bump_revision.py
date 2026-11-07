from pathlib import Path
APP=Path(__file__).resolve().parent.parent/'outputs/Kliff-Body-Editor'
for file in ['web/index.html','editor.py','READ-ME.txt']:
 p=APP/file;s=p.read_text().replace('EDITOR 1.4','EDITOR 1.5').replace('Editor 1.4','Editor 1.5').replace("'version':'1.4.0'","'version':'1.5.0'");p.write_text(s)
p=APP/'web/app.js';s=p.read_text().replace('Extra geometric smoothing around the full join; base seam cleanup is always applied.','Smooths the attachment and adjacent fold continuously. Higher values soften more and can reduce local volume.');p.write_text(s)
p=APP/'READ-ME.txt';s=p.read_text()+'''
SURFACE REVISION 1.5
Replaces the separate attachment/scrotal relaxation masks with a continuous
9,714-vertex metric fairing patch. Its physical smoothing radius ranges from
4 to 9 mm, so small dense triangles no longer receive ineffective cleanup.
The patch crosses the old scrotal/shaft weight boundary and tapers to a fixed
outer boundary. The attachment loft now follows the pelvis surface tangent.
The relative-height field is also relaxed to remove angular path artifacts;
the torso, attachment rim, and fully translated core retain their placement
behavior. Existing presets and slider values are retained.
Smoothing can reduce local volume and change the shape of an existing fit.
This is a static mesh correction, not a verified in-game replacement. The
original materials remain in Blender exports; texture seam work is separate.
The geometry solver uses NumPy bundled with Blender; the local server still
uses Python's standard library. No additional download is needed.
''';p.write_text(s)
