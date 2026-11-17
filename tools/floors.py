import pymupdf as fitz, re, numpy as np, cv2, json, sys, potrace
d=fitz.open(sys.argv[1]); out=sys.argv[2]
floors={}
for i in range(1,len(d)):
    t=d[i].get_text(); code=re.search(r'([G12R]-\d\d)',t).group(1)
    x=d[i].get_images()[0][0]
    pix=fitz.Pixmap(d,x); a=np.frombuffer(pix.samples,np.uint8).reshape(pix.h,pix.w,pix.n)[:,:,:3].copy()
    floors.setdefault(code[0],[]).append((code,a))
S=4
def trace(mask, turd=8):
    bm=potrace.Bitmap(~mask.astype(bool))
    pl=bm.trace(turdsize=turd, alphamax=0.6, opticurve=True, opttolerance=0.3)
    parts=[]
    for c in pl:
        sp=c.start_point; parts.append('M%.1f %.1f'%(sp.x/S,sp.y/S))
        for seg in c.segments:
            if seg.is_corner:
                parts.append('L%.1f %.1fL%.1f %.1f'%(seg.c.x/S,seg.c.y/S,seg.end_point.x/S,seg.end_point.y/S))
            else:
                parts.append('C%.1f %.1f %.1f %.1f %.1f %.1f'%(seg.c1.x/S,seg.c1.y/S,seg.c2.x/S,seg.c2.y/S,seg.end_point.x/S,seg.end_point.y/S))
        parts.append('z')
    return ''.join(parts)
res={}
for f,lst in floors.items():
    H,W=lst[0][1].shape[:2]
    stack=np.stack([a for _,a in lst]).astype(np.int16)
    base=np.median(stack,axis=0).astype(np.uint8)
    units={}
    allm=np.zeros((H,W),np.uint8)
    for code,a in lst:
        diff=np.abs(a.astype(int)-base.astype(int)).sum(2)
        m=(diff>40).astype(np.uint8)*255
        m=cv2.morphologyEx(m,cv2.MORPH_CLOSE,np.ones((5,5),np.uint8))
        cs,_=cv2.findContours(m,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
        c=max(cs,key=cv2.contourArea)
        ap=cv2.approxPolyDP(c,1.0,True).reshape(-1,2)
        filled=np.zeros((H,W),np.uint8); cv2.drawContours(filled,[c],-1,255,-1)
        allm|=filled
        dt=cv2.distanceTransform(filled,cv2.DIST_L2,5)
        y,x=np.unravel_index(dt.argmax(),dt.shape)
        bx,by,bw,bh=cv2.boundingRect(c)
        units[code]={'poly':ap.tolist(),'lx':int(x),'ly':int(y),'r':float(round(dt.max(),1)),'bbox':[bx,by,bw,bh]}
    # bbox of all units
    ys,xs=np.where(allm>0)
    x0,x1,y0,y1=xs.min(),xs.max(),ys.min(),ys.max()
    pad=6
    if f=='R': y1=H-pad
    x0=max(0,x0-pad);y0=max(0,y0-pad);x1=min(W,x1+pad);y1=min(H,y1+pad)
    g=cv2.cvtColor(base,cv2.COLOR_RGB2GRAY)
    big=cv2.resize(g,None,fx=S,fy=S,interpolation=cv2.INTER_CUBIC)
    region=np.zeros_like(big,bool); region[y0*S:y1*S,x0*S:x1*S]=True
    walls=(big<120)&region
    fm=((g<240).astype(np.uint8)*255); fm=cv2.morphologyEx(fm,cv2.MORPH_CLOSE,np.ones((3,3),np.uint8))
    fm=cv2.resize(fm,None,fx=S,fy=S,interpolation=cv2.INTER_LINEAR); fm=cv2.GaussianBlur(fm,(9,9),0)
    foot=(fm>128)&region
    # buildings: cluster unit centroids by x
    cx=sorted((v['bbox'][0]+v['bbox'][2]/2,k) for k,v in units.items())
    gaps=sorted(((cx[i+1][0]-cx[i][0],i) for i in range(len(cx)-1)),reverse=True)
    nb=3
    cuts=sorted(i for _,i in gaps[:nb-1]) if f!='R' else None
    if f=='R':
        # roof: 6 pieces → buildings by pairs of pieces: use the 2 biggest gaps among 5 gaps between pieces? use thirds
        bounds=[W/3,2*W/3]
        bmap={k:(0 if x<bounds[0] else 1 if x<bounds[1] else 2) for x,k in cx}
    else:
        bmap={}; b=0
        for i,(x,k) in enumerate(cx):
            bmap[k]=b
            if i in cuts: b+=1
    for k in units: units[k]['b']=bmap[k]
    blds=[]
    for b in range(3):
        bb=[units[k]['bbox'] for k in units if units[k]['b']==b]
        bx0=min(v[0] for v in bb);by0=min(v[1] for v in bb);bx1=max(v[0]+v[2] for v in bb);by1=max(v[1]+v[3] for v in bb)
        blds.append([bx0,by0,bx1-bx0,by1-by0])
    res[f]={'vb':[int(x0),int(y0),int(x1-x0),int(y1-y0)],'walls':trace(walls,6),'foot':trace(foot,200),'units':units,'buildings':blds}
    print(f,res[f]['vb'],len(res[f]['walls'])//1000,'k',len(res[f]['foot'])//1000,'k',{b:sum(1 for k in units if units[k]['b']==b) for b in range(3)})
json.dump(res,open(out,'w'),separators=(',',':'))
