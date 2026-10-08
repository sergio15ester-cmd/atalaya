# Gobernanza semanal

Especificación para implementar. El scaffold permite redactar propuestas: crear una Issue, reaccionar o aprobar una PR no constituye un voto operativo ni una autorización financiera.

Mientras el repositorio sea público, solo borradores sin datos personales. La votación operativa requiere privacidad, identidades verificadas y controles implementados.

## Reglas
Tres humanos con derecho a voto; todos reciben solicitud semanal sobre estrategia, límites y cambios relevantes.
1. Tres aprobaciones válidas: aprobado.
2. Dos aprobaciones y tercero sin responder: la IA puede ratificar después del plazo, verificando votos, vencimiento y seguridad.
3. Oposición expresa, conflicto o menos de dos aprobaciones al vencer: revisión humana.
4. Toda decisión registra fecha, responsables, evidencia y justificación.
5. La IA no puede modificar unilateralmente estas reglas.
6. Estrategia aprobada no autoriza operaciones reales.

Antes del vencimiento, las aprobaciones insuficientes mantienen la votación pendiente. La vigencia expira sin nueva confirmación semanal.

Calendario propuesto, pendiente de acuerdo: solicitud viernes 18:00 y cierre domingo 20:00 America/Santiago, para la semana siguiente.

## Propuesta sellada
Debe fijar ID/revisión, commit, hash de contenido, versión de gobernanza, hash de riesgos, tres participantes verificados, apertura/vencimiento/vigencia, evidencia de convocatoria y modalidad.

El hash comprende estrategia, activos, límites, costes, suspensiones y vigencia. Todos votan exactamente esa revisión. Campos incompletos: DRAFT. Cambios sustanciales: nueva revisión, convocatoria y votos; sin traslado de aprobaciones.

## Identidad y convocatoria
Verificar cada voto mediante el ID numérico autenticado de GitHub y la lista autorizada de tres humanos. No confiar en nombres escritos, reacciones ni asociación aparente al repositorio. Bots/agentes no votan. El humano proponente conserva su derecho a voto.

Comprobar acceso de los tres y canal acordado; registrar solicitud, hora y evidencia de envío. Una mención no prueba lectura. Fallos conocidos de entrega/acceso impiden ratificar por silencio.

No publicar identidades personales en ejemplos públicos.

## Votos
Formato futuro, una vez sellada la propuesta:

    APPROVE <proposal_id> <content_sha256>
    OPPOSE <proposal_id> <content_sha256>
    WITHDRAW <proposal_id> <content_sha256>

Cada integrante cuenta una vez; duplicados son idempotentes. Abstención, retirada o respuesta ambigua no equivale a silencio.

Oposición expresa, incluso en lenguaje natural, requiere revisión humana. OPPOSE seguido de APPROVE conserva el conflicto; solo humanos lo resuelven o abren otra revisión.

Conservar evidencia de ediciones/eliminaciones. Si no puede reconstruirse, no ratificar.

## Estados
| Estado | Condición |
|---|---|
| DRAFT | Propuesta incompleta/editable |
| OPEN | Sellada, convocatoria verificada, plazo abierto |
| APPROVED_UNANIMOUS | Tres aprobaciones auténticas sin oposición/conflicto |
| WAITING_RATIFICATION | Plazo vencido, dos aprobaciones y tercero sin respuesta |
| APPROVED_RATIFIED | IA documenta todas las comprobaciones y ratifica |
| HUMAN_REVIEW | Oposición, conflicto, aprobaciones insuficientes o fallo de verificación |
| SUPERSEDED | Sustituida por nueva revisión |
| EXPIRED | Vigencia terminada |

Oposición o retirada posterior suspende aplicación pendiente para revisión; conservar resultado histórico.

## Tiempo
Guardar UTC, mostrar America/Santiago contemplando cambios estacionales.
Voto válido: opened_at <= created_at de GitHub < deadline.
Exactamente en el vencimiento: tardío. Un evento recibido tarde cuenta si fue creado antes del plazo y se concilia la evidencia.

Ratificar solo después del vencimiento real y de conciliar todos los comentarios/eventos. Un job retrasado no cambia el plazo. Aprobaciones tardías no reescriben la decisión histórica.

## Ratificación y auditoría
Comprobar dos aprobaciones de distintos integrantes sobre versión vigente, ausencia de respuesta/oposición/retirada del tercero, convocatoria, vencimiento, integridad, evidencia completa y seguridad. Un fallo de API o evidencia faltante bloquea ratificación.

Registrar actor autenticado, comentario/enlace, contenido original, creación/recepción, hashes, versión del evaluador, resultado y razones. Procesar serialmente por propuesta y deduplicar para evitar decisiones dobles.

Proteger rama/historial y guardar respaldos revisados. Los hashes detectan alteraciones respecto de copias anteriores, pero no impiden reescritura por un administrador. Verificar protección disponible en el plan privado; sin controles suficientes, revisión humana.

## Autorizaciones separadas
Toda decisión semanal: scope=strategy y real_order_authorized=false.
Una futura orden real necesita otro expediente con autorización humana expresa, activo, lado, importe, precios/límites, costes, vigencia y controles. El silencio o ratificación semanal nunca autoriza transferencias, cuentas o ejecución real.

## Pruebas del evaluador futuro
Unanimidad; dos aprobaciones antes/después del plazo; oposición; abstención/retirada; duplicados; bot/suplantación; hash antiguo; ediciones/borrados; voto en el vencimiento; evento retrasado; convocatoria fallida; vigencia expirada; concurrencia. En todos los casos: ninguna autorización real.
