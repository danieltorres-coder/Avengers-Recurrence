"""Actualiza la página Calidad Post-Sales · QA (versión descifrada) sin rehacer el diseño:
- datos (META, CALLS, QUO, EJS) desde una salida nueva de build_qa.py, con datos sensibles ocultos;
- textos de la plantilla (RK, GSI) desde qa_template.html;
- GUIONES con los scripts finales (JSON de speech_final.py) y la regla de pago vigente (regla_pago.py).
Uso: python3 actualizar_qa.py plano_actual.html salida_build_qa.html <dir_scripts_json> plano_nuevo.html"""
import json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import redact, regla_pago

cur, nuevo, DOCS, dst = sys.argv[1:5]
h = open(cur, encoding='utf-8').read()
b = open(nuevo, encoding='utf-8').read()
tpl = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'qa_template.html'), encoding='utf-8').read()
OPS = {'Upsell': 'upsell', 'Recurrence': 'recurrence', 'Bootcamp': 'bootcamp', 'Resurrection': 'resurrection'}

def const(src, name):
    k = 'const %s=' % name
    i = src.index(k) + len(k)
    o, n = json.JSONDecoder().raw_decode(src[i:])
    return o, i, n

def poner(h, name, o):
    _, i, n = const(h, name)
    return h[:i] + json.dumps(o, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/') + h[i + n:]

for name in ('META', 'CALLS', 'QUO', 'EJS'):
    o, _, _ = const(b, name)
    h = poner(h, name, o if name == 'META' else redact.ocultar_json(o))

for name in ('RK', 'GSI'):   # una línea cada una en la plantilla
    l = re.search(r'^const %s=.*;$' % name, tpl, re.M).group(0)
    h = re.sub(r'^const %s=.*;$' % name, lambda m: l, h, count=1, flags=re.M)

G, _, _ = const(h, 'GUIONES')
for op, k in OPS.items():
    d = json.load(open(os.path.join(DOCS, k + '.json'), encoding='utf-8'))
    for s, f in zip(G[op]['stages'], d['stages']):
        assert s['key'] == f['key']
        for c in ('obj', 'frase', 'hacer', 'preg', 'var', 'evitar', 'trans'): s[c] = f[c]
    G[op]['ctx'] = d['ctx']; G[op]['reglas'] = d['reglas']
h = poner(h, 'GUIONES', G)
h, n = regla_pago.aplicar(h)
open(dst, 'w', encoding='utf-8').write(h)
print('ok', dst, '| textos con la regla de pago:', n)
