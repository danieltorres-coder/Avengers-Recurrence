# Pestaña "092026 - Tracker:MKTSales" en el dashboard

## Corrección importante (18-sep)
La primera versión de esta pestaña usaba un desglose por día (14-17 sep) con PLAN/PROYECCIÓN estimados a mano. Eso no correspondía a cómo está armada la pestaña real del Sheet. Ahora los datos se leen **directo de la pestaña del Sheet, celda por celda**: desglose por **semana del mes** (1ra a 5ta semana, tal como está en el Sheet) y PLAN / PROYECCIÓN / DIFERENCIA **ya calculados ahí** — nada estimado ni inventado.

## Qué trae esta versión
- Botón en la navegación: **"092026 - Tracker:MKTSales"**.
- Filtro por operación (pills: Todas / Upsell / Recurrence / Bootcamp LTV / Resurrection).
- Resumen ejecutivo automático por operación: 🔎 **A vigilar** (el KPI con la mayor desviación negativa vs. su referencia, entre las semanas que ya arrancaron) y 🟢 **Amortiguador** (el de mayor desviación positiva).
- Celdas resaltadas en rojo/verde cuando una semana se desvía 15% o más de su referencia. Las semanas que aún no arrancan se muestran en blanco (no se evalúan).
- Tabla de detalle semanal del mes en curso (1ra-5ta semana + Acumulado MTD + PLAN + PROYECCIÓN + Diferencia, tal como el Sheet) y tabla de tendencia mensual (Sep 2025 / Jun / Jul / Ago / Sep MTD) por operación.
- Datos en `data/tracker_2026-09.json`, generados directamente del archivo del Sheet (no de un resumen de texto).

## KPIs por operación (los mismos que usamos en el brief manual)
- **Upsell**: Expansion → Revenue → CR general → ASP + Volumen de ventas (1st Sales).
- **Recurrence**: Revenue → CR sobre Calls ≥2min → ASP + Contactabilidad (% Calls ≥2min).
- **Bootcamp LTV**: Revenue → ASP → CR sobre Calls ≥2min + Contactabilidad (% Calls ≥2min).
- **Resurrection**: Revenue → ASP → Conversión (Calls ≥2min) → Elegibles + Contactabilidad (% Calls ≥2min).

## Cómo se calcula la "referencia" de cada semana
- **Revenue y Volumen** (KPIs que se acumulan día a día): la referencia es el PLAN mensual **prorrateado** por los días de esa semana que ya pasaron — así una semana parcial (como la del 15-21 sep, en curso) se compara de forma justa.
- **ASP y las tasas (%)**: no se prorratean — se comparan directo contra el PLAN mensual, porque son promedios/tasas, no algo que se acumule con los días.

## Visión estratégica de esta pestaña
La idea es que sea la vista de "sala de guerra" para el Director de Ventas: en 5 segundos, sin leer ninguna tabla, las 4 tarjetas de resumen le dicen qué operación tiene un problema real (🔎) y cuál tiene margen para compensar (🟢) — igual a como armamos el brief de lunes a jueves, pero ahora automático, repetible cada semana, y con los números tal cual los calcula el Sheet.

## Filtros recomendados (ya incluidos)
1. **Por operación** — ya implementado.
2. **Resaltado por desviación** — ya implementado (15% de umbral). Si quieres un umbral distinto por KPI, dímelo y lo ajusto.

## Filtros que NO incluí (para que decidas si valen la pena)
- **Por mes**: hoy no lo puse porque solo hay un mes cargado (septiembre). En cuanto agregues octubre, vale la pena agregarlo.
- **Umbral de desviación ajustable**: lo dejé fijo en 15%.

## Cómo subirlo
1. Reemplaza tu `index.html` por el de este paquete.
2. Reemplaza `tracker_2026-09.json` en `data/` (mismo nombre, contenido corregido).
3. `tracker_manifest.json` no cambió — no hace falta volver a subirlo si ya lo subiste.
4. Sube (commit + push).

## Sigue siendo manual (igual que el resto del dashboard)
No lee el Google Sheet en vivo — lee este `.json` ya guardado en el repo. Si editas la pestaña 092026 - Tracker:MKTSales en Sheets, avísame y regenero el `.json` con los números nuevos.

## Cómo cargar el siguiente mes
Cuando tengas la pestaña del siguiente mes lista en el Sheet, avísame y te genero `tracker_2026-10.json` con este mismo método (directo del Sheet, no de resúmenes). Tú solo:
1. Agregas ese archivo a `data/`.
2. Agregas `"2026-10"` al final de `months` en `tracker_manifest.json`.
3. Subes los dos archivos — el dashboard toma automáticamente el último mes de la lista como "mes en curso" (con desglose semanal) y deja los anteriores en acumulado mensual.
