"""Package the development observer only; never install or inject it."""
from pathlib import Path
import argparse,hashlib,json,zipfile

def package(out):
    root=Path(__file__).resolve().parent.parent
    binary=root/'work/neutral-runtime/build/Release/NeutralRuntimeProbe.asi'
    if not binary.is_file():raise SystemExit('Build the Release probe before packaging.')
    readme='''Natural Anatomy upload-binding probe 0.2 — DEVELOPMENT DIAGNOSTIC

This package does not enable anatomy sliders or physics. The native fitting
backend is tested offline; connecting its output to the rendered game body
still needs live binding evidence. Do not replace your working static anatomy
DMM package with this diagnostic.

No installation, injection, game restart, or save change has been performed
by the packaging script. For a later voluntary test, when the game is closed,
place NeutralRuntimeProbe.asi next to the game's existing ASI plugins in
bin64 (an ASI loader must already be present). Then launch/load normally.

Stand with Kliff visible, preferably unclothed so the added body is visible.
Press F10 once with the game focused. Observe for about 20 seconds; changing
the camera angle or briefly walking is useful. F10 again stops sampling.
No hook is installed until F10. Unknown executable fingerprints are refused.
The hook remains pass-through afterward until that game process exits.

The probe intentionally avoids pose/mesh writes, but installs a code hook
inside the game. Offline ABI tests pass; live stability and coexistence with
other plugins remain unverified. Runtime unloading is unsupported. Remove
the diagnostic ASI only after a normal game exit if you no longer need it.

The files NeutralRuntimeProbe.log and NeutralRuntimeProbe.capture.tsv are
written next to the ASI. Keep them local and provide them privately for the
binding investigation; they contain addresses and sampled runtime bytes.
A successful capture is evidence to inspect, not proof of a working binding.

See PROBE.md for profiles, sampling format, and known limitations. No game
assets or third-party ASI binaries are included. MinHook's license is included.
'''
    payloads={'NeutralRuntimeProbe.asi':binary.read_bytes(),'README.txt':readme.encode('utf-8'),
              'PROBE.md':(root/'docs/PROBE.md').read_bytes(),
              'MINHOOK-LICENSE.txt':(root/'work/neutral-runtime/vendor/minhook/LICENSE.txt').read_bytes()}
    payloads['SHA256.json']=json.dumps({n:hashlib.sha256(b).hexdigest() for n,b in payloads.items()},indent=2).encode()
    out.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
        for name,data in payloads.items():z.writestr(name,data)
    with zipfile.ZipFile(out) as z:
        for name,data in payloads.items():assert z.read(name)==data
    print(json.dumps({'package':str(out),'bytes':out.stat().st_size,'sha256':hashlib.sha256(out.read_bytes()).hexdigest()}))

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,required=True)
    package(ap.parse_args().output)
