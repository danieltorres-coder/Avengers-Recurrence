"""Quita de una página (Speech) los ejemplos de llamadas que hablan de datos de tarjeta y oculta números sensibles.
Revisa las constantes JSON de la página (LIB, G, OB, PROD). Un ejemplo es un objeto con «q» (asesor) y «r» o «ag».
Uso: python3 limpiar_tarjeta.py plano_in.html plano_out.html"""
import json, re, sys, unicodedata, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import guia, redact

norm = lambda s: ''.join(c for c in unicodedata.normalize('NFD', (s or '').lower()) if unicodedata.category(c) != 'Mn')
TARJ = re.compile(r'numero de (la |tu |su |mi )?tarjeta|tarjeta[^.?]{0,30}numero|datos de (la |tu |su |mi )?tarjeta|codigo de seguridad|numero de seguridad'
                  r'|\bcvv\b|\bcvc\b|digitos|••••|vencimiento|caducidad|guardar (la )?informacion de pago|recibir los datos')

def es_tarjeta(o):
    t = norm((o.get('q') or '') + ' ' + (o.get('r') or '') + ' ' + (o.get('cli') or '') + ' ' + (o.get('ase') or ''))
    return bool(TARJ.search(t) or (guia.RX_TARJ.search(t) and not guia.RX_TARJ_NO.search(t)))

def filtrar(x, cont):
    if isinstance(x, list):
        out = []
        for v in x:
            if isinstance(v, dict) and (('q' in v and ('r' in v or 'ag' in v)) or ('ase' in v and 'cli' in v)) and es_tarjeta(v):
                cont[0] += 1; continue
            out.append(filtrar(v, cont))
        return out
    if isinstance(x, dict): return {k: filtrar(v, cont) for k, v in x.items()}
    return x

def limpiar(h):
    total = 0
    for name in ('LIB', 'G', 'OB', 'PROD'):
        k = 'const %s=' % name
        if k not in h: continue
        i = h.index(k) + len(k)
        o, n = json.JSONDecoder().raw_decode(h[i:])
        cont = [0]
        o = redact.ocultar_json(filtrar(o, cont))
        total += cont[0]
        h = h[:i] + json.dumps(o, ensure_ascii=False).replace('</', '<\\/') + h[i + n:]
    return h, total

if __name__ == '__main__':
    h, n = limpiar(open(sys.argv[1], encoding='utf-8').read())
    open(sys.argv[2], 'w', encoding='utf-8').write(h)
    print('ejemplos quitados:', n)
