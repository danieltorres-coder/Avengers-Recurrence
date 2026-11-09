"""Etapa 11 (despedida para venta) con la regla de pago de noviembre 2026, igual en las 4 operaciones.
Aplica sobre el JSON de speech_final.py, antes de inject_final.py.
Uso: python3 etapa11_pago.py guion.json"""
import json, re, sys

PASA = ('«Revisa tus mensajes: el banco te pide aceptar la compra. Una vez la aceptes, volvemos a ingresar los datos». '
        'Si no llega, enviamos otro link. Si el pago sigue sin completarse, le preguntas si requiere ayuda. Si te solicita apoyo, puedes pedirle los datos.')
DICTA = ('Lo guías pantalla por pantalla sin que te diga los datos: «Recuerda no decir tus datos en voz alta.» '
         'Si no lo logra: le preguntas si requiere ayuda. Si te solicita apoyo, puedes pedirle los datos.')

def aplicar(d):
    s = next(x for x in d['stages'] if x['key'] == 'desp_v')
    # caja «Importante»: queda solo lo del link que no llega
    s['hacer'] = [re.split(r'\s+(?:Link que falla|Si el link no funciona)', h)[0] if h.startswith('Importante') else h for h in s['hacer']]
    var = [v for v in s['var'] if not re.match(r'^(«El pago no pasa»|«Díctame|El link falla por algo técnico)', v[0])]
    i = next((k + 1 for k, v in enumerate(var) if re.match(r'^(No le llega el link|Si responde)', v[0])), 1)
    if var and var[0][0].startswith('Si responde') and i == 1:
        i = 1 + sum(1 for v in var[1:] if v[0].startswith('No le llega el link'))
    s['var'] = var[:i] + [['«El pago no pasa»', PASA], ['«Díctame, ayúdame a llenarlo»', DICTA]] + var[i:]
    return d

if __name__ == '__main__':
    p = sys.argv[1]
    d = aplicar(json.load(open(p, encoding='utf-8')))
    json.dump(d, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('etapa 11 ok', p)
