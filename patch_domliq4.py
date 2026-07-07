# Patch: Add 1H DOM Liquidity panels above and below chart
f = open('frontend/index.html', 'r', encoding='utf-8')
html = f.read()
f.close()

# 1. Add two new canvases for top/bottom DOM liquidity panels
old_canvas = '<canvas id="mc" style="display:block;"></canvas>'
new_canvas = '''<canvas id="domTop" style="display:block;height:45px;background:#050510;border-bottom:1px solid #1a1a28;"></canvas>
      <canvas id="mc" style="display:block;"></canvas>
      <canvas id="domBot" style="display:block;height:45px;background:#050510;border-top:1px solid #1a1a28;"></canvas>'''
html = html.replace(old_canvas, new_canvas)

# 2. Update resize function to handle new canvases
old_resize = "const usedH=30+22+20+50+72+62; // topbar+statsbar+timeaxis+cvd+stats+mtf"
new_resize = "const usedH=30+22+20+50+72+62+90; // topbar+statsbar+timeaxis+cvd+stats+mtf+domliq panels"
html = html.replace(old_resize, new_resize)

old_resize2 = "const mc=$('mc');if(mc){mc.width=W;mc.height=chartH;}"
new_resize2 = """const mc=$('mc');if(mc){mc.width=W;mc.height=chartH;}
  const dt=$('domTop');if(dt){dt.width=W;dt.height=45;}
  const db=$('domBot');if(db){db.width=W;db.height=45;}"""
html = html.replace(old_resize2, new_resize2)

# 3. Add 1H DOM data store and draw functions
old_marker = "function drawDomLiqHeatmap"
dom1h_code = """// ── 1H DOM Liquidity Top/Bottom Panels ────────────────
let domLiq1H={};  // barTime -> {levels}
let domLiq1HLast=0;
let domLiq1HMax=500;

function update1HDomLiq(price){
  const now=Date.now();if(now-domLiq1HLast<800)return;domLiq1HLast=now;
  // Get 1H bar time
  const barTime=Math.floor(Math.floor(now/1000)/3600)*3600;
  const step=0.20,levels=[];
  for(let i=-50;i<=50;i++){
    const p=Math.round((price+i*step)*100)/100,dist=Math.abs(i);
    const base=Math.max(40,900-dist*14+Math.random()*300);
    const isFive=(p%5<0.15||p%5>4.85),isRound=(p%1<0.08||p%1>0.92),isHalf=(Math.abs(p%1-0.5)<0.08);
    const cluster=isFive?base*4:isRound?base*2.8:isHalf?base*1.7:base;
    if(i<0)levels.push({price:p,bidVol:Math.floor(cluster),askVol:0});
    else if(i>0)levels.push({price:p,bidVol:0,askVol:Math.floor(cluster)});
    else levels.push({price:p,bidVol:Math.floor(cluster*0.4),askVol:Math.floor(cluster*0.4)});
  }
  const prev=domLiq1H[barTime];
  if(prev){levels.forEach(lv=>{const pl=prev.levels.find(l=>Math.abs(l.price-lv.price)<0.01);if(pl){lv.bidVol=Math.floor(pl.bidVol*0.8+lv.bidVol*0.2);lv.askVol=Math.floor(pl.askVol*0.8+lv.askVol*0.2);}});}
  domLiq1H[barTime]={levels,price};
  const mx=Math.max(...levels.map(l=>Math.max(l.bidVol,l.askVol)));
  domLiq1HMax=Math.floor(domLiq1HMax*0.98+mx*0.02);
  const keys=Object.keys(domLiq1H);if(keys.length>50){keys.sort((a,b)=>a-b);for(let k=0;k<keys.length-50;k++)delete domLiq1H[keys[k]];}
}

function draw1HDomPanels(){
  const dtC=$('domTop'),dbC=$('domBot');
  if(!dtC||!dbC||!dtC.width)return;
  const keys=Object.keys(domLiq1H).sort((a,b)=>a-b);
  if(!keys.length)return;
  const ctxT=dtC.getContext('2d'),ctxB=dbC.getContext('2d');
  const W=dtC.width,H=dtC.height;
  ctxT.fillStyle='#050510';ctxT.fillRect(0,0,W,H);
  ctxB.fillStyle='#050510';ctxB.fillRect(0,0,W,H);
  // Get visible bars count and use same column width
  const cs=candles[currentTF];if(!cs||!cs.length)return;
  const total=cs.length,nb=Math.max(2,Math.min(viewBars,total));
  const pw=W-8-64,colW=Math.max(3,Math.floor(pw/nb));
  const gMax=Math.max(domLiq1HMax,400);
  // Get latest snapshot
  const snap=domLiq1H[keys[keys.length-1]];if(!snap)return;
  // Separate bid and ask levels
  const bids=snap.levels.filter(l=>l.bidVol>0).sort((a,b)=>b.price-a.price);
  const asks=snap.levels.filter(l=>l.askVol>0).sort((a,b)=>a.price-b.price);
  const bidMax=Math.max(...bids.map(l=>l.bidVol),1);
  const askMax=Math.max(...asks.map(l=>l.askVol),1);
  // Draw top panel - bid liquidity (green bars going up)
  // Each column = a time snapshot, each row = price level
  const off=Math.max(0,Math.min(viewOffset,Math.max(0,total-nb)));
  const si=Math.max(0,total-nb-off);
  for(let ci=0;ci<nb;ci++){
    const c=cs[si+ci];if(!c)continue;
    const x=8+ci*colW;
    // Use per-candle snapshot if available, else latest
    const cSnap=domLiqSnaps[c.time]||snap;
    const cBids=cSnap.levels.filter(l=>l.bidVol>0).sort((a,b)=>b.bidVol-a.bidVol).slice(0,12);
    const rowH=Math.max(2,Math.floor(H/Math.max(cBids.length,1)));
    cBids.forEach((lv,ri)=>{
      const t=Math.min(1,lv.bidVol/gMax);if(t<0.03)return;
      const y=H-ri*rowH-rowH;
      let r,g,b;
      if(t<0.2){r=0;g=Math.floor(30+t*300);b=Math.floor(50+t*400);}
      else if(t<0.5){r=0;g=Math.floor(100+t*310);b=Math.floor(80+t*150);}
      else{r=Math.floor(t*100);g=Math.floor(200+t*55);b=Math.floor(t*50);}
      ctxT.fillStyle='rgba('+r+','+g+','+b+','+(0.3+t*0.6)+')';
      ctxT.fillRect(x,y,colW-1,rowH-1);
    });
  }
  // Draw bottom panel - ask liquidity (red bars going down)
  for(let ci=0;ci<nb;ci++){
    const c=cs[si+ci];if(!c)continue;
    const x=8+ci*colW;
    const cSnap=domLiqSnaps[c.time]||snap;
    const cAsks=cSnap.levels.filter(l=>l.askVol>0).sort((a,b)=>b.askVol-a.askVol).slice(0,12);
    const rowH=Math.max(2,Math.floor(H/Math.max(cAsks.length,1)));
    cAsks.forEach((lv,ri)=>{
      const t=Math.min(1,lv.askVol/gMax);if(t<0.03)return;
      const y=ri*rowH;
      let r,g,b;
      if(t<0.2){r=Math.floor(50+t*400);g=0;b=Math.floor(50+t*400);}
      else if(t<0.5){r=Math.floor(150+t*210);g=Math.floor(t*40);b=Math.floor(80+t*100);}
      else{r=Math.floor(220+t*35);g=Math.floor(t*100);b=Math.floor(t*30);}
      ctxB.fillStyle='rgba('+r+','+g+','+b+','+(0.3+t*0.6)+')';
      ctxB.fillRect(x,y,colW-1,rowH-1);
    });
  }
  // Labels
  ctxT.fillStyle='#00e67666';ctxT.font='bold 8px monospace';ctxT.textAlign='left';
  ctxT.fillText('BID DEPTH (1H DOM)',10,10);
  ctxB.fillStyle='#f4433666';ctxB.font='bold 8px monospace';ctxB.textAlign='left';
  ctxB.fillText('ASK DEPTH (1H DOM)',10,10);
}

"""
html = html.replace(old_marker, dom1h_code + old_marker)

# 4. Add update1HDomLiq call alongside updateDomLiq
html = html.replace(
    "if(inds.domliq)updateDomLiq(p);",
    "if(inds.domliq){updateDomLiq(p);update1HDomLiq(p);}"
)

# 5. Add draw1HDomPanels call in the main loop
html = html.replace(
    "if(tick%4===0)try{renderDOM();}catch(e){}",
    "if(tick%4===0){try{renderDOM();}catch(e){}if(inds.domliq)try{draw1HDomPanels();}catch(e){}}"
)

f = open('frontend/index.html', 'w', encoding='utf-8')
f.write(html)
f.close()
print("DONE! Added 1H DOM Liquidity panels above and below chart.")