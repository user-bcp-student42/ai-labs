# Hallazgos de ReqFlow

Seguimiento único de hallazgos. IDs por componente: `H-AUTH-NN`, `H-API-NN`, `H-WEB-NN`. Las filas de otros componentes se conservan si ya existen.

## api

### Discovery (Lab 01, paso 4)

- Fecha de referencia: 2026-11-02. Rama de trabajo: `day1/prompting`.
- Sin cambios de código. `docs/ENDPOINTS.md` no existe; el contrato abajo se deriva del código y no es un contrato acordado.
- Fuente de hallazgos: [RETO.md](RETO.md), sección `api`. Las siete filas del reto existen en el código; ninguna queda como "No encontrado". Se añaden hallazgos adicionales detectados en el código, marcados como "(adicional)".

#### Contrato observado

| Método | Ruta | Auth | Entrada | Respuesta observada | Evidencia |
|---|---|---|---|---|---|
| GET | `/api/tasks` | Bearer | `owner` opcional (query) | 200, lista de tareas con `createdAt` | `api/app/main.py:67-75` |
| POST | `/api/tasks` | Bearer | JSON libre: `title`, `description`, `status` (def. `TODO`), `priority` (def. `MEDIUM`), `owner` (def. usuario del token) | 201, tarea creada | `api/app/main.py:77-88` |
| GET | `/api/summary` | Bearer | `owner` opcional (query) | 200, `{owner,total,byStatus,highPriorityOpen}` | `api/app/main.py:90-105` |
| POST | `/api/requirements` | Bearer | multipart `file` | 201, `{owner,fileName,storedAt,size}` | `api/app/main.py:107-112` |
| GET | `/api/backend-health` | Bearer | — | 200, `{requestedBy,status,body}`; `status: 0` si falla la consulta | `api/app/main.py:114-121` |
| — | Cualquiera protegida | — | Token inválido | 401, `detail` = `"Invalid token: " + error` | `api/app/main.py:17-26` |

Otros datos observados:
- Variables de entorno: `WORKSHOP_DB_PATH` (def. `./data/workshop.db`), `WORKSHOP_UPLOAD_DIR` (def. `./uploads`) en `api/app/main.py:29-31`; `AUTH_HEALTH_URL` (def. `http://localhost:8080/q/health`) en `api/app/main.py:116`.
- Semilla: 3 tareas si la tabla está vacía, `api/app/main.py:37-43`.
- CORS: todos los orígenes con credenciales, `api/app/main.py:48-53`.

#### Flujo del token (observado)

1. El cliente envía `Authorization: Bearer <token>`. El código quita el texto `Bearer ` con `replace`, sin exigir el esquema (`api/app/main.py:19`).
2. Decodifica Base64 y separa por barra vertical en 4 partes: usuario, rol, expiración (epoch) y secreto (`api/app/main.py:20-21`).
3. Compara el secreto con la constante `LEGACY_SECRET` y revisa la expiración (`api/app/main.py:14`, `api/app/main.py:22`).
4. Devuelve `{username, role}` (`api/app/main.py:24`). Ninguna ruta usa el rol para autorizar. No hay firma, emisor ni audiencia.

#### Acceso a SQLite (observado)

- Una conexión global se crea en `create_app` (`api/app/main.py:36`), con `check_same_thread=False` y sin lock; la comparten todas las peticiones.
- DDL y semilla en `api/app/main.py:37-43`.
- Las consultas se arman por concatenación: listado (`api/app/main.py:70`), inserción (`api/app/main.py:84`), recuperación tras insertar (`api/app/main.py:87`) y resumen (`api/app/main.py:93`).

#### Carga de archivos (observado)

- `api/app/main.py:109`: `Path(selected_uploads) / str(file.filename)`, sin normalizar el nombre.
- `api/app/main.py:110`: lee el archivo completo en memoria, sin límite de tamaño.
- `api/app/main.py:111`: escribe en disco sin validar extensión.
- `api/app/main.py:112`: devuelve la ruta física del servidor en `storedAt`.

#### Matriz de seguimiento

Orden: severidad de mayor a menor. Todos los estados iniciales son "Pendiente" (ninguno se ha corregido).

| id | componente | hallazgo | tipo | explicacion | evidencia (archivo:linea) | severidad | estado |
|---|---|---|---|---|---|---|---|
| H-API-01 | api | Token Base64 con secreto embebido, sin firma (RETO: Auth) | Vulnerabilidad | Cualquiera que conozca el formato y el secreto constante puede fabricar un token con cualquier usuario y rol. La expiración se revisa, pero no hay firma, emisor ni audiencia. | api/app/main.py:14, api/app/main.py:19-24 | alta | Resuelto. Verificación HS256 con `hmac`/`hashlib` en api/app/security.py: firma, `exp`, `iss`, `aud` y `alg`; secreto desde `WORKSHOP_JWT_SECRET`; solo esquema `Bearer`; 401 genérico, también para `exp` no numérico (corregido en revisión). Pruebas en api/tests/test_api.py (28 pasan, cobertura 94.61%). Pendiente de coordinación externa: el emisor de tokens (auth/) debe firmar con este formato y secreto. |
| H-API-02 | api | Consultas SQL con concatenación de filtros e inserts (RETO: SQL) | Vulnerabilidad | Los valores de `owner`, `title`, `description`, `status` y `priority` van directo en la sentencia. Un valor con comillas puede alterar la consulta y leer o modificar filas ajenas. | api/app/main.py:70, api/app/main.py:84, api/app/main.py:93 | alta | Resuelto. Consultas con `?` en api/app/repository.py; main.py solo llama a esas funciones. Pruebas de caracterización y de inyección en api/tests/test_api.py (7 pasan, cobertura 91.53%). |
| H-API-03 | api | El cliente puede consultar y crear tareas de otro `owner` (RETO: Autorización) | Vulnerabilidad | `owner` llega por query o por cuerpo y reemplaza la identidad del token. Un usuario lee el resumen o las tareas de otro, y puede crear tareas a nombre de otro. | api/app/main.py:68-69, api/app/main.py:83, api/app/main.py:91-92 | alta | Resuelto. `authorized_owner()` en api/app/main.py compara `owner` con la identidad del token y responde 403 si difiere; list, summary y create lo usan. Pruebas en api/tests/test_api.py (13 pasan, cobertura 92.86%). |
| H-API-04 | api | Nombre de archivo sin normalizar, sin límite de extensión ni tamaño (RETO: Files) | Vulnerabilidad | `file.filename` se une a la ruta de uploads sin normalizar, por lo que un nombre con separadores o `..` podría escribir fuera del directorio. Tampoco hay límite de tamaño ni de extensión. Pendiente de reproducir en entorno aislado. | api/app/main.py:109-112 | alta | Resuelto. Nombre normalizado con `safe_file_name()` y extensión permitida (422), lectura acotada a 1 MiB (413) en api/app/uploads.py. Los nombres con espacios se permiten (decisión humana en revisión). Pruebas de traversal, extensión, tamaño y espacios en api/tests/test_api.py (28 pasan, cobertura 94.61%). |
| H-API-05 | api | Dependencias con CVEs conocidos: `urllib3 2.5.0` y `python-multipart 0.0.21` (RETO: SCA) | Vulnerabilidad | urllib3 2.5.0 está afectado por CVE-2025-66418 y CVE-2025-66471, corregidos en 2.6.0; afecta la respuesta de `backend-health`. python-multipart 0.0.21 está afectado por CVE-2026-24486 (path traversal en configuración no predeterminada), corregido en 0.0.22. La exposición real depende del uso; no se ha corrido `pip-audit`. | api/requirements.txt:4-5 | media | Aprobado |
| H-API-06 | api | Respuestas exponen detalles internos: error de token y error de `backend-health` (adicional) | Vulnerabilidad | El mensaje de excepción crudo (`str(error)`) llega al cliente y revela detalles de la implementación. Debe ser un mensaje genérico y el detalle quedar en el log del servidor. | api/app/main.py:26, api/app/main.py:121 | media | Pendiente |
| H-API-07 | api | Calidad: `dict[str, Any]` sin tipos, excepciones amplias, condicionales anidados y duplicación (RETO: Calidad) | Refactor | Los modelos de entrada y salida no están tipados; `except Exception` oculta errores reales. El resumen usa `if` anidados y la lista de columnas está repetida. Dificulta probar y cambiar sin romper contratos. | api/app/main.py:25, api/app/main.py:78, api/app/main.py:94-105, api/app/main.py:70, api/app/main.py:87 | media | Pendiente |
| H-API-08 | api | Rutas, base de datos, reglas y serialización en una sola función (RETO: Arquitectura) | Refactor | `create_app` mezcla creación de tablas, semilla, serialización, CORS y todas las rutas con SQL. Cualquier cambio en una capa toca las demás, y no se puede probar la lógica sin HTTP. | api/app/main.py:29-127 | media | Pendiente |
| H-API-09 | api | CORS con `allow_origins=["*"]` y `allow_credentials=True` (adicional) | Vulnerabilidad | La combinación es permisiva. Hoy la autenticación va en cabecera y no en cookies, lo que reduce el riesgo; cambiarlo a cookies lo volvería explotable. | api/app/main.py:48-53 | baja | Pendiente |
| H-API-10 | api | `@app.on_event("shutdown")` está obsoleto en FastAPI (adicional) | Refactor | La API marca deprecación en las pruebas. Migrar a `lifespan` evita que el cierre de la conexión deje de ejecutarse en versiones futuras. | api/app/main.py:123-125 | baja | Pendiente |

#### Evidencia de ejecución (línea base, sin cambios)

| Fecha | Componente | IDs relacionados | Comando (cwd `api/`, vía raíz) | Resultado |
|---|---|---|---|---|
| 2026-11-02 | api | ninguno (línea base) | `python tools/lab.py setup api` | Dependencias ya satisfechas en `api/.venv`; sin errores. |
| 2026-11-02 | api | ninguno (línea base) | `python tools/lab.py test api` | 4 passed; cobertura de `app` 91.07% (gate 85% cumplido). No cubiertas: `api/app/main.py` 23, 102->95, 103->95, 116-121. Código de salida 0. |

Nota: el gate de 85% de `test api` mide toda la app, no el código modificado. La cobertura del diff queda pendiente hasta que existan cambios.

#### Pendientes (sin resolver)

- P-API-01: reproducir la escritura fuera de `uploads` (H-API-04) en un directorio temporal aislado. No se ejecutó en Discovery.
- P-API-02: auditoría con `pip-audit` no ejecutada. Los CVE de H-API-05 se verificaron en fuentes públicas (OSV, Ubuntu USN), no con la herramienta del proyecto.
- P-API-03: `docs/ENDPOINTS.md` y `docs/TESTING.md` no se crean en este paso; corresponden a los pasos 8 y 9.
- P-API-04: el contrato acordado no existe todavía. Requiere aprobación humana antes de cambiar rutas o formatos.
- P-API-05: las pruebas actuales no cubren autorización por `owner`, consultas con comillas, subida de archivos maliciosa ni la rama de error de `backend-health`.
- P-API-06: existen ramas remotas de Dependabot para `python-multipart` 0.0.32 y `fastapi` 0.162.0. Se registran solo como referencia; no se integran en Discovery.
