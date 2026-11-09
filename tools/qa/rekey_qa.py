"""Tablero de Calidad: guion final, sin datos de tarjeta y con la misma clave que los demás tableros.
- Actualiza GUIONES con los scripts finales (salida de speech_final.py) en la página del mes en curso.
- Oculta números sensibles en todas las citas de la página y en todas las transcripciones (.enc).
- Vuelve a cifrar páginas y transcripciones con la clave nueva; la página pide la clave igual que los demás
  tableros (sin distinguir mayúsculas) y comparte la sesión con ellos.
Uso: OLD_PW=... NEW_PW=... python3 rekey_qa.py <repo> <dir_scripts_json>"""
import os, sys, json, glob, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from crypt import descifrar, cifrar, reemplazar_blob, _key
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import redact

REPO, DOCS = sys.argv[1], sys.argv[2]
OLD, NEW = os.environ['OLD_PW'], os.environ['NEW_PW']
NEWN = NEW.lower().replace(' ', '')
OPS = {'Upsell': 'upsell', 'Recurrence': 'recurrence', 'Bootcamp': 'bootcamp', 'Resurrection': 'resurrection'}

def dec_bytes(b, pw): return AESGCM(_key(pw, b[:16], 150000)).decrypt(b[16:28], b[28:], None)
def enc_bytes(t, pw):
    salt, iv = os.urandom(16), os.urandom(12)
    return salt + iv + AESGCM(_key(pw, salt, 150000)).encrypt(iv, t, None)

def consts(h):
    for m in re.finditer(r'const ([A-Z_]{2,})=(?=[\[{"])', h):
        yield m.group(1), m.end()

def limpiar_pagina(h, actualizar_guion):
    n_cambios = 0
    for name, i in list(consts(h)):
        i = h.index('const %s=' % name) + len('const %s=' % name)
        try: o, n = json.JSONDecoder().raw_decode(h[i:])
        except ValueError: continue
        nuevo = o
        if name == 'GUIONES' and actualizar_guion:
            for op, k in OPS.items():
                d = json.load(open(os.path.join(DOCS, k + '.json'), encoding='utf-8'))
                g = nuevo[op]
                for s, f in zip(g['stages'], d['stages']):
                    assert s['key'] == f['key']
                    for c in ('obj', 'frase', 'hacer', 'preg', 'var', 'evitar', 'trans'): s[c] = f[c]
                g['ctx'] = d['ctx']; g['reglas'] = d['reglas']; g['pendientes'] = []
                g['version'] = 'Versión 3 · noviembre 2026 · script final de la operación'
        elif name != 'GUIONES':
            nuevo = redact.ocultar_json(o)
        s = json.dumps(nuevo, ensure_ascii=False).replace('</', '<\\/')
        if s != json.dumps(o, ensure_ascii=False).replace('</', '<\\/'): n_cambios += 1
        h = h[:i] + s + h[i + n:]
    h = h.replace("sessionStorage.getItem('qa_pw')", "sessionStorage.getItem('sp_pw')")
    return h, n_cambios

def envoltorio(html):
    """Misma forma de pedir la clave que los demás tableros: sin distinguir mayúsculas y sesión compartida (sp_pw)."""
    a = "async function dec(pw){"
    assert a in html
    html = html.replace(a, "const norm=s=>s.toLowerCase().replace(/\\s+/g,'');\n" + a, 1)
    html = html.replace("sessionStorage.setItem('qa_pw',pw)", "sessionStorage.setItem('sp_pw',pw)")
    html = html.replace("sessionStorage.removeItem('qa_pw')", "sessionStorage.removeItem('sp_pw')")
    html = html.replace("sessionStorage.getItem('qa_pw')", "sessionStorage.getItem('sp_pw')")
    html = html.replace("go(document.getElementById('p').value)", "go(norm(document.getElementById('p').value))")
    html = html.replace('Ingresa la contraseña.', 'Ingresa la clave.').replace('Contraseña incorrecta.', 'Clave incorrecta.')
    return html

for f, guion in (('calidad-llamadas.html', True), ('calidad-llamadas-2026-09.html', False)):
    p = os.path.join(REPO, f)
    outer = open(p, encoding='utf-8').read()
    plain = descifrar(outer, OLD)
    plain, n = limpiar_pagina(plain, guion)
    outer = envoltorio(reemplazar_blob(outer, cifrar(plain, NEWN)))
    assert descifrar(outer, NEWN) == plain
    open(p, 'w', encoding='utf-8').write(outer)
    print(f, 'constantes con cambios:', n, '| guion final:', guion)

tot = 0
for f in sorted(glob.glob(os.path.join(REPO, 'data', '**', '*.enc'), recursive=True)):
    b = open(f, 'rb').read()
    t = dec_bytes(b, OLD).decode('utf-8')
    o = json.loads(t)
    a = json.dumps(o, ensure_ascii=False)
    o2 = {k: (redact.ocultar_transcripcion(v) if isinstance(v, list) else redact.ocultar_json(v)) for k, v in o.items()} if isinstance(o, dict) else redact.ocultar_json(o)
    t2 = json.dumps(o2, ensure_ascii=False)
    cambios = t2.count(redact.OCULTO)
    tot += cambios
    nb = enc_bytes(t2.encode('utf-8'), NEWN)
    assert dec_bytes(nb, NEWN).decode('utf-8') == t2
    open(f, 'wb').write(nb)
    print(os.path.relpath(f, REPO), 'fragmentos ocultados:', cambios)
print('total fragmentos ocultados en transcripciones:', tot)
