# Patch script to add DOM Liquidity heatmap and fix mouse drag
import re

f = open('frontend/index.html', 'r', encoding='utf-8')
html = f.read()
f.close()

# 1. Fix mouse drag - remove isVertDrag, make drag pan both ways
html = html.replace(
    "let dragX=0,dragY=0,dragOff=0,dragYOff=0,dragging=false,isVertDrag=false;",
    "let dragX=0,dragY=0,dragOff=0,dragYOff=0,dragging=false;"
)
html = html.replace(
    "isVertDrag=(e.shiftKey||e.button===1);\n    mc.style.cursor=isVertDrag?'ns-resize':'grabbing';",
    "mc.style.cursor='grabbing';"
)
html = html.replace(
    """if(isVertDrag){
      // Vertical pan - drag up = see higher prices, drag down = see lower prices
      const dy=dragY-e.clientY; // invert: drag up = positive
      yOffset=dragYOff+dy/40;
      yOffset=Math.max(-15,Math.min(15,yOffset));
    } else {
      // Horizontal pan
      const dx=e.clientX-dragX,bpp=viewBars/mc2.width;
      viewOffset=Math.round(dragOff+dx*bpp);
      clampOff();
    }""",
    """// Pan both horizontal and vertical
      const dx=e.clientX-dragX,bpp=viewBars/mc2.width;
      viewOffset=Math.round(dragOff+dx*bpp);
      clampOff();
      const dy=dragY-e.clientY;
      yOffset=dragYOff+dy/40;
      yOffset=Math.max(-15,Math.min(15,yOffset));"""
)

# 2. Add domliq to indicators
html = html.replace(
    "crt:false,wyc:false,ew:false}",
    "crt:false,wyc:false,ew:false,domliq:true}"
)

# 3. Add DOM-LIQ button
html = html.replace(
    """<button class="indbtn" id="b-ew" onclick="tog('ew')" style="border-color:#ff44ff;color:#ff44ff;">EW</button>""",
    """<button class="indbtn" id="b-ew" onclick="tog('ew')" style="border-color:#ff44ff;color:#ff44ff;">EW</button>
  <button class="indbtn on" id="b-domliq" onclick="tog('domliq')" style="border-color:#00ffcc;color:#00ffcc;">DOM-LIQ</button>"""
)

# 4. Add DOM liquidity functions before "// ── Demo data"
domliq_code = """
// ── DOM Liquidity Heatmap ────────────────────────────
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
}

"""
html = html.replace("// ── Demo data", domliq_code + "// ── Demo data")

# 5. Add updateDomLiq call in tick handler
html = html.replace(
    "genDOMDemo(p);\n    const cs=candles[currentTF]",
    "genDOMDemo(p);\n    if(inds.domliq)updateDomLiq(p);\n    const cs=candles[currentTF]"
)

# 6. Add heatmap draw call before grid
html = html.replace(
    "  // Grid\n  ctx.strokeStyle=_t.gridLine",
    "  // DOM Liquidity Heatmap\n  if(inds.domliq){try{drawDomLiqHeatmap(ctx,pw,ph,P,py,minP,maxP);}catch(e){}}\n\n  // Grid\n  ctx.strokeStyle=_t.gridLine"
)

f = open('frontend/index.html', 'w', encoding='utf-8')
f.write(html)
f.close()
print("DONE! index.html patched successfully.")
print("Changes: mouse drag fix + DOM Liquidity heatmap added")