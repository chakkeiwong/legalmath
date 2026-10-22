"""One reviewed GET with the anonymous session from the exact source page."""
from datetime import datetime,timezone
from html.parser import HTMLParser
from http.cookies import SimpleCookie
from pathlib import Path
from urllib.parse import urljoin
import json,os,resource,subprocess,time
from scripts import prospectus_schvg_history as s

def main():
    s.frozen();s.costs()
    assert len(list((s.HERE/'requests').glob('*/started.json')))==7
    page=s.HERE/'requests/gazette-document-view'
    assert s.sha(page/'body')=='bcd56136216e14d3327f00eb5a0280d92c477c39f6d35aecc127fd518faea845'
    class Links(HTMLParser):
        def __init__(self):super().__init__();self.links=[]
        def handle_starttag(self,tag,attrs):
            a=dict(attrs)
            if tag=='img' and a.get('src','').startswith('media.xav/'):self.links.append(a['src'])
    links=Links();links.feed((page/'body').read_text());assert len(links.links)==1
    url=urljoin('https://www.bgbl.de/xaver/bgbl/',links.links[0])
    cookies=SimpleCookie()
    for line in (page/'headers').read_text().splitlines():
        if line.lower().startswith('set-cookie:'):cookies.load(line.split(':',1)[1].strip())
    assert 'JSESSIONID' in cookies and set(cookies)<={'JSESSIONID','bgblxaver'}
    folder=s.HERE/'requests/gazette-original-session';folder.mkdir(parents=True,exist_ok=False)
    cookie_path=Path('/tmp/prospectus-schvg-anonymous-session.cookies')
    fd=os.open(cookie_path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'w') as f:
        f.write('# Netscape HTTP Cookie File\n')
        for name,cookie in cookies.items():f.write('www.bgbl.de\tFALSE\t/\tTRUE\t0\t'+name+'\t'+cookie.value+'\n')
    cmd=['curl','--silent','--show-error','--proto','=https','--max-time','20','--connect-timeout','8',
        '--max-filesize',str(8*1024**2),'--cookie',str(cookie_path),
        '--referer',s.read(page/'started.json')['url'],'--dump-header',str(folder/'headers'),
        '--output',str(folder/'body'),'--write-out','%{json}',url]
    s.save(folder/'started.json',{'command':cmd,'source_page_sha256':s.sha(page/'body'),
        'anonymous_cookie_names':list(cookies),'cookie_values_logged':False,'started_at':datetime.now(timezone.utc).isoformat(),
        'review':'COOKIE-REQUEST-REVIEW.md','method_sha256':s.sha(Path(__file__)),
        'automatic_retries':0,'redirects':False})
    begin=time.monotonic()
    def cap():resource.setrlimit(resource.RLIMIT_FSIZE,(8*1024**2,8*1024**2))
    try:r=subprocess.run(cmd,capture_output=True,timeout=25,preexec_fn=cap);code,out,err=r.returncode,r.stdout,r.stderr
    except subprocess.TimeoutExpired as e:code,out,err=124,e.stdout or b'',e.stderr or b''
    finally:cookie_path.unlink()
    (folder/'curl-metadata').write_bytes(out);(folder/'curl-stderr').write_bytes(err)
    try:meta=json.loads(out)
    except ValueError:meta={}
    result={'status':'RESPONSE_RETAINED' if code==0 else 'FAILED_RETAINED','curl_exit':code,
        'http_status':meta.get('http_code'),'content_type':meta.get('content_type'),
        'body_bytes':(folder/'body').stat().st_size if (folder/'body').exists() else 0,
        'body_sha256':s.sha(folder/'body') if (folder/'body').exists() else None,
        'wall_seconds':time.monotonic()-begin,'source_accepted':False,'acquired_at':datetime.now(timezone.utc).isoformat()}
    s.save(folder/'receipt.json',result);s.costs();print(json.dumps(result))

if __name__=='__main__':main()
