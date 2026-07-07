# Patch: Add candle countdown timer next to the running candle
f = open('frontend/index.html', 'r', encoding='utf-8')
html = f.read()
f.close()

# Add timer drawing after the delta box section, inside the candle loop
# Find the closing of the delta box section
old_delta_end = """      ctx.fillStyle=tc2;ctx.textAlign='center';ctx.textBaseline='middle';
      ctx.fillText(dl,midX,dY+dH/2);ctx.textBaseline='alphabetic';
    }
  });"""

new_delta_end = """      ctx.fillStyle=tc2;ctx.textAlign='center';ctx.textBaseline='middle';
      ctx.fillText(dl,midX,dY+dH/2);ctx.textBaseline='alphabetic';
    }

    // Candle countdown timer on last candle
    if(i===vn-1&&c.time){
      const tfSec={'1m':60,'5m':300,'15m':900,'1h':3600,'2h':7200,'4h':14400,'1d':86400};
      const barLen=tfSec[currentTF]||900;
      const now=Math.floor(Date.now()/1000);
      const elapsed=now-c.time;
      const remain=Math.max(0,barLen-elapsed);
      const mins=Math.floor(remain/60);
      const secs=remain%60;
      const tmr=mins+':'+String(secs).padStart(2,'0');
      // Draw timer background
      const tmX=x+bw+4,tmY=py(c.close)-8;
      ctx.fillStyle='#000000aa';
      const tmW=ctx.measureText(tmr).width||30;
      ctx.font='bold 10px monospace';
      const tw2=ctx.measureText(tmr).width+8;
      ctx.fillStyle='#00000099';ctx.fillRect(tmX,tmY-1,tw2,16);
      ctx.strokeStyle=remain<30?'#ff4444':'#ffffff33';ctx.lineWidth=1;ctx.strokeRect(tmX,tmY-1,tw2,16);
      // Timer text - flash red when <30s
      const tmCol=remain<30?(Math.floor(Date.now()/500)%2===0?'#ff4444':'#ff8888'):remain<60?'#ffdd00':'#00ccff';
      ctx.fillStyle=tmCol;ctx.font='bold 10px monospace';ctx.textAlign='left';ctx.textBaseline='middle';
      ctx.fillText(tmr,tmX+4,tmY+7);
      ctx.textBaseline='alphabetic';
    }
  });"""

if old_delta_end in html:
    html = html.replace(old_delta_end, new_delta_end)
    f = open('frontend/index.html', 'w', encoding='utf-8')
    f.write(html)
    f.close()
    print("DONE! Candle countdown timer added.")
else:
    print("ERROR: Could not find delta box section.")