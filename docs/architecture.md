# Arquitectura y primera aplicación

## Componentes
1. Adaptadores de datos de solo lectura: mercados, noticias y tipos de cambio.
2. Normalización: instrumento, mercado, moneda, bid/ask, volumen, fuente, hora del mercado, recepción y cobertura.
3. Analistas de mercado, técnico y noticias: trabajan sobre el mismo snapshot.
4. Motor determinista de riesgo/costes: admite o rechaza una propuesta.
5. Coordinador: registra contradicciones, evidencia y conclusión.
6. GitHub: versiones, propuestas, votos, decisiones y desarrollo.
7. Simulador: entradas/salidas hipotéticas y contabilidad separada.
8. Dashboard local: consulta datos y decisiones; no ejecuta operaciones reales.

Seis agentes son seis contratos de trabajo, no seis servicios permanentes ni seis fuentes independientes cuando comparten evidencia.

## Datos
Evaluar una fuente y un universo pequeño inicialmente. Cripto en CLP puede investigarse con la [API pública de Buda](https://api.buda.com/); sus cotizaciones simuladas no garantizan ejecución. Verificar tarifa, mínimo, precisión, profundidad y licencia para el mercado concreto.

En acciones/ETF, indicar explícitamente retraso y cobertura. [Alpaca](https://docs.alpaca.markets/us/docs/about-market-data-api) distingue IEX y SIP; no asumir que datos de una bolsa son el mercado consolidado.

No integrar cuentas con permisos de trading. Las API autenticadas, si se necesitan, serán de solo lectura y sus secretos se mantendrán fuera del repositorio.

## Aplicación mínima
Python + Streamlit, ejecutado localmente durante sesiones configuradas. Archivos JSON/JSONL con esquemas versionados para intercambio; SQLite local como caché reconstruible, no comprometida en Git. Un único escritor del historial en la primera versión evita conflictos.

Cuatro vistas:
- Resumen: patrimonio simulado, resultado neto, exposición, caída máxima y bloqueos.
- Mercado: lista de observación, antigüedad/cobertura y hasta tres oportunidades.
- Operaciones: historial, costes y resultados por estrategia y modo.
- Equipo: votaciones, decisiones y evidencias; enlazar a GitHub para votar.

La primera versión mostrará SIMULACIÓN de forma visible. La configuración incompleta impedirá generar entradas. No tendrá botones para operar con dinero real.

## Desarrollo por prioridad
- P0: incorporar esta documentación; habilitar acceso privado y tres integrantes antes de datos del equipo.
- P1: confirmar capital, fuente, tarifas, mínimos, sesión y configuración humana; implementar contabilidad/riesgo.
- P2: una fuente de datos, esquemas e informe; datos insuficientes producen NO OPERAR.
- P3: dashboard local y exportación reproducible de registros.
- P4: experimento prospectivo congelado y revisión semanal.
- P5: automatización de lotes y eventual acceso compartido con autenticación y presupuesto.

## Automatización
GitHub Actions: pruebas, validación de esquemas, informes de lote y conciliación de votos. Las ejecuciones programadas pueden retrasarse o perderse; el plazo registrado es la autoridad, no la hora de inicio de un job. [Documentación](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows).

Captura intradía/streams/alertas rápidas: requieren un proceso activo y supervisado. Primero una sesión local; evaluar infraestructura externa únicamente con costes y permisos definidos.

Work: investigación bajo demanda o tareas expresamente configuradas según cuenta/conexiones. No presumir vigilancia permanente. [Tareas programadas](https://help.openai.com/en/articles/10291617-scheduled-tasks-in-chatgpt).

La versión 0.2 incorpora el panel local, cálculos de riesgo/estadísticas, informes y evaluador puro de votaciones. Hay un workflow de pruebas con datos ficticios; no hay trabajos de operaciones, conexiones financieras ni agentes autónomos activos. No contratar servicios ni gastar capital sin autorización.

## Trazabilidad
Cada decisión incluirá ID, fecha UTC y America/Santiago, autores/agentes, fuentes, snapshot, versiones de código/instrucciones/configuración, resultado y razones. Las correcciones son nuevos eventos enlazados al original.

Conservar respaldos externos revisados por humanos. GitHub y hashes ayudan a detectar cambios respecto de una copia; no convierten el historial en inmutable frente a administradores.

## Fiscalidad
Registrar compras, ventas, monedas, comisiones y respaldos cuando corresponda. El resultado principal será neto de ejecución antes de impuestos. Antes de dinero real, definir titularidad y tratamiento de cada instrumento/contribuyente, usando fuentes del SII. No aplicar una tasa plana inventada.
