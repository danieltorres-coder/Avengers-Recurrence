"""Mete el speech oficial (salida de speech_doc.py) en la página Speech descifrada y la vuelve a cifrar.
Uso: python3 inject_speech.py dec/speech_x.html doc.json ../../repo/speech/x.html clave"""
import json, re, sys
sys.path.insert(0, __file__.rsplit('/', 1)[0])
from crypt import cifrar, reemplazar_blob

dec, docj, dst, pw = sys.argv[1:5]
h = open(dec, encoding='utf-8').read()
doc = json.load(open(docj, encoding='utf-8'))
i = h.index('const G=') + 8
G, n = json.JSONDecoder().raw_decode(h[i:])
assert len(G['stages']) == len(doc['stages']) == 13
for s, d in zip(G['stages'], doc['stages']):
    for k in ('obj', 'frase', 'hacer', 'preg', 'var', 'evitar'):
        s[k] = d[k]
    s.pop('trans', None)  # el doc oficial no trae transiciones
G['ctx'] = doc['ctx']
G['reglas'] = doc['reglas']
G['intro'] = doc['intro']
G['guion'] = [dict(b, t=re.sub(r'\s+(Etapas? |Cierre$)', r' — \1', b['t'])) for b in doc['guion']]
for b in G['intro']:
    b['l'] = [y.strip() for x in b['l'] for y in re.split(r'\s(?=Forma \d)', x) if y.strip()]
G['version'] = 'Versión 2 · octubre 2026 · speech oficial de la operación; la pestaña de llamadas se actualiza cada mes'
h = h[:i] + json.dumps(G, ensure_ascii=False) + h[i + n:]

if 'id="sec_guion"' not in h:
    css = ('.gui{display:flex;flex-direction:column;gap:8px}.gui details{background:var(--surface);border:1px solid var(--line);border-radius:8px;padding:10px 14px}'
           '.gui summary{cursor:pointer;font-weight:600}.gui ol{list-style:none;padding:0;margin:8px 0 0;display:flex;flex-direction:column;gap:6px}'
           '.gui li{font-size:14px;line-height:1.45}.gui li.si{padding-left:18px;color:var(--muted)}.gui li.nt{font-style:italic;color:var(--muted)}'
           '.gui li.es{font-style:italic}.gui li b{font-weight:600}\n')
    h = h.replace('</style>', css + '</style>', 1)
    sec = ('<section id="sec_guion"><span class="eyebrow">Guion oficial</span><h2>Script de la llamada, línea por línea</h2>'
           '<p class="small muted">Es el mismo documento oficial de la operación. Ábrelo por fases; las 13 etapas de arriba son el resumen que revisa calidad.</p>'
           '<div class="gui" id="gui"></div></section>\n')
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

open(dec.replace('.html', '_new.html'), 'w', encoding='utf-8').write(h)
out = open(dst, encoding='utf-8').read()
open(dst, 'w', encoding='utf-8').write(reemplazar_blob(out, cifrar(h, pw)))
print('ok', dst, len(h))
