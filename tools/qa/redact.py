"""Oculta datos sensibles que se dictan en una llamada (tarjeta, código de seguridad, vencimiento, teléfonos).
Se usa en todo texto de llamadas que se muestra en las páginas: citas, ejemplos y transcripciones."""
import re

_DIG = r'(?:\d[\s,.\-/]{0,3}){8,}\d'               # 9+ dígitos con separadores: tarjeta, teléfono, cuenta
_RX_LARGO = re.compile(_DIG)
_RX_GRUPOS = re.compile(r'\b\d{4}(?:[\s,.\-]+(?:y\s+)?\d{4}){2,}\b')   # «2691, 0834 y 0419»
_RX_CVV = re.compile(r'(c[oó]digo (?:de )?(?:seguridad|verificaci[oó]n|cvv|cvc)|\bcvv\b|\bcvc\b|los (?:tres|3) (?:n[uú]meros |d[ií]gitos )?de atr[aá]s)([^.!]{0,40}?)(\b\d{3,4}\b)', re.I)
_RX_VENCE = re.compile(r'((?:fecha de )?(?:vencimiento|caducidad|expiraci[oó]n|vence)[^.!]{0,30}?)(\b(?:cero\s*)?\d{1,2}\s*(?:/|del?)\s*\d{2,4}\b)', re.I)
_PAL = r'(?:cero|uno|una|dos|tres|cuatro|cinco|seis|siete|ocho|nueve)'
_RX_PALABRAS = re.compile(r'\b' + _PAL + r'(?:[\s,]+' + _PAL + r'\b){7,}', re.I)   # 8+ dígitos dictados en palabras
_RX_TARJ_NUM = re.compile(r'((?:n[uú]mero de (?:la )?tarjeta|tarjeta (?:termina|terminada) en|los (?:4|cuatro) [uú]ltimos)[^.?!]{0,25}?)(\b\d{4}\b)', re.I)

OCULTO = '[dato oculto]'

def ocultar(t, ctx=True):
    """ctx=False: solo patrones claros (para texto redactado por nosotros: guion, datos, escenarios)."""
    if not t or not isinstance(t, str): return t
    t = _RX_GRUPOS.sub(OCULTO, t)
    t = _RX_LARGO.sub(OCULTO, t)
    t = _RX_PALABRAS.sub(OCULTO, t)
    t = _RX_TARJ_NUM.sub(lambda m: m.group(1) + OCULTO, t)
    t = _RX_CVV.sub(lambda m: m.group(1) + m.group(2) + OCULTO, t)
    t = _RX_VENCE.sub(lambda m: m.group(1) + OCULTO, t)
    if ctx and CTX_TARJETA.search(_n(t)): t = _ocultar_cifras(t)
    return t

import unicodedata as _ud
_n = lambda s: ''.join(c for c in _ud.normalize('NFD', s.lower()) if _ud.category(c) != 'Mn')
CTX_TARJETA = re.compile(r'tarjeta|vencimiento|caducidad|\bcvv\b|\bcvc\b|\bcbc\b|codigo de seguridad|numero de seguridad|los (?:tres|3) de atras|mes y (?:el )?ano')
_RX_NUM_CTX = re.compile(r'\b\d[\d\s,.\-/]*\d\b|\b\d\b(?!\s*(?:usd|dolar|d[oó]lares|%|por ciento))', re.I)
_PRECIO = re.compile(r'^\s*(?:usd|dolar|d[oó]lares|%|por ciento|mensual|al mes|pagos?|cuotas?|meses|clases|sesiones|horas)', re.I)

def _ocultar_cifras(t):
    out, last = [], 0
    for m in re.finditer(r'\d[\d\s,.\-/]*\d|\d', t):
        if _PRECIO.match(t[m.end():m.end() + 14]): continue
        out.append(t[last:m.start()]); out.append(OCULTO); last = m.end()
    out.append(t[last:]); return ''.join(out)

def ocultar_transcripcion(lineas):
    """Lista de turnos [seg, quien, texto]: oculta datos sensibles y, cerca de donde se habla de la tarjeta
    (dos turnos antes y después), todas las cifras que no sean precios."""
    textos = [l[2] if isinstance(l, list) and len(l) > 2 and isinstance(l[2], str) else None for l in lineas]
    cerca = set()
    for i, t in enumerate(textos):
        if t and CTX_TARJETA.search(_n(t)): cerca.update(range(i - 2, i + 3))
    out = []
    for i, l in enumerate(lineas):
        t = textos[i]
        if t is None: out.append(l); continue
        t = ocultar(t)
        if i in cerca: t = _ocultar_cifras(t)
        out.append(l[:2] + [t] + l[3:])
    return out

_SOLO_ID = re.compile(r'^\d{6,}$')
_TEXTO = re.compile(r'[A-Za-zÁÉÍÓÚáéíóúñÑ]{2,}\s+\S')   # solo texto hablado (no códigos internos como «10000010---00»)

# Texto redactado (no dicho en una llamada): no se ocultan cifras por contexto, solo patrones claros de tarjeta.
_REDACTADO = {'dato', 'base', 'esc', 'obj', 'frase', 'hacer', 'preg', 'var', 'evitar', 'trans', 'name', 't', 'l'}

def ocultar_json(o, clave=None):
    """Aplica ocultar() a todas las cadenas de una estructura JSON (no toca ids de llamada)."""
    if isinstance(o, str): return o if (clave == 'id' or not _TEXTO.search(o)) else ocultar(o, clave not in _REDACTADO)
    if isinstance(o, list): return [ocultar_json(x, clave) for x in o]
    if isinstance(o, dict): return {k: ocultar_json(v, k) for k, v in o.items()}
    return o

if __name__ == '__main__':
    for s in ['Sí, 2691, 0834 y 0419. Sí, así es', 'la fecha de vencimiento es el cero 3 del 30', '¿Y el código de seguridad? 512',
              'mi número es 305 555 1234', 'Recuerda que son 25 USD al mes desde el 15 de octubre', 'cuatro cinco uno dos tres cuatro cinco seis siete',
              'Vale 450 dolares en 3 pagos de 150', 'el número de tarjeta termina en 4421', 'pago de 1300 USD', 'tu acceso vence el 15 de octubre', 'vence el 03/30', 'tu plan vence el 15 de 2027']:
        print(repr(s), '->', repr(ocultar(s)))
