"""Convierte el script final de una operación (Google Doc exportado a markdown, formato «Script de llamada · …»)
en los datos de la página Speech: ctx, reglas, intro, guion y las 13 etapas.
Uso: python3 speech_final.py script.md salida.json"""
import re, sys, json

ST = ['saludo', 'conexion', 'sondeo', 'beneficio', 'integracion', 'ejemplos', 'precio', 'cierre1', 'objeciones', 'cierre2', 'desp_v', 'desp_nv', 'seguimiento']

def clean(s):
    s = s.replace('\u200b', '').replace('\xa0', ' ').replace('\u000b', ' ')
    s = re.sub(r'\\([\[\]\.\!\+\-\*_#()>])', r'\1', s)
    s = s.replace('**', '').replace('🗣', '').replace('🔒', '')
    s = re.sub(r'(?<!\w)\*(?!\s)|(?<!\s)\*(?!\w)', '', s)
    s = re.sub(r'\s+', ' ', s).strip()
    s = re.sub(r'\.\s*\.(?!\.)', '.', s)
    s = re.sub(r'^[>*\s]+', '', s)
    return s.strip(' >')

def rows(block):
    """Filas de una tabla markdown (sin encabezado ni separador)."""
    out = []
    for ln in block:
        if not ln.startswith('|') or re.match(r'^\|\s*:?-', ln): continue
        cells = [clean(c) for c in ln.strip().strip('|').split('|')]
        out.append(cells)
    return out[1:] if out else []

def split_dot(s):
    return [x.strip(' .') + ('.' if not x.strip().endswith(('?', '»', '.')) else '') for x in re.split(r'\s·\s', s) if x.strip(' .')]

def parse(md):
    L = md.split('\n')
    title = clean(L[0])
    ctx = clean(L[1]) if len(L) > 1 else ''
    # bloques por encabezado
    secs, cur = [], None
    for ln in L[2:]:
        m = re.match(r'^(#{1,3})\s*(.*)$', ln)
        if m:
            cur = {'lvl': len(m.group(1)), 't': clean(m.group(2)), 'lines': []}; secs.append(cur); continue
        if cur is not None: cur['lines'].append(ln)
    reglas, cajas, intro, stages, guion = [], [], [], [], []
    in_stages = in_bank = in_conv = False
    bank = []
    for s in secs:
        t, lines = s['t'], s['lines']
        if s['lvl'] == 1:
            in_stages = t.startswith('3.'); in_bank = t.startswith('4.'); in_conv = t.startswith('5.')
        tabs = [ln for ln in lines if ln.startswith('|')]
        # cajas «Importante» (tabla de una celda) en cualquier parte
        for ln in tabs:
            c = clean(ln.strip().strip('|'))
            m = re.match(r'^(Importante\.\s*([^.:]+)[.:]|Cierre y alternativas\.)\s*(.*)$', c)
            if m and not in_stages:
                name = (m.group(2) or 'Cierre y alternativas').strip()
                if [name, m.group(3)] not in cajas: cajas.append([name, m.group(3)])
        if s['lvl'] == 1 and t.startswith('1.'):
            intro.append({'t': 'Palabras que usamos', 'l': [f'{a}: {b}' for a, b, *_ in rows(lines)]})
        elif t.startswith('El recorrido en una mirada'):
            intro.append({'t': 'El recorrido en una mirada: las 13 etapas', 'l': [f'{a} — {b} ({c})' for a, b, c, *_ in rows(lines)]})
        elif t == 'Qué ofrecemos':
            intro.append({'t': 'Qué ofrecemos', 'l': [' — '.join(x for x in r if x) for r in rows(lines)]})
        elif t == 'Cuándo no se ofrece':
            intro.append({'t': 'Cuándo no se ofrece', 'l': [clean(ln) for ln in lines if clean(ln)]})
        elif t == 'En toda la llamada':
            for ln in lines:
                c = clean(ln)
                if not c or c.startswith('|'): continue
                m = re.match(r'^([^:.]{2,70})[:.]\s*(.*)$', c)
                if m: reglas.append([m.group(1), m.group(2)[:1].upper() + m.group(2)[1:]])
        elif in_stages and s['lvl'] == 2:
            m = re.match(r'^(\d+)\.\s*(.*)$', t)
            if not m: continue
            st = {'key': ST[int(m.group(1)) - 1], 'name': m.group(2), 'obj': '', 'frase': '', 'hacer': [], 'preg': [], 'var': [], 'evitar': [], 'trans': []}
            says, tiempo = [], ''
            for ln in lines:
                raw = ln.strip()
                c = clean(raw)
                if not c: continue
                if raw.startswith('|'):
                    continue
                if c.startswith('Objetivo:'): st['obj'] = c[9:].strip()
                elif c.startswith('Tiempo:'): tiempo = c[7:].strip().rstrip('.')
                elif c.startswith('Datos de la ficha:'): st['hacer'].append('Antes de hablar, revisa en la ficha: ' + c[18:].strip())
                elif c.startswith('Preguntas y seguimiento:'): st['preg'] = split_dot(c[24:].strip())
                elif c.startswith('Avanzar / profundizar / detener:'): st['trans'].append(c[32:].strip())
                elif c.startswith('Errores a evitar:'): st['evitar'] = split_dot(c[17:].strip())
                elif c.startswith('Así lo dicen asesores que vendieron:'): st['hacer'].append('Así lo dicen asesores que vendieron: ' + c[36:].strip())
                elif '🗣' in raw: says.append(c)
                else: says.append(c)
            for r in rows([ln for ln in lines if ln.startswith('|')]):
                if len(r) >= 2: st['var'].append([r[0], r[1]])
                elif r and r[0].startswith('Importante'): st['hacer'].append(r[0])
            imp = [clean(ln.strip().strip('|')) for ln in lines if ln.startswith('|') and clean(ln.strip().strip('|')).startswith('Importante')]
            st['hacer'] = [x for x in st['hacer'] if not x.startswith('Importante')] + imp
            if says:
                st['frase'] = says[0]
                st['hacer'] = ['Di: ' + x for x in says[1:]] + st['hacer']
            if tiempo: st['obj'] = (st['obj'] + f' Tiempo: {tiempo}.').strip()
            stages.append(st)
        elif in_bank and s['lvl'] == 1:
            bank.append({'t': 'Banco de objeciones · cómo se trabajan', 'l': [clean(ln) for ln in lines if clean(ln) and not ln.startswith('|')]})
        elif in_bank and s['lvl'] == 3:
            l = []
            for ln in lines:
                c = clean(ln)
                if not c or ln.startswith('|'): continue
                l.append(c)
            for r in rows([ln for ln in lines if ln.startswith('|')]):
                if len(r) >= 2: l.append(f'→ {r[0]}: {r[1]}')
            bank.append({'t': 'Objeción ' + t, 'l': l})
        elif s['lvl'] == 1 and t.startswith('Recursos permitidos'):
            bank.append({'t': 'Recursos permitidos (opcionales)', 'l': [f'→ {a}: {b}' for a, b, *_ in rows(lines)]})
        elif s['lvl'] == 1 and t.startswith('Lo que nunca se dice'):
            bank.append({'t': 'Lo que nunca se dice, y qué decir en su lugar', 'l': [f'→ Nunca: {a} En su lugar: {b}' for a, b, *_ in rows(lines)]})
        elif s['lvl'] == 1 and t.startswith('¿Esto vale en mi estado'):
            bank.append({'t': t, 'l': [f'→ {a}: {b} Qué no se dice: {c}' for a, b, c, *_ in rows(lines)]})
        elif in_conv and s['lvl'] == 3:
            l = []
            for ln in lines:
                c = clean(ln)
                if not c: continue
                c = re.sub(r'^(Coordinador\(a\)|Coordinadora|Coordinador):', 'Asesor:', c)
                l.append(c)
            guion.append({'t': 'Conversación de ejemplo · ' + re.sub(r'^\d+\.\s*', '', t), 'l': l})
    assert len(stages) == 13, (len(stages), [s['name'] for s in stages])
    return {'titulo': title, 'ctx': ctx, 'reglas': reglas + cajas, 'intro': intro + bank, 'guion': guion, 'stages': stages}

if __name__ == '__main__':
    d = parse(open(sys.argv[1], encoding='utf-8').read())
    json.dump(d, open(sys.argv[2], 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(d['titulo'], '| reglas', len(d['reglas']), '| intro', len(d['intro']), '| guion', len(d['guion']), '| etapas', len(d['stages']))
