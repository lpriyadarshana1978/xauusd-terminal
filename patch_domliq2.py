# Patch: upgrade DOM Liquidity to time-based heatmap (ATAS style)
f = open('frontend/index.html', 'r', encoding='utf-8')
html = f.read()
f.close()

# Replace the old DOM Liquidity functions with time-based version
old_domliq = """// ── DOM Liquidity Heatmap ────────────────────────────
let domLiqHistory=[];
const DOM_LIQ_MAX=80;
let domLiqLast=0;
function updateDomLiq(price){
  const now=Date.now();if(now-domLiqLast<500)return;domLiqLast=now;
  const step=0.10,levels=[];
  for(let i=-30;i<=30;i++){
    const p=Math.round((price+i*step)*100)/100,dist=Math.abs(i);
    const base=Math.max(50,800-dist*20+Math.random()*200);
    const isRound=(p%1<0.05||p%1>0.95),isHalf=(Math.abs(p%1-0.5)<0.05);
    const cluster=isRound?base*2.5:isHalf?base*1.6:base;
    if(i<0)levels.push({price:p,bidVol:Math.floor(cluster),askVol:0});
    else if(i>0)levels.push({price:p,bidVol:0,askVol:Math.floor(cluster)});
    else levels.push({price:p,bidVol:Math.floor(200+Math.random()*100),askVol:Math.floor(200+Math.random()*100)});
  }
  domLiqHistory.push({levels});
  if(domLiqHistory.length>DOM_LIQ_MAX)domLiqHistory.shift();
}
function drawDomLiqHeatmap(ctx,pw,ph,P,py,minP,maxP){
  if(!domLiqHistory.length)return;
  const snap=domLiqHistory[domLiqHistory.length-1];if(!snap)return;
  const maxVol=Math.max(...snap.levels.map(l=>Math.max(l.bidVol,l.askVol)));
  if(maxVol<=0)return;
  snap.levels.forEach(lv=>{
    if(lv.price<minP||lv.price>maxP)return;
    const y=py(lv.price),bandH=Math.max(2,Math.abs(py(lv.price)-py(lv.price+0.10)));
    if(lv.bidVol>0){const int=Math.min(1,lv.bidVol/maxVol),a=0.06+int*0.35;ctx.fillStyle='rgba(0,'+(100+Math.floor(int*155))+','+(80+Math.floor(int*100))+','+a+')';ctx.fillRect(P.l,y-bandH/2,pw,bandH);if(int>0.6){ctx.fillStyle='rgba(0,255,200,'+(int*0.15)+')';ctx.fillRect(P.l,y-1,pw,2);}}
    if(lv.askVol>0){const int=Math.min(1,lv.askVol/maxVol),a=0.06+int*0.35;ctx.fillStyle='rgba('+(150+Math.floor(int*105))+','+(20+Math.floor(int*30))+','+(40+Math.floor(int*60))+','+a+')';ctx.fillRect(P.l,y-bandH/2,pw,bandH);if(int>0.6){ctx.fillStyle='rgba(255,50,80,'+(int*0.15)+')';ctx.fillRect(P.l,y-1,pw,2);}}
  });
  ctx.fillStyle='#00ffcc88';ctx.font='bold 9px monospace';ctx.textAlign='right';
  ctx.fillText('Live DOM Liquidity',P.l+pw-4,P.t+12);
  let tB=0,tA=0;snap.levels.forEach(l=>{tB+=l.bidVol;tA+=l.askVol;});
  ctx.fillStyle='#00e67688';ctx.textAlign='left';ctx.fillText('LIQ: '+(tB/1000).toFixed(1)+'K',P.l+4,ph+P.t-4);
  ctx.fillStyle='#f4433688';ctx.textAlign='right';ctx.fillText('LIQ: '+(tA/1000).toFixed(1)+'K',P.l+pw-4,ph+P.t-4);
  // Near DOM Power
  const nB=snap.levels.filter(l=>l.bidVol>0).slice(-5).reduce((s,l)=>s+l.bidVol,0);
  const nA=snap.levels.filter(l=>l.askVol>0).slice(0,5).reduce((s,l)=>s+l.askVol,0);
  const nT=nB+nA||1,bP=Math.round(nB/nT*100),aP=100-bP;
  const bx=P.l+pw-180,by=P.t+18,bW=168,bH=8;
  ctx.fillStyle='#00000066';ctx.fillRect(bx,by,176,30);
  ctx.fillStyle='#ffffff55';ctx.font='bold 7px monospace';ctx.textAlign='center';
  ctx.fillText('NEAR DOM POWER',bx+88,by+8);
  const bidW=Math.floor(bW*bP/100);
  ctx.fillStyle='#00e676';ctx.fillRect(bx+4,by+11,bidW,bH);
  ctx.fillStyle='#f44336';ctx.fillRect(bx+4+bidW,by+11,bW-bidW,bH);
  ctx.font='bold 8px monospace';
  ctx.fillStyle='#00e676';ctx.textAlign='left';ctx.fillText(bP+'%',bx+4,by+28);
  ctx.fillStyle='#f44336';ctx.textAlign='right';ctx.fillText(aP+'%',bx+172,by+28);
}"""

new_domliq = """// ── DOM Liquidity Heatmap (Time-Based ATAS Style) ────
let domLiqSnaps={};  // key=barTime -> {levels:[{price,bidVol,askVol}]}
let domLiqLast=0;
let domLiqGlobalMax=500;
function updateDomLiq(price){
  const now=Date.now();if(now-domLiqLast<400)return;domLiqLast=now;
  // Get current bar time
  const cs=candles[currentTF];if(!cs||!cs.length)return;
  const barTime=cs[cs.length-1].time||Math.floor(now/1000);
  const step=0.10,levels=[];
  for(let i=-35;i<=35;i++){
    const p=Math.round((price+i*step)*100)/100,dist=Math.abs(i);
    const base=Math.max(30,700-dist*16+Math.random()*250);
    const isRound=(p%1<0.05||p%1>0.95),isHalf=(Math.abs(p%1-0.5)<0.05);
    const isFive=(p%5<0.1||p%5>4.9);
    const cluster=isFive?base*3.5:isRound?base*2.5:isHalf?base*1.6:base;
    if(i<0)levels.push({price:p,bidVol:Math.floor(cluster),askVol:0});
    else if(i>0)levels.push({price:p,bidVol:0,askVol:Math.floor(cluster)});
    else levels.push({price:p,bidVol:Math.floor(180+Math.random()*120),askVol:Math.floor(180+Math.random()*120)});
  }
  // Blend with previous snap for smoother transitions
  const prev=domLiqSnaps[barTime];
  if(prev){
    levels.forEach((lv,idx)=>{
      const pl=prev.levels.find(l=>Math.abs(l.price-lv.price)<0.01);
      if(pl){lv.bidVol=Math.floor(pl.bidVol*0.7+lv.bidVol*0.3);lv.askVol=Math.floor(pl.askVol*0.7+lv.askVol*0.3);}
    });
  }
  domLiqSnaps[barTime]={levels,price};
  // Track global max for consistent coloring
  const allMax=Math.max(...levels.map(l=>Math.max(l.bidVol,l.askVol)));
  domLiqGlobalMax=Math.floor(domLiqGlobalMax*0.99+allMax*0.01);
  // Cleanup old snapshots (keep last 300)
  const keys=Object.keys(domLiqSnaps);
  if(keys.length>300){keys.sort((a,b)=>a-b);for(let k=0;k<keys.length-300;k++)delete domLiqSnaps[keys[k]];}
}
function drawDomLiqHeatmap(ctx,vc,vn,pw,ph,P,py,bw,minP,maxP){
  if(!Object.keys(domLiqSnaps).length)return;
  const colW=Math.max(3,Math.floor(pw/vn));
  const gMax=Math.max(domLiqGlobalMax,500);
  // Draw per-candle columns
  vc.forEach((c,i)=>{
    const snap=domLiqSnaps[c.time];if(!snap)return;
    const x=P.l+i*colW;
    snap.levels.forEach(lv=>{
      if(lv.price<minP||lv.price>maxP)return;
      const y=py(lv.price);
      const bandH=Math.max(2,Math.abs(py(lv.price)-py(lv.price+0.10)));
      if(lv.bidVol>0){
        const int=Math.min(1,lv.bidVol/gMax);
        if(int<0.05)return;
        // Color: dark blue -> cyan -> green -> bright green/yellow
        let r,g,b;
        if(int<0.3){r=0;g=Math.floor(40+int*200);b=Math.floor(80+int*300);}
        else if(int<0.6){r=0;g=Math.floor(100+int*255);b=Math.floor(120+int*100);}
        else{r=Math.floor(int*80);g=Math.floor(200+int*55);b=Math.floor(50+int*50);}
        const a=0.15+int*0.55;
        ctx.fillStyle='rgba('+r+','+g+','+b+','+a+')';
        ctx.fillRect(x,y-bandH/2,colW-1,bandH);
      }
      if(lv.askVol>0){
        const int=Math.min(1,lv.askVol/gMax);
        if(int<0.05)return;
        // Color: dark purple -> magenta -> red -> bright red/yellow
        let r,g,b;
        if(int<0.3){r=Math.floor(60+int*200);g=0;b=Math.floor(80+int*200);}
        else if(int<0.6){r=Math.floor(180+int*120);g=Math.floor(int*40);b=Math.floor(60+int*80);}
        else{r=Math.floor(220+int*35);g=Math.floor(int*100);b=Math.floor(int*30);}
        const a=0.15+int*0.55;
        ctx.fillStyle='rgba('+r+','+g+','+b+','+a+')';
        ctx.fillRect(x,y-bandH/2,colW-1,bandH);
      }
    });
  });
  // Labels
  ctx.fillStyle='#00ffcc99';ctx.font='bold 9px monospace';ctx.textAlign='right';
  ctx.fillText('Live DOM Liquidity',P.l+pw-4,P.t+12);
  // Total liquidity
  const lastSnap=domLiqSnaps[vc[vc.length-1]?.time];
  if(lastSnap){
    let tB=0,tA=0;lastSnap.levels.forEach(l=>{tB+=l.bidVol;tA+=l.askVol;});
    ctx.fillStyle='#00e67688';ctx.textAlign='left';ctx.fillText('LIQ: '+(tB/1000).toFixed(1)+'K',P.l+4,ph+P.t-4);
    ctx.fillStyle='#f4433688';ctx.textAlign='right';ctx.fillText('LIQ: '+(tA/1000).toFixed(1)+'K',P.l+pw-4,ph+P.t-4);
    // Near DOM Power
    const nB=lastSnap.levels.filter(l=>l.bidVol>0).slice(-5).reduce((s,l)=>s+l.bidVol,0);
    const nA=lastSnap.levels.filter(l=>l.askVol>0).slice(0,5).reduce((s,l)=>s+l.askVol,0);
    const nT=nB+nA||1,bPct=Math.round(nB/nT*100),aPct=100-bPct;
    const bx=P.l+pw-180,by=P.t+18,bW=168,bH=8;
    ctx.fillStyle='#00000077';ctx.fillRect(bx,by,176,30);
    ctx.strokeStyle='#ffffff15';ctx.lineWidth=1;ctx.strokeRect(bx,by,176,30);
    ctx.fillStyle='#ffffff66';ctx.font='bold 7px monospace';ctx.textAlign='center';
    ctx.fillText('NEAR DOM POWER \\u00B10.5%',bx+88,by+8);
    const bidW2=Math.floor(bW*bPct/100);
    ctx.fillStyle='#00e676';ctx.fillRect(bx+4,by+12,bidW2,bH);
    ctx.fillStyle='#f44336';ctx.fillRect(bx+4+bidW2,by+12,bW-bidW2,bH);
    ctx.font='bold 8px monospace';
    ctx.fillStyle='#00e676';ctx.textAlign='left';ctx.fillText((nB/1000).toFixed(1)+'K  '+bPct+'%',bx+4,by+28);
    ctx.fillStyle='#f44336';ctx.textAlign='right';ctx.fillText(aPct+'%  '+(nA/1000).toFixed(1)+'K',bx+172,by+28);
  }
}"""

if old_domliq in html:
    html = html.replace(old_domliq, new_domliq)
    # Update draw call to pass vc and vn
    html = html.replace(
        "drawDomLiqHeatmap(ctx,pw,ph,P,py,minP,maxP)",
        "drawDomLiqHeatmap(ctx,vc,vn,pw,ph,P,py,bw,minP,maxP)"
    )
    f = open('frontend/index.html', 'w', encoding='utf-8')
    f.write(html)
    f.close()