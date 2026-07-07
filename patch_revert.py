# Revert: Remove the top/bottom DOM panels, keep main chart DOM liquidity
f = open('frontend/index.html', 'r', encoding='utf-8')
html = f.read()
f.close()

# 1. Remove the extra canvases
html = html.replace(
    '''<canvas id="domTop" style="display:block;height:45px;background:#050510;border-bottom:1px solid #1a1a28;"></canvas>
      <canvas id="mc" style="display:block;"></canvas>
      <canvas id="domBot" style="display:block;height:45px;background:#050510;border-top:1px solid #1a1a28;"></canvas>''',
    '<canvas id="mc" style="display:block;"></canvas>'
)

# 2. Fix resize height
html = html.replace(
    "const usedH=30+22+20+50+72+62+90; // topbar+statsbar+timeaxis+cvd+stats+mtf+domliq panels",
    "const usedH=30+22+20+50+72+62; // topbar+statsbar+timeaxis+cvd+stats+mtf"
)

# 3. Remove extra canvas sizing
html = html.replace(
    """  const dt=$('domTop');if(dt){dt.width=W;dt.height=45;}
  const db=$('domBot');if(db){db.width=W;db.height=45;}""",
    ""
)

# 4. Remove update1HDomLiq call
html = html.replace(
    "if(inds.domliq){updateDomLiq(p);update1HDomLiq(p);}",
    "if(inds.domliq)updateDomLiq(p);"
)

# 5. Remove draw1HDomPanels call
html = html.replace(
    "if(tick%4===0){try{renderDOM();}catch(e){}if(inds.domliq)try{draw1HDomPanels();}catch(e){}}",
    "if(tick%4===0)try{renderDOM();}catch(e){}"
)

f = open('frontend/index.html', 'w', encoding='utf-8')
f.write(html)
f.close()
print("DONE! Removed top/bottom panels. Main chart DOM liquidity heatmap is still there.")