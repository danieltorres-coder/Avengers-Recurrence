"""Regenera la pestaña «Llamadas que funcionan» (const LIB) de cada página Speech con todos los meses del motor QA.
Uso: python3 -I build_lib.py <dir_qa> <dir_repo>"""
import json, sys, collections, os
D, REPO = sys.argv[1], sys.argv[2]
sys.path.insert(0, D)
from crypt import descifrar, cifrar, reemplazar_blob
d = json.load(open(D + '/out/calls.json', encoding='utf-8'))
ej = json.load(open(D + '/out/ej.json', encoding='utf-8'))
ST = d['ST']
POST = {'precio', 'cierre1', 'cierre2', 'desp_v', 'desp_nv'}
PW = os.environ['SPEECH_PW']  # clave del Speech, normalizada (minúsculas, sin espacios)

def pc(a, b): return round(100 * a / b) if b else None

def lift_adj(L, i):
    """Diferencia de venta (pts) entre hacer y no hacer la etapa, comparando dentro de tercios de duración."""
    ap = [r for r in L if r[11][i] is not None and r[6] != 'I']
    if len(ap) < 40: return None
    ds = sorted(r[10] for r in ap); cortes = [ds[len(ds) // 3], ds[2 * len(ds) // 3]]
    tot, w = 0, 0
    for g in range(3):
        G = [r for r in ap if (g == 0 and r[10] <= cortes[0]) or (g == 1 and cortes[0] < r[10] <= cortes[1]) or (g == 2 and r[10] > cortes[1])]
        si = [r for r in G if r[11][i]]; no = [r for r in G if not r[11][i]]
        if len(si) < 5 or len(no) < 5: continue
        dif = 100 * sum(r[6] == 'V' for r in si) / len(si) - 100 * sum(r[6] == 'V' for r in no) / len(no)
        tot += dif * len(G); w += len(G)
    return round(tot / w, 1) if w else None

def bloque(L, meses, op):
    ok = [r for r in L if r[6] != 'I']
    V = [r for r in ok if r[6] == 'V']; N = [r for r in ok if r[6] == 'N']
    stages = []
    for i, k in enumerate(ST):
        v = [r for r in V if r[11][i] is not None]; n = [r for r in N if r[11][i] is not None]
        stages.append(dict(k=k, pv=pc(sum(r[11][i] for r in v), len(v)), pn=pc(sum(r[11][i] for r in n), len(n)),
                           adj=None if k in POST else lift_adj(L, i), post=k in POST, nv=len(v), nn=len(n)))
    ejs = collections.defaultdict(list)
    for m in meses:
        for k in ST:
            for x in ej.get(f'{m}|{op}', {}).get('st_' + k, []):
                ejs[k].append(dict(id=x['id'], f=x['f'], t=x['t'], ag=x['ag'], q=x['q'], r=x.get('r', '')))
    ejs = {k: v[:25] for k, v in ejs.items() if v}
    # llamadas modelo: ventas con más etapas cumplidas que tienen frases guardadas
    por_id = collections.defaultdict(list)
    for k, v in ejs.items():
        for x in v: por_id[x['id']].append((k, x))
    byid = {r[0]: r for r in V}
    cand = []
    for cid, xs in por_id.items():
        r = byid.get(cid)
        if not r or len(xs) < 3: continue
        ap = [x for x in r[11] if x is not None]
        cand.append((round(100 * sum(ap) / len(ap)), len(xs), r, xs))
    cand.sort(key=lambda t: (-t[0], -t[1]))
    vistos, modelo = set(), []
    for cu, _, r, xs in cand:
        if r[5] in vistos: continue
        vistos.add(r[5])
        modelo.append(dict(id=r[0], f=r[1], t=r[3], ag=r[5], d=r[10], cu=cu, st=[k for k, x in zip(ST, r[11]) if x],
                           ex=[dict(k=k, q=x['q']) for k, x in sorted(xs, key=lambda t: ST.index(t[0]))][:4]))
        if len(modelo) >= 6: break
    return dict(n=len(L), ventas=len(V), stages=stages, ej=ejs, modelo=modelo, acciones=[])

FUENTE = {'upsell': 'dec/speech_upsell_new.html', 'recurrence': 'dec/speech_recurrence_new.html',
          'bootcamp': 'dec/speech_bootcamp.html', 'resurrection': 'dec/speech_resurrection.html'}
for op_l, f in FUENTE.items():
    op = op_l.capitalize()
    h = open(os.path.join(D, f), encoding='utf-8').read()
    i = h.index('const G=') + 8
    G, _ = json.JSONDecoder().raw_decode(h[i:])
    assert [s['key'] for s in G['stages']] == ST, op
    rows = [r for r in d['rows'] if r[2] == op]
    meses = sorted({r[1][:7] for r in rows})
    LIB = {m: bloque([r for r in rows if r[1][:7] == m], [m], op) for m in meses}
    LIB['todos'] = bloque(rows, meses, op)
    i = h.index('const LIB=') + 10
    _, n = json.JSONDecoder().raw_decode(h[i:])
    h = h[:i] + json.dumps(LIB, ensure_ascii=False) + h[i + n:]
    open(os.path.join(D, f.replace('.html', '_lib.html')), 'w', encoding='utf-8').write(h)
    dst = os.path.join(REPO, 'speech', op_l + '.html')
    out = open(dst, encoding='utf-8').read()
    assert descifrar(out, PW)  # la clave actual abre la página
    open(dst, 'w', encoding='utf-8').write(reemplazar_blob(out, cifrar(h, PW)))
    print(op, {m: (b['n'], b['ventas']) for m, b in LIB.items()}, 'modelo', len(LIB['todos']['modelo']))
