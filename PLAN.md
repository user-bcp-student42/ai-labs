# Plan de corrección de ReqFlow

Seguimiento de propuestas de corrección. Los hallazgos y su estado viven en [HALLAZGOS.md](HALLAZGOS.md). Las filas de otros componentes se conservan si ya existen.

## api

### Alcance y condiciones

- Hallazgos cubiertos: H-API-01, H-API-02, H-API-03 y H-API-04, todos con estado "Pendiente" en [HALLAZGOS.md](HALLAZGOS.md).
- Este plan no modifica código. Cada cambio se hace después de escribir la prueba de caracterización indicada en su sección.
- `docs/ENDPOINTS.md` no existe. El contrato a preservar es el comportamiento observado en `api/app/main.py` (ver la tabla de contrato en [HALLAZGOS.md](HALLAZGOS.md)). Cuando un cambio altere ese comportamiento, se marca como **decisión pendiente** y requiere aprobación humana antes de implementarse.
- Reglas de código: [AGENTS.md](AGENTS.md) (sección api, clean code) y [docs/GOOD_PRACTICES.md](docs/GOOD_PRACTICES.md) (sección api). Ninguna convención adicional se asume.
- Verificación: `python tools/lab.py test api` con cwd `api/`. La meta de cobertura del código modificado es 85% o superior.

### Estado de aprobación

- H-API-01, H-API-02, H-API-03 y H-API-04 están marcados "Aprobado" en [HALLAZGOS.md](HALLAZGOS.md). Esa aprobación cubre el hallazgo, no las decisiones de implementación.
- Las decisiones P-PLAN-01 a P-PLAN-04 no tienen respuesta registrada. Hasta que se registre, las propuestas por defecto de este documento son provisionales.
- Sin decisión registrada: H-API-01 no puede cerrar la emisión de tokens (P-PLAN-01), H-API-03 usa `403` provisional (P-PLAN-02), H-API-04 usa `.txt`, `.md` y 1 MiB provisionales (P-PLAN-03).
- Este documento no registra aprobaciones que no existan en el repositorio.

### Orden de ejecución

1. Pruebas de caracterización para H-API-01 a H-API-04 (sin cambiar código de producción).
2. H-API-02 (SQL parametrizado). Es un cambio aislado en la capa de datos.
3. H-API-03 (autorización por identidad). Depende de 2 porque ambos tocan las mismas consultas.
4. H-API-04 (carga segura de archivos). Independiente de 2 y 3.
5. H-API-01 (verificación real del token). Es el de mayor impacto y depende de una decisión de emisión de tokens (ver P-PLAN-01). Va al final.
6. Después de cerrar 1 a 5, se aplica el prompt de `GET /health` en [prompts/health-api.md](prompts/health-api.md). Ese endpoint agrega un middleware sobre `create_app`, así que conviene que llegue sobre el código ya corregido.

Nota de interacción: al corregir H-API-01 y H-API-03, las respuestas `401` y `403` pasarán a contar como fallos en el endpoint `/health`. Ese comportamiento debe quedar cubierto por pruebas.

---

#### H-API-01 — Token Base64 con secreto embebido y sin firma

- **Hallazgo:** Vulnerabilidad, severidad alta. Evidencia: `api/app/main.py:14` (constante `LEGACY_SECRET`) y `api/app/main.py:19-24` (decodificación Base64 y comparación del cuarto campo).
- **Problema:** El token es `base64("usuario|rol|exp|secreto")`. El secreto está en el código, así que cualquiera puede fabricar un token con cualquier usuario y rol. No hay firma, emisor (`iss`) ni audiencia (`aud`). El rol se devuelve pero ninguna ruta lo usa.
- **Cambio propuesto:** Verificación real de JWT con HS256.
  - El secreto se lee de una variable de entorno (por ejemplo `WORKSHOP_JWT_SECRET`), sin valor por defecto en producción. Las pruebas usan un valor de prueba aislado.
  - Se verifican firma, `exp`, `iss` y `aud`. Los claims `sub` y `role` se leen del token verificado.
  - Se acepta solo el esquema `Bearer`. Si falta o es otro, se responde `401`.
  - Dependencia: se propone `PyJWT`, ya que implementar JWT a mano aumenta el riesgo. Requiere aprobación (ver P-PLAN-01). Alternativa sin dependencia nueva: `hmac` y `hashlib` de la biblioteca estándar, con más código propio que mantener.
- **Archivos a tocar:** `api/app/main.py` (función `legacy_identity`, líneas 14-26), `api/requirements.txt` (solo si se aprueba `PyJWT`), `api/tests/test_api.py`.
- **Prueba de caracterización (antes de tocar):**
  - Un token válido en el formato actual (`base64("student|STUDENT|<exp>|WORKSHOP_SECRET_2026")`) responde `200` en `/api/tasks`. Esta prueba documenta el comportamiento que se reemplaza y se elimina al aplicar el cambio.
  - Un token expirado responde `401`.
  - Un token sin `Bearer` o con base64 inválido responde `401`.
  - Un token con cuarto campo distinto responde `401`.
- **Pruebas nuevas tras el cambio:** token firmado válido `200`; firma alterada `401`; `exp` vencida `401`; `aud` o `iss` incorrectos `401`; el mensaje de error es genérico (ver H-API-06).
- **Decisión pendiente:** P-PLAN-01 (quién emite los tokens que consume esta API).

---

#### H-API-02 — Consultas SQL concatenadas

- **Hallazgo:** Vulnerabilidad, severidad alta. Evidencia: `api/app/main.py:70` (listado), `api/app/main.py:84` y `api/app/main.py:87` (inserción y lectura posterior), `api/app/main.py:93` (resumen).
- **Problema:** `owner`, `title`, `description`, `status` y `priority` se unen a la sentencia como texto. Un valor con comillas altera la consulta y puede leer o modificar filas ajenas.
- **Cambio propuesto:** SQL parametrizado con `?` en todas las consultas, y una capa de repositorio (`api/app/repository.py`, nuevo) con funciones separadas: listar, insertar, leer por id y resumir. Las rutas solo llaman al repositorio.
  - La lista de columnas se define una sola vez como constante. Hoy está repetida en `api/app/main.py:70` y `api/app/main.py:87`.
  - El `ORDER BY id` se conserva.
- **Archivos a tocar:** `api/app/main.py`, `api/app/repository.py` (nuevo), `api/tests/test_api.py`.
- **Prueba de caracterización (antes de tocar):**
  - Crear una tarea con un título normal y verificar que se lista y aparece en el resumen. Esto fija el contrato de `POST /api/tasks` y `GET /api/tasks`.
  - Crear una tarea con comillas simples en `title` y observar el resultado actual. La prueba documenta el fallo o la inyección observada. No se asume un resultado sin ejecutarla.
- **Pruebas nuevas tras el cambio:** un valor con comillas se guarda literal y se devuelve sin alterar; el listado y el resumen no cambian para valores normales; ninguna consulta contiene concatenación de datos del usuario.
- **Efecto en el contrato:** un valor con comillas que hoy rompe o altera la consulta pasará a guardarse literal. Es el comportamiento correcto, pero es un cambio observable que se debe registrar en la matriz.

---

#### H-API-03 — El cliente elige el `owner`

- **Hallazgo:** Vulnerabilidad, severidad alta. Evidencia: `api/app/main.py:68-69` (`owner` por query), `api/app/main.py:83` (`owner` en el cuerpo), `api/app/main.py:91-92` (resumen).
- **Problema:** `owner` reemplaza la identidad del token. Cualquier usuario autenticado lee el listado o el resumen de otro, y puede crear tareas a nombre de otro.
- **Cambio propuesto:** La autorización se liga a `identity["username"]`.
  - `GET /api/tasks`, `GET /api/summary`: si `owner` se envía y es distinto del usuario del token, responder `403`. Si no se envía, usar la identidad. Así un cliente que envía el mismo `owner` que su usuario no se rompe.
  - `POST /api/tasks`: si el cuerpo trae `owner` distinto del usuario del token, responder `403`. Sin `owner`, se usa la identidad.
  - Se conserva el parámetro `owner` aceptado en las rutas por compatibilidad con el frontend. Su uso como filtro de otro usuario deja de estar permitido.
- **Archivos a tocar:** `api/app/main.py` (líneas 67-105), `api/tests/test_api.py`.
- **Prueba de caracterización (antes de tocar):**
  - Con token de `student`, `GET /api/tasks?owner=trainer` devuelve la tarea de `trainer`. Hoy responde `200`. La prueba documenta el comportamiento que se corrige.
  - Con token de `student`, `POST /api/tasks` con `owner: "trainer"` responde `201` y guarda la tarea con ese dueño.
  - Sin `owner`, listado y resumen usan `student`.
- **Pruebas nuevas tras el cambio:** `owner` distinto responde `403` en las tres rutas; `owner` igual o ausente responde como antes; la tarea creada siempre pertenece al usuario del token.
- **Decisión pendiente:** P-PLAN-02 (si el frontend usa `owner` distinto a la identidad del token). No se verificó en este paso porque el código de `web/` está fuera del ámbito de `api/`. Hasta confirmarlo, la propuesta es `403`.

---

#### H-API-04 — Nombre de archivo sin normalizar y sin límites

- **Hallazgo:** Vulnerabilidad, severidad alta. Evidencia: `api/app/main.py:109-112`. Pendiente de reproducir en directorio aislado (P-API-01 en [HALLAZGOS.md](HALLAZGOS.md)).
- **Problema:** `Path(selected_uploads) / str(file.filename)` usa el nombre que envía el cliente. Un nombre con separadores o `..` podría escribir fuera de `uploads`. El archivo se lee completo en memoria sin tamaño máximo (`api/app/main.py:110`) y sin validar extensión (`api/app/main.py:111`).
- **Cambio propuesto:** Carga segura en un servicio de archivos (`api/app/uploads.py`, nuevo).
  - Normalizar el nombre con `Path(name).name` y validarlo con una expresión regular permitida (letras, dígitos, `.`, `_`, `-`, longitud máxima constante). Si no cumple, responder `422`.
  - Lista de extensiones permitidas como constante. El valor inicial propuesto es `.txt` y `.md`, a confirmar (P-PLAN-03).
  - Tamaño máximo como constante (por ejemplo 1 MiB), leyendo en bloques y cortando al superar el límite (`413`).
  - Se conserva `storedAt`, la ruta física devuelta hoy, para no romper el contrato. Su exposición se corrige por separado en H-API-06 con aprobación.
- **Archivos a tocar:** `api/app/main.py` (líneas 107-112), `api/app/uploads.py` (nuevo), `api/tests/test_api.py`.
- **Prueba de caracterización (antes de tocar):**
  - Subir `requirements.txt` con contenido de texto responde `201` y el archivo existe en `uploads`. Fija el contrato actual.
  - Subir un archivo con nombre `../x.txt` en un directorio temporal aislado (`tmp_path`): documentar si el archivo queda fuera de `uploads`. Esta prueba se ejecuta solo dentro de `tmp_path`, nunca fuera de él.
- **Pruebas nuevas tras el cambio:** `../x.txt` se guarda dentro de `uploads` con el nombre normalizado o se rechaza; extensión no permitida `422`; archivo mayor al límite `413`; archivo válido `201` sin cambios en `fileName` y `size`.
- **Decisión pendiente:** P-PLAN-03 (extensiones y tamaño máximo).

---

### Decisiones pendientes para aprobación humana

Decisiones registradas por el usuario en la sesión (respuesta del formulario de aprobación):

- **P-PLAN-01 (resuelta):** `verificar_con_secreto_compartido`. La API verifica HS256 con un secreto de entorno. Como no se aprobó una dependencia nueva, H-API-01 usa `hmac` y `hashlib` de la biblioteca estándar, no PyJWT.
- **P-PLAN-02 (resuelta):** `403_si_difiere`. Si `owner` difiere de la identidad, la API responde `403`.
- **P-PLAN-03 (resuelta):** `txt_md_1mib`. Extensiones `.txt` y `.md`, tamaño máximo 1 MiB.
- **P-PLAN-04 (resuelta):** `mantener_201`. `title` faltante sigue respondiendo `201` con valor vacío.


### Pydantic en `POST /api/tasks` (apoya H-API-07)

El plan para tipar la entrada cambia el comportamiento observado: hoy `title` faltante se guarda como `""` y responde `201` (`api/app/main.py:79`). Con un modelo Pydantic, responde `422`. Se propone:

- Escribir primero la prueba de caracterización de `title` faltante.
- Mantener `201` y valor vacío hasta que se apruebe P-PLAN-04, o cambiarlo con aprobación explícita.

### Registro de ejecuciones

- H-API-02, antes del cambio: `python tools/lab.py test api` → 6 passed, cobertura 91.07%, exit 0. Incluye las 2 pruebas de caracterización (`test_characterizes_task_payload_shape`, `test_characterizes_summary_breakdown`).
- H-API-02, después del cambio: `python tools/lab.py test api` → 7 passed, cobertura 91.53%, exit 0. Incluye la prueba de inyección `test_sql_injection_payload_is_stored_as_literal_text`.
- Nota: la prueba de inyección se escribió después del cambio, así que no hay resultado previo de ella contra el código original.
- Desviación: el plan de H-API-02 se implementó sin cambiar contratos. Por lectura del código (no reproducido antes del cambio), un `owner` con comilla antes provocaba un error SQL; ahora devuelve lista vacía.
- H-API-03, después del cambio: `python tools/lab.py test api` → 13 passed, cobertura 92.86%, exit 0. Incluye `test_rejects_other_owner_listing`, `test_accepts_own_owner_and_defaults_to_identity` y `test_rejects_other_owner_creation_and_keeps_identity`. Desviación: la prueba de inyección de H-API-02 esperaba 200 con `owner` ajeno; ahora espera 403 por H-API-03.
- H-API-04, antes del cambio: la prueba de traversal (caracterización) escribió `escaped.txt` fuera de `uploads` (201), lo que confirma el hallazgo.
- H-API-04, después del cambio: `python tools/lab.py test api` → 13 passed, cobertura 92.86%, exit 0. Incluye `test_stores_traversal_name_only_inside_uploads`, `test_rejects_disallowed_extension` (422) y `test_rejects_file_over_size_limit` (413).
- H-API-01, antes del cambio: `python tools/lab.py test api` → 18 passed, cobertura 94.05%, exit 0. Incluye las pruebas de caracterización del token legacy: expirado, cuarto campo incorrecto, esquema no `Bearer`, base64 inválido y token legacy válido aceptado (`200`).
- H-API-01, después del cambio: `python tools/lab.py test api` → 24 passed, cobertura 93.85%, exit 0. El token legacy ya responde `401`; se agregan pruebas de firma incorrecta, expiración, `iss`/`aud` incorrectos, `alg` no permitido, secreto no configurado y token firmado válido.
- Desviación H-API-01: el módulo de verificación vive en `api/app/security.py` (no estaba en el plan) para separar la verificación de la ruta. El detalle del 401 pasó de `Invalid token: <error>` a `Invalid token` (genérico, cubre parte de H-API-06). Pendiente externo: el emisor de tokens debe firmar HS256 con `iss` `ai-labs-auth`, `aud` `ai-labs-api`, y el mismo secreto de entorno.
- Revisión local (H-API-01, H-API-04, con H-API-07 parcial), antes del cambio: `python tools/lab.py test api` → 24 passed, 4 failed (`exp` no numérico devolvía 500; nombre con espacios devolvía 422), exit 1. Estas pruebas se agregaron antes de corregir.
- Revisión local (H-API-01, H-API-04, con H-API-07 parcial), después del cambio: `python tools/lab.py test api` → 28 passed, cobertura 94.61%, exit 0. Cambios: `verify_expiration` en `api/app/security.py` convierte `exp` con `try` y responde 401 genérico; `SAFE_NAME_PATTERN` en `api/app/uploads.py` acepta espacios por decisión humana; `build_summary` y `is_high_priority_open` en `api/app/main.py` reemplazan los `if` anidados y las cadenas sueltas; se corrige la sangría de `authorized_owner`.
### Verificación al final de cada hallazgo

- `python tools/lab.py test api` con cwd `api/`, y registrar el resultado en [HALLAZGOS.md](HALLAZGOS.md) (sección de evidencias de ejecución). Este documento no registra resultados de pruebas que aún no se hayan ejecutado.
- Cobertura del código modificado: meta de 85% o superior.
- Actualizar el estado del hallazgo en [HALLAZGOS.md](HALLAZGOS.md) solo después de que la prueba pase.
