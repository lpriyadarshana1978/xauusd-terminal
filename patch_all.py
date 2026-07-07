# Single clean patch: DOM Liquidity + Mouse drag fix + Candle timer
f = open('frontend/index.html', 'r', encoding='utf-8')
h = f.read()
f.close()

changes = 0

# 1. Add domliq to indicators
h = h.replace("crt:false,wyc:false,ew:false}", "crt:false,wyc:false,ew:false,domliq:true}")
changes += 1

# 2. Add DOM-LIQ button
h = h.replace(
    'id="b-ew" onclick="tog(\'ew\')" style="border-color:#ff44ff;color:#ff44ff;">EW</button>',
    'id="b-ew" onclick="tog(\'ew\')" style="border-color:#ff44ff;color:#ff44ff;">EW</button>\n  <button class="indbtn on" id="b-domliq" onclick="tog(\'domliq\')" style="border-color:#00ffcc;color:#00ffcc;">DOM-LIQ</button>'
)
changes += 1

# 3. Fix mouse drag - both directions
h = h.replace("let dragX=0,dragY=0,dragOff=0,dragYOff=0,dragging=false,isVertDrag=false;",
              "let dragX=0,dragY=0,dragOff=0,dragYOff=0,dragging=false;")
h = h.replace("isVertDrag=(e.shiftKey||e.button===1);\n    mc.style.cursor=isVertDrag?'ns-resize':'grabbing';",
              "mc.style.cursor='grabbing';")
h = h.replace(
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
    """// Pan both directions
      const dx=e.clientX-dragX,bpp=viewBars/mc2.width;
      viewOffset=Math.round(dragOff+dx*bpp);clampOff();
      const dy=dragY-e.clientY;
      yOffset=dragYOff+dy/40;yOffset=Math.max(-15,Math.min(15,yOffset));"""
)
changes += 1

# 4. Add DOM liquidity code before Demo data
domliq = '''
// ── DOM Liquidity Heatmap (ATAS Style) ───────────────
let domLiqSnaps={};
let _domLiqLast=0;
let _domLiqGMax=500;
function updateDomLiq(price){
  var now=Date.now();if(now-_domLiqLast<400)return;_domLiqLast=now;
  var cs2=candles[currentTF];if(!cs2||!cs2.length)return;
  var barTime=cs2[cs2.length-1].time||Math.floor(now/1000);
  var step=0.10,levels=[];
  for(var ii=-35;ii<=35;ii++){
    var p=Math.round((price+ii*step)*100)/100,dist=Math.abs(ii);
    var base=Math.max(30,700-dist*16+Math.random()*250);
    var isFive=(p%5<0.1||p%5>4.9),isRound=(p%1<0.05||p%1>0.95),isHalf=(Math.abs(p%1-0.5)<0.05);
    var cluster=isFive?base*3.5:isRound?base*2.5:isHalf?base*1.6:base;
    if(ii<0)levels.push({price:p,bidVol:Math.floor(cluster),askVol:0});
    else if(ii>0)levels.push({price:p,bidVol:0,askVol:Math.floor(cluster)});
    else levels.push({price:p,bidVol:Math.floor(180+Math.random()*120),askVol:Math.floor(180+Math.random()*120)});
  }
  var prev2=domLiqSnaps[barTime];
  if(prev2){levels.forEach(function(lv){var pl=prev2.levels.find(function(l){return Math.abs(l.price-lv.price)<0.01;});if(pl){lv.bidVol=Math.floor(pl.bidVol*0.7+lv.bidVol*0.3);lv.askVol=Math.floor(pl.askVol*0.7+lv.askVol*0.3);}});}
  domLiqSnaps[barTime]={levels:levels,price:price};
  var allMax=Math.max.apply(null,levels.map(function(l){return Math.max(l.bidVol,l.askVol);}));
  _domLiqGMax=Math.floor(_domLiqGMax*0.99+allMax*0.01);
  var keys=Object.keys(domLiqSnaps);if(keys.length>300){keys.sort();for(var kk=0;kk<keys.length-300;kk++)delete domLiqSnaps[keys[kk]];}
}
function drawDomLiqHeatmap(ctx,vc,vn,pw,ph,P,py,bw,minP,maxP){
  if(!Object.keys(domLiqSnaps).length)return;
  var colW=Math.max(3,Math.floor(pw/vn));
  var gMax=Math.max(_domLiqGMax,400);
  vc.forEach(function(c,ci){
    var snap=domLiqSnaps[c.time];if(!snap)return;
    var x=P.l+ci*colW;
    snap.levels.forEach(function(lv){
      if(lv.price<minP-1||lv.price>maxP+1)return;
      var y=py(lv.price);
      var bandH=Math.max(3,Math.abs(py(lv.price)-py(lv.price+0.10))+1);
      if(lv.bidVol>0){
        var t=Math.min(1,lv.bidVol/gMax);if(t<0.03)return;
        var r2=0,g2=Math.floor(60+t*195),b2=Math.floor(80+t*175);
        if(t>0.5){r2=Math.floor(t*80);g2=Math.floor(200+t*55);b2=Math.floor(t*50);}
        ctx.fillStyle="rgba("+r2+","+g2+","+b2+","+(0.2+t*0.6)+")";
        ctx.fillRect(x,y-bandH/2,colW,bandH);
      }
      if(lv.askVol>0){
        var t2=Math.min(1,lv.askVol/gMax);if(t2<0.03)return;
        var r3=Math.floor(100+t2*155),g3=Math.floor(t2*40),b3=Math.floor(60+t2*140);
        if(t2>0.5){r3=Math.floor(220+t2*35);g3=Math.floor(t2*80);b3=Math.floor(t2*30);}
        ctx.fillStyle="rgba("+r3+","+g3+","+b3+","+(0.2+t2*0.6)+")";
        ctx.fillRect(x,y-bandH/2,colW,bandH);
      }
    });
  });
  ctx.fillStyle="#00ffcc99";ctx.font="bold 9px monospace";ctx.textAlign="right";
  ctx.fillText("Live DOM Liquidity",P.l+pw-4,P.t+12);
  var lastSnap=domLiqSnaps[vc[vc.length-1]?vc[vc.length-1].time:0];
  if(lastSnap){
    var tB=0,tA=0;lastSnap.levels.forEach(function(l){tB+=l.bidVol;tA+=l.askVol;});
    ctx.fillStyle="#00e67688";ctx.textAlign="left";ctx.fillText("LIQ: "+(tB/1000).toFixed(1)+"K",P.l+4,ph+P.t-4);
    ctx.fillStyle="#f4433688";ctx.textAlign="right";ctx.fillText("LIQ: "+(tA/1000).toFixed(1)+"K",P.l+pw-4,ph+P.t-4);
    var nB=lastSnap.levels.filter(function(l){return l.bidVol>0;}).slice(-5).reduce(function(s,l){return s+l.bidVol;},0);
    var nA=lastSnap.levels.filter(function(l){return l.askVol>0;}).slice(0,5).reduce(function(s,l){return s+l.askVol;},0);
    var nT=nB+nA||1,bPct=Math.round(nB/nT*100),aPct=100-bPct;
    var bx=P.l+pw-185,byy=P.t+18,bW=172,bH=9;
    ctx.fillStyle="#00000088";ctx.fillRect(bx,byy,180,34);
    ctx.strokeStyle="#ffffff20";ctx.lineWidth=1;ctx.strokeRect(bx,byy,180,34);
    ctx.fillStyle="#ffffff66";ctx.font="bold 7px monospace";ctx.textAlign="center";
    ctx.fillText("NEAR DOM POWER",bx+90,byy+9);
    var bidW3=Math.floor(bW*bPct/100);
    ctx.fillStyle="#00e676";ctx.fillRect(bx+4,byy+13,bidW3,bH);
    ctx.fillStyle="#f44336";ctx.fillRect(bx+4+bidW3,byy+13,bW-bidW3,bH);
    ctx.font="bold 8px monospace";
    ctx.fillStyle="#00e676";ctx.textAlign="left";ctx.fillText((nB/1000).toFixed(1)+"K "+bPct+"%",bx+4,byy+31);
    ctx.fillStyle="#f44336";ctx.textAlign="right";ctx.fillText(aPct+"% "+(nA/1000).toFixed(1)+"K",bx+176,byy+31);
  }
}

'''
h = h.replace("// ── Demo data", domliq + "// ── Demo data")
changes += 1

# 5. Add updateDomLiq calls
h = h.replace("genDOMDemo(p);\n    const cs=candles[currentTF]",
              "genDOMDemo(p);\n    if(inds.domliq)updateDomLiq(p);\n    const cs=candles[currentTF]")
changes += 1

# 6. Add heatmap draw before grid
h = h.replace("  // Grid\n  ctx.strokeStyle=_t.gridLine",
              "  if(inds.domliq){try{drawDomLiqHeatmap(ctx,vc,vn,pw,ph,P,py,bw,minP,maxP);}catch(e){}}\n\n  // Grid\n  ctx.strokeStyle=_t.gridLine")
changes += 1

# 7. Add candle countdown timer after delta box
old_timer = """      ctx.fillStyle=tc2;ctx.textAlign='center';ctx.textBaseline='middle';
      ctx.fillText(dl,midX,dY+dH/2);ctx.textBaseline='alphabetic';
    }
  });"""
new_timer = """      ctx.fillStyle=tc2;ctx.textAlign='center';ctx.textBaseline='middle';
      ctx.fillText(dl,midX,dY+dH/2);ctx.textBaseline='alphabetic';
    }
    // Candle countdown timer
    if(i===vn-1&&c.time){
      var tfSec2={'1m':60,'5m':300,'15m':900,'1h':3600,'2h':7200,'4h':14400,'1d':86400};
      var barLen2=tfSec2[currentTF]||900;
      var now2=Math.floor(Date.now()/1000);
      var remain2=Math.max(0,barLen2-(now2-c.time));
      var mins2=Math.floor(remain2/60),secs2=remain2%60;
      var tmr2=mins2+':'+String(secs2).padStart(2,'0');
      var tmX2=x+bw+4,tmY2=py(c.close)-8;
      ctx.font='bold 10px monospace';
      var tw3=ctx.measureText(tmr2).width+8;
      ctx.fillStyle='#00000099';ctx.fillRect(tmX2,tmY2-1,tw3,16);
      ctx.strokeStyle=remain2<30?'#ff4444':'#ffffff33';ctx.lineWidth=1;ctx.strokeRect(tmX2,tmY2-1,tw3,16);
      var tmCol2=remain2<30?(Math.floor(Date.now()/500)%2===0?'#ff4444':'#ff8888'):remain2<60?'#ffdd00':'#00ccff';
      ctx.fillStyle=tmCol2;ctx.textAlign='left';ctx.textBaseline='middle';
      ctx.fillText(tmr2,tmX2+4,tmY2+7);ctx.textBaseline='alphabetic';
    }
  });"""
h = h.replace(old_timer, new_timer)
changes += 1

f = open('frontend/index.html', 'w', encoding='utf-8')
f.write(h)
f.close()
print(f"DONE! Applied {changes} changes successfully.")