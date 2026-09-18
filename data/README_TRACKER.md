# Pestaña "092026 - Tracker:MKTSales" en el dashboard

## Qué trae esta versión
- Botón nuevo en la navegación: **"092026 - Tracker:MKTSales"**.
- Filtro por operación (pills: Todas / Upsell / Recurrence / Bootcamp LTV / Resurrection) — igual al patrón de "Grupo de agentes" que ya usa el resto del dashboard.
- Resumen ejecutivo automático por operación: 🔎 **A vigilar** (el KPI con la mayor desviación negativa vs. su referencia) y 🟢 **Amortiguador** (el de mayor desviación positiva) — mismo criterio de "mayor desviación %" que usamos en el análisis 14-17 sep, ahora calculado solo, para cualquier mes que cargues.
- Celdas resaltadas en rojo/verde en las tablas de detalle cuando un día se desvía 15% o más de la referencia de ese KPI — así el "día con zoom" salta a la vista sin tener que leer cada número.
- Tabla de detalle del mes en curso (desglose diario + Acumulado + Referencia + PLAN + PROYECCIÓN + Diferencia) y tabla de tendencia mensual (Jun/Jul/Ago/MTD) por operación.
- Datos en `data/tracker_2026-09.json` (ya corregido: el PLAN de "Elegibles" de Resurrection ahora muestra "—" en vez de un error, no tenía PLAN definido en el Sheet).

## Visión estratégica de esta pestaña
La idea es que sea la vista de "sala de guerra" para el Director de Ventas: en 5 segundos, sin leer ninguna tabla, las 4 tarjetas de resumen le dicen qué operación tiene un problema real (🔎) y cuál tiene margen para compensar (🟢) — igual a como armamos el brief de lunes a jueves, pero ahora automático y repetible cada vez que cargues un mes nuevo. Las tablas de abajo son para cuando alguien quiere entrar al detalle de por qué, no para el primer vistazo.

## Filtros recomendados (ya incluidos)
1. **Por operación** — ya implementado. Es el filtro más importante porque cada operación tiene su propia lista de KPIs prioritarios (no son comparables entre sí), así que ver "Todas" junto es solo para el panorama general.
2. **Resaltado por desviación** — ya implementado (15% de umbral, el mismo que usamos a mano). Si más adelante quieres un umbral distinto por KPI (ej. que Revenue sea más sensible que ASP), dímelo y lo ajusto — hoy es un solo umbral para todos.

## Filtros que NO incluí (para que decidas si valen la pena)
- **Por mes** (como el filtro "Meses" del resto del dashboard): hoy no lo puse porque solo hay un mes cargado (septiembre). En cuanto agregues el segundo mes (octubre), vale la pena agregar este filtro para comparar meses lado a lado — te lo puedo construir cuando llegue ese momento.
- **Umbral de desviación ajustable** (un control deslizante para subir/bajar el 15%): lo dejé fijo porque agregar un control interactivo ahí es más código sin necesidad clara todavía — dime si lo quieres.

## Cómo subirlo
1. Reemplaza tu `index.html` por el de este paquete (o aplica `index.html.diff`).
2. Copia `tracker_2026-09.json` y `tracker_manifest.json` a `data/`.
3. Sube (commit + push).

## Sigue siendo manual (igual que el resto del dashboard)
No lee el Google Sheet en vivo — lee estos `.json` ya guardados en el repo. Si editas la pestaña 092026 - Tracker:MKTSales en Sheets, hay que regenerar el `.json` y volver a subirlo, igual que ya haces con "Year Calls" y las demás.

## Cómo cargar el siguiente mes
Cuando tengas la pestaña del siguiente mes lista en el Sheet, compártemela y te genero `tracker_2026-10.json`. Tú solo:
1. Agregas ese archivo a `data/`.
2. Agregas `"2026-10"` al final de `months` en `tracker_manifest.json`.
3. Subes los dos archivos — el dashboard toma automáticamente el último mes de la lista como "mes en curso" (con desglose diario) y deja los anteriores en acumulado mensual.
