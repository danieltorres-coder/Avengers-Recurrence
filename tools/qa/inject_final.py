"""Mete el script final (salida de speech_final.py) en una página Speech descifrada y escribe la versión plana.
Conserva lo que sale de las llamadas (ejemplos, datos, volumen). Agrega la sección «Guion oficial» si no existe.
Uso: python3 inject_final.py speech_plano.html final.json salida_plana.html"""
import json, sys

src, docj, dst = sys.argv[1:4]
h = open(src, encoding='utf-8').read()
doc = json.load(open(docj, encoding='utf-8'))
i = h.index('const G=') + 8
G, n = json.JSONDecoder().raw_decode(h[i:])
assert len(G['stages']) == len(doc['stages']) == 13
for s, d in zip(G['stages'], doc['stages']):
    assert s['key'] == d['key'], (s['key'], d['key'])
    for k in ('name', 'obj', 'frase', 'hacer', 'preg', 'var', 'evitar', 'trans'):
        s[k] = d[k]
G['ctx'] = doc['ctx']
G['reglas'] = doc['reglas']
G['intro'] = doc['intro']
G['guion'] = doc['guion']
G['version'] = 'Versión 3 · noviembre 2026 · script final de la operación; la pestaña de llamadas se actualiza cada mes'
h = h[:i] + json.dumps(G, ensure_ascii=False) + h[i + n:]

if 'id="sec_guion"' not in h:
    css = ('.gui{display:flex;flex-direction:column;gap:8px}.gui details{background:var(--surface);border:1px solid var(--line);border-radius:8px;padding:10px 14px}'
           '.gui summary{cursor:pointer;font-weight:600}.gui ol{list-style:none;padding:0;margin:8px 0 0;display:flex;flex-direction:column;gap:6px}'
           '.gui li{font-size:14px;line-height:1.45}.gui li.si{padding-left:18px;color:var(--muted)}.gui li.nt{font-style:italic;color:var(--muted)}'
           '.gui li.es{font-style:italic}.gui li b{font-weight:600}\n')
    h = h.replace('</style>', css + '</style>', 1)
    sec = ('<section id="sec_guion"><span class="eyebrow">Guion oficial</span><h2>Script de la llamada</h2>'
           '<p class="small muted">Es el script final de la operación: palabras clave, qué ofrecemos, banco de objeciones, lo que nunca se dice y conversaciones de ejemplo. Las 13 etapas de arriba son lo que revisa calidad.</p>'
           '<div class="gui" id="gui"></div></section>\n')
    assert '<nav class="stg" id="nav"' in h
    h = h.replace('<nav class="stg" id="nav"', sec + '<nav class="stg" id="nav"', 1)
    js = r"""
const gl=s=>{const e=esc(s).replace(/^(\d+\s+(?:Sin venta · |Seguimiento · )?Asesor:|Asesor:|→ [^:]{1,90}:|Nota:|Estudiante:)/,'<b>$1</b>');return e};
const gc=s=>/^→/.test(s)?'si':/^Nota:/.test(s)?'nt':/^Estudiante:/.test(s)?'es':'';
$('gui').innerHTML=(G.intro||[]).map(b=>`<details><summary>${esc(b.t)}</summary><ol>${b.l.map(x=>`<li>${esc(x)}</li>`).join('')}</ol></details>`).join('')
 +(G.guion||[]).map(b=>`<details><summary>${esc(b.t)}</summary><ol>${b.l.map(x=>`<li class="${gc(x)}">${gl(x)}</li>`).join('')}</ol></details>`).join('');
$('sec_guion').hidden=!((G.intro||[]).length||(G.guion||[]).length);
"""
    anchor = "$('nav').innerHTML="
    assert anchor in h
    h = h.replace(anchor, js.strip() + '\n' + anchor, 1)
open(dst, 'w', encoding='utf-8').write(h)
print('ok', dst, len(h))
