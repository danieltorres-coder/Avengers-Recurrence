"""Arma la página Calidad Post-Sales · QA (versión mensual) a partir de la salida del motor.
Uso: python3 -I build_qa.py <dir_qa> <salida.html>"""
import json, sys, collections, datetime
D, dst = sys.argv[1], sys.argv[2]
d = json.load(open(D + '/out/calls.json', encoding='utf-8'))
quo = json.load(open(D + '/out/quo.json', encoding='utf-8'))
ej = json.load(open(D + '/out/ej.json', encoding='utf-8'))
vp = json.load(open(D + '/out/venta_prob.json', encoding='utf-8'))['rep']
h = open(D + '/dec/calidad_new.html', encoding='utf-8').read()
i = h.index('const GUIONES=') + 14
GUIONES, _ = json.JSONDecoder().raw_decode(h[i:])
for g in GUIONES.values(): g.pop('vol', None)

OPS = ['Upsell', 'Recurrence', 'Bootcamp', 'Resurrection']
PRODS = sorted({r[8] for r in d['rows'] if r[8]})
OBJ = ['Dinero', 'Tiempo', 'Pensarlo / consultar', 'Más tarde', 'Otro pago / sorpresa', 'No le interesa']
CH = ['opcional', 'complemento', 'memb', 'link', 'oferta_temprana', 'memb_any']
c = lambda v: '-' if v is None else str(v)
rows = []
for r in d['rows']:
    rows.append([r[0], r[1], OPS.index(r[2]), r[3], r[4], r[5], r[6], r[7], PRODS.index(r[8]) if r[8] else -1, r[9], r[10],
                 ''.join(c(x) for x in r[11]), [OBJ.index(o) for o in r[12]], sorted(r[13]), ''.join(c(r[14].get(k)) for k in CH), r[15], r[16], r[17]])
meses = collections.defaultdict(list)
for r in d['rows']: meses[r[1][:7]].append(r[1])
MESES = {m: dict(desde=min(v), hasta=max(v), n=len(v)) for m, v in sorted(meses.items())}
# archivos de transcripción (cifrados) por mes · operación · turno
TXF = {}
for r in d['rows']:
    m, op, t = r[1][:7], r[2], r[3]
    k = f'{m}|{op}|{t}'
    if k in TXF: continue
    if m == '2026-09': TXF[k] = 'data/transcripciones_' + (f'upsell_{t.lower()}' if op == 'Upsell' else op.lower()) + '.enc'
    else: TXF[k] = f'data/qa/{m}_{op.lower()}' + (f"_{t.lower().replace(' ', '_')}" if t else '') + '.enc'
# citas por etapa (ventas) y ancla: 12 por etapa para no inflar la página
EJS = {k: {s: v[:12] for s, v in val.items() if s.startswith('st_') or s == 'rk_ancla'} for k, val in ej.items()}
META = dict(generado=datetime.date.today().isoformat(), meses=MESES, ops=OPS, prods=PRODS, obj=OBJ, ch=CH, txf=TXF,
            vp={k: {x: round(v[x], 3) for x in ('acc', 'prec', 'rec', 'n')} for k, v in vp.items()})
data = ('const META=' + json.dumps(META, ensure_ascii=False) + ';\nconst CALLS=' + json.dumps(rows, ensure_ascii=False, separators=(',', ':')) +
        ';\nconst QUO=' + json.dumps(quo, ensure_ascii=False, separators=(',', ':')) + ';\nconst EJS=' + json.dumps(EJS, ensure_ascii=False, separators=(',', ':')) +
        ';\nconst GUIONES=' + json.dumps(GUIONES, ensure_ascii=False, separators=(',', ':')) + ';\n')
tpl = open(D + '/qa_template.html', encoding='utf-8').read()
out = tpl.replace('/*__DATA__*/', data)
open(dst, 'w', encoding='utf-8').write(out)
print('ok', dst, len(out), MESES)
