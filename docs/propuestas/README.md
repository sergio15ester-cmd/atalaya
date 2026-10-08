# Propuestas económicas de Atalaya — borrador para deliberación

Fecha: 2026-10-08. Estado: PROPUESTO, sin decisión del equipo.

## Objetivo y límite de esta propuesta

Comparar vías para generar utilidades y capital reinvertible mediante colaboración humana e IA. El trading existente sigue siendo una alternativa. Este documento no cambia el alcance aprobado, las reglas de gobernanza, los límites de riesgo ni la autorización de operaciones. Los datos privados de aportes y participantes permanecen fuera de esta documentación.

Hay dos economías distintas: invertir capital y vender trabajo/productos. Los servicios pueden facturar, pero consumen horas comerciales y operativas. Si el equipo solo acepta una actividad pasiva, esa restricción cambia la selección y deben descartarse las propuestas que exijan atención a clientes.

## Comparación inicial

Precios, costes y esfuerzos son hipótesis de prueba, no cotizaciones de mercado. Costes monetarios estimados excluyen horas, impuestos y licencias ya disponibles. No se asume acceso gratuito a herramientas pagadas.

| Prioridad propuesta | Alternativa | Oferta mínima | Hipótesis de precio | Esfuerzo exploratorio estimado | Evidencia y obstáculo |
|---|---|---|---|---|---|
| 1 | Conciliación y reporte por archivos | Un período, una cuenta, dos archivos y excepciones revisables | CLP 60.000 por piloto; CLP 30.000 por repetición del mismo formato | 6 h de demo reusable + 8 h del primer piloto, incluyendo captación | S1–S4: solicitudes directas; falta un cliente dispuesto a pagar por nuestro alcance |
| 2 | Calidad de datos territoriales | Hasta 100 registros de una comuna, control de coordenadas/direcciones y mapa | CLP 60.000 por lote acotado | 5–8 h por lote incluyendo captación, por comprobar | S5–S6: problema adyacente y herramienta disponible; muchos casos ambiguos pueden consumir el margen |
| 3 | Radar sectorial de compras públicas | Un rubro, una región y una selección explicada con fuentes | CLP 20.000 por mes como hipótesis | 6–10 h de preparación y 2 h mensuales por cliente, por comprobar | S7–S8: datos y competencia; alertas genéricas ya tienen sustitutos |
| 4 | Simulación de inversión | Un mercado, estrategia fijada y contabilidad con costes | Sin venta ni rentabilidad prometida | Alcance técnico actual incompleto; estimar tras ejecutar la base | S9–S10: fuente disponible; no hay evidencia de ventaja ni tarifa completa verificada |

No desarrollar las cuatro opciones a la vez. Proponer una opción principal y mantener las otras en evaluación. Los recursos se asignan solo tras acuerdo humano. Plantillas o una aplicación vendible pueden derivarse de un servicio repetido; no se presupone que construir primero un SaaS cree demanda.

## Primer experimento recomendado para discutir

Piloto de conciliación por archivos para un cliente privado. Entrega: archivo con conciliados, pendientes, ambigüedades, totales y un resumen de diferencias. Una cuenta, una moneda, un mes y hasta 500 filas por entrada. Una ronda de correcciones dentro del alcance. No incluye declaraciones tributarias, credenciales bancarias, extracción automática ni soporte permanente.

La prueba comercial se hace antes de ampliar el producto: cinco conversaciones calificadas, al menos dos confirmaciones de un problema recurrente y una aceptación explícita del alcance/precio. Los contactos y envíos requieren instrucciones concretas del equipo. Registrar también rechazos y objeciones. Cinco conversaciones no prueban tamaño de mercado; sirven para decidir si avanzar al siguiente experimento.

La demo utiliza datos sintéticos. Se mide tiempo manual contra asistido con las mismas entradas y se exige cero conciliaciones incorrectas marcadas como definitivas en el conjunto revisado. Los casos ambiguos deben quedar pendientes. Meta propuesta: ahorrar al menos 50% del tiempo del caso de prueba; se informa el tamaño de muestra y no se generaliza desde una demo.

## Secuencia por hitos, sin carga semanal obligatoria

1. El equipo compara las cuatro opciones, acuerda una prueba y fija su tope de gasto/horas.
2. Valida el problema con cinco conversaciones; primera revisión al completar las cinco o en dos semanas desde el inicio aprobado, lo que ocurra primero.
3. Construye una demo acotada y revisada. Máximo exploratorio propuesto: seis horas antes de reevaluar.
4. Ejecuta un único piloto pagado con alcance y entrega acordados. Cuenta captación, desarrollo, revisión y soporte.
5. Decide repetir, ajustar precio/alcance o detener. No compra infraestructura recurrente sin uso demostrado.

Si no hay voluntad de pago tras la prueba, no se agregan funciones por inercia. Si todas las personas consultadas piden otra solución, se registra el hallazgo y se propone un nuevo experimento. Una venta no demuestra repetibilidad: buscar al menos dos entregas comparables y una recompra antes de considerar expansión.

## Otras alternativas, con límites claros

**Datos territoriales:** entregar calidad y trazabilidad. Un punto sugerido no se etiqueta como domicilio confirmado; no inferir precisión desde una dirección ambigua. El piloto puede usar coordenadas aportadas por el cliente y QGIS. Proveedores de geocodificación, licencias y costes se revisan antes de prometer enriquecimiento externo. No incluye levantamiento de terreno ni informes periciales.

**Radar:** comenzar manualmente con fuentes oficiales para comprobar relevancia. La diferencia por validar sería curación de un nicho y explicación de requisitos; la competencia ya ofrece IA. Propuesta de paso técnico: veinte resultados evaluados, al menos dieciséis relevantes y todos con enlace/fecha/plazo verificados; después solicitar ticket oficial si el equipo elige avanzar. No postular, ofertar ni representar al cliente automáticamente.

**Trading:** conservar el experimento de simulación, obtener tarifas aplicables y completar entradas/salidas, posiciones abiertas y referencia comparable. No computar ganancias simuladas como ingresos del negocio. Mantener los criterios de validación actuales; esta comparación no los reduce ni autoriza dinero real.

**Comercio físico, afiliación y productos digitales genéricos:** no priorizados en esta ronda porque no hay un producto, audiencia ni demanda específica validada. Es una ausencia de evidencia local, no una conclusión de inviabilidad.

Fuentes: [registro de evidencia](fuentes.md). Economía: [escenarios](economia.md). Implementación propuesta: [backlog](backlog.md).
