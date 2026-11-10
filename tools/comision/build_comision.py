"""Arma la página Comisión Líderes (plana) a partir de la plantilla.
- Toma el endpoint y el token del Web App de la página de Control descifrada (no se imprimen).
- Incrusta una copia del esquema del mes (snapshot JSON) para cuando la acción comlideres aún no está publicada.
Uso: python3 build_comision.py control_plano.html snapshot.json salida_plana.html"""
import json, re, sys
ctl, snap, dst = sys.argv[1:4]
h = open(ctl, encoding='utf-8').read()
ep = re.search(r"WFM_ENDPOINT\s*=\s*['\"]([^'\"]+)", h).group(1)
tk = re.search(r"WFM_TOKEN\s*=\s*['\"]([^'\"]+)", h).group(1)
tpl = open(__file__.replace('build_comision.py', 'comision_template.html'), encoding='utf-8').read()
s = json.dumps(json.load(open(snap, encoding='utf-8')), ensure_ascii=False).replace('</', '<\\/')
out = tpl.replace('__WFM_ENDPOINT__', ep).replace('__WFM_TOKEN__', tk).replace('__SNAP__', s)
open(dst, 'w', encoding='utf-8').write(out)
print('ok', dst, len(out))
