"""Alinea los textos de una página (Speech o Calidad) con la regla vigente de «Pagos y tarjeta» (noviembre 2026):
el estudiante ingresa sus datos en el link; si pide ayuda o tarda demasiado, se le pregunta si necesita acompañamiento,
y solo con su autorización expresa y la autorización previa del supervisor se pueden tomar los datos de pago.
Lo que no se permite: pedirlos de forma proactiva u ofrecer ingresarlos sin que el estudiante pida ayuda.
Uso: python3 regla_pago.py plano_in.html plano_out.html"""
import sys

SI_AYUDA = ('Si pide ayuda o tarda demasiado, le preguntas si necesita acompañamiento; solo con su autorización expresa '
            'y la autorización previa del supervisor puedes tomar los datos de pago.')

CAMBIOS = [
    # cierre de cajas y tablas de la etapa 11
    ('Nunca se piden datos de tarjeta.', 'Datos de tarjeta: nunca de forma proactiva. ' + SI_AYUDA),
    # «Lo que nunca se dice»
    ('Pedir o tomar datos de tarjeta, por cualquier motivo.',
     'Pedir datos de tarjeta de forma proactiva u ofrecer ingresarlos sin que el estudiante pida ayuda, o tomarlos sin su autorización expresa y la del supervisor.'),
    ('El estudiante ingresa los datos en el link de su correo. Si falla: que pague sin mantener la llamada abierta; si sigue fallando, reagendar unos minutos después.',
     'El estudiante ingresa los datos en el link de su correo. ' + SI_AYUDA + ' Si el link falla: que pague sin mantener la llamada abierta; si sigue fallando, reagendar unos minutos después.'),
    # errores a evitar (etapa 11)
    ('«Díctame los números de la tarjeta y te ayudo rápido»',
     'Ofrecer tomar los datos sin que el estudiante pida ayuda («Díctame los números de la tarjeta y te ayudo rápido»)'),
    ('Pedir datos de tarjeta o el código del banco',
     'Pedir datos de tarjeta sin que el estudiante pida ayuda o sin su autorización y la del supervisor · Pedir el código del banco'),
    ('Pedir los datos de la tarjeta («ponme los datos… me lo dictas», «el número de la tarjeta, yo sé que eres muy hábil»)',
     'Pedir los datos de la tarjeta sin que el estudiante pida ayuda o sin autorización del supervisor («ponme los datos… me lo dictas», «el número de la tarjeta, yo sé que eres muy hábil»)'),
    ('— nunca se toman datos de tarjeta', '— sin que pida ayuda y sin autorización no se toman datos de tarjeta'),
    # pestaña de objeciones
    ('el pago lo haces tú en el enlace seguro, yo nunca te pido tu tarjeta.»',
     'el pago lo haces tú en el enlace seguro a tu nombre, que te llega al correo.»'),
    ('Nunca pidas datos de tarjeta por teléfono: el pago se hace en su enlace seguro.',
     'El pago se hace en su enlace seguro. No pidas datos de tarjeta por iniciativa propia: solo si el estudiante pide ayuda, con su autorización expresa y la del supervisor.'),
    ('Pedir o anotar datos de tarjeta por teléfono.',
     'Pedir o anotar datos de tarjeta sin que el estudiante pida ayuda o sin su autorización y la del supervisor.'),
]

def aplicar(h):
    n = 0
    for a, b in CAMBIOS:
        if b in h: continue   # ya aplicado (algunos textos nuevos contienen el anterior)
        if a in h:
            n += h.count(a); h = h.replace(a, b)
    return h, n

if __name__ == '__main__':
    h, n = aplicar(open(sys.argv[1], encoding='utf-8').read())
    open(sys.argv[2], 'w', encoding='utf-8').write(h)
    print('textos ajustados a la regla de pago:', n)
