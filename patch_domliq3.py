# Patch: Make DOM Liquidity thicker, more vivid, ATAS-style with right-side profile
f = open('frontend/index.html', 'r', encoding='utf-8')
html = f.read()
f.close()

# Find and replace the drawDomLiqHeatmap function
old_draw = "function drawDomLiqHeatmap(ctx,vc,vn,pw,ph,P,py,bw,minP,maxP){"
if old_draw not in html:
    print("ERROR: Cannot find drawDomLiqHeatmap function")
    exit()

# Find the end of the function (next function definition)
start = html.index(old_draw)
# Find closing brace by counting braces
depth = 0
i = start
found_end = -1
for i in range(start, len(html)):
    if html[i] == '{':
        depth += 1
    elif html[i] == '}':
        depth -= 1
        if depth == 0:
            found_end = i + 1
            break

old_func = html[start:found_end]

new_func = """function drawDomLiqHeatmap(ctx,vc,vn,pw,ph,P,py,bw,minP,maxP){
  if(!Object.keys(domLiqSnaps).length)return;
  const colW=Math.max(3,Math.floor(pw/vn));
  const gMax=Math.max(domLiqGlobalMax,400);
  const step=0.10;
  const priceStep=Math.max(step,((maxP-minP)/120));
  // Draw thick heatmap columns per candle
  vc.forEach((c,ci)=>{
    const snap=domLiqSnaps[c.time];if(!snap)return;
    const x=P.l+ci*colW;
    snap.levels.forEach(lv=>{
      if(lv.price<minP-1||lv.price>maxP+1)return;
      const y=py(lv.price);
      const bandH=Math.max(3,Math.abs(py(lv.price)-py(lv.price+priceStep))+1);
      if(lv.bidVol>0){
        const t=Math.min(1,lv.bidVol/gMax);if(t<0.03)return;
        let r,g,b;
        if(t<0.15){r=0;g=Math.floor(20+t*200);b=Math.floor(60+t*400);}
        else if(t<0.35){r=0;g=Math.floor(60+t*400);b=Math.floor(120+t*200);}
        else if(t<0.6){r=0;g=Math.floor(150+t*170);b=Math.floor(100+t*100);}
        else{r=Math.floor(t*120);g=Math.floor(220+t*35);b=Math.floor(t*60);}
        ctx.fillStyle='rgba('+r+','+g+','+b+','+(0.25+t*0.65)+')';
        ctx.fillRect(x,y-bandH/2,colW,bandH);
      }
      if(lv.askVol>0){
        const t=Math.min(1,lv.askVol/gMax);if(t<0.03)return;
        let r,g,b;
        if(t<0.15){r=Math.floor(40+t*300);g=0;b=Math.floor(60+t*400);}
        else if(t<0.35){r=Math.floor(120+t*300);g=0;b=Math.floor(100+t*200);}
        else if(t<0.6){r=Math.floor(200+t*55);g=Math.floor(t*50);b=Math.floor(80+t*80);}
        else{r=Math.floor(230+t*25);g=Math.floor(t*130);b=Math.floor(t*40);}
        ctx.fillStyle='rgba('+r+','+g+','+b+','+(0.25+t*0.65)+')';
        ctx.fillRect(x,y-bandH/2,colW,bandH);
      }
    });
  });
  // Right-side volume profile bars
  const lastSnap=domLiqSnaps[vc[vc.length-1]?.time];
  if(lastSnap){
    const profX=P.l+pw+2,profW=56;
    const pMax=Math.max(...lastSnap.levels.map(l=>Math.max(l.bidVol,l.askVol)),1);
    lastSnap.levels.forEach(lv=>{
      if(lv.price<minP||lv.price>maxP)return;
      const y=py(lv.price);
      const bandH=Math.max(2,Math.abs(py(lv.price)-py(lv.price+priceStep)));
      if(lv.bidVol>0){
        const w=Math.floor(profW*(lv.bidVol/pMax));
        ctx.fillStyle='rgba(0,200,120,0.5)';
        ctx.fillRect(profX,y-bandH/2,w,bandH-1);
      }
      if(lv.askVol>0){
        const w=Math.floor(profW*(lv.askVol/pMax));
        ctx.fillStyle='rgba(220,40,60,0.5)';
        ctx.fillRect(profX,y-bandH/2,w,bandH-1);
      }
    });
  }
  // Labels
  ctx.fillStyle='#00ffccaa';ctx.font='bold 9px monospace';ctx.textAlign='right';
  ctx.fillText('Live DOM Liquidity',P.l+pw-4,P.t+12);
  if(lastSnap){
    let tB=0,tA=0;lastSnap.levels.forEach(l=>{tB+=l.bidVol;tA+=l.askVol;});
    ctx.fillStyle='#00e67699';ctx.textAlign='left';ctx.fillText('LIQ: '+(tB/1000).toFixed(1)+'K',P.l+4,ph+P.t-4);
    ctx.fillStyle='#f4433699';ctx.textAlign='right';ctx.fillText('LIQ: '+(tA/1000).toFixed(1)+'K',P.l+pw-4,ph+P.t-4);
    const nB=lastSnap.levels.filter(l=>l.bidVol>0).slice(-5).reduce((s,l)=>s+l.bidVol,0);
    const nA=lastSnap.levels.filter(l=>l.askVol>0).slice(0,5).reduce((s,l)=>s+l.askVol,0);
    const nT=nB+nA||1,bPct=Math.round(nB/nT*100),aPct=100-bPct;
    const bx=P.l+pw-185,by=P.t+18,bW=172,bH=9;
    ctx.fillStyle='#00000088';ctx.fillRect(bx,by,180,34);
    ctx.strokeStyle='#ffffff20';ctx.lineWidth=1;ctx.strokeRect(bx,by,180,34);
    ctx.fillStyle='#ffffff66';ctx.font='bold 7px monospace';ctx.textAlign='center';
    ctx.fillText('NEAR DOM POWER \\u00B10.5%',bx+90,by+9);
    const bidW2=Math.floor(bW*bPct/100);
    ctx.fillStyle='#00e676';ctx.fillRect(bx+4,by+13,bidW2,bH);
    ctx.fillStyle='#f44336';ctx.fillRect(bx+4+bidW2,by+13,bW-bidW2,bH);
    ctx.font='bold 8px monospace';
    ctx.fillStyle='#00e676';ctx.textAlign='left';ctx.fillText((nB/1000).toFixed(1)+'K  '+bPct+'%',bx+4,by+31);
    ctx.fillStyle='#f44336';ctx.textAlign='right';ctx.fillText(aPct+'%  '+(nA/1000).toFixed(1)+'K',bx+176,by+31);
  }
}"""

html = html[:start] + new_func + html[found_end:]

f = open('frontend/index.html', 'w', encoding='utf-8')
f.write(html)
f.close()
print("DONE! DOM Liquidity upgraded to thick ATAS-style with volume profile.")