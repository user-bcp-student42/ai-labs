# Endpoints de la API (componente `api`)

Documento de integración para la API FastAPI de tareas y requerimientos (`api/app/main.py`).
Las secciones de `auth` y `web` no existen todavía en este archivo; cuando se agreguen, deben conservarse.

## Estado del contrato

- **Contrato observado**: lo que hace hoy el código en `api/app/`, verificado ejecutando la API con `TestClient` y un token HS256 de prueba (secreto de ejemplo, no real).
- **Contrato acordado**: el de `PLAN.md` y `HALLAZGOS.md` para H-API-01 a H-API-04 (ya resueltos). Mantiene el comportamiento observado.
- **Riesgos pendientes**: se listan al final de cada endpoint y en la sección "Preguntas abiertas y riesgos pendientes".

## Convenciones generales

- Base: `http://<host>:<puerto>` (el puerto lo define el arranque de la API; ver `README.md`).
- Formato: JSON, salvo `POST /api/requirements`, que usa `multipart/form-data`.
- Autenticación: todas las rutas `/api/*` requieren el header:

  ```
  Authorization: Bearer <token_jwt>
  ```

  El token lo emite el servicio `auth/`. Debe ser HS256, firmado con el secreto compartido de la variable de entorno `WORKSHOP_JWT_SECRET`, y contener `sub` (usuario), `role`, `exp` (expiración en epoch), `iss` = `ai-labs-auth` y `aud` = `ai-labs-api` (`api/app/security.py`). Se rechaza cuando el tiempo actual es igual o posterior a `exp`. El token legado en base64 ya no se acepta.
- Identidad: el usuario del token (`sub`) es la identidad autorizada. El parámetro/campo `owner` es opcional: si se omite se usa la identidad; si se envía igual a la identidad se acepta; si difiere, la API responde 403.
- Errores de autenticación: cualquier error de token responde 401 con el mismo cuerpo genérico (no se revela la causa).

Errores comunes:

| Código | Cuándo | Cuerpo |
|---|---|---|
| 401 | Falta el header, el esquema no es `Bearer`, o el token es inválido, expirado o tiene firma/issuer/audience incorrectos | `{"detail":"Invalid token"}` |
| 403 | El `owner` solicitado es distinto de la identidad del token | `{"detail":"Forbidden"}` |
| 422 | Validación de FastAPI (campo faltante o formato incorrecto) o nombre/extensión de archivo inválidos | Ver cada endpoint |

---

## 1. GET /api/tasks

1. **Qué hace**: devuelve las tareas del usuario autenticado (o del `owner` indicado, si coincide con su identidad).

2. **Autenticación**: sí. Header `Authorization: Bearer <token_jwt>`.

3. **Request**

   Parámetros de consulta:

   | Parámetro | Tipo | Obligatorio | Descripción |
   |---|---|---|---|
   | `owner` | string | No | Usuario cuyas tareas se consultan. Si se omite, se usa la identidad del token. Si difiere de la identidad, responde 403. |

   Sin cuerpo.

   Ejemplo:

   ```http
   GET /api/tasks HTTP/1.1
   Host: localhost:8000
   Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJzdHVkZW50Iiwi...
   ```

4. **Respuesta exitosa: 200 OK**

   Cuerpo: arreglo JSON de objetos tarea.

   | Campo | Tipo | Descripción |
   |---|---|---|
   | `id` | integer | Identificador de la tarea (autoincremental). |
   | `title` | string | Título. |
   | `description` | string | Descripción. |
   | `status` | string | Estado, por ejemplo `TODO`, `IN_PROGRESS`, `DONE`, `ARCHIVED`. |
   | `owner` | string | Usuario dueño de la tarea. |
   | `priority` | string | Prioridad, por ejemplo `LOW`, `MEDIUM`, `HIGH`. |
   | `createdAt` | string | Fecha y hora de creación, formato `YYYY-MM-DD HH:MM:SS` (UTC según SQLite `datetime('now')`). |

   Ejemplo (datos de semilla, usuario `student`):

   ```json
   [
     {
       "id": 1,
       "title": "Refactor login",
       "description": "Separar responsabilidades en frontend",
       "status": "TODO",
       "owner": "student",
       "priority": "HIGH",
       "createdAt": "2026-11-02 22:14:21"
     },
     {
       "id": 2,
       "title": "Review API",
       "description": "Revisar seguridad de endpoints",
       "status": "IN_PROGRESS",
       "owner": "student",
       "priority": "MEDIUM",
       "createdAt": "2026-11-02 22:14:21"
     }
   ]
   ```

5. **Errores posibles**

   - **401 Unauthorized**: token ausente o inválido.

     ```json
     {"detail":"Invalid token"}
     ```

   - **403 Forbidden**: `owner` distinto de la identidad del token.

     ```json
     {"detail":"Forbidden"}
     ```

6. **Notas de seguridad**
   - La autorización depende de la identidad del token, no de un parámetro `owner` libre: un usuario no puede listar las tareas de otro (H-API-03, resuelto).
   - Las consultas SQL están parametrizadas (H-API-02, resuelto).

---

## 2. POST /api/tasks

1. **Qué hace**: crea una tarea para el usuario autenticado (o para `owner`, si coincide con su identidad).

2. **Autenticación**: sí. Header `Authorization: Bearer <token_jwt>`.

3. **Request**

   Cuerpo JSON (objeto):

   | Campo | Tipo | Obligatorio | Descripción |
   |---|---|---|---|
   | `title` | string | No (ver pregunta abierta 1) | Título de la tarea. Si falta, la API lo guarda como cadena vacía. |
   | `description` | string | No | Descripción. Si falta, cadena vacía. |
   | `status` | string | No | Estado. Valor por defecto `TODO`. |
   | `priority` | string | No | Prioridad. Valor por defecto `MEDIUM`. |
   | `owner` | string | No | Dueño. Si se omite, la identidad del token. Si difiere de la identidad, responde 403. |

   Los valores se convierten a texto con `str()` (`api/app/main.py`, POST /api/tasks).

   Ejemplo:

   ```json
   {
     "title": "Escribir docs",
     "description": "Documentar API",
     "status": "TODO",
     "priority": "HIGH"
   }
   ```

4. **Respuesta exitosa: 201 Created**

   Cuerpo: el objeto tarea creado (mismos campos que en GET /api/tasks).

   | Campo | Tipo | Descripción |
   |---|---|---|
   | `id` | integer | Identificador asignado. |
   | `title` | string | Título guardado. |
   | `description` | string | Descripción guardada. |
   | `status` | string | Estado guardado. |
   | `owner` | string | Dueño asignado (identidad del token si no se envió `owner`). |
   | `priority` | string | Prioridad guardada. |
   | `createdAt` | string | Fecha y hora de creación, `YYYY-MM-DD HH:MM:SS`. |

   Ejemplo (request del punto 3 enviado por `student`):

   ```json
   {
     "id": 4,
     "title": "Escribir docs",
     "description": "Documentar API",
     "status": "TODO",
     "owner": "student",
     "priority": "HIGH",
     "createdAt": "2026-11-02 22:14:21"
   }
   ```

5. **Errores posibles**

   - **401 Unauthorized**: token ausente o inválido.

     ```json
     {"detail":"Invalid token"}
     ```

   - **403 Forbidden**: el campo `owner` difiere de la identidad del token.

     ```json
     {"detail":"Forbidden"}
     ```

   - **422 Unprocessable Entity**: el cuerpo está ausente o no es un objeto JSON válido. El cuerpo lo genera FastAPI (formato probado en `POST /api/requirements`; para este endpoint se observó el código 422, no el texto exacto).

     ```json
     {
       "detail": [
         {
           "type": "missing",
           "loc": ["body"],
           "msg": "Field required",
           "input": null
         }
       ]
     }
     ```

     Nota: el ejemplo de `loc` y `msg` sigue el formato estándar de FastAPI; confirmar con una prueba antes de depender de él (pregunta abierta 2).

6. **Notas de seguridad**
   - El `owner` no puede ser otro usuario: se valida contra la identidad del token (H-API-03, resuelto).
   - La inserción usa parámetros `?` en SQLite, no concatenación (H-API-02, resuelto).
   - No hay validación de longitud ni de valores permitidos para `status` y `priority`; cualquier texto se acepta (ver riesgos pendientes).

---

## 3. GET /api/summary

1. **Qué hace**: devuelve un resumen de las tareas del usuario autenticado (o de `owner`, si coincide): total, cantidad por estado y cantidad de tareas de prioridad alta abiertas.

2. **Autenticación**: sí. Header `Authorization: Bearer <token_jwt>`.

3. **Request**

   Parámetros de consulta:

   | Parámetro | Tipo | Obligatorio | Descripción |
   |---|---|---|---|
   | `owner` | string | No | Usuario a resumir. Si se omite, la identidad del token. Si difiere, 403. |

   Sin cuerpo.

   Ejemplo:

   ```http
   GET /api/summary HTTP/1.1
   Host: localhost:8000
   Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJzdHVkZW50Iiwi...
   ```

4. **Respuesta exitosa: 200 OK**

   | Campo | Tipo | Descripción |
   |---|---|---|
   | `owner` | string | Usuario resumido. |
   | `total` | integer | Número total de tareas del usuario. |
   | `byStatus` | objeto (string → integer) | Cantidad de tareas por estado. Solo aparecen los estados que tienen al menos una tarea. |
   | `highPriorityOpen` | integer | Tareas con `priority` = `HIGH` y estado distinto de `DONE` y `ARCHIVED`. |

   Ejemplo (datos de semilla, usuario `student`: "Refactor login" TODO/HIGH y "Review API" IN_PROGRESS/MEDIUM):

   ```json
   {
     "owner": "student",
     "total": 2,
     "byStatus": {
       "TODO": 1,
       "IN_PROGRESS": 1
     },
     "highPriorityOpen": 1
   }
   ```

   Nota: estos valores se derivan de la lista de semilla que devolvió GET /api/tasks en la ejecución de verificación. Ver pregunta abierta 3.

5. **Errores posibles**

   - **401 Unauthorized**: token ausente o inválido.

     ```json
     {"detail":"Invalid token"}
     ```

   - **403 Forbidden**: `owner` distinto de la identidad del token.

     ```json
     {"detail":"Forbidden"}
     ```

6. **Notas de seguridad**
   - Igual que GET /api/tasks: la identidad del token define qué usuario se resume (H-API-03, resuelto).
   - La lógica de conteo está separada en `build_summary` e `is_high_priority_open` (`api/app/main.py`); no cambia la respuesta.

---

## 4. POST /api/requirements

1. **Qué hace**: recibe un archivo de requerimientos (`.txt` o `.md`) del usuario autenticado y lo guarda en el directorio de subidas.

2. **Autenticación**: sí. Header `Authorization: Bearer <token_jwt>`.

3. **Request**

   Cuerpo `multipart/form-data`:

   | Campo | Tipo | Obligatorio | Descripción |
   |---|---|---|---|
   | `file` | archivo | Sí | Archivo a subir. Solo se toma el nombre base. El nombre debe cumplir `[A-Za-z0-9._ -]{1,128}` (se permiten espacios) y terminar en `.txt` o `.md` (sin distinguir mayúsculas). Tamaño máximo: 1 MiB (1 048 576 bytes). |

   Ejemplo:

   ```http
   POST /api/requirements HTTP/1.1
   Host: localhost:8000
   Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJzdHVkZW50Iiwi...
   Content-Type: multipart/form-data; boundary=----ejemplo

   ------ejemplo
   Content-Disposition: form-data; name="file"; filename="informe final.txt"
   Content-Type: text/plain

   requisito
   ------ejemplo--
   ```

4. **Respuesta exitosa: 201 Created**

   | Campo | Tipo | Descripción |
   |---|---|---|
   | `owner` | string | Usuario que subió el archivo (identidad del token). |
   | `fileName` | string | Nombre del archivo tras normalizarlo (solo nombre base). |
   | `storedAt` | string | Ruta donde quedó guardado el archivo en el servidor, dentro del almacenamiento aislado del usuario. Ver riesgo pendiente. |
   | `size` | integer | Tamaño en bytes. |

   Ejemplo (archivo `informe final.txt` de 3 bytes):

   ```json
   {
     "owner": "student",
     "fileName": "informe final.txt",
     "storedAt": "C:\\ai-labs\\api\\uploads\\<directorio-usuario>\\informe final.txt",
     "size": 3
   }
   ```

   Nota: la ruta de `storedAt` depende del sistema operativo y del directorio de subidas configurado. El ejemplo usa una ruta de Windows.

5. **Errores posibles**

   - **401 Unauthorized**: token ausente o inválido.

     ```json
     {"detail":"Invalid token"}
     ```

   - **413 Payload Too Large**: el archivo supera 1 MiB.

     ```json
     {"detail":"File too large"}
     ```

   - **422 Unprocessable Entity** (nombre o extensión no permitidos): el nombre no cumple el patrón o no termina en `.txt`/`.md`.

     ```json
     {"detail":"Invalid file name or extension"}
     ```

   - **409 Conflict**: el usuario ya tiene un archivo con ese nombre.

     ```json
     {"detail":"File already exists"}
     ```

   - **422 Unprocessable Entity** (falta el campo `file`): error de validación de FastAPI (observado).

     ```json
     {
       "detail": [
         {
           "type": "missing",
           "loc": ["body", "file"],
           "msg": "Field required",
           "input": null
         }
       ]
     }
     ```

6. **Notas de seguridad**
   - Se normaliza el nombre al nombre base (`Path(name).name`), lo que bloquea rutas como `../x.txt` (H-API-04, resuelto).
   - Solo se aceptan extensiones `.txt` y `.md`, y el tamaño se limita a 1 MiB sin cargar más de ese límite en memoria (H-API-04, resuelto).
   - Las cargas se aíslan por identidad: dos usuarios pueden usar el mismo nombre sin reemplazarse; el mismo usuario recibe 409 si intenta reutilizar un nombre ya cargado.
   - Riesgo pendiente: `storedAt` expone la ruta absoluta del servidor al cliente.

---

## 5. GET /api/backend-health

1. **Qué hace**: consulta el endpoint de salud del servicio `auth/` (por defecto `http://localhost:8080/q/health`, configurable con `AUTH_HEALTH_URL`) y devuelve su resultado al cliente autenticado.

2. **Autenticación**: sí. Header `Authorization: Bearer <token_jwt>`.

3. **Request**

   Sin parámetros ni cuerpo.

   ```http
   GET /api/backend-health HTTP/1.1
   Host: localhost:8000
   Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJzdHVkZW50Iiwi...
   ```

4. **Respuesta exitosa: 200 OK** (el servicio `auth/` respondió)

   | Campo | Tipo | Descripción |
   |---|---|---|
   | `requestedBy` | string | Usuario que hizo la consulta (identidad del token). |
   | `status` | integer | Código HTTP devuelto por el servicio `auth/`. |
   | `body` | string | Cuerpo de la respuesta del servicio `auth/`, como texto. |

   Forma de la respuesta (el valor de `body` depende de lo que devuelva `auth/`; no se capturó un ejemplo real porque `auth/` no estaba levantado en la verificación):

   ```json
   {
     "requestedBy": "student",
     "status": 200,
     "body": "<cuerpo devuelto por auth/ como texto>"
   }
   ```

5. **Errores posibles**

   - **401 Unauthorized**: token ausente o inválido.

     ```json
     {"detail":"Invalid token"}
     ```

   - **200 OK con `status` 0** (el servicio `auth/` no respondió o hubo error de conexión o timeout de 3 s). Es el comportamiento observado: el error no se devuelve como 5xx.

     ```json
     {
       "requestedBy": "student",
       "status": 0,
       "body": "HTTPConnectionPool(host='localhost', port=8080): Max retries exceeded with url: /q/health (Caused by NewConnectionError(...))"
     }
     ```

     Nota: el texto de `body` es el mensaje interno de la excepción (incluye host, puerto y ruta). Ver riesgo pendiente.

6. **Notas de seguridad**
   - Riesgo pendiente (H-API-06, Pendiente): `body` expone el mensaje interno de la excepción, incluidos host y puerto internos.
   - La consulta requiere token válido, por lo que no es pública.
   - El endpoint no valida `AUTH_HEALTH_URL`; quien controle esa variable de entorno controla el destino de la consulta.

---

## Preguntas abiertas y riesgos pendientes

1. `POST /api/tasks` sin `title`: el código lo acepta y guarda cadena vacía (respuesta 201). Confirmar si esa es la regla de negocio o si debe responder 422 (decisión P-PLAN-04 de `PLAN.md`: `mantener_201`).
2. `POST /api/tasks` sin cuerpo: se observó 422 de FastAPI; el texto exacto del `detail` no se verificó con una prueba específica.
3. Resumen de semilla: los valores de `GET /api/summary` de este documento se derivan de la lista de semilla, no de una llamada directa a ese endpoint con datos de semilla.
4. `storedAt` expone la ruta absoluta del servidor (riesgo de divulgación de información).
5. `GET /api/backend-health` expone el mensaje interno de la excepción en `body` (H-API-06, Pendiente).
6. `status` y `priority` no se validan contra una lista de valores permitidos.
7. `web/` puede depender de que `owner` sea igual a la identidad: no se revisó porque está fuera del ámbito de `api/`.
8. El servicio `auth/` debe emitir tokens compatibles (HS256, mismo secreto, `iss`/`aud`). Dependencia externa sin verificar desde `api/`.
9. Dependencias con CVE conocidos (`urllib3` 2.5.0, `python-multipart` 0.0.21; H-API-05, Aprobado, sin cambios). `pip-audit` no se ejecutó.
10. CORS con `allow_origins=["*"]` y `allow_credentials=True` (H-API-09, Pendiente).
