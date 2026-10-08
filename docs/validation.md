# Validación del laboratorio

Estado: límites y experimento propuestos para revisión humana. La configuración de ejemplo no activa operaciones. Capital exacto, integrantes, sesión, proveedor y tarifas están pendientes. La versión 0.2 implementa cálculos puros de riesgo, estadísticas y un panel de consulta; todavía no captura mercados ni genera ejecuciones prospectivas automáticamente.

Aprobar una estrategia y superar pruebas no autoriza dinero real.

## Preparación y límites
Registrar capital C0, estrategia, universo, sesiones America/Santiago y tiempos UTC, fuentes, tarifas con mínimos, precisión, efectivo liquidado, liquidez y tipo de cambio con hora. Costes o datos insuficientes: NO OPERAR.

Cbase = mínimo(C0, patrimonio al inicio de sesión). Límites propuestos:
- Riesgo por operación con costes: 0,25% de Cbase.
- Exposición por operación: 20%; total: 40%.
- Riesgo abierto: 0,50%; máximo dos posiciones.
- Pérdida diaria: 0,75%; máximo tres entradas por sesión.
- Suspensión por caída del 5% desde el máximo patrimonial o pérdida del 5% desde C0.
- Relación neta ganancia/pérdida prevista mínima: 2.
- Costes de ida y vuelta: máximo 25% del presupuesto de riesgo por operación.

La pérdida diaria incluye posiciones abiertas y costes estimados de liquidación. Antes de otra entrada, el riesgo abierto más el nuevo debe caber en el presupuesto diario restante. No añadir aportes/retiros durante el experimento.

Estos límites son presupuestos, no garantías: saltos, falta de liquidez y deslizamiento pueden superar el stop. Alcanzar un límite bloquea entradas, registra liquidación simulada con costes y exige revisión humana.

## Motor
Verificar contabilidad, cantidades mínimas, redondeo, efectivo, comisiones mínimas, FX, límites y datos vencidos. Comprar al ask y vender al bid, con deslizamiento adicional; no duplicar costes incorporados al precio.

Si una vela toca objetivo y stop sin conocer el orden, asumir desenlace adverso o marcar indeterminada. La entrada ocurre en el siguiente evento ejecutable después de la decisión, nunca retrospectivamente.

## Historia y simulación prospectiva
Separar desarrollo, validación y prueba final en orden cronológico, fijando fechas antes de optimizar. No barajar fechas ni usar información futura. Documentar ajustes corporativos, instrumentos deslistados cuando proceda y sesgos del universo.

Registrar todas las variantes ensayadas, incluidas las fallidas. Congelar una estrategia antes de la simulación prospectiva: al menos 60 sesiones y 100 operaciones cerradas, cumpliendo ambos mínimos. No forzar entradas. Una modificación inicia una nueva versión experimental; conservar el experimento anterior.

Los mínimos operativos no demuestran rentabilidad futura.

## Métricas y decisión
- Retorno = (patrimonio final - C0) / C0, sin flujos externos.
- Aciertos = operaciones con beneficio / operaciones cerradas; empates en el denominador.
- Expectativa = media del resultado neto por operación; medir también resultado/riesgo inicial.
- Profit factor = ganancias / pérdidas absolutas; sin pérdidas, indicar no estimable y tamaño de muestra.
- Drawdown = mayor caída porcentual desde el máximo patrimonial previo, incluyendo posiciones abiertas.
- Costes, señales rechazadas, días sin operar, exposición e incidencias.

Comparar con efectivo CLP y una referencia previamente elegida, usando mismas fechas, moneda y costes comparables. Mostrar diferencias de riesgo.

Exigir registros completos, cero vulneraciones no resueltas, expectativa positiva y caída máxima dentro del límite. Evaluar escenario predefinido con doble spread y deslizamiento adicional; mantener tarifas verificadas y exigir resultado neto positivo. Estimar incertidumbre por bloques de días: si el intervalo incluye cero, INCONCLUSO. No reajustar parámetros mirando esa prueba.

Presentar resultado neto de ejecución antes de impuestos. Gastos de datos/infraestructura y conciliación fiscal se muestran aparte. Revisar tratamiento por instrumento y titular antes de evaluar dinero real, sin tasa universal inventada.

Resultado válido: NO VIABLE PARA ESTE CAPITAL o EVIDENCIA INSUFICIENTE. No anualizar pocas semanas como promesa.

## Fuentes
- [FINRA: costes y riesgos intradía](https://www.finra.org/rules-guidance/rulebooks/finra-rules/2270).
- [SII: criptomonedas](https://www.sii.cl/preguntas_frecuentes/criptomonedas/001_250_7872.htm).
