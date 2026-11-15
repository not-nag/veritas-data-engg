"""Generate the SVG drawings and editable Draw.io document using the standard library."""
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / 'docs/diagrams'
WIDTH, HEIGHT = 1240, 740
BURGUNDY, INK, MUTED, BORDER = '#49182b', '#262126', '#716870', '#ddd6db'


def node(identifier, x, y, w, h, *lines, accent=False):
    return dict(id=identifier,x=x,y=y,w=w,h=h,lines=lines,accent=accent)


pages = [
    dict(slug='local-architecture',title='Local application architecture',
         subtitle='Implemented prototype · Python processing, SQLite persistence, and a Next.js operations interface',
         nodes=[
             node('input',40,190,175,90,'Report inputs','Folder / JSON upload','CLI batch'),
             node('intake',280,190,200,90,'Intake','Discovery and retention','Persistent watcher queue'),
             node('engine',560,190,220,90,'Python processing engine','Map → normalise → validate','Deduplicate and flag',accent=True),
             node('config',560,55,220,80,'Editable JSON configuration','Clinic schemas, tests,','units, ranges, medicines'),
             node('db',930,190,240,90,'SQLite','Raw and canonical records','History, reviews, wide view'),
             node('errors',560,375,220,80,'Failed-file store','Original payload and error','Retry attempt audit'),
             node('retry',280,375,200,80,'Inspect and repair','Retry original or edited JSON'),
             node('api',930,375,240,80,'Python HTTP API','Loopback-only local service'),
             node('metrics',560,555,220,80,'Operational visibility','Logs, metrics, threshold alerts'),
             node('ui',930,555,240,80,'Next.js interface','API proxy and operations UI',accent=True)],
         edges=[('input','intake',[(215,235),(280,235)]),('intake','engine',[(480,235),(560,235)]),
                ('config','engine',[(670,135),(670,190)]),('engine','db',[(780,235),(930,235)]),
                ('engine','errors',[(670,280),(670,375)]),('errors','retry',[(560,415),(480,415)]),
                ('retry','engine',[(380,375),(380,330),(520,330),(520,255),(560,255)]),
                ('db','api',[(1050,280),(1050,375)]),('api','ui',[(1050,455),(1050,555)]),
                ('engine','metrics',[(780,255),(840,255),(840,595),(780,595)]),
                ('metrics','ui',[(780,615),(930,615)])],
         footer='Each file commits atomically. Invalid observations remain available for review; malformed files retain their input for retry.'),
    dict(slug='production-architecture',title='Production architecture and resilience',
         subtitle='Proposed deployment · Managed object storage, event queue, scalable Python workers, and analytical storage',
         nodes=[
             node('clinic',35,190,155,90,'Clinics','JSON reports'),
             node('gcs',230,190,180,90,'Cloud Storage','Clinic / date paths','Immutable object versions'),
             node('queue',460,190,180,90,'Pub/Sub','Arrival events','Buffer burst traffic'),
             node('workers',720,190,200,90,'Cloud Run workers','Parse and standardise','Validate and flag',accent=True),
             node('config',720,55,200,80,'Versioned configuration','Reviewed and pinned per job'),
             node('warehouse',980,190,220,90,'BigQuery','Staging → MERGE','Stable-ID deduplication'),
             node('dlq',460,385,180,80,'Dead-letter storage','Payload, error, correlation ID'),
             node('replay',230,385,180,80,'Repair and replay','Retain original generation'),
             node('apiui',980,385,220,80,'Read API and UI','Authenticated operations','Raw / canonical inspection'),
             node('monitor',720,560,200,80,'Cloud Monitoring','Queue age, p95, error rate','Correlated logs and alerts',accent=True)],
         edges=[('clinic','gcs',[(190,235),(230,235)]),('gcs','queue',[(410,235),(460,235)]),
                ('queue','workers',[(640,235),(720,235)]),('config','workers',[(820,135),(820,190)]),
                ('workers','warehouse',[(920,235),(980,235)]),('warehouse','apiui',[(1090,280),(1090,385)]),
                ('workers','dlq',[(760,280),(760,325),(550,325),(550,385)]),
                ('dlq','replay',[(460,425),(410,425)]),
                ('replay','queue',[(320,385),(320,330),(440,330),(440,255),(460,255)]),
                ('workers','monitor',[(820,280),(820,560)])],
         footer='Design targets: 200k files/day, 2× bursts, p95 ≤15 min, 99.5% availability. Autoscale on queue age/depth; capacity and uptime require validation.'),
    dict(slug='production-controls',title='Onboarding, governance, and observability',
         subtitle='Proposed operating controls · Configuration-only onboarding is supported locally; production governance requires deployment',
         nodes=[
             node('schema',40,155,240,85,'Clinic schema and samples','Identify version and field paths'),
             node('mapping',345,155,240,85,'Versioned configuration','Aliases, units, quality contracts'),
             node('verify',650,155,240,85,'Validate and review','Representative sample tests','Domain review of medical rules'),
             node('release',955,155,240,85,'Release mappings','Pin configuration per job','Replay with output history',accent=True),
             node('raw',40,355,240,85,'Immutable source evidence','Object generation and clinic ID'),
             node('lineage',345,355,240,85,'Traceable output','Stable IDs, timestamps, config hash'),
             node('security',650,355,240,85,'Privacy and security','Encryption and tokenisation','Least-privilege access'),
             node('retention',955,355,240,85,'Governed access','Retention, deletion, audit policy'),
             node('events',40,555,240,85,'Structured events','Run and record correlation IDs'),
             node('signals',345,555,240,85,'Operational metrics','Throughput, errors, lag, p95','Coverage and duplicates'),
             node('alerts',650,555,240,85,'Threshold alerts','Error rate >1%','Queue age / latency breach',accent=True),
             node('response',955,555,240,85,'Operational response','Investigate → repair → replay','Track resolution and recovery')],
         edges=[('schema','mapping',[(280,197),(345,197)]),('mapping','verify',[(585,197),(650,197)]),('verify','release',[(890,197),(955,197)]),
                ('raw','lineage',[(280,397),(345,397)]),('lineage','security',[(585,397),(650,397)]),('security','retention',[(890,397),(955,397)]),
                ('events','signals',[(280,597),(345,597)]),('signals','alerts',[(585,597),(650,597)]),('alerts','response',[(890,597),(955,597)])],
         headings=[(40,130,'CLINIC ONBOARDING'),(40,330,'DATA QUALITY AND GOVERNANCE'),(40,530,'MONITORING AND RESPONSE')],
         footer='Coverage target: ≥98% of actual test-name variants within 30 days. Track raw and eligible denominators separately; review precision and exclusions.')
]


def svg_text(parent, x, y, text, size=14, color=INK, weight='400', anchor='start'):
    ET.SubElement(parent,'text',{'x':str(x),'y':str(y),'font-size':str(size),'fill':color,'font-weight':weight,'text-anchor':anchor}).text=text


def render(page, document):
    svg=ET.Element('svg',{'xmlns':'http://www.w3.org/2000/svg','width':str(WIDTH),'height':str(HEIGHT),'viewBox':f'0 0 {WIDTH} {HEIGHT}','role':'img','aria-label':page['title'],'font-family':'Arial, Helvetica, sans-serif'})
    ET.SubElement(svg,'title').text=page['title']
    ET.SubElement(svg,'desc').text=page['subtitle']
    ET.SubElement(svg,'rect',{'width':str(WIDTH),'height':str(HEIGHT),'fill':'#ffffff'})
    svg_text(svg,35,30,page['title'],24,weight='600')
    svg_text(svg,35,52,page['subtitle'],13,MUTED)
    for x,y,label in page.get('headings',[]):svg_text(svg,x,y,label,12,MUTED,weight='600')
    defs=ET.SubElement(svg,'defs')
    marker=ET.SubElement(defs,'marker',{'id':'arrow','viewBox':'0 0 10 10','refX':'9','refY':'5','markerWidth':'7','markerHeight':'7','orient':'auto-start-reverse'})
    ET.SubElement(marker,'path',{'d':'M 0 0 L 10 5 L 0 10 z','fill':MUTED})
    diagram=ET.SubElement(document,'diagram',{'id':page['slug'],'name':page['title']})
    model=ET.SubElement(diagram,'mxGraphModel',{'dx':str(WIDTH),'dy':str(HEIGHT),'grid':'1','gridSize':'10','page':'1','pageWidth':str(WIDTH),'pageHeight':str(HEIGHT),'arrows':'1','connect':'1'})
    root=ET.SubElement(model,'root');ET.SubElement(root,'mxCell',{'id':'0'});ET.SubElement(root,'mxCell',{'id':'1','parent':'0'})
    def label(identifier,text,x,y,w,h,size=14,color=INK):
        cell=ET.SubElement(root,'mxCell',{'id':identifier,'value':text,'vertex':'1','parent':'1','style':f'text;html=0;align=left;verticalAlign=middle;fontFamily=Helvetica;fontSize={size};fontColor={color};'})
        ET.SubElement(cell,'mxGeometry',{'x':str(x),'y':str(y),'width':str(w),'height':str(h),'as':'geometry'})
    label('title',page['title'],35,8,1170,30,24)
    label('subtitle',page['subtitle'],35,35,1170,28,13,MUTED)
    for i,(x,y,text) in enumerate(page.get('headings',[])):label('heading'+str(i),text,x,y-22,700,28,12,MUTED)
    by_id={n['id']:n for n in page['nodes']}
    for index,(source,target,points) in enumerate(page['edges']):
        ET.SubElement(svg,'polyline',{'points':' '.join(f'{x},{y}' for x,y in points),'fill':'none','stroke':MUTED,'stroke-width':'1.6','stroke-linejoin':'round','marker-end':'url(#arrow)'})
        a,b=by_id[source],by_id[target]
        exit_x,exit_y=(points[0][0]-a['x'])/a['w'],(points[0][1]-a['y'])/a['h']
        entry_x,entry_y=(points[-1][0]-b['x'])/b['w'],(points[-1][1]-b['y'])/b['h']
        cell=ET.SubElement(root,'mxCell',{'id':'edge'+str(index),'edge':'1','parent':'1','source':source,'target':target,'style':f'edgeStyle=orthogonalEdgeStyle;rounded=0;endArrow=block;strokeColor={MUTED};exitX={exit_x};exitY={exit_y};entryX={entry_x};entryY={entry_y};'})
        geom=ET.SubElement(cell,'mxGeometry',{'relative':'1','as':'geometry'})
        if len(points)>2:
            array=ET.SubElement(geom,'Array',{'as':'points'})
            for x,y in points[1:-1]:ET.SubElement(array,'mxPoint',{'x':str(x),'y':str(y)})
    for n in page['nodes']:
        fill,text_color=(BURGUNDY,'#ffffff') if n['accent'] else ('#faf8f9',INK)
        ET.SubElement(svg,'rect',{'x':str(n['x']),'y':str(n['y']),'width':str(n['w']),'height':str(n['h']),'rx':'9','fill':fill,'stroke':BURGUNDY if n['accent'] else BORDER})
        first_y=n['y']+n['h']/2-(len(n['lines'])-1)*10+5
        for i,line in enumerate(n['lines']):svg_text(svg,n['x']+n['w']/2,first_y+i*20,line,14 if i==0 else 12,text_color,'600' if i==0 else '400','middle')
        value='\n'.join(n['lines'])
        cell=ET.SubElement(root,'mxCell',{'id':n['id'],'value':value,'vertex':'1','parent':'1','style':f'rounded=1;whiteSpace=wrap;html=0;fillColor={fill};strokeColor={BURGUNDY if n["accent"] else BORDER};fontColor={text_color};fontSize=13;fontFamily=Helvetica;spacing=8;'})
        ET.SubElement(cell,'mxGeometry',{'x':str(n['x']),'y':str(n['y']),'width':str(n['w']),'height':str(n['h']),'as':'geometry'})
    ET.SubElement(svg,'line',{'x1':'35','y1':'682','x2':'1205','y2':'682','stroke':BORDER})
    svg_text(svg,35,708,page['footer'],12,MUTED)
    label('footer',page['footer'],35,688,1170,40,12,MUTED)
    ET.ElementTree(svg).write(DEST/(page['slug']+'.svg'),encoding='utf-8',xml_declaration=True)


if __name__=='__main__':
    DEST.mkdir(parents=True,exist_ok=True)
    document=ET.Element('mxfile',{'host':'app.diagrams.net','type':'device','compressed':'false'})
    for page in pages:render(page,document)
    ET.ElementTree(document).write(DEST/'veritas-architecture.drawio',encoding='utf-8',xml_declaration=True)
    print('Generated three SVG drawings and a three-page editable Draw.io document.')
