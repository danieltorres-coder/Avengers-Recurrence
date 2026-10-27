"""Motor QA mensual · Post-Sales.

Lee las transcripciones de todos los meses y aplica las MISMAS reglas a cada llamada:
resultado (venta / no venta / indeterminada), oferta y producto, las 13 etapas del speech oficial,
objeciones del estudiante, señales de riesgo (no negociables) y buenas prácticas.

Fuentes por mes (carpeta qa/):
  sep/<op>.json         transcripciones de septiembre ({guid: [[seg, 0=asesor/1=estudiante, texto]]})
                        + metadatos de septiembre (CALLS de la página anterior: fecha, turno, supervisor, asesor)
  oct/*.json            partes descargadas de Drive (formato original con transcript «N-expert: …»)
Salida: out/calls.json (una fila por llamada), out/ej.json (citas por etapa y señal), out/tx_<mes>_<op>.json
Uso: python3 -I qa_engine.py <dir_qa>
"""
import json, glob, re, sys, unicodedata, collections, os

D = sys.argv[1]
OUT = D + '/out'
os.makedirs(OUT, exist_ok=True)

def norm(s):
    s = unicodedata.normalize('NFD', s or '')
    return ''.join(c for c in s if unicodedata.category(c) != 'Mn').lower()

def titulo(s):
    return ' '.join(w.capitalize() for w in re.split(r'[._\s]+', s) if w)

# ---------------------------------------------------------------- carga
OPS = ['Upsell', 'Recurrence', 'Bootcamp', 'Resurrection']
LL = []   # {id, mes, fecha, op, t, sup, ag, tx:[[seg, quien, texto]]}

# Septiembre: metadatos de la página anterior + transcripciones del repo
h = open(D + '/dec/calidad.html', encoding='utf-8').read()
i = h.index('const CALLS=') + 12
CALLS, _ = json.JSONDecoder().raw_decode(h[i:])
TXS = {}
for f in ['bootcamp', 'recurrence', 'resurrection', 'upsell_am', 'upsell_int', 'upsell_pm']:
    TXS.update(json.load(open(f'{D}/sep/{f}.json', encoding='utf-8')))
for r in CALLS:
    LL.append(dict(id=r[0], mes=r[1][:7], fecha=r[1], op=r[2], t=r[3], sup=r[4], ag=r[5], tx=TXS.get(r[0], []), old=r[8]))

# Mapas de septiembre para completar octubre (supervisor, turno y nombre del asesor)
NOMBRE = {}                   # clave sin tildes -> nombre como aparece en septiembre
AG_SUP, AG_T = collections.defaultdict(collections.Counter), collections.defaultdict(collections.Counter)
SUP_T = collections.defaultdict(collections.Counter)
for c in LL:
    NOMBRE[norm(c['ag'])] = c['ag']; NOMBRE[norm(c['sup'])] = c['sup']
    AG_SUP[(c['op'], c['ag'])][c['sup']] += 1
    if c['t']: AG_T[c['ag']][c['t']] += 1; SUP_T[c['sup']][c['t']] += 1
SUP_EMAIL = {}
for f in glob.glob(D + '/parts/Upsell_septiembre_*'):
    for x in json.loads(open(f, encoding='utf-8').read().replace('NaN', 'null')):
        pass

def persona(email):
    if not email: return ''
    base = titulo(str(email).split('@')[0])
    return NOMBRE.get(norm(base), base)

def turnos_raw(t):
    out = []
    for ln in (t or '').split('\n'):
        m = re.match(r'\s*(\d+)-(expert|client|agent|asesor|cliente)\s*:\s*(.*)', ln, re.I)
        if m: out.append([int(m.group(1)), 0 if m.group(2).lower() in ('expert', 'agent', 'asesor') else 1, m.group(3).strip()])
        elif out and ln.strip(): out[-1][2] += ' ' + ln.strip()
    return out

def op_de(nombre):
    n = norm(nombre)
    for k, op in (('upsell', 'Upsell'), ('recurrence', 'Recurrence'), ('bootcamp', 'Bootcamp'), ('resur', 'Resurrection')):
        if k in n: return op
    return None
# Meses nuevos: cualquier .json en <dir_qa>/oct/ o <dir_qa>/meses/ (partes de Drive); la operación sale del nombre del archivo
NUEVOS = collections.defaultdict(list)
for f in sorted(glob.glob(D + '/oct/*') + glob.glob(D + '/meses/*')):
    if op_de(os.path.basename(f)): NUEVOS[op_de(os.path.basename(f))].append(f)
vistos = {c['id'] for c in LL}
for op, fs in NUEVOS.items():
    if True:
        for f in fs:
            for x in json.loads(open(f, encoding='utf-8').read().replace('NaN', 'null')):
                gid = str(x.get('guid'))
                if gid in vistos: continue
                vistos.add(gid)
                ag = persona(x.get('agent'))
                sup = persona(x.get('supervisor')) if x.get('supervisor') else ''
                if not sup:
                    cand = AG_SUP.get((op, ag)) or next((v for (o, a), v in AG_SUP.items() if a == ag), None)
                    sup = cand.most_common(1)[0][0] if cand else 'Sin supervisor asignado'
                t = ''
                if op == 'Upsell':
                    t = (AG_T.get(ag) or SUP_T.get(sup) or collections.Counter({'Sin turno': 1})).most_common(1)[0][0]
                fecha = str(x.get('Fecha'))[:10]
                LL.append(dict(id=gid, mes=fecha[:7], fecha=fecha, op=op, t=t, sup=sup, ag=ag, tx=turnos_raw(x.get('transcript')), old=None))

# ---------------------------------------------------------------- reglas
NUM = r'(\d{1,4}(?:[.,]\d{1,2})?|cien\w*|doscient\w*|trescient\w*|cuatrocient\w*|quinient\w*|seiscient\w*|setecient\w*|ochocient\w*|novecient\w*|mil|diez|quince|veinte|veinticinco|treinta|cuarenta(?: y \w+)?|cincuenta|sesenta|setenta|ochenta|noventa)'
RX_USD = re.compile(NUM + r' ?(usd|dolares|dolar)\b')
PROD = [  # (producto, regex en la ventana de la oferta), en orden de prioridad
    ('Certificación', r'certificaci|examen|licencia|credencial'),
    ('Bootcamp / proyecto', r'bootcamp|proyecto'),
    ('Clases magistrales', r'magistral|clases? grabadas|quedan grabadas'),
    ('Clases privadas', r'clases? (privad|individual|personalizad|uno a uno|1 a 1)|sesion(es)? (privad|individual|personalizad)|uno a uno|tutor'),
    ('Material de apoyo', r'material|kit|plan academico|paquete|herramienta'),
    ('Membresía / extensión', r'membresia|extension|extender|mensualidad|suscripcion|reactiv'),
    ('Programa adicional', r'diplomado|otro programa|programa (adicional|nuevo|complementario)|segundo programa|nuevo programa|curso (adicional|nuevo|de ingles)|especializa|\bingles\b'),
    ('Clases privadas', r'sesion|docente|experto|practic|refuerzo|acompanamiento|complementari|\bclases?\b'),
    ('Membresía / extensión', r'al mes|cada mes|mensual'),
]
PROD = [(p, re.compile(r)) for p, r in PROD]
RX_PAGO = re.compile(r'(ya |listo,? |ahi )(te |me |nos |le )?(salio|sale|aparece|aparecio|dice|marca|llego|cargo)[^.?]{0,40}(pago (realizado|exitoso|aprobado|procesado|completado)|aprobad|exitos|transaccion|compra (realizada|exitosa))|ya (realice|hice|efectue|termine) el pago|ya (quedo|se realizo|se hizo|se proceso|se aprobo|se reflejo|paso) (el|tu|su) pago|(quedo|esta) (aprobado|confirmado|realizado) (el|tu|su) pago|el pago (ya )?(quedo|esta|fue|salio) (aprobado|realizado|exitoso|confirmado|procesado)|felicitaciones por (tu|su) (compra|inversion|decision|adquisicion)|bienvenid[oa] a (tus|sus) clases (privadas|personalizadas)|(pago|transaccion|compra) (realizad[oa]|exitos[oa]|aprobad[oa]|procesad[oa]|completad[oa])')
RX_INSTR = re.compile(r'(va a|vas a|te debe|debe|cuando|hasta que|si te|para que|aparecera|deberia|te tiene que|tiene que|luego|despues)\W+(\w+\W+){0,6}$')
def es_pago(t):
    for m in RX_PAGO.finditer(t):
        if m.group(0).startswith(('ya ', 'listo', 'ahi', 'felicit', 'bienvenid', 'el pago', 'quedo', 'esta')): return True
        if not RX_INSTR.search(t[max(0, m.start() - 60):m.start()]): return True
    return False
RX_CIERRE = re.compile(r'(con )?cual (de las dos|de estas|opcion|te gustaria|prefieres|te queda)|te gustaria (comenzar|empezar|tomar|adquirir|aprovechar|dejar|iniciar|sumar|agregar)|lo dejamos (hoy|listo)|(realizamos|hacemos|procedemos con) el pago|te (envio|mando|comparto) el (link|enlace)|(tarjeta|pago) (de |con )?(debito|credito)|(debito|credito) o (debito|credito)|te parece si (lo )?(dejamos|hacemos|realizamos)|(quieres|deseas) (aprovechar|tomar|adquirir)|vamos a (aprovechar|formalizar|dejarlo)')
CLI_OBJ = [
    ('Dinero', r'\bno (tengo|cuento con) (dinero|plata|el dinero|presupuesto|los recursos|como pagar)|no me alcanza|\bacabo de pagar|\bno tengo para|esta (muy )?(caro|costoso)|\bno puedo pagar|situacion (economica|financiera)'),
    ('Tiempo', r'no tengo tiempo|no me da el tiempo|no tengo (el )?horario|no me queda tiempo'),
    ('Pensarlo / consultar', r'\b(lo|la) (voy a |tengo que |quiero )?(pensar|consultar)|(consultarlo|hablarlo) con (mi )?(esposo|esposa|pareja|marido|familia)|dejame (pensarlo|ver)'),
    ('Más tarde', r'(llamame|llameme|me llamas|me llama|me puedes llamar|marcame|me marcas) (mas tarde|despues|luego|otro dia|manana|en un rato)|ahorita no (puedo|tengo|me queda|me alcanza)|no por ahora|en otro momento'),
    ('Otro pago / sorpresa', r'nadie me (dijo|explico|menciono)|no me (dijeron|explicaron|mencionaron|informaron)|(me|nos) (van a )?cobrar (mas|otra vez|de nuevo)|pense que (ya )?(estaba|era) todo|(otro|otra) (pago|cobro)\b[^.]{0,20}\?|ya (habia |había )?pagado (todo|completo)'),
    ('No le interesa', r'no me interesa|no estoy interesad|no (lo |la )?(quiero|necesito) (por ahora|ahorita|en este momento)|(quiero|voy a) cancelar'),
]
CLI_OBJ = [(k, re.compile(r)) for k, r in CLI_OBJ]
RX_QUEJA = re.compile(r'\bestafa\b|\bengan(o|aron)\b|\bfraude\b|\breembolso\b|\bdevolucion\b|\bme siento (presionad|engan)|\bme estan presionando\b')

R = {  # no negociables / evitar (texto del asesor)
    'apelativo': ('Trato', r'\bmi (amor|reina|rey|vida|cielo|corazon|princesa|bro|pana|hermano|hermana)\b|\bmamita\b|\bpapito\b|\bmija\b|\bmijo\b|(^|[,.!?¿¡] ?)corazon[,.!?]|\bcarino[,.!?]', 'Apelativos («mi amor», «mi reina», «mija», «corazón»)'),
    'maltrato': ('Trato', r'\bno me (interrumpa|interrumpas)\b|\bya (te|le) (lo )?(dije|explique) (varias|mil|muchas) veces\b|\bescucheme bien\b|\bno (sea|seas) (terco|terca|grosero|grosera)\b|\busted no entiende\b|(?<!si )\btu no entiendes\b|\bque pereza\b', 'Trato brusco o descalificador'),
    'tarjeta': ('Pagos seguros', r'(dicta|dame|dime|regalame|me (das|da|dice|dices|regala|dictas|dicta)|me (puedes|podrias|puede) (dar|dictar|decir|regalar))[^.]{0,30}(numero(s)? de (la |tu |su )?tarjeta|los (16|dieciseis) (digitos|numeros)|fecha de (vencimiento|expiracion)|codigo de seguridad|(el )?cvv|codigo que (te|le) (llego|lleg[oó]))|(los )?(tres|3) (digitos|numeritos) de atras', 'Pide datos de la tarjeta o el código por teléfono'),
    'terceros': ('Pagos seguros', r'tarjeta de (tu|su) (esposo|esposa|mama|papa|hijo|hija|hermano|hermana|pareja|novio|novia|amigo|amiga|familiar)|(pidele|pide|pidas|pedirle|pidale)[^.]{0,30}(prestad|un prestamo)|(hagas|hacer|saques|sacar) un prestamo', 'Sugiere préstamo o tarjeta de un familiar'),
    'nada_mas': ('Cobros claros', r'no (vas|va|van) a (pagar|tener que pagar) nada mas|no se (te|le) (va a )?cobra(r|ra)? nada mas|no (hay|tienes|tiene) (ningun|otro) (cobro|pago) (adicional|extra|mas)|unico pago que (realizas|haces|vas a hacer|realizarias)? ?(durante|en) todo (el|tu)', '«No vas a pagar nada más» (omite membresía o cuotas)'),
    'promesa': ('Sin promesas', r'(te|le) (garantizo|garantizamos|aseguro|aseguramos)[^.]{0,40}(trabajo|empleo|ingreso|dinero|clientes)|(vas|va) a (conseguir|tener) (trabajo|empleo) (seguro|garantizado)|titulo (oficial|universitario)|validez oficial|avalad[oa] por (el gobierno|la sep|el estado)|(es|son) del gobierno', 'Promete empleo, ingresos o validez oficial'),
    'urgencia': ('Sin presión', r'(solo|unicamente) (por )?hoy[^.]{0,80}(precio|descuento|valor|oferta|beneficio|oportunidad|costo|usd|dolares)|(precio|descuento|valor|oferta|beneficio|oportunidad)[^.]{0,60}(solo|unicamente) (por )?hoy|(se (te |le )?vence|vence) (hoy|el link|la oferta|el descuento|el beneficio)|(ultimos|solo quedan|me quedan) (\w+ )?cupos', 'Urgencia ligada al precio («solo por hoy»)'),
    'caducidad': ('Sin presión', r'ya no (te|le) aplica (el|la) (descuento|beneficio|beca)|si (cuelgo|colgamos|termina la llamada)[^.]{0,60}(descuento|beneficio|precio|valor|ya no)|no (te|se) (lo|la) (podriamos|podemos|puedo) guardar|se cierra el sistema|ya no va a salir', 'El beneficio «se pierde» si no paga hoy o al colgar'),
    'supervisor': ('Sin presión', r'(me |lo |la )?(autoriz[oa]|aprob[oa]|habilit[oa])( a)?( mi| el| la)? (supervisor|supervisora|coordinador|coordinadora|jefe|gerente)|(mi|el|la) (supervisor|supervisora|jefe)[^.]{0,60}(me )?(autoriz|aprob|habilit|excepcion|descuento)', '«Me autorizó mi supervisor» un precio'),
    'descuento': ('Sin presión', r'(te|le) (puedo|podria|podemos|voy a|vamos a) (dejar|hacer|dar|aplicar|habilitar)[^.]{0,25}(descuento|precio especial|rebaja)|descuento (especial|exclusivo) (para ti|contigo|para usted)', 'Descuento o precio especial del asesor'),
    'regalo': ('Sin presión', r'(te|le|nos) (vamos a )?(regal(o|a|amos|ar)|obsequi(o|a|amos|ar))[^.]{0,40}(clase|sesion|las otras|las restantes)|(son|serian|quedan) \d+ (gratis|de regalo)', '«Te regalamos» clases a cambio de pagar hoy'),
    'ancla': ('Sin presión', r'(normalmente|habitualmente|el valor (habitual|real|normal)|precio (normal|real|habitual)|tus companeros|los demas estudiantes)[^.]{0,200}\b\d{2,4} ?(usd|dolares)', 'Precio ancla («normalmente vale…»)'),
    'condicion': ('Tú decides', r'\b(tienes|tiene|debes|debe) que (adquirir|tomar|pagar|comprar) (el|la|las|los|tu|su|este|esta) (material|complement|clases? (privad|individual|magistral)|herramient|paquete|kit|sesion)|te corresponde (el|la|las|los) (material|clases|sesiones|kit)|(todos|todas) (los|las) (estudiantes|alumnos) (lo |la |las |los )?(toman|adquieren|tienen que|deben)', 'Presenta lo adicional como obligatorio o «que le corresponde»'),
}
R = {k: (c, re.compile(p), d) for k, (c, p, d) in R.items()}

VP = json.load(open(OUT + '/venta_prob.json'))
ST = ['saludo', 'conexion', 'sondeo', 'beneficio', 'integracion', 'ejemplos', 'precio', 'cierre1', 'objeciones', 'cierre2', 'desp_v', 'desp_nv', 'seguimiento']
RX = {
    'presenta': re.compile(r'(te habla|le habla|hablas con|habla con|mi nombre es|te saluda|le saluda|\bsoy\b)[^.?]{0,80}(aprende|coordinador|asesor|analista|area)|aprende institute'),
    'grabacion': re.compile(r'grabad|monitoread'),
    'conexion_up': re.compile(r'certificado|correo|contrasena|plataforma|aplicacion|\bapp\b|link de (ingreso|acceso)|zoom|primera clase|induccion|sala de apoyo'),
    'conexion_rec': re.compile(r'(llevas|tienes|vas|va) [^.?]{0,25}(\d+ ?%|por ciento|porcentaje)|\bavance\b|acceso (hasta|activo|vence|esta)|(como|que tal) (te|le) (ha ido|has sentido|ha parecido|va)|clases en vivo|que te ha (gustado|costado|impedido)'),
    'sondeo': re.compile(r'que te motiv|que (le )?motiv|a que te dedicas|a que se dedica|(trabajas|trabaja) (en|actualmente|como)|(quieres|quiere) emprender|para que (lo|la) (quieres|quiere|necesitas)|que te gustaria lograr|que quieres lograr|(tu|su) meta|cuanto tiempo (le )?(puedes|dedicas|tienes)|propio negocio|experiencia en|ya (trabajas|tienes experiencia)|primera vez (estudiando|en linea)'),
    'beneficio': re.compile(r'(te|le) (va|van) a (ayudar|permitir|servir|facilitar)|vas a poder|va a poder|beneficio|te permite|le permite|ventaja|lo que (ganas|logras)|te ayuda a'),
    'integracion': re.compile(r'como (tu |usted )?me (dijiste|comentaste|contaste|decias|mencionaste|dijo|comento)|por lo que me (dijiste|comentaste|contaste|cuentas|mencionaste)|(me|que me) (dijiste|comentaste|contaste|mencionaste) que|lo que me (cuentas|dices|mencionaste|comentaste|dijiste)|para lo que (me )?(quieres|dijiste|necesitas)|ya que (me dices|trabajas|quieres)|(tu|su) meta (de|es)|en tu caso|para tu (caso|negocio|trabajo|meta|emprendimiento)'),
    'ejemplos': re.compile(r'por ejemplo|imaginate|imagina que|te pongo un ejemplo|es como (cuando|si)|por decirte algo|un caso'),
    'obj_resp': re.compile(r'entiendo|comprendo|te entiendo|que te (frena|preocupa|genera duda)|el valor o el momento|(2|3|dos|tres) (pagos|cuotas)|cuotas|alternativa|opcion|que te (impide|falta)'),
    'desp_v': re.compile(r'te resumo|en resumen|recuerda que|(quedo|queda|quedan) (tu|su|tus|sus|agendad|program|list|activ)|bienvenid|cualquier (cosa|duda|inquietud)|mucho exito'),
    'desp_nv': re.compile(r'gracias por (tu|su) (tiempo|atencion)|que tengas|que tenga|que estes|cualquier (cosa|duda|inquietud)|quedamos (atentos|pendientes)|contactanos|escribenos|mucho exito|feliz (dia|tarde|noche)|cuidate'),
    'seguimiento': re.compile(r'(te|le) (llamo|marco|contacto|escribo|llamamos|marcamos)|(me|nos) (comunico|comunicamos)|quedamos (el|para el|manana|entonces el)|(lunes|martes|miercoles|jueves|viernes|sabado|domingo|manana) (a las|en la|en el transcurso)|(a las|tipo) \d{1,2}'),
    'memb': re.compile(r'membresia[^.?]{0,80}(\d{2}|veinticinco|cuarenta y cinco|diez) ?(usd|dolares)|(\d{2}|veinticinco|cuarenta y cinco|diez) ?(usd|dolares)[^.?]{0,60}(al mes|mensual|membresia)'),
    'opcional': re.compile(r'opcional|no es obligatori|nada es obligatori|(valor|costo|pago) (aparte|adicional)|por aparte|tu decides|usted decide|decides si|no (esta|viene|va) incluid'),
    'link': re.compile(r'link (de pago|a tu nombre)|enlace de pago|te (envio|envie|mando|mande) el (link|enlace)'),
}

# Regla «opcional o complemento»: cuenta si va junto a clases, material, valor o pago (no «cuestionarios opcionales»)
RX_OPC = re.compile(r'\bopcional(es)?\b|no es obligatori|nada es obligatori')
RX_COMPL = re.compile(r'\b(complemento|complementos|complementari[oa]s?)\b')
RX_CTX = re.compile(r'clase|sesion|material|herramient|valor|usd|dolar|pago|adicional|aparte|inversion|paquete|plan|privad|experto|docente')
RX_NOCTX = re.compile(r'cuestionario|actividad|leccion|modulo|tarea|reto')
RX_MAT = re.compile(r'material (de apoyo|de estudio|academico|didactico|practico)|plan academico|herramientas? (academica|de apoyo|de estudio)|(tu|su) material\b')
RX_UNICO = re.compile(r'(valor|pago) unico|unico (pago|valor)')
RX_MEMB_ANY = re.compile(r'membresia|mensualidad')
def dice(rx, txt):
    for m in rx.finditer(txt):
        if RX_CTX.search(txt[max(0, m.start() - 160): m.end() + 160]) and not RX_NOCTX.search(txt[max(0, m.start() - 60): m.end() + 40]): return m
    return None
# Reglas de la auditoría Upsell (presión, pagos, trato): se suman a las de arriba para que el tablero y la auditoría cuenten igual
OLD_R = [
    # --- Condicionamiento: el complemento presentado como parte de la compra, obligatorio o requisito
    ('obligatorio', 'condicionamiento', r'(?<!no )(?<!nada )\b(es|son|seria|sería) (obligatori[oa]s?|un requisito)\b|\b(tienes|tiene|debes|debe) que (adquirir|tomar|pagar|comprar) (el|la|las|los|tu|su|este|esta|estas) (material|complement|clases? (privad|individual|practic|magistral)|herramient|paquete|kit|sesion)|sin (el|la|las|los|este|esta|estas|estos) (material|complement|clases (privadas|individuales|practicas)|sesiones)[^.]{0,50}\bno (vas a poder|puedes|podras|puede|podra|te (podemos|puedo) (certificar|entregar))|para (poder )?(certificarte|obtener (tu|su) certificado|graduarte)[^.]{0,50}(necesitas|necesita|debes|tienes que) (tomar|tener|adquirir|pagar|hacer) (las|los|el|la) (clases|sesiones|practicas|material)', 'Presenta el complemento como obligatorio o como requisito'),
    ('incluido_falso', 'condicionamiento', r'\bte corresponde (el|la|las|los) (material|clases|sesiones|kit)|\b(material|clases|sesiones) que (te|le) corresponde|(todos|todas) (los|las) (estudiantes|alumnos) (lo |la |las |los )?(toman|adquieren|tienen que|deben)|es parte (del|de tu|de su) (proceso|programa|inscripcion) (que|el|la)? ?(material|clases|sesion)|(activar|activo|cargar|cargo|entregar|entrego)(te)? (tu|su|el) material (academico|de apoyo|complementario|practico)[^.]{0,120}(usd|dolares|valor|pago|costo|inversion)', 'Lo presenta como algo que "le corresponde" o que se activa con la compra y luego le pone precio'),
    ('material_academico', 'guion', r'\bmaterial academico\b', 'Llama "material académico" al complemento (el script dice evitarlo)'),
    # --- Presión comercial / precios
    ('urgencia', 'presion', r'(solo|unicamente) (por )?hoy[^.]{0,80}(precio|descuento|valor|oferta|beneficio|oportunidad|costo|usd|dolares)|(precio|descuento|valor|oferta|beneficio|oportunidad)[^.]{0,60}(solo|unicamente) (por )?hoy|(se (te |le )?vence|vence) (hoy|el link|la oferta|el descuento|el beneficio)|(ultimos|solo quedan|me quedan) (\w+ )?cupos|por tiempo limitado[^.]{0,40}(precio|descuento|oferta)', 'Escasez o urgencia ligada al precio ("solo por hoy")'),
    ('supervisor', 'presion', r'(me |lo |la )?(autoriz[oa]|aprob[oa]|habilit[oa])( a)?( mi| el| la)? (supervisor|supervisora|coordinador|coordinadora|jefe|gerente)|(mi|el|la) (supervisor|supervisora|jefe)[^.]{0,60}(me )?(autoriz|aprob|habilit|excepcion|descuento)|hable con mi (supervisor|supervisora|jefe)[^.]{0,80}(descuento|precio|excepcion|habilitar)', '"Me autorizó mi supervisor" un precio o excepción'),
    ('descuento_asesor', 'presion', r'(te|le) (puedo|podria|podemos|voy a|vamos a) (dejar|hacer|dar|aplicar|habilitar|entregar)[^.]{0,25}(descuento|precio especial|rebaja)|descuento (especial|exclusivo|academico) (para ti|contigo|para usted)|(te|le) (aplica|aplico) (el|un) descuento', 'Descuento o precio especial ofrecido por el asesor'),
    # --- Cobros poco claros
    ('nada_mas', 'cobros', r'no (vas|va|van) a (pagar|tener que pagar) nada mas|no se (te|le) (va a )?cobra(r|ra)? nada mas|no (hay|tienes|tiene) (ningun|otro) (cobro|pago) (adicional|extra|mas)|unico pago que (realizas|haces|vas a hacer|realizarias)? ?(durante|en) todo (el|tu)', '"No vas a pagar nada más" / "único pago durante todo el programa" (omite la membresía)'),
    # --- Pagos seguros
    ('tarjeta', 'pagos', r'(dicta|dame|dime|regalame|me (das|da|dice|dices|regala|dictas|dicta)|me (puedes|podrias|puede) (dar|dictar|decir|regalar))[^.]{0,30}(numero(s)? de (la |tu |su )?tarjeta|los (16|dieciseis) (digitos|numeros)|fecha de (vencimiento|expiracion)|codigo de seguridad|(el )?cvv|codigo que (te|le) (llego|lleg[oó]))|(los )?(tres|3) (digitos|numeritos) de atras', 'Pide datos de la tarjeta por teléfono'),
    ('terceros', 'pagos', r'tarjeta de (tu|su) (esposo|esposa|mama|papa|hijo|hija|hermano|hermana|pareja|novio|novia|amigo|amiga|familiar)|(pidele|pide|pidas|pedirle|pidale)[^.]{0,30}(prestad|un prestamo)|(hagas|hacer|saques|sacar) un prestamo', 'Sugiere préstamo o tarjeta de un familiar'),
    # --- Trato
    ('apelativo', 'trato', r'\bmi (amor|reina|rey|vida|cielo|corazon|princesa|bro|pana)\b|\bmamita\b|\bpapito\b|\bmija\b|\bmijo\b|(^|[,.!?¿¡] ?)corazon[,.!?]|\bcarino[,.!?]', 'Apelativos ("mi amor", "mi reina", "mija", "corazón")'),
    ('maltrato', 'trato', r'\b(no me (interrumpa|interrumpas))\b|\b(ya (te|le) (lo )?(dije|explique) (varias|mil|muchas) veces)\b|\bescucheme bien\b|\b(no sea|no seas) (terco|terca|grosero|grosera)\b|\busted no entiende\b|(?<!si )\btu no entiendes\b|\bque pereza\b', 'Trato brusco o descalificador'),
    # --- Promesas
    ('promesa', 'promesas', r'(te|le) (garantizo|garantizamos|aseguro|aseguramos)[^.]{0,40}(trabajo|empleo|ingreso|dinero|clientes)|(vas|va) a (conseguir|tener) (trabajo|empleo) (seguro|garantizado)|titulo (oficial|universitario)|validez oficial|avalad[oa] por (el gobierno|la sep|el estado)', 'Promete empleo, ingresos o validez oficial'),
    # --- Técnicas de cierre no autorizadas por el Speech
    ('ancla', 'presion', r'(normalmente|habitualmente|el valor (habitual|real|normal)|precio (normal|real|habitual)|tus companeros|tus companeras|los demas estudiantes|cada mes el estudiante|un estudiante (curricular|normal|regular)|se le entrega en ventas|sin descuento,? sin)[^.]{0,200}\b\d{2,4} ?(usd|dolares)', 'Precio ancla ("tus compañeros pagan 1.375 USD", "normalmente vale 550")'),
    ('regalo', 'presion', r'(te|le|nos) (vamos a )?(regal(o|a|amos|ar)|obsequi(o|a|amos|ar))[^.]{0,40}(clase|sesion|las otras|las restantes)|nos (encargamos|vamos a encargar) de (regalar|obsequiar)|(son|serian|quedan) \d+ (gratis|de regalo)|(te|le) (entrega|entregan|da|dan) las restantes', '"Te regalamos" clases (a cambio de pagar hoy)'),
    ('caducidad', 'presion', r'ya no (te|le) aplica (el|la) (descuento|beneficio|beca)|si (cuelgo|colgamos|termina la llamada)[^.]{0,60}(descuento|beneficio|precio|valor|ya no)|(solo|solamente|unicamente) (hasta|por) (el dia de )?hoy[^.]{0,40}(beneficio|descuento|oportunidad|precio|valor)|no (te|se) (lo|la) (podriamos|podemos|puedo) guardar|despues de (la|esta) activacion (ya )?no|se cierra el sistema|ya no va a salir', 'El "beneficio" se pierde si no paga hoy o al colgar'),
]
OLD = {('descuento' if k == 'descuento_asesor' else k): re.compile(p) for k, c, p, d in OLD_R if k in ('regalo', 'caducidad', 'urgencia', 'supervisor', 'descuento_asesor', 'terceros', 'tarjeta', 'nada_mas', 'apelativo', 'maltrato', 'promesa')}


def corte(i, n, desde=0.0, hasta=1.0):
    return n and desde <= i / n <= hasta

def analizar(c):
    ts = c['tx']
    # saltar transferencia interna: empieza donde el asesor se presenta
    i0 = 0
    for i, (_, q, t) in enumerate(ts[:40]):
        if q == 0 and RX['presenta'].search(norm(t)): i0 = i; break
    ts = ts[i0:]
    n = len(ts)
    A = [(i, norm(t)) for i, (_, q, t) in enumerate(ts) if q == 0]
    C = [(i, norm(t)) for i, (_, q, t) in enumerate(ts) if q == 1]
    chars_c = sum(len(t) for _, t in C)
    dur = round(((c['tx'][-1][0] if c['tx'] else 0) - (c['tx'][0][0] if c['tx'] else 0)) / 60, 1)
    # oferta: primer turno del asesor con un valor (excluye la membresía del saludo en Upsell)
    i_of, prod, precio, mpos = None, None, None, (0, 0)
    for i, t in A:
        m = RX_USD.search(t)
        if not m: continue
        prev = next((tt for ii, tt in reversed(A) if ii < i), '')
        win = (prev[-300:] + ' ' + t[max(0, m.start() - 260): m.end() + 120])
        if re.search(r'referid|ganas? 100', win): continue
        p = next((p for p, rx in PROD if rx.search(win)), None)
        if c['op'] == 'Upsell' and i / max(1, n) < 0.35 and (p in (None, 'Membresía / extensión') or 'membresia' in win): continue
        mpos = (m.start(), m.end())
        i_of, prod = i, p or {'Bootcamp': 'Bootcamp / proyecto', 'Resurrection': 'Membresía / extensión'}.get(c['op'], 'Otro')
        try: precio = float(m.group(1).replace(',', '.')) if re.match(r'\d', m.group(1)) else None
        except ValueError: precio = None
        break
    oferta = i_of is not None
    G = 'U' if c['op'] == 'Upsell' else 'O'
    venta = VP['p'].get(c['id'], 0) >= VP['rep'][G]['thr'] and n >= 8
    if venta and not oferta:
        oferta, i_of, prod = True, max(0, n // 2), (prod or ('Membresía / extensión' if c['op'] != 'Upsell' else 'Otro'))
    if venta: res = 'V'
    elif n < 8 or chars_c < 250 or dur < 2: res = 'I'
    else: res = 'N'
    # objeciones (después de la oferta; si no hay oferta, en toda la llamada)
    objs = []
    for i, t in C:
        if oferta and i <= i_of: continue
        for k, rx in CLI_OBJ:
            if rx.search(t) and k not in objs: objs.append(k)
    i_obj = next((i for i, t in C if (not oferta or i > i_of) and any(rx.search(t) for _, rx in CLI_OBJ)), None)
    # etapas: 1 cumple · 0 no cumple · None no aplica
    ini = [t for i, t in A if i / max(1, n) <= 0.3]
    fin = [t for i, t in A if i / max(1, n) >= 0.7]
    txt_a = ' '.join(t for _, t in A)
    s = {}
    s['saludo'] = int(any(RX['presenta'].search(t) for t in ini[:6]) and any(RX['grabacion'].search(t) for t in ini))
    rxc = RX['conexion_up'] if c['op'] == 'Upsell' else RX['conexion_rec']
    s['conexion'] = int(len({m.group(0) for t in ini + [t for i, t in A if i / max(1, n) <= 0.6] for m in rxc.finditer(t)}) >= 2)
    s['sondeo'] = int(bool(RX['sondeo'].search(' '.join(t for i, t in A if not oferta or i <= i_of + 2))))
    s['beneficio'] = int(bool(RX['beneficio'].search(txt_a)))
    s['integracion'] = int(bool(RX['integracion'].search(txt_a)))
    s['ejemplos'] = int(bool(RX['ejemplos'].search(txt_a)))
    s['precio'] = int(oferta)
    s['cierre1'] = int(any(RX_CIERRE.search(t) for i, t in A if i >= i_of)) if oferta else None
    s['objeciones'] = int(any(RX['obj_resp'].search(t) for i, t in A if i > i_obj)) if i_obj is not None else None
    s['cierre2'] = int(any(RX_CIERRE.search(t) for i, t in A if i > i_obj)) if (i_obj is not None and oferta) else None
    s['desp_v'] = int(any(RX['desp_v'].search(t) for t in fin)) if res == 'V' else None
    s['desp_nv'] = int(any(RX['desp_nv'].search(t) for t in fin)) if res == 'N' else None
    s['seguimiento'] = int(any(RX['seguimiento'].search(t) for t in fin)) if res != 'I' else None
    # señales de riesgo
    rk, citas = {}, {}
    for k, (cat, rx, _) in R.items():
        for i, t in A:
            m = rx.search(t)
            if m:
                rk[k] = rk.get(k, 0) + 1
                if k not in citas: citas[k] = (i, m.start(), m.end())
    for k, rx in OLD.items():
        for i, t in A:
            m = rx.search(t)
            if m:
                if k not in rk: rk[k] = 1
                if k not in citas: citas[k] = (i, m.start(), m.end())
                break
    sorpresa = any(CLI_OBJ[4][1].search(t) for _, t in C)
    queja = any(RX_QUEJA.search(t) for _, t in C)
    neg = sum(1 for i, t in C if (not oferta or i > i_of) and any(rx.search(t) for _, rx in CLI_OBJ))
    if venta and neg >= 4: rk['presion'] = 1
    win = ' '.join(t for i, t in A if oferta and i <= i_of + 3)
    opc, comp = (dice(RX_OPC, win), dice(RX_COMPL, win)) if oferta else (None, None)
    memb_any = bool(RX_MEMB_ANY.search(txt_a))
    if oferta and not (opc or comp):
        for i, t in A:
            if i > i_of + 3: break
            m = RX_MAT.search(t)
            if m: rk['cond_impl'] = 1; citas['cond_impl'] = (i, m.start(), m.end()); break
    if c['op'] == 'Upsell' and not memb_any:
        for i, t in A:
            m = RX_UNICO.search(t)
            if m: rk['unico_sin_memb'] = 1; citas['unico_sin_memb'] = (i, m.start(), m.end()); break
    # buenas prácticas / checks
    chk = {
        'grabacion': int(any(RX['grabacion'].search(t) for t in ini)),
        'memb': int(bool(RX['memb'].search(' '.join(ini)))) if c['op'] == 'Upsell' else None,
        'opcional': int(bool(opc)) if oferta else None,
        'complemento': int(bool(comp)) if oferta else None,
        'memb_any': int(memb_any) if c['op'] == 'Upsell' else None,
        'link': int(bool(RX['link'].search(txt_a))) if venta else None,
        'oferta_temprana': int(i_of / max(1, n) < 0.2) if oferta else None,
    }
    # silencios largos del asesor (> 60 s entre turnos)
    gaps = [b[0] - a[0] for a, b in zip(c['tx'], c['tx'][1:])]
    s60 = sum(1 for g in gaps if g > 60)
    return dict(res=res, of=int(oferta), pr=prod, precio=precio, dur=dur, n=n, st=s, ob=objs, rk=rk, chk=chk,
                sorp=int(sorpresa), queja=int(queja), s60=s60, i_of=i_of, ts=ts, citas=citas, i_obj=i_obj)

# ---------------------------------------------------------------- citas (enmascaradas)
def limpiar(t, todo=False):
    t = re.sub(r'\S+@\S+', '[correo]', t)
    if todo:
        t = re.sub(r'\d', '•', t)
        return re.sub(r'\b(cero|uno|una|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|once|doce|trece|catorce|quince|dieci\w+|veinte|veinti\w+|treinta|cuarenta|cincuenta|sesenta|setenta|ochenta|noventa|cien|ciento|\w+cientos|mil)\b', '•', t, flags=re.I)
    return re.sub(r'\d[\d ,.-]*\d(?! ?(usd|dolares|dólares))', lambda m: m.group(0) if len(re.sub(r'\D', '', m.group(0))) < 4 else '••••', t)

def frase(t, a=None, b=None, w=170):
    """Recorta el texto original alrededor de la coincidencia (las posiciones vienen del texto normalizado, que tiene el mismo largo)."""
    if a is None: a, b = 0, min(len(t), w * 2)
    x, y = max(0, a - w), min(len(t), b + w)
    s = t[x:y].strip()
    return ('…' if x > 0 else '') + s + ('…' if y < len(t) else '')

STRX = {'saludo': RX['presenta'], 'conexion': re.compile(RX['conexion_up'].pattern + '|' + RX['conexion_rec'].pattern), 'sondeo': RX['sondeo'], 'beneficio': RX['beneficio'], 'integracion': RX['integracion'],
        'ejemplos': RX['ejemplos'], 'precio': RX_USD, 'cierre1': RX_CIERRE, 'objeciones': RX['obj_resp'], 'cierre2': RX_CIERRE,
        'desp_v': RX['desp_v'], 'desp_nv': RX['desp_nv'], 'seguimiento': RX['seguimiento']}

rows, EJ, QUO = [], collections.defaultdict(lambda: collections.defaultdict(list)), {}
TX = collections.defaultdict(dict)
for c in LL:
    a = analizar(c)
    ts = a['ts']
    rows.append([c['id'], c['fecha'], c['op'], c['t'], c['sup'], c['ag'], a['res'], a['of'], a['pr'], a['precio'], a['dur'],
                 [a['st'][k] for k in ST], a['ob'], a['rk'], a['chk'], a['sorp'], a['queja'], a['s60'], c['old']])
    TX[(c['mes'], c['op'], c['t'])][c['id']] = c['tx']
    key = (c['mes'], c['op'])
    # citas de riesgo (todas las llamadas)
    for k, (i, x, y) in a['citas'].items():
        if k != 'ancla':
            QUO.setdefault(c['id'], {})[k] = limpiar(frase(ts[i][2], x, y, 140), k in ('tarjeta', 'terceros'))
        if len(EJ[key]['rk_' + k]) < 60:
            EJ[key]['rk_' + k].append(dict(id=c['id'], ag=c['ag'], sup=c['sup'], t=c['t'], f=c['fecha'], res=a['res'],
                                          q=limpiar(frase(ts[i][2], x, y), k in ('tarjeta', 'terceros'))))
    # citas de etapas en ventas (para «llamadas que funcionan»)
    if a['res'] == 'V':
        for k in ST:
            if a['st'][k] != 1 or len(EJ[key]['st_' + k]) >= 40: continue
            rx = STRX.get(k)
            if not rx: continue
            hit = next(((i, m) for i, (_, q, t) in enumerate(ts) if q == 0 for m in [rx.search(norm(t))] if m), None)
            if not hit: continue
            i, m = hit
            nxt = next((t for _, q, t in ts[i + 1:i + 3] if q == 1), '')
            EJ[key]['st_' + k].append(dict(id=c['id'], ag=c['ag'], t=c['t'], f=c['fecha'], q=limpiar(frase(ts[i][2], m.start(), m.end(), 150)), r=limpiar(nxt[:160])))

json.dump(dict(ST=ST, cols=['id', 'fecha', 'op', 'turno', 'sup', 'ag', 'res', 'of', 'pr', 'precio', 'dur', 'st', 'ob', 'rk', 'chk', 'sorp', 'queja', 's60', 'old'], rows=rows),
          open(OUT + '/calls.json', 'w', encoding='utf-8'), ensure_ascii=False)
json.dump(QUO, open(OUT + '/quo.json', 'w', encoding='utf-8'), ensure_ascii=False)
json.dump({f'{m}|{o}': v for (m, o), v in EJ.items()}, open(OUT + '/ej.json', 'w', encoding='utf-8'), ensure_ascii=False)
for (m, o, t), v in TX.items():
    nombre = f"{m}_{o.lower()}" + (f"_{t.lower().replace(' ', '_')}" if t else '')
    json.dump(v, open(f'{OUT}/tx_{nombre}.json', 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
cnt = collections.Counter((r[1][:7], r[2], r[6]) for r in rows)
print('llamadas', len(rows))
for k in sorted(cnt): print(k, cnt[k])
