# Backlog propuesto — no equivale a autorización de desarrollo completo

Fecha: 2026-10-08. Todas las tareas están por hacer. Este archivo no crea Issues ni asigna personas.

| ID | Prioridad | Tarea | Criterio de aceptación |
|---|---|---|---|
| A-001 | P0 | Incorporar dossier y plantillas mediante PR documental | Solo archivos nuevos bajo docs/propuestas y templates/propuestas; sin sobrescribir trabajo, sin cambiar reglas; fuentes, supuestos y estado propuesto visibles |
| A-002 | P0 humano | Elegir prueba, presupuesto y dedicación máxima | Decisión de los tres registrada en privado; confirmar si se acepta prestar servicios a clientes; no convertir silencio en aprobación de gasto |
| A-003 | P1 | Ficha comercial y validación del problema | Alcance, precio a probar, cinco conversaciones autorizadas y objeciones registradas; al menos una aceptación para pasar al piloto |
| A-004 | P1 condicional | Demo local de conciliación por archivos | Un banco/formato, moneda y período; montos exactos; conciliados/pendientes/ambiguos y totales reconciliados; únicamente ejemplos sintéticos en Git |
| A-005 | P1 condicional | Verificar calidad y tiempos | Cubrir duplicados, reversos, importes repetidos, fechas, separador decimal y entradas inválidas; ninguna coincidencia dudosa como definitiva; comparación manual/asistida |
| A-006 | P1 | Registro económico y reporte del experimento | Ingresos, costes, comisiones y horas diferenciados; resultados reales/simulados/proyectados separados; exportación con período y evidencia |
| A-007 | P2 independiente | Auditar motor de simulación existente | Reproducir pruebas en rama vigente; confirmar bloqueo temprano de cálculos antes de proponer separación cálculo/autorización; conservar controles |
| A-008 | P2 condicional | Prueba de calidad territorial | Lote sintético de hasta 100 registros; fuente, estado y precisión declarados; inciertos pendientes; estimación de tiempo |
| A-009 | P2 condicional | Prueba manual del radar | Veinte resultados de un rubro/región, relevancia y plazos cotejados; estudiar condiciones/cuotas de API antes de conectar |
| A-010 | P2 condicional | Completar simulación de mercado | Una fuente verificada, tarifas vigentes, posiciones abiertas, costes y referencia; mantener validación y modo paper |

## Encargo para Codex tras la decisión comercial

Leer AGENTS.md y documentación actual antes de modificar. Trabajar en una rama propia y entregar PR. Seleccionar A-004/A-005 solo si A-002/A-003 habilitan el piloto. No construir autenticación, SaaS, cobros, bancos conectados ni una orquestación de agentes para la demo. Si el equipo elige otra alternativa, cambiar el encargo mediante una decisión registrada.

La lógica numérica y las conciliaciones deben ser deterministas. La IA puede sugerir categorías o redactar explicaciones, sin sustituir la evidencia ni confirmar coincidencias ambiguas. Evitar que fórmulas o contenido de archivos importados se ejecuten al abrir exportaciones. Conservar originales y trazabilidad de cada decisión.

Para A-007, iniciar desde la rama con el código existente o su equivalente ya integrado. main puede contener solo el README; inspeccionar el estado actual. No fusionar automáticamente la PR de fundación ni reescribirla. Ejecutar pruebas proporcionales y no declarar verificaciones que no se hayan realizado.
