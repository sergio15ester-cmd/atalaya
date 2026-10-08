# Panel local de simulación

El MVP calcula informes, riesgo, estadísticas y estados de votación a partir de instantáneas JSON. No obtiene cotizaciones ni conecta cuentas. No guarda automáticamente archivos cargados, publica datos o ejecuta órdenes.

## Ejecutar

Con Python 3.12 o superior, desde la carpeta del proyecto:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip --isolated install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

En Linux/macOS, usar `.venv/bin/python` en lugar de `.venv\Scripts\python.exe`.

Abrir http://127.0.0.1:8501. La configuración limita el servidor a localhost, desactiva telemetría y observación automática de archivos, y mantiene CORS/XSRF. El acceso compartido con otros integrantes requiere un diseño posterior de autenticación y permisos; no exponer este servidor directamente a Internet.

## Uso

- La sesión comienza vacía: NO OPERAR y ninguna cotización inventada.
- «Ver ejemplo sintético» muestra tres operaciones ficticias para comprobar métricas. Sus valores no representan el capital ni el historial de ninguna persona.
- «Cargar instantánea JSON» procesa el archivo elegido en memoria. No lee otras carpetas ni sigue URLs incluidas en el archivo.
- «Vaciar sesión» elimina la instantánea del estado de esa sesión. No elimina archivos originales ni promete borrado forense del navegador/proceso.
- El informe descargado puede contener los datos que el usuario haya cargado: guardarlo y compartirlo según su sensibilidad.

## Formato

Consultar `data/demo.json`. El objeto superior requiere `schema_version: 1`, `mode: "paper"` y `synthetic: true/false`. Incluye `policy`, `account`, `opportunities`, `trades`, `equity_curve`, `watchlist`, `sources`, `governance`, `agent_decisions` y `market_context`.

Solo se aceptan datos de simulación. Se rechazan JSON ambiguos, valores no finitos, campos de credenciales conocidos y estructuras excesivas. Esos filtros no garantizan que un documento esté libre de toda información sensible: elegir únicamente datos autorizados.

El JSON no autentica personas, precios ni aprobaciones. Las banderas de confianza importadas se invalidan antes de inspeccionar una votación. Las propuestas económicas se calculan sin habilitar operaciones; aprobar estrategia y autorizar una orden real siguen siendo expedientes diferentes.

## Alcance implementado

- Evaluador de riesgo: tamaño, efectivo, exposición, pérdidas, coste mínimo, bid/ask, deslizamiento y cambio; configuración incompleta bloquea.
- Historial y estadísticas netas antes de impuestos.
- Informe diario con cero a tres oportunidades y evidencia declarada.
- Evaluador puro de votaciones: unanimidad o espera/revisión. Dos votos con silencio no se ratifican automáticamente.
- Cuatro vistas de consulta y ejemplo sintético.

Pendientes: colector autenticado de GitHub, ratificador independiente, sesiones semanales, fuentes verificadas de mercado, contabilidad de posiciones abiertas y comparación con referencias. Los agentes siguen siendo roles invocados por tarea; no se despliegan seis servicios continuos.

## Pruebas

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

GitHub Actions ejecuta las mismas pruebas con datos ficticios, permisos de lectura y sin secretos. No contiene programación de operaciones ni avisos al equipo.
