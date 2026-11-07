"""Guía mandatoria de evaluación de llamadas: 13 puntos (1 riesgo · 0 sin riesgo · None no aplica) y 5 datos de seguimiento.

Se aplica sobre la llamada ya normalizada por qa_engine (turnos del asesor y del estudiante, resultado, oferta).
Reglas de la guía que se respetan aquí:
  · se evalúa sólo al asesor; lo del cliente cuenta si el asesor lo confirma;
  · venta = pago confirmado; si no se puede saber si hubo venta, los puntos que dependen de ella quedan en no aplica;
  · membresía (3 a 9): sólo con venta; pago en efectivo como acuerdo final → no aplica;
  · los puntos 3–7 y 9 miran qué se dijo; el 8 mira cuándo (antes del pago);
  · en estas operaciones (post-venta) no hay primera venta: los puntos 2 y 6 quedan en no aplica.
"""
import re

PUNTOS = ['Condicionamiento en Upsell', 'Condicionamiento en primera venta', 'Membresía: precio', 'Membresía: cobro mensual',
          'Membresía: inicio 2.º mes', 'Membresía: inicio 3.er mes', 'Membresía: cancelación', 'Membresía: antes del pago',
          'Membresía: separada de la cuota', 'Certificados', 'Promesa de empleo', 'Promesa de ingresos', 'Datos de tarjeta']
QUE_PASO = ['Rechazo por membresía', 'Objeción sin resolver', 'Objeción resuelta', 'Sin rechazo', 'Indeterminado', 'No aplica']

NEG = r'(?<!\bno )(?<!\bni )(?<!\bnunca )'
RX_MEMB = re.compile(r'membresia|suscripcion|mantenimiento de (la |tu )?(cuenta|plataforma)')
RX_MONTO_OK = re.compile(r'\b(25|49|50|veinticinco|cuarenta y nueve|cincuenta)\b ?(usd|dolares|dolar|\$)?')
RX_MONTO = re.compile(r'\b(\d{1,3}(?:[.,]\d{1,2})?|veinticinco|treinta|cuarenta(?: y \w+)?|cincuenta|sesenta|veinte)\b ?(usd|dolares|dolar)')
RX_MENSUAL = re.compile(r'cada mes|mensual|al mes|mes a mes|todos los meses|por mes|mensualmente')
RX_TERMINA = re.compile(r'hasta que (termines|terminas|saques|obtengas|te gradues|finalices)|solo (el|los|durante) (segundo|tercer|dos|tres|primeros)|(se|lo) (cobra|pagas) (solamente|solo) (el|los)|termina (sola|cuando termines)')
RX_MES2 = re.compile(r'segundo mes|(a partir|desde) del? (mes siguiente|proximo mes|siguiente mes)|primer mes (no (la )?pagas|es gratis|no se cobra|gratis)[^.]{0,80}(siguiente|segundo|proximo|despues)|(empiezas|empieza|comienza|comienzas) a (pagar|cobrar)(la)?[^.]{0,30}(mes siguiente|proximo mes|siguiente mes|segundo mes)|despues del primer mes|a los (30|treinta) dias')
RX_MES3 = re.compile(r'tercer mes|(dos|2) (primeros )?meses (gratis|sin pagar|no pagas)')
RX_CANCEL = re.compile(r'cancelar(la)?|dar(la)? de baja|darla de baja|des?activar(la)?|cuando (tu |usted )?(quieras|quiera|decidas|decida)|el tiempo que (tu |usted )?(quieras|decidas|desees)|la puedes quitar|retirar(la)? cuando')
RX_NOCANCEL = re.compile(r'no (la )?(puedes|puede|se puede) (cancelar|dar de baja)|(meses|mes) obligatori|a partir del (cuarto|quinto) mes es opcional|minimo (de )?(tres|3|seis|6) meses')
# La membresía se evalúa sólo cuando el asesor la OFRECE en esta venta: si el estudiante ya la tiene, no se ofrece.
RX_MEMB_YA = re.compile(r'(tu|su) membresia|membresia (que )?(ya )?(tienes|tiene|pagas|paga|tenias|activa|actual)|ya (tienes|tiene|pagas|paga|cuentas con) (la |tu |una )?membresia|(sigue|seguira|continua|queda) (igual|activa)|no (cambia|se modifica|afecta) (la |tu )?membresia|ningun cargo adicional|ya (lo |la )?(sabes|sabe|conoces|conoce)|(te|le) (dijeron|hablaron|explicaron|comentaron|mencionaron)|hablaron de la membresia|como (te|le) (dijeron|explicaron)|recuerda que|recuerde que|acordad[oa]s?|que (te|le) (explico|dijo|comento) (mi|tu|el|la) (companer|asesor)')
RX_MEMB_OF = re.compile(r'(membresia|suscripcion)[^.?]{0,90}\b(\d{2}|veinticinco|cuarenta y nueve|cincuenta)\b ?(usd|dolares|dolar|al mes|mensual)|\b(\d{2}|veinticinco|cuarenta y nueve|cincuenta)\b ?(usd|dolares|dolar)[^.?]{0,60}(membresia|suscripcion)|(te|le) (ofrezco|incluyo|activo|activamos|dejamos) (la |una )?(membresia|suscripcion)|membresia mensual|(empiezas|empieza|comienza|comienzas) a pagar (la )?membresia|(se|te) (suma|agrega|cobra) (la )?membresia')
RX_CUOTAS = re.compile(r'\b(cuotas|en (2|3|4|dos|tres|cuatro) (pagos|partes|mensualidades)|(2|3|4|dos|tres|cuatro) (pagos|mensualidades) de|pago inicial|primer pago de)\b')
RX_MEZCLA = re.compile(r'(esas|las) (cuotas|mensualidades) (son|es) (tu|su|la) membresia|membresia (son|es) (las|esas) cuotas')
RX_EFECTIVO = re.compile(r'(pagar|pago|pagas|pagaria|pagarlo) en efectivo|efectivo en (oxxo|tienda|el banco)|(oxxo|walmart|seven|7 eleven|farmacia)')
RX_CERT = re.compile(
    NEG + r'(certificad\w*|diploma|titulo)[^.?]{0,70}(te (permite|permitira|va a permitir|habilita|habilitara)( a| para)?|para (que puedas )?|(estas|esta) (capacitad\w*|habilitad\w*) para )[^.?]{0,12}\b(trabajar|ejercer|laborar)\b'
    r'|' + NEG + r'(certificad\w*|diploma)[^.?]{0,40}\b(es|son|seria) (oficial|un titulo|una licencia|valido en (cualquier|todo|todos))'
    r'|' + NEG + r'(certificad\w*|diploma|titulo)[^.?]{0,60}(valid\w*|vale|sirve|reconocid\w*) en (cualquier (estado|parte|lugar)|todo (el pais|estados unidos|usa|eeuu|ee uu)|todos los estados)'
    r'|' + NEG + r'(certificad\w*|diploma)[^.?]{0,40}(avalad\w*|reconocid\w*|aprobad\w*) por el (estado|gobierno|departamento)'
    r'|' + NEG + r'(obtienes|recibes|te (damos|dan|entregamos)) (tu |una |la )?licencia\b')
RX_CERT_NO = re.compile(r'no (es|son) (una |un )?(licencia|titulo|oficial)|no (te )?la (damos|da|entregamos)|ellos te (dan|entregan) la licencia|no (te )?(habilita|permite)|depende de (cada|la|el) (estado|entidad|empleador)')
RX_EMPLEO = re.compile(
    NEG + r'(te|le) (garantizo|garantizamos|aseguro|aseguramos|prometo)[^.?]{0,40}(trabajo|empleo|contrat|puesto)'
    r'|' + NEG + r'(trabajo|empleo|contratacion) (asegurad|garantizad|segur)\w*'
    r'|' + NEG + r'(te|le) van a contratar (seguro|si o si|de una|inmediatamente)'
    r'|' + NEG + r'(ya|de una) (tienes|tendras|vas a tener) (trabajo|empleo)')
RX_INGRESO = re.compile(
    NEG + r'inversion segura|se (paga|va pagando) sol[oa]s?(?= *([.,;!?]|$| y | con ))|' + NEG + r'(vas|va) a recuperar (la|tu|su|esa|esta)? ?(inversion|dinero|plata)'
    r'|' + NEG + r'(recuperas|recupera|recuperar|recuperarias) (la inversion|tu inversion|su inversion|el dinero|tu dinero|esos|los \d+|lo invertido)'
    r'|' + NEG + r'(lo|la) (vas a|va a) recuperar (rapido|en (un|dos|pocos) (mes|meses|semanas))'
    r'|' + NEG + r'(te|le) (garantizo|garantizamos|aseguro|aseguramos)[^.?]{0,40}(ingreso|ganancia|dinero|clientes)')
RX_TARJ = re.compile(r'(dicta|dame|dime|regalame|pasame|indicame|me (das|da|dice|dices|regalas|regala|dictas|dicta|pasas|indicas)|me (puedes|podrias|puede) (dar|dictar|decir|regalar|pasar|indicar)|necesito)[^.?]{0,40}'
                     r'(numero(s)? de (la |tu |su )?tarjeta|(los )?(16|dieciseis) (digitos|numeros)|(fecha de )?(vencimiento|expiracion)|codigo de seguridad|cvv|cvc|(los )?(tres|3) (numeros|digitos)( de atras| de seguridad)?|numeros de atras)'
                     r'|(foto|fotografia|imagen) de (la |tu |su )?tarjeta')
RX_TARJ_NO = re.compile(r'pedido|(te|me) (aparecio|aparece|salio|sale) (el|un) numero|ya (te|le) (aparecio|salio)|orden|codigo (de|del) (pedido|compra|aprende)|empieza (por|con)|coloca|colocas|escribe|escribes|ingresa|ingresas|digita|digitas|no me (los|la|lo) (digas|compartas|dictes)|imaginate|por ejemplo')
RX_AYUDA = re.compile(r'ayudame|ayudeme|me ayudas|me ayuda (a|con)|no (puedo|pude|me deja|me abre|abre|me carga|carga|me sale|sale|me llego|llego|me aparece|aparece|se como|se hacerlo|entiendo)|me (da|dio|sale|salio) (error|un error)|no (me )?funciona|fallo|rechaz|no paso|no pasa|tengo las manos|estoy manejando|hazlo tu|hagalo usted')
RX_PAGO_INTENTO = re.compile(r'link (de pago|a tu nombre)|enlace de pago|tarjeta|realizar (el )?pago|procesar (el )?pago|pasarela|numero de pedido')
RX_OBJ_MEMB = re.compile(r'(no (quiero|me interesa|estoy de acuerdo|voy a pagar|puedo pagar|sabia|me (dijeron|explicaron|informaron|comentaron))|muy caro|es caro|es mucho|mucho dinero|demasiado|otro (pago|cobro)|mas (pagos|cobros)|(quiero|puedo) cancelar|no me gusta|sin la membresia|quitar la membresia|por que (me )?(cobran|tengo que pagar))')
RX_PREG = re.compile(r'^\W*(y )?(cuanto|desde cuando|cuando|como|que es)\b')
RX_SE_CORRIGE = re.compile(r'^\W*(perdon|perdona|disculpa|me corrijo|no,? (te|le) corrijo|corrijo)')


def _primero(A, rx, desde=None, hasta=None, ctx=None):
    """Primer turno del asesor (índice, match) que cumple rx; ctx exige otra regex en el mismo turno o el anterior."""
    for k, (i, t) in enumerate(A):
        if desde is not None and i < desde: continue
        if hasta is not None and i > hasta: break
        m = rx.search(t)
        if not m: continue
        if ctx is not None:
            prev = A[k - 1][1] if k else ''
            if not (ctx.search(t) or ctx.search(prev[-200:])): continue
        return i, m
    return None, None


def _riesgo(A, rx):
    """Frase de riesgo del asesor; se descarta si el asesor se corrige en el turno siguiente y por completo."""
    for k, (i, t) in enumerate(A):
        m = rx.search(t)
        if not m: continue
        sig = A[k + 1][1] if k + 1 < len(A) else ''
        if RX_SE_CORRIGE.search(sig): continue
        return i, m
    return None, None


def evaluar(op, res, oferta, i_of, ts, A, C, es_pago):
    """Devuelve (puntos[13], citas{punto: (i_turno, ini, fin)}, datos[5], cita_cliente)."""
    n = len(ts)
    g = [None] * 13
    cit = {}
    txt_a = ' '.join(t for _, t in A)
    venta = res == 'V'
    # --- 1 · condicionamiento en Upsell (llamadas de Upsell, con o sin venta, cuando se ofreció el adicional)
    if op == 'Upsell':
        rx1 = re.compile(r'(clases? privad\w*|material( de apoyo| de estudio)?|premium|paquete|kit|sesiones|herramienta)[^.?]{0,50}\b(es|son|seria|serian) (obligatori[oa]s?|necesari[oa]s? para (terminar|graduarte|certificarte|avanzar|el certificado))'
                         r'|\b(es|son) (obligatori[oa]s?|un requisito)[^.?]{0,30}(las clases privad|el material|el premium|el paquete|el kit)'
                         r'|(tienes|tiene|debes|debe) que (adquirir|tomar|pagar|comprar)[^.?]{0,25}(las clases privad|clases privad|el material|material de apoyo|el premium|el paquete|el kit|las sesiones)'
                         r'|sin (las clases|el (paquete )?premium|el material|el paquete)[^.?]{0,40}no (puedes|puede|vas a poder|podras)')
        RX1_NO = re.compile(r'\b(no|nada|ni|ningun\w*|nunca)\b[^.?]{0,25}$')
        i, m = None, None
        for k_, (i_, t_) in enumerate(A):
            for m_ in rx1.finditer(t_):
                if RX1_NO.search(t_[max(0, m_.start() - 40):m_.start()]) or re.search(r'\bno (es|son|tienes|tiene|debes|debe)\b', m_.group(0)): continue
                i, m = i_, m_; break
            if i is not None: break
        if i is not None: g[0], cit[0] = 1, (i, m.start(), m.end())
        elif oferta: g[0] = 0
    # --- 2 y 6 · primera venta: no hay primera venta en estas operaciones
    # --- 3 a 9 · membresía (sólo venta; efectivo como acuerdo final → no aplica)
    efectivo = any(RX_EFECTIVO.search(t) for i, t in A + C if i / max(1, n) >= 0.6)
    ya_tiene = any(RX_MEMB.search(t) and RX_MEMB_YA.search(t) for _, t in A)
    ofrece_memb = (not ya_tiene) and any(RX_MEMB_OF.search(t) for i, t in A if oferta and i >= (i_of or 0) - 2)
    if venta and not efectivo and ofrece_memb:
        i_pago = next((i for i, (_, q, t) in enumerate(ts) if es_pago(t.lower())), None)
        mt = [(i, t) for i, t in A if RX_MEMB.search(t)]          # turnos del asesor que hablan de la membresía
        cerca = lambda rx: next(((i, m) for i, t in A for m in [rx.search(t)] if m and any(abs(i - j) <= 1 for j, _ in mt)), (None, None))
        # 3 · precio
        i3, m3 = cerca(RX_MONTO_OK)
        if i3 is not None: g[2] = 0
        else:
            g[2] = 1
            i, m = cerca(RX_MONTO)
            if i is not None: cit[2] = (i, m.start(), m.end())
        # 4 · cobro mensual
        i4, m4 = cerca(RX_MENSUAL)
        it, mt_ = cerca(RX_TERMINA)
        g[3] = 1 if (i4 is None or it is not None) else 0
        if it is not None: cit[3] = (it, mt_.start(), mt_.end())
        # 5 · inicio en el segundo mes
        i5, m5 = cerca(RX_MES2)
        i5b, m5b = cerca(RX_MES3)
        if i5 is not None and i5b is None: g[4] = 0
        else:
            g[4] = 1
            if i5b is not None: cit[4] = (i5b, m5b.start(), m5b.end())
        # 7 · cancelación
        i7, m7 = cerca(RX_CANCEL)
        i7b, m7b = _riesgo(A, RX_NOCANCEL)
        g[6] = 1 if (i7 is None or i7b is not None) else 0
        if i7b is not None: cit[6] = (i7b, m7b.start(), m7b.end())
        # 8 · explicada antes del pago (sólo mira cuándo: una condición que no se dijo no cuenta aquí)
        dichos = [i for i in (i3, i4, i5, i7) if i is not None]
        if not mt: g[7] = 1
        elif i_pago is None: g[7] = 0
        else:
            # 1 si la membresía (o alguna condición) se dice por primera vez después de procesar el pago
            tarde = [i for i in [mt[0][0]] + dichos if i > i_pago]
            g[7] = 1 if tarde else 0
            if tarde:
                j = min(tarde); t = next(t for i, t in A if i == j)
                cit[7] = (j, 0, min(len(t), 140))
        # 9 · separada de la cuota (sólo ventas en 2 o más cuotas)
        if RX_CUOTAS.search(txt_a):
            im, mm = _riesgo(A, RX_MEZCLA)
            g[8] = 1 if (not mt or i3 is None or im is not None) else 0
            if im is not None: cit[8] = (im, mm.start(), mm.end())
    # --- 10 a 12 · promesas (todas las llamadas)
    for k, rx in ((9, RX_CERT), (10, RX_EMPLEO), (11, RX_INGRESO)):
        if n < 4: continue
        i, m = _riesgo(A, rx)
        if k == 9 and i is not None:
            t_ = next(t for j, t in A if j == i)
            if RX_CERT_NO.search(t_[max(0, m.start() - 120): m.end() + 120]): i, m = None, None
        g[k] = 1 if i is not None else 0
        if i is not None: cit[k] = (i, m.start(), m.end())
    # --- 13 · datos de tarjeta (llamadas con pago o intento de pago)
    if venta or RX_PAGO_INTENTO.search(txt_a):
        i, m = None, None
        for i_, t_ in A:
            for m_ in RX_TARJ.finditer(t_):
                if RX_TARJ_NO.search(t_[max(0, m_.start() - 60): m_.end() + 40]): continue
                i, m = i_, m_; break
            if i is not None: break
        if i is None: g[12] = 0
        else:
            ayuda = any(RX_AYUDA.search(t) for j, t in C if j < i) or any(RX_AYUDA.search(t) for j, t in A if i - 6 <= j < i)
            if ayuda: g[12] = 0
            elif ts and ts[0][0] > 60 and i < 6: g[12] = None   # grabación cortada al inicio: no se ve si antes pidió ayuda
            else: g[12], cit[12] = 1, (i, m.start(), m.end())
    # --- datos de seguimiento
    con_oferta = oferta
    menc = (1 if RX_MEMB.search(txt_a) else 0) if con_oferta else None
    menc_p = None
    if menc is not None:
        menc_p = int(any(RX_MONTO.search(t) or RX_MONTO_OK.search(t) for i, t in A if RX_MEMB.search(t)))
    obj, que, fcli = 0, 5, None
    i_m = next((i for i, t in A if RX_MEMB.search(t)), None)
    if i_m is not None:
        for j, t in C:
            if j <= i_m: continue
            if RX_PREG.search(t) and not RX_OBJ_MEMB.search(t): continue
            if RX_OBJ_MEMB.search(t) and (RX_MEMB.search(t) or RX_MENSUAL.search(t) or any(RX_MEMB.search(a) for k, a in A if j - 3 <= k < j)):
                i_p = next((i for i, (_, q, tt) in enumerate(ts) if es_pago(tt.lower())), None)
                if i_p is not None and j > i_p: break       # objeción después del pago: no aplica
                obj, fcli = 1, j
                break
        if obj:
            que = {'V': 2, 'N': 0 if any(RX_MEMB.search(t) and RX_OBJ_MEMB.search(t) for k, t in C if k >= fcli) else 1, 'I': 4}[res]
        else:
            que = 3
    datos = [obj if i_m is not None else None, que, fcli, menc, menc_p]
    return g, cit, datos
