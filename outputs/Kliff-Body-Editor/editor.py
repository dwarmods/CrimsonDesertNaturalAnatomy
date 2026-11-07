"""Local-only editor server. Python standard library; Blender needed for .blend export."""
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse
import json,secrets,threading,subprocess,shutil,os,sys,webbrowser,time,argparse,urllib.request,socket
from fit import validate
ROOT=Path(__file__).resolve().parent
EXPORTS=ROOT/'exports';TOKEN=secrets.token_urlsafe(32);JOBS={};LOCK=threading.Lock()
def find_blender():
    found=shutil.which('blender')
    if found:return found
    options=sorted(Path(os.environ.get('PROGRAMFILES','C:/Program Files'),'Blender Foundation').glob('Blender */blender.exe'),reverse=True)
    return str(options[0]) if options else None
BLENDER=find_blender()
class LocalServer(ThreadingHTTPServer):
    allow_reuse_address=False
    def server_bind(self):
        if hasattr(socket,'SO_EXCLUSIVEADDRUSE'):self.socket.setsockopt(socket.SOL_SOCKET,socket.SO_EXCLUSIVEADDRUSE,1)
        super().server_bind()
def export_job(key,preset):
    job=EXPORTS/(key+'.json');job.write_text(json.dumps(preset,indent=2))
    try:
        result=subprocess.run([BLENDER,'--background','--factory-startup','--python',str(ROOT/'export_blend.py'),'--',str(job)],capture_output=True,text=True,timeout=240,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        (EXPORTS/(key+'.log')).write_text(result.stdout+'\n'+result.stderr,encoding='utf-8')
        if result.returncode or not job.with_suffix('.blend').exists():raise RuntimeError('Blender export failed. See the log in exports/.')
        JOBS[key]={'state':'done','url':'/exports/'+key+'.blend','report':'/exports/'+key+'.report.json'}
    except Exception as e:JOBS[key]={'state':'error','message':str(e)}
class Handler(SimpleHTTPRequestHandler):
    def __init__(self,*a,**kw):super().__init__(*a,directory=str(ROOT/'web'),**kw)
    def end_headers(self):
        self.send_header('Cache-Control','no-store')
        super().end_headers()
    def log_message(self,*a):pass
    def send_json(self,code,data):
        data=json.dumps(data).encode();self.send_response(code);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(data)));self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(data)
    def allowed_host(self):return self.headers.get('Host') in (f'127.0.0.1:{self.server.server_port}',f'localhost:{self.server.server_port}')
    def do_GET(self):
        if not self.allowed_host():return self.send_json(403,{'error':'Local requests only.'})
        path=urlparse(self.path).path
        if path=='/api/session':return self.send_json(200,{'token':TOKEN,'blender':bool(BLENDER),'version':'1.5.0','app':'kliff-body-editor'})
        if path.startswith('/api/jobs/'):
            return self.send_json(200,JOBS.get(path.rsplit('/',1)[-1],{'state':'error','message':'Unknown export.'}))
        if path.startswith('/exports/'):
            name=path.rsplit('/',1)[-1];p=EXPORTS/name
            if '/' in path[len('/exports/'):] or '\\' in name or p.resolve().parent!=EXPORTS.resolve() or not p.is_file() or p.suffix not in ('.blend','.json'):return self.send_error(404)
            self.send_response(200);self.send_header('Content-Type','application/octet-stream');self.send_header('Content-Disposition',f'attachment; filename="{p.name}"');self.send_header('Content-Length',str(p.stat().st_size));self.end_headers()
            with p.open('rb') as f:shutil.copyfileobj(f,self.wfile)
            return
        return super().do_GET()
    def do_POST(self):
        origin=self.headers.get('Origin');expected=f'http://{self.headers.get("Host")}'
        if not self.allowed_host() or self.headers.get('X-Editor-Token')!=TOKEN or (origin and origin!=expected):return self.send_json(403,{'error':'Session check failed.'})
        if self.path!='/api/export':return self.send_json(404,{'error':'Unknown operation.'})
        if not BLENDER:return self.send_json(409,{'error':'Blender was not found. OBJ export and presets are still available.'})
        try:
            length=int(self.headers.get('Content-Length','0'))
            if not 0<length<16384:raise ValueError('Invalid request size.')
            data=json.loads(self.rfile.read(length));validate(data.get('parameters'))
            if data.get('asset')!='kliff-connected-v04' or data.get('schema')!=1:raise ValueError('This preset belongs to a different body.')
        except (ValueError,TypeError) as e:return self.send_json(400,{'error':str(e)})
        with LOCK:
            if any(j['state']=='running' for j in JOBS.values()):return self.send_json(409,{'error':'An export is already running.'})
            key='Kliff-fit-'+time.strftime('%Y%m%d-%H%M%S')+'-'+secrets.token_hex(3);JOBS[key]={'state':'running'}
        EXPORTS.mkdir(exist_ok=True);threading.Thread(target=export_job,args=(key,data),daemon=True).start();self.send_json(202,{'job':key})
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--no-browser',action='store_true');ap.add_argument('--port',type=int,default=48763);args=ap.parse_args()
    try:server=LocalServer(('127.0.0.1',args.port),Handler)
    except OSError:
        url=f'http://127.0.0.1:{args.port}/'
        try:
            with urllib.request.urlopen(url+'api/session',timeout=2) as response:existing=json.load(response)
            if existing.get('app')!='kliff-body-editor':raise ValueError('Port belongs to another app.')
        except Exception:raise SystemExit('The editor port is in use. Close the other app or use --port with another number.')
        print('Editor already running: '+url)
        if not args.no_browser:webbrowser.open(url)
        raise SystemExit(0)
    url=f'http://127.0.0.1:{server.server_port}/'
    print('Kliff Body Editor: '+url,flush=True);print('Close this window to stop the editor.',flush=True)
    if not args.no_browser:webbrowser.open(url)
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close()
