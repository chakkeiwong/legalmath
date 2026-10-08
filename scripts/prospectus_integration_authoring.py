"""Real browser authoring and ordinary-account authentication on isolated INCEpTION."""
from copy import deepcopy
import io
import json
from pathlib import Path
import re
import secrets
import zipfile
from urllib.parse import parse_qsl
from scripts import prospectus_inception as old
from scripts.prospectus_integration_repair import ROOT,OUT,SIDECAR,save,sha,command
from legalmath.prospectus.successor import annotation_authoring as draft
from legalmath.prospectus.successor.annotation_bridge import export
from legalmath.prospectus.successor.contracts import digest


def configuration():
    raw,project=old.configured_project()
    project.update(name='LegalMath unlabelled authoring trial',slug='legalmath-authoring',project_invites=[])
    project['layers']=[row for row in project['layers'] if row.get('built_in')]+draft.layers()
    archive,name,_=old.project_json(raw)
    buf=io.BytesIO()
    with zipfile.ZipFile(buf,'w',zipfile.ZIP_DEFLATED) as target:
        for member in archive.namelist():
            target.writestr(member,json.dumps(project).encode() if member==name else archive.read(member))
    return buf.getvalue(),project


def login(page,base,username,password):
    page.goto(base+'/login.html')
    page.locator('input[name="username"]').fill(username)
    page.locator('input[name="password"]').fill(password)
    page.locator('button[type="submit"],input[type="submit"]').first.click()
    page.wait_for_load_state('networkidle')


def settled(page):
    # Wicket schedules its second change handler after the first network request.
    # Network-idle alone can return before that queued handler replaces the DOM.
    page.wait_for_function('() => window.Wicket && Object.values(Wicket.channelManager.channels).every(c => !c.busy)')


def field(page,name,value):
    settled(page)
    locator=page.locator('.fe-input').filter(has=page.locator('label span').filter(has_text=re.compile('^'+re.escape(name)+'$'))).locator('input')
    locator.click()
    locator.press('ControlOrMeta+A')
    locator.press_sequentially(value,delay=40)
    with page.expect_response(lambda response: 'featureEditors' in response.url):
        page.locator('#annotationDetailEditorPanel label').first.click()
    settled(page)
    if locator.input_value()!=value:
        raise ValueError('Feature edit did not persist in editor: '+name)


def select_text(page,quote,occurrence=0):
    # SVG character positions determine a real mouse text selection. No server
    # annotation or expected CAS is injected by this helper.
    points=page.evaluate('''([quote, occurrence]) => {
      let found=[];
      for (let row of document.querySelectorAll('svg g.text g.text-row')) {
        let s='', positions=[];
        for (let el of row.querySelectorAll('text')) {
          if (el.classList.contains('row-initial') || el.classList.contains('row-final')) continue;
          if (el.classList.contains('spacing')) {s+=' '; positions.push(null); continue;}
          for (let j=0;j<el.textContent.length;j++) {
            s+=el.textContent[j]; positions.push({el,j});
          }
        }
        let i=-1;
        while ((i=s.indexOf(quote,i+1))>=0) {
          let begin=positions[i], end=positions[i+quote.length-1];
          let a=begin.el.getStartPositionOfChar(begin.j), b=end.el.getEndPositionOfChar(end.j);
          let first=new DOMPoint(a.x,a.y-4).matrixTransform(begin.el.getScreenCTM());
          let last=new DOMPoint(b.x,b.y-4).matrixTransform(end.el.getScreenCTM());
          found.push({x1:first.x+0.4,y1:first.y,x2:last.x-0.4,y2:last.y});
        }
      }
      if (found.length<=occurrence) throw new Error('Text selection target absent: '+quote);
      return found[occurrence];
    }''',[quote,occurrence])
    page.mouse.move(points['x1'],points['y1']);page.mouse.down()
    page.mouse.move(points['x2'],points['y2'],steps=12);page.mouse.up()


def add_span(page,quote,key,label,occurrence=0):
    select_text(page,quote,occurrence)
    settled(page)
    field(page,'groupId',key);field(page,'label',label)
    page.locator('svg g.span').filter(has_text=key+' | '+label).first.wait_for(state='visible')


def select_span(page,key,label,index=0):
    page.locator('div.sticky-top').filter(has_text=key+' | '+label).locator('..').get_by_title('Select',exact=True).nth(index).click()


def delete_span(page,key,label,index=0):
    select_span(page,key,label,index)
    page.locator('#annotationDetailEditorPanel').get_by_title('Delete',exact=True).click()
    page.wait_for_load_state('networkidle')


def relation(page,from_key,to_key,relation_id,kind,from_index=0,to_index=0):
    # Brat supports relation creation by dragging an annotation to another.
    a=page.locator('svg g.span').filter(has_text=from_key+' |').nth(from_index).locator('[data-span-id]').first
    b=page.locator('svg g.span').filter(has_text=to_key+' |').nth(to_index).locator('[data-span-id]').first
    a.drag_to(b)
    field(page,'relationId',relation_id);field(page,'kind',kind)
    page.locator('svg').filter(has_text=kind).first.wait_for(state='visible')


def execute(folder):
    from playwright.sync_api import sync_playwright
    text='😀 Alpha clause. Same. Same.\nException for insolvency. Café remains.'
    source={'document':'unlabelled-authoring-development','source_sha256':digest(b'explicit synthetic authoring source'),
            'text_sha256':digest(text.encode())}
    expected=export(text,source,[],[])
    save(folder/'initial-expected.json',expected)
    command(folder,'empty-cas',[str(SIDECAR),'-m','scripts.prospectus_integration_codec','empty',
            str(folder/'initial-expected.json'),str(folder/'initial.xmi'),str(folder/'types.xml')],30)
    raw,config=configuration();(folder/'project-import.zip').write_bytes(raw)
    save(folder/'intended-project.json',config)
    operations=[]
    browser_path=Path('/home/chakwong/python/legalmath/.localresources/browser/chromium_headless_shell-1208/chrome-headless-shell-linux64/chrome-headless-shell')
    save(folder/'runtime.json',old.runtime_identity())
    with old.server(folder,guests=False) as (client,runtime):
        connection=json.loads((runtime/'connection.json').read_text())
        with sync_playwright() as automation:
            browser=automation.chromium.launch(executable_path=str(browser_path),headless=True,args=['--disable-gpu'])
            def context():
                c=browser.new_context(viewport={'width':1600,'height':1100})
                c.set_default_timeout(12000)
                c.route('**/*',lambda route: route.continue_() if route.request.url.startswith(client.base+'/') else route.abort())
                return c
            admin=context();page=admin.new_page();reader_page=None
            try:
                login(page,client.base,'trial-admin',connection['password'])
                credentials={name:secrets.token_urlsafe(20) for name in ('reader-a','reader-b')}
                # Passwords stay in the ignored, private runtime directory only.
                save(runtime/'reader-credentials.json',credentials);(runtime/'reader-credentials.json').chmod(0o600)
                for username,password in credentials.items():
                    page.goto(client.base+'/users.html')
                    page.locator('button').filter(has=page.locator('i.fa-user-plus')).click()
                    page.locator('input[name="username"]').fill(username)
                    page.locator('input[name="uiName"]').fill('Synthetic '+username)
                    page.locator('input[autocomplete="new-password"]').first.fill(password)
                    page.locator('input[name$=":repeatPassword"],input[name="repeatPassword"]').fill(password)
                    page.locator('button[name="save"]').click()
                    page.get_by_text('Synthetic '+username,exact=True).wait_for(state='visible')
                response=client.request('POST',old.API+'/projects/import',files={'file':('project.zip',raw,'application/zip')})
                project=response['body']['id']
                for username in credentials:
                    client.request('POST',f'{old.API}/projects/{project}/permissions/{username}',fields={'roles':'ANNOTATOR'})
                response=client.request('POST',f'{old.API}/projects/{project}/documents',fields={'name':'source.txt','format':'text'},
                    files={'content':('source.txt',text.encode(),'text/plain; charset=utf-8')})
                document=response['body']['id']
                for username in ('trial-admin',*credentials):
                    client.request('POST',f'{old.API}/projects/{project}/documents/{document}/annotations/{username}',
                        fields={'format':'xmi','state':'IN-PROGRESS'},files={'content':('source.xmi',(folder/'initial.xmi').read_bytes(),'application/xml')})
                save(folder/'accounts.json',{'users':list(credentials),'kind':'ORDINARY_PASSWORD_ACCOUNTS_SYNTHETIC','guest_entry':False})
                permissions=client.request('GET',f'{old.API}/projects/{project}/permissions',name='permissions.json')['body']
                for username in credentials:
                    if {p['role'] for p in permissions if p['user']==username}!={'ANNOTATOR'}:
                        raise ValueError('Reader has unintended project roles')
                def snapshot(stage,packet,user='reader-a'):
                    exp=folder/(stage+'-expected.json');save(exp,packet)
                    rawname=stage+'.zip'
                    client.request('GET',f'{old.API}/projects/{project}/documents/{document}/annotations/{user}?format=xmi',name=rawname)
                    command(folder,stage+'-codec',[str(SIDECAR),'-m','scripts.prospectus_integration_codec','decode',
                            str(exp),str(folder/rawname),str(folder/(stage+'-decoded.json'))],30)
                    operations.append({'stage':stage,'user':user,'raw':rawname,'expected':exp.name,'status':'EXACT_PACKET_PASS'})
                    save(folder/'operations.json',operations)
                for user in credentials:snapshot('initial-'+user,expected,user)
                bad=context();badpage=bad.new_page()
                login(badpage,client.base,'reader-a','deliberately-wrong-password')
                badpage.locator('input[name="password"]').wait_for(state='visible')
                if 'Invalid' not in badpage.locator('body').inner_text() and 'failed' not in badpage.locator('body').inner_text().lower():
                    raise ValueError('Wrong-password rejection not established')
                old.save_html(badpage,folder/'wrong-password.html');bad.close()
                unauth=context();up=unauth.new_page()
                up.goto(client.base+f'/p/{project}/annotate#!d={document}')
                up.locator('input[name="password"]').wait_for(state='visible')
                old.save_html(up,folder/'unauthenticated-denied.html');unauth.close()
                readers=[]
                for user,password in credentials.items():
                    rc=context();rp=rc.new_page();login(rp,client.base,user,password)
                    rp.goto(client.base+f'/p/{project}/annotate#!d={document}')
                    rp.locator('svg g.text').wait_for(state='visible')
                    readers.append((user,rc,rp))
                reader_page=readers[0][2]
                feature_requests=[]
                def record_feature(request):
                    if 'featureEditors' in request.url:
                        feature_requests.append({'url':request.url.split('?',1)[-1],
                            'fields':[(k,v) for k,v in parse_qsl(request.post_data or '',keep_blank_values=True)
                                      if 'featureEditors' in k or k=='value']})
                        save(folder/'feature-requests.json',feature_requests)
                reader_page.on('request',record_feature)
                def group(quote,key,label,occurrence=0):
                    at=-1
                    for _ in range(occurrence+1):at=text.index(quote,at+1)
                    return {'id':key,'label':label,'spans':[{'start':at,'end':at+len(quote),'quote':quote}]}
                groups=[];relations=[]
                add_span(reader_page,'Alpha','g1','condition');groups.append(group('Alpha','g1','condition'))
                reader_page.reload();reader_page.locator('svg g.span').filter(has_text='g1 | condition').wait_for(state='visible')
                snapshot('created-span',export(text,source,groups,relations))
                # A boundary replacement is explicit delete+reselect in this UI workflow.
                # The intermediate deletion and replacement are preserved separately.
                delete_span(reader_page,'g1','condition');groups=[]
                snapshot('deleted-span',export(text,source,groups,relations))
                add_span(reader_page,'Alpha clause','g1','condition');groups.append(group('Alpha clause','g1','condition'))
                snapshot('changed-boundary',export(text,source,groups,relations))
                add_span(reader_page,'insolvency','g1','condition')
                groups[0]['spans']+=group('insolvency','unused','condition')['spans']
                relation(reader_page,'g1','g1','g1-piece-1','same_evidence_group',0,1)
                snapshot('discontinuous-group',export(text,source,groups,relations))
                add_span(reader_page,'Same','g2','exception',1);groups.append(group('Same','g2','exception',1))
                relation(reader_page,'g1','g2','exception-edge','exception')
                relations=[{'id':'exception-edge','from':'g1','to':'g2','kind':'exception'}]
                reader_page.reload();reader_page.locator('svg g.span').filter(has_text='g2 | exception').wait_for(state='visible')
                snapshot('semantic-relation',export(text,source,groups,relations))
                snapshot('peer-unchanged',expected,'reader-b')
                denials=[]
                for user,rc,rp in readers:
                    for peer in ('trial-admin','reader-b' if user=='reader-a' else 'reader-a'):
                        rp.goto(client.base+f'/p/{project}/annotate#!d={document}&u={peer}')
                        message=rp.get_by_text('Requested document does not exist or you have no permissions to access it.',exact=True)
                        message.wait_for(state='attached')
                        old.save_html(rp,folder/(user+'-'+peer+'-denied.html'))
                        denials.append({'reader':user,'owner':peer,'denied':True})
                save(folder/'access.json',denials)
                exported=client.request('GET',f'{old.API}/projects/{project}/export.zip?format=xmi',name='project-final.zip')
                _,_,actual=old.project_json(exported);save(folder/'project-final.json',actual)
                if actual.get('recommenders') or actual.get('project_invites'):
                    raise ValueError('Recommendations or invitations unexpectedly active')
                prefs={p['name']:json.loads(p['traits']) for p in actual['default-preferences']}
                if prefs['annotation/editor/curation-sidebar/manager']['autoMergeCurationSidebar'] is not False:
                    raise ValueError('Automatic premerge active')
                return {'status':'PASS','authoring':'REAL_BROWSER_CREATED_DELETED_RESELECTED_LINKED_AND_RELATED',
                        'authentication':'ORDINARY_PASSWORD_ACCOUNTS; WRONG_PASSWORD_REJECTED; GUESTS_DISABLED',
                        'unauthenticated_annotation':'LOGIN_REQUIRED',
                        'exact_exports':len(operations),'cross_account_denials':len(denials),'independent_humans':False,
                        'boundary_method':'Explicit delete and reselect; direct handle-resize not claimed'}
            finally:
                for name,p in (('admin',page),('reader',reader_page)):
                    if p and not p.is_closed():
                        old.save_html(p,folder/(name+'-last.html'))
                        (folder/(name+'-last.txt')).write_text(p.locator('body').inner_text())
                        p.screenshot(path=str(folder/(name+'-last.png')),full_page=True)
                browser.close()
