"""Convierte el Google Doc oficial del speech (markdown o texto de PDF) en datos para la página Speech.
Uso: python3 speech_doc.py doc.(md|txt) salida.json"""
import re, sys, json

src, out = sys.argv[1], sys.argv[2]
raw = open(src, encoding='utf-8').read().replace('​', '').replace('\xa0', ' ')
MD = src.endswith('.md')

TYPOS = [(r'\bmanjear\b', 'manejar'), (r'\bmanajea\b', 'maneja'), (r'\bobjecion\b', 'objeción'), (r'\bco argumentos', 'con argumentos'),
         (r'\bacademico\b', 'académico'), (r'tomarioas le beneficio', '¿tomarías el beneficio'), (r'mexico,\.', 'México.'),
         (r'\bcertificacion\b', 'certificación'), (r'\bmas\b', 'más'), (r'\bq\b', 'que'), (r'\bpq\b', 'porque'), (r'\baveces\b', 'a veces'),
         (r'\brapido\b', 'rápido'), (r'\bfacil\b', 'fácil'), (r'\bdeberia\b', 'debería'), (r'\btecnicas\b', 'técnicas'),
         (r'\bopcion\b', 'opción'), (r'\bsegun\b', 'según'), (r'\bcompañia\b', 'compañía'), (r'\bdias\b', 'días'),
         (r'\bcomo estas\?', 'cómo estás?'), (r'\bcuanto tiempo\b', 'cuánto tiempo'), (r'\bcuantas\b', 'cuántas'), (r'\bcuanto puedes\b', 'cuánto puedes'),
         (r'\besta siendo\b', 'está siendo'), (r'\bestudiantes si el\b', 'estudiante; si el'), (r'\.\.', '…'), (r'acabo de paga\b', 'acabo de pagar')]

def clean(s):
    s = s.replace('\\', '')
    s = re.sub(r'\*+', '', s)
    s = re.sub(r'\s+', ' ', s).strip()
    for a, b in TYPOS: s = re.sub(a, b, s)
    return s.strip(' ​')

# --- 1) lista de "renglones lógicos": (tipo, texto) con tipo h1/h2/bullet/text
items = []
if MD:
    for ln in raw.split('\n'):
        if not ln.strip():
            items.append(('blank', '')); continue
        m = re.match(r'^(#+)\s*(.*)$', ln)
        if m: items.append(('h' + str(min(len(m.group(1)), 2)), clean(m.group(2)))); continue
        m = re.match(r'^\s*[*-]\s+(.*)$', ln)
        if m: items.append(('bullet', clean(m.group(1)))); continue
        if ln.startswith('  ') and items and items[-1][0] == 'bullet':
            items[-1] = ('bullet', items[-1][1] + ' ' + clean(ln)); continue
        if items and items[-1][0] == 'text' and not ln.startswith('|') and not items[-1][1].startswith('|') and not re.match(r'^\s*\**\s*(\d+\s|→|Nota|Asesor|Estudiante|[A-ZÁÉÍÓÚ ]{4,}\**$)', ln):
            items[-1] = ('text', items[-1][1] + ' ' + clean(ln)); continue
        items.append(('text', clean(ln)))
    items = [i for i in items if i[0] != 'blank' and i[1]]
else:
    START = re.compile(r'^\s*(\d+\s+(Sin venta · |Seguimiento · )?Asesor:|→|Nota:|Estudiante:|Asesor:|[•☐])')
    for ln in raw.split('\n'):
        if not ln.strip() or ln.strip() == 'APRENDE INSTITUTE ·': items.append(('blank', '')); continue
        s = ln.strip()
        if re.match(r'^\d+\.\s*[A-ZÁÉÍÓÚ][^.]{2,40}$', s) and not ln.startswith(' ') :
            items.append(('h2', clean(s))); continue
        if re.match(r'^(Fase \d+ · .*|A quién llamamos|Por qué lo hacemos así|Cómo va la llamada|No negociables|El speech paso a paso|En toda la llamada|Cómo leer este script|Antes de llamar.*|Antes de Activar)$', s):
            items.append(('h1', clean(s))); continue
        if s in ('QUÉ DECIR', 'QUÉ HACER', 'PREGUNTAS', 'SI EL ESTUDIANTE…', 'EVITAR'):
            items.append(('text', s)); continue
        if re.match(r'^[•☐]', s):
            items.append(('bullet', clean(s[1:]))); continue
        if START.match(ln):
            items.append(('text', clean(s))); continue
        if items and items[-1][0] in ('bullet', 'text') and items[-1][1] not in ('QUÉ DECIR', 'QUÉ HACER', 'PREGUNTAS', 'SI EL ESTUDIANTE…', 'EVITAR', ''):
            items[-1] = (items[-1][0], items[-1][1] + ' ' + clean(s)); continue
        items.append(('text', clean(s)))
    items = [i for i in items if i[0] != 'blank' and i[1]]

# --- 2) secciones
def secciones():
    out, cur = [], None
    for t, s in items:
        if t in ('h1', 'h2'):
            cur = {'lvl': t, 't': s, 'it': []}; out.append(cur)
        elif cur: cur['it'].append((t, s))
        else: out.append({'lvl': 'pre', 't': '', 'it': [(t, s)]}); cur = out[-1]
    return out
S = secciones()

def etapa(sec):
    d = {'obj': '', 'frase': '', 'hacer': [], 'preg': [], 'var': [], 'evitar': []}
    modo = None
    for t, s in sec['it']:
        if s.startswith('Objetivo:'): d['obj'] = s[9:].strip(); modo = 'obj'; continue
        k = {'QUÉ DECIR': 'frase', 'QUÉ HACER': 'hacer', 'PREGUNTAS': 'preg', 'SI EL ESTUDIANTE…': 'var', 'EVITAR': 'evitar'}.get(s)
        if k: modo = k; continue
        if modo == 'obj': d['obj'] += ' ' + s
        elif modo == 'frase': d['frase'] = (d['frase'] + ' ' + s).strip()
        elif modo == 'var':
            m = re.match(r'^([^:]{3,80}):\s*(.*)$', s)
            if m: d['var'].append([m.group(1).strip(), m.group(2).strip()])
            elif d['var']: d['var'][-1][1] += ' ' + s
        elif modo in ('hacer', 'preg', 'evitar'):
            if t == 'bullet' or not d[modo]: d[modo].append(s)
            else: d[modo][-1] += ' ' + s
    for v in d['var']:
        c = v[0]
        if '»' in c and not c.startswith('«'): c = '«' + c
        if c.count('«') > c.count('»'): c += '»'
        v[0] = c
    d['var'] = [v for v in d['var'] if v[1].strip()]
    d['frase'] = '«' + d['frase'].strip('«»“”" ') + '»' if d['frase'] else ''
    return d

res = {'ctx': '', 'stages': [], 'reglas': [], 'intro': [], 'guion': []}
pre = [s for x in S if x['lvl'] == 'pre' for t, s in x['it']]
titulo_idx = next(i for i, s in enumerate(pre) if s.startswith('Speech de ventas'))
if MD: res['ctx'] = pre[titulo_idx + 1] if len(pre) > titulo_idx + 1 else ''
else:  # en el PDF el título y el contexto quedan en el mismo renglón lógico
    res['ctx'] = re.sub(r'^Speech de ventas · \S+\s*', '', pre[titulo_idx]) + ' '.join(pre[titulo_idx + 1:])

fase_zone = False
for sec in S:
    t = sec['t']
    if re.match(r'^\d+\.\s', t) and not fase_zone:
        n, name = t.split('.', 1)
        res['stages'].append(dict(n=int(n), name=name.strip(), **etapa(sec)))
        continue
    if t.startswith('Cómo leer') or t.startswith('Antes de'): fase_zone = True
    if t in ('Cómo contactamos al estudiante:', 'A quién llamamos', 'Por qué lo hacemos así', 'Cómo va la llamada'):
        res['intro'].append({'t': t.rstrip(':'), 'l': [s for _, s in sec['it']]})
    elif t == 'En toda la llamada':
        for _, s in sec['it']:
            m = re.match(r'^([^:]{3,40}):\s*(.*)$', s)
            if m: res['reglas'].append([m.group(1).strip(), m.group(2).strip()])
            elif res['reglas']: res['reglas'][-1][1] += ' ' + s
    elif fase_zone and (t.startswith('Fase') or t.startswith('Antes de')):
        tt = re.sub(r'\s{2,}', ' · ', t) if MD else t
        lines = []
        for _, s in sec['it']:
            if MD and lines and not re.match(r'^(\d+\s|→|Nota|Asesor|Estudiante|Sin venta|Seguimiento)', s) and not t.startswith('Antes'):
                lines[-1] += ' ' + s
            else: lines.append(s)
        res['guion'].append({'t': tt, 'l': lines})

# El markdown trae "Cómo va la llamada" como tabla: | paso | descripción |
for b in res['intro']:
    rows = []
    for s in b['l']:
        if s.startswith('|'):
            cells = [c.strip() for c in s.strip('|').split('|')]
            if cells and not set(cells[0]) <= set(':- '): rows.append(' — '.join(c for c in cells if c))
        elif not MD and b['t'] == 'Cómo va la llamada':
            parts = re.split(r'\s(?=\d+\.\s?[A-ZÁÉÍÓÚ])', s)
            rows.append(parts[0])
            for x in parts[1:]:
                m = re.match(r'^(\d+\.)\s?(\S+(?: (?:real|le ha ido|académico|de objeciones))?)\s+(.*)$', x)
                rows.append(f'{m.group(1)} {m.group(2)} — {m.group(3)}' if m else x)
        else: rows.append(s)
    b['l'] = rows

json.dump(res, open(out, 'w'), ensure_ascii=False, indent=1)
print('ctx:', res['ctx'][:120])
print('etapas:', [(s['n'], s['name'], len(s['hacer']), len(s['preg']), len(s['var']), len(s['evitar']), bool(s['frase'])) for s in res['stages']])
print('reglas:', [r[0] for r in res['reglas']])
print('intro:', [(b['t'], len(b['l'])) for b in res['intro']])
print('guion:', [(g['t'], len(g['l'])) for g in res['guion']])
