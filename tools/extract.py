import pymupdf as fitz, unicodedata as ud, re, json, sys, os
src, outdir = sys.argv[1], sys.argv[2]
os.makedirs(outdir+'/plans', exist_ok=True)
d=fitz.open(src)
FLOOR={'G':'الدور الأرضي','1':'الدور الأول','2':'الدور الثاني','R':'الملحق العلوي'}
def col(c):
    if c is None: return 'none'
    return '#%02x%02x%02x'%tuple(int(round(v*255)) for v in c[:3])
def f(v): return ('%.1f'%v).rstrip('0').rstrip('.')
def path_of(items):
    s=[];cur=None
    for it in items:
        k=it[0]
        if k=='l':
            a,b=it[1],it[2]
            if cur is None or abs(cur.x-a.x)>.01 or abs(cur.y-a.y)>.01: s.append('M%s %s'%(f(a.x),f(a.y)))
            s.append('L%s %s'%(f(b.x),f(b.y))); cur=b
        elif k=='c':
            a,b,c,e=it[1:5]
            if cur is None or abs(cur.x-a.x)>.01 or abs(cur.y-a.y)>.01: s.append('M%s %s'%(f(a.x),f(a.y)))
            s.append('C%s %s %s %s %s %s'%(f(b.x),f(b.y),f(c.x),f(c.y),f(e.x),f(e.y))); cur=e
        elif k=='re':
            r=it[1]; s.append('M%s %sh%sv%sh%sz'%(f(r.x0),f(r.y0),f(r.width),f(r.height),f(-r.width))); cur=None
        elif k=='qu':
            q=it[1]; s.append('M%s %sL%s %sL%s %sL%s %sz'%(f(q.ul.x),f(q.ul.y),f(q.ur.x),f(q.ur.y),f(q.lr.x),f(q.lr.y),f(q.ll.x),f(q.ll.y))); cur=None
    return ''.join(s)
units=[]
for i in range(1,len(d)):
    p=d[i]
    t=p.get_text(); code=re.search(r'([G12R]-\d\d)',t).group(1)
    els=[]; bb=None
    for dr in p.get_drawings():
        R=dr['rect']
        if R.x1>820 or R.width>760: continue
        if R.y0>740: continue
        if R.x1<125 and R.y0>680: continue
        bb = R if bb is None else bb|R
        pth=path_of(dr['items'])
        if dr.get('closePath') and not pth.endswith('z'): pth+='z'
        attrs=[]
        fill=dr.get('fill'); stroke=dr.get('color')
        if dr['type'] in ('f','fs') and fill is not None: attrs.append('fill="%s"'%col(fill))
        else: attrs.append('fill="none"')
        if dr.get('fill_opacity') not in (None,1) and fill is not None: attrs.append('fill-opacity="%s"'%f(dr['fill_opacity']))
        if dr['type'] in ('s','fs') and stroke is not None:
            attrs.append('stroke="%s" stroke-width="%s"'%(col(stroke),f(dr.get('width') or 1)))
            if dr.get('dashes') and dr['dashes'] not in ('[] 0','[] 0.0'):
                m=re.match(r'\[(.*)\]',dr['dashes']); 
                if m and m.group(1).strip(): attrs.append('stroke-dasharray="%s"'%m.group(1).strip().replace(' ',','))
            if dr.get('lineCap') and max(dr['lineCap'])==1: attrs.append('stroke-linecap="round"')
        if dr.get('even_odd'): attrs.append('fill-rule="evenodd"')
        els.append('<path d="%s" %s/>'%(pth,' '.join(attrs)))
    texts=[]
    for b in p.get_text('dict')['blocks']:
        for l in b.get('lines',[]):
            if l['bbox'][2]>820 or l['bbox'][1]>740: continue
            for s in l['spans']:
                tx=ud.normalize('NFKC',s['text']).strip()
                if not tx: continue
                x0,y0,x1,y1=s['bbox']; cx=(x0+x1)/2; cy=(y0+y1)/2
                bb = bb|fitz.Rect(s['bbox'])
                dx,dy=l['dir']
                import math
                ang=math.degrees(math.atan2(dy,dx))
                tr='' if abs(ang)<1 else ' transform="rotate(%s %s %s)"'%(f(ang),f(cx),f(cy))
                cls=' class="n"' if tx.isdigit() else ''
                texts.append('<text%s x="%s" y="%s" font-size="%s" fill="%s" text-anchor="middle" dominant-baseline="central"%s>%s</text>'%(cls,f(cx),f(cy),f(s['size']),col([((s['color']>>16)&255)/255,((s['color']>>8)&255)/255,(s['color']&255)/255]),tr,tx))
    m=6
    vb='%s %s %s %s'%(f(bb.x0-m),f(bb.y0-m),f(bb.width+2*m),f(bb.height+2*m))
    svg='<svg xmlns="http://www.w3.org/2000/svg" viewBox="%s">%s<g class="lbl" font-family="inherit" font-weight="700">%s</g></svg>'%(vb,''.join(els),''.join(texts))
    open(f'{outdir}/plans/{code}.svg','w').write(svg)
    # data
    info={'code':code,'floor':code[0],'floorName':FLOOR[code[0]]}
    rooms=[]; stop={}
    lines=sorted([l for b in p.get_text('dict')['blocks'] for l in b.get('lines',[])], key=lambda l:l['bbox'][1])
    for l in lines:
        if True:
            x0,y0,x1,y1=l['bbox']
            txt=ud.normalize('NFKC',' '.join(s['text'] for s in l['spans'] if s['bbox'][0]<1130)).strip()
            if x0<820: continue
            if 'غرف النوم' in txt or 'دورات المياه' in txt or 'المساحة الصافية' in txt: continue
            if y0>300 and y0<700 and txt and 'إجمالي' not in txt and not stop.get(1):
                mm=re.match(r'^(.*?)([\d.]+)$',txt)
                if mm:
                    name=mm.group(1).strip(); 
                    n2=re.match(r'^(\d+)\s+(.*)$',name)
                    if n2: name=n2.group(2)+' '+n2.group(1)
                    rooms.append({'name':name,'area':float(mm.group(2))})
            if 'إجمالي المساحة الداخلية' in txt: stop[1]=1; info['net']=float(re.search(r'([\d.]+)$',txt).group(1))
            mm=re.search(r'م([\d.]+) مساحة البيع ([\d,]+)',txt)
            if mm: info['sale']=float(mm.group(1)); info['price']=int(mm.group(2).replace(',',''))
    # beds/baths: big numbers at y 161
    nums=[]
    for b in p.get_text('dict')['blocks']:
        for l in b.get('lines',[]):
            if l['bbox'][0]>820 and 150<l['bbox'][1]<176:
                nums.append((l['bbox'][0],ud.normalize('NFKC',l['spans'][0]['text']).strip()))
    nums.sort()
    info['beds']=int([n for x,n in nums if x>1050][0]); info['baths']=int([n for x,n in nums if 950<x<1050][0])
    info['rooms']=rooms
    sc=re.search(r'Scale 1:(\d+)',t); info['scale']=int(sc.group(1))
    units.append(info)
json.dump(units,open(f'{outdir}/units.json','w'),ensure_ascii=False,indent=0)
print(len(units))
