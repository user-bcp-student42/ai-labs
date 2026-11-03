# Pruebas de la API

Componente: `api`. IDs de hallazgo relacionados: H-API-01, H-API-02, H-API-03, H-API-04 (resueltos), H-API-06 (pendiente).

Contrato de referencia: [ENDPOINTS.md](./ENDPOINTS.md). Las pruebas no inventan endpoints ni comportamientos fuera de ese documento.

## Como ejecutar

| Campo | Valor |
|---|---|
| Comando | `python tools/lab.py test api` (desde la raiz `ai-labs/`) |
| Comando interno | `api\.venv\Scripts\python.exe -m pytest --cov=app --cov-report=term-missing --cov-report=html --cov-fail-under=85` |
| Directorio de ejecucion | `api/` |
| Archivos de prueba | `api/tests/test_api.py` (28 tests), `api/tests/test_endpoint_contract.py` (22 tests) |

## Matriz de pruebas por endpoint

Tipos: **FELIZ** (camino feliz), **BORDE** (caso borde), **ERROR** (respuesta de error documentada), **SEG** (seguridad).

| endpoint | caso | tipo | resultado esperado |
|---|---|---|---|
| GET /api/tasks | Lista las tareas seeded del usuario `student` (`test_lists_seeded_tasks`, `test_api.py`) | FELIZ | 200, lista con tareas de `student` |
| GET /api/tasks | Usuario sin tareas (`test_list_returns_empty_array_for_user_without_tasks`) | BORDE | 200, `[]` |
| GET /api/tasks | Parametro `owner` vacio se trata como identidad (`test_list_empty_owner_query_falls_back_to_identity`) | BORDE | 200, tareas de `student` |
| GET /api/tasks | Propia identidad explicita y valor por defecto coinciden (`test_accepts_own_owner_and_defaults_to_identity`) | FELIZ | 200, misma respuesta con y sin `owner` |
| GET /api/tasks | Sin cabecera Authorization (`test_list_without_authorization_header_returns_401`) | ERROR | 401, `{"detail":"Invalid token"}` |
| GET /api/tasks | Token invalido (`test_rejects_invalid_token`) | ERROR | 401 |
| GET /api/tasks | Un usuario no puede leer tareas de otro owner (`test_rejects_other_owner_listing`) | SEG | 403, `{"detail":"Forbidden"}` |
| POST /api/tasks | Creacion valida y resumen (`test_creates_task_and_summary`) | FELIZ | 201, tarea con `owner` de la identidad |
| POST /api/tasks | Forma del payload de respuesta (`test_characterizes_task_payload_shape`) | FELIZ | 201, campos `id,title,description,status,owner,priority,createdAt` |
| POST /api/tasks | Payload `{}` aplica defaults (`test_create_with_empty_payload_applies_documented_defaults`) | BORDE | 201, `title=""`, `description=""`, `status=TODO`, `priority=MEDIUM` |
| POST /api/tasks | Sin body (`test_create_without_body_returns_422`) | ERROR | 422, `loc` = `["body"]` |
| POST /api/tasks | Body JSON no objeto (`test_create_with_non_object_body_returns_422`) | BORDE | 422 |
| POST /api/tasks | Sin cabecera Authorization (`test_create_without_authorization_header_returns_401`) | ERROR | 401, `{"detail":"Invalid token"}` |
| POST /api/tasks | Owner distinto en el body (`test_rejects_other_owner_creation_and_keeps_identity`) | SEG | 403 |
| GET /api/summary | Resumen del usuario `student` (`test_characterizes_summary_breakdown`) | FELIZ | 200, `total`, `byStatus`, `highPriorityOpen` |
| GET /api/summary | Usuario sin tareas (`test_summary_for_user_without_tasks_is_empty`) | BORDE | 200, `total=0`, `byStatus={}`, `highPriorityOpen=0` |
| GET /api/summary | Excluye tareas HIGH cerradas DONE/ARCHIVED (`test_summary_excludes_closed_high_priority_tasks`) | BORDE | `highPriorityOpen` no cuenta las cerradas |
| GET /api/summary | Sin cabecera Authorization (`test_summary_without_authorization_header_returns_401`) | ERROR | 401 |
| GET /api/summary | Owner distinto (`test_rejects_other_owner_listing`) | SEG | 403 |
| POST /api/requirements | Carga valida (`test_uploads_requirement`) | FELIZ | 201, `{owner,fileName,storedAt,size}` |
| POST /api/requirements | Nombre con espacios (`test_accepts_file_name_with_spaces`) | BORDE | 201 |
| POST /api/requirements | Archivo de exactamente 1 MiB (`test_upload_file_at_exact_size_limit_is_accepted`) | BORDE | 201, `size=1048576` |
| POST /api/requirements | Archivo vacio de 0 bytes (`test_upload_empty_file_is_stored_with_zero_size`) | BORDE | 201, `size=0` |
| POST /api/requirements | Archivo sin extension (`test_upload_file_without_extension_returns_422`) | BORDE | 422, `{"detail":"Invalid file name or extension"}` |
| POST /api/requirements | Caracter no permitido en el nombre (`test_upload_name_with_disallowed_characters_returns_422`) | BORDE | 422, mismo detalle |
| POST /api/requirements | Nombre de mas de 128 caracteres (`test_upload_name_longer_than_limit_returns_422`) | BORDE | 422 |
| POST /api/requirements | Extension no permitida (`test_rejects_disallowed_extension`) | ERROR | 422 |
| POST /api/requirements | Archivo mayor a 1 MiB (`test_rejects_file_over_size_limit`) | ERROR | 413, `{"detail":"File too large"}` |
| POST /api/requirements | Traversal en el nombre queda dentro de uploads (`test_stores_traversal_name_only_inside_uploads`) | SEG | Se guarda solo dentro de `uploads/` |
| POST /api/requirements | Campo `file` ausente (`test_upload_without_file_field_returns_422`) | ERROR | 422, `loc` = `["body","file"]` |
| POST /api/requirements | Sin cabecera Authorization (`test_upload_without_authorization_header_returns_401`) | ERROR | 401 |
| POST /api/requirements | Token invalido (`test_rejects_invalid_token`) | ERROR | 401 |
| GET /api/backend-health | Upstream responde 200 (`test_backend_health_returns_upstream_status_and_body`) | FELIZ | 200, `{requestedBy,status:200,body}` |
| GET /api/backend-health | URL configurada con `AUTH_HEALTH_URL` (`test_backend_health_uses_configured_url`) | FELIZ | Se llama a la URL configurada |
| GET /api/backend-health | Upstream responde 503 (`test_backend_health_passes_through_upstream_error_status`) | ERROR | 200 con `status:503` |
| GET /api/backend-health | Upstream no alcanzable (`test_backend_health_unreachable_upstream_returns_status_zero`) | ERROR | 200 con `status:0` y `body` con el mensaje de error (ver nota H-API-06) |
| GET /api/backend-health | Sin cabecera Authorization (`test_backend_health_without_authorization_header_returns_401`) | ERROR | 401 y no se llama al upstream |

Nota: los tests de `test_api.py` que validan tokens (`test_rejects_legacy_token_without_signature`, `test_rejects_token_signed_with_other_secret`, `test_rejects_expired_signed_token`, `test_rejects_non_numeric_expiration_with_generic_401`, `test_rejects_unexpected_issuer_or_audience`, `test_rejects_unsupported_algorithm`, `test_rejects_token_when_secret_not_configured`) cubren la verificacion de JWT de H-API-01. Se mantienen en su archivo original.

## Ejecucion registrada

| Fecha de ejecucion | Componente | IDs | Comando | Directorio | Codigo de salida | Resultado |
|---|---|---|---|---|---|---|
| Esta ejecucion | api | H-API-01, H-API-02, H-API-03, H-API-04 | `python tools/lab.py test api` | `api/` (via lab.py) | 0 | 50 passed, 0 failed, 103 warnings (deprecaciones de FastAPI `on_event` y de starlette, H-API-10) |

Resultado de referencia previo a esta ejecucion: 28 passed, 94.61% (sin tests de `/api/backend-health` ni de los casos borde nuevos).

## Cobertura

Metodo: coverage.py con `pytest --cov=app`, medicion de lineas y ramas (`branch`), reporte `term-missing` y `htmlcov/`. Alcance: el paquete `api/app/`, que contiene todo el codigo modificado por los hallazgos H-API-01..04.

| Medida | Numerador | Denominador | Porcentaje |
|---|---|---|---|
| Lineas, codigo modificado (`app/`) | 206 | 209 | 98.56% |
| Cobertura total del reporte (lineas + ramas) | sumatoria del reporte | sumatoria del reporte | 97.93% |
| `app/main.py` | 100% | 100% | 100% |
| `app/uploads.py` | 100% | 100% | 100% |
| `app/repository.py` | 100% | 100% | 100% |
| `app/security.py` | 70 | 73 | 95.89% (sin cubrir lineas 46, 62, 85) |

Cobertura global: el paquete medido es el mismo que el codigo modificado, asi que la cobertura global de la API (lineas + ramas) es 97.93%. Las pruebas no se miden a si mismas.

Umbral de AGENTS.md: 85%. Cumplido en la ejecucion registrada (`--cov-fail-under=85`).

## Fallos

Ninguno en esta ejecucion. No se adaptó ningun test para que pasara.

## Bugs o comportamientos observados (reportados aparte)

- H-API-06 (pendiente): `/api/backend-health` devuelve `body` con el texto de la excepcion (`test_backend_health_unreachable_upstream_returns_status_zero` lo confirma con `"connection refused"`). El test caracteriza el comportamiento actual; no lo aprueba. Al corregir H-API-06, este test debe cambiar a un `body` generico, y ese cambio debe revisarse aparte.
- Decision P-PLAN-04 (`mantener_201`): `POST /api/tasks` con `{}` crea una tarea con `title=""`. Esta registrado como comportamiento observado, no como defecto.
- `storedAt` de `POST /api/requirements` expone la ruta del servidor (ver ENDPOINTS.md, riesgos pendientes). No hay test que lo fije como contrato.

## Pendientes

- Lineas 46, 62 y 85 de `api/app/security.py` sin cubrir. Son ramas de error de JWT que requieren tokens con estructura malformada o claims especificos. Pendiente de un test dedicado.
- H-API-05 (dependencias): `pip-audit` no se ha ejecutado; no hay evidencia de CVEs corregidos. Pendiente.
- Dependencia externa: el servicio `auth/` debe emitir tokens HS256 compatibles (`iss=ai-labs-auth`, `aud=ai-labs-api`). Las pruebas no lo verifican; usan tokens firmados en el propio test.
- Ninguna prueba cubre el comportamiento real del upstream de `backend-health` (`GET /q/health` en `auth/`); se usa un fake de `urllib3`.

## Pruebas propuestas (no implementadas)

- Timeout del upstream en `/api/backend-health` (`urllib3` lanza `TimeoutError`): esperado `status:0`.
- Nombre de archivo de exactamente 128 caracteres: esperado 201 (cierra el limite superior).
- `POST /api/tasks` con body JSON valido pero `priority` no reconocido: documentar si se acepta.
- Confirmar que `storedAt` deja de exponer la ruta del servidor cuando se resuelva el riesgo pendiente.
