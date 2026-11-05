# Design

## Context

Ver `proposal.md` (Why) para la motivación y `specs/auth-login/spec.md` para los requisitos.

Estado actual, todo dentro de `auth/`:

- `AuthResource.login` valida el cuerpo (400), llama a `LegacyDatabase.findByCredentials(username, password)` y responde 401 si devuelve `null`, o crea el token y responde 200.
- `findByCredentials` concatena `username` y `password` en un `SELECT` sobre `legacy_users` y lo ejecuta con un `Statement` (`LegacyDatabase.java:32`). Cualquier excepción se imprime y se devuelve `null`; por eso, hoy, un valor con comilla que rompe la sintaxis (`o'brien`) ya termina en 401 y no en 500.
- La base es SQLite (`AUTH_DB_URL`, por defecto `jdbc:sqlite:./data/workshop.db`), con usuarios semilla `student` y `trainer` creados en `@PostConstruct`. Las contraseñas se comparan en texto plano en la propia consulta.
- Las pruebas son `@QuarkusTest` con RestAssured sobre la base real; `AuthResourceTest` tiene un único caso (login válido). JaCoCo ya está configurado en `pom.xml`.
- `docs/ENDPOINTS.md` no documenta `/auth/login`; el baseline es el comportamiento observado (ver `proposal.md`, "Comportamiento que debe preservarse").

## Goals / Non-Goals

**Goals:**
- Que ningún valor de `username` o `password` pueda modificar la estructura de la consulta de verificación.
- Mantener sin cambios el contrato externo de `POST /auth/login` y la firma pública de `findByCredentials`.
- Dejar pruebas que fallen si la concatenación vuelve a introducirse.

**Non-Goals:**
- Hash de contraseñas, migración de datos o cambio del esquema de `legacy_users`.
- Separar `AuthResource` en capas, reducir su anidamiento o extraer constantes (`3600`); son mejoras de clean code ajenas a este hallazgo y se tratarían en otro cambio.
- Cambiar el manejo de excepciones de `findByCredentials` (sigue devolviendo `null`).
- Tocar `LegacyTokenUtil`, `api/` o `web/`.

## Contratos protegidos

| Contrato | Valor a preservar | Origen |
|---|---|---|
| Ruta y método | `POST /auth/login`, JSON | `AuthResource` |
| 400 | Cuerpo nulo, `username` o `password` ausente o en blanco; cuerpo con `message` | spec: validación de campos |
| 401 | Sin coincidencia; `message` con la forma `Invalid user <usuario> or password`; sin `token` | spec: credenciales inválidas |
| 200 | `token`, `expiresIn`, `user.username`, `user.displayName` (escapado), `user.role`, y el campo `debug` actual | `AuthResource` |
| 500 | Excepción inesperada en el recurso | `AuthResource` |
| Firma | `UserRecord findByCredentials(String, String)` devuelve `null` si no hay coincidencia | `LegacyDatabase` |
| Token hacia `api/` | `LegacyTokenUtil.create(username, role)` sin cambios | `docs/ENDPOINTS.md` (autenticación) |

## Componentes afectados

- Modifica: `auth/.../LegacyDatabase.java`, solo el método `findByCredentials`.
- Modifica: `auth/.../AuthResourceTest.java` (nuevos casos).
- Sin cambios: `AuthResource`, `LegacyTokenUtil`, `LoginRequest`, `UserRecord`, `pom.xml`, `application.properties`.

## Decisions

### D1. Consulta con parámetros enlazados en lugar de concatenación
`findByCredentials` pasa a ejecutar una sentencia preparada con marcadores para `username` y `password`, enlazados como valores. Es el mecanismo que exige el criterio de aceptación del Issue y elimina la causa raíz: el motor nunca interpreta el contenido de las credenciales como SQL.

Alternativas descartadas:
- **Escapar comillas manualmente**: frágil, dependiente del dialecto y propenso a omisiones; no elimina la causa.
- **Validar o filtrar caracteres en `AuthResource`**: rechazaría usuarios legítimos con caracteres especiales y deja la consulta vulnerable ante otros llamadores.
- **Buscar solo por `username` y comparar la contraseña en Java**: es más segura a futuro (habilita hashing), pero cambia el criterio de aceptación y roza el límite de alcance (contraseñas). Queda como siguiente paso en otro cambio.
- **Introducir un ORM o capa de repositorio**: dependencia y rediseño no justificados por un hallazgo puntual.

### D2. Mantener la consulta y el modelo de datos
Se conserva el mismo `SELECT` con la misma condición de igualdad sobre `username` y `password`, solo con valores enlazados. Así el resultado para credenciales válidas e inválidas es idéntico al actual, lo que protege el contrato.

### D3. Mantener el manejo de errores actual
Las excepciones siguen capturándose en `findByCredentials` y devolviendo `null`. Cambiarlo alteraría el contrato (401 vs 500) y está fuera de alcance. Con parámetros enlazados, un valor como `o'brien` ya no provoca error de sintaxis: simplemente no coincide y responde 401 por la vía normal.

### D4. Pruebas a nivel HTTP, sobre la base semilla
Se prueba con `@QuarkusTest` y RestAssured, igual que la prueba existente, para verificar el contrato observable sin acoplarse a la implementación (ver spec: las pruebas no dependen de clases internas). No se añaden dependencias de prueba.

## Estrategia incremental

1. **Caracterización (verde)**: añadir a `AuthResourceTest` las pruebas del comportamiento actual que no cambia, sin tocar código de producción.
2. **Prueba de inyección (roja)**: añadir los casos de inyección y confirmar que fallan contra el código actual. Es la evidencia de la vulnerabilidad y la red de seguridad del cambio.
3. **Corrección**: modificar solo `findByCredentials` conforme a D1.
4. **Verificación**: ejecutar `mvn test` desde `auth/`; todas las pruebas, incluidas las rojas del paso 2, deben pasar. Revisar cobertura JaCoCo del método modificado (meta 85% o más).

Cada paso es un commit revisable por separado, en la rama `feature/h-auth-01`.

## Pruebas de caracterización necesarias antes de modificar

Deben pasar contra el código actual (paso 1):

| Prueba | Contrato que fija |
|---|---|
| Login válido `student` / `Workshop123!` | 200; `user.username`, `user.role`, `user.displayName`, `token`, `expiresIn` |
| Login válido `trainer` / `Trainer123!` | 200 con `role` distinto; confirma que el usuario correcto se resuelve |
| Contraseña incorrecta | 401, sin `token`, `message` con la forma `Invalid user <usuario> or password` |
| Usuario inexistente | 401, sin `token` |
| Cuerpo sin `username` / `username` en blanco | 400 con `message` |
| Cuerpo sin `password` / `password` en blanco | 400 con `message` |
| Usuario con comilla simple y credenciales no válidas (`o'brien`) | 401, no 500 |

Deben fallar contra el código actual y pasar tras el cambio (paso 2):

| Prueba | Resultado esperado |
|---|---|
| `username` `' OR 1=1--` con contraseña cualquiera | 401, sin `token` (con `' OR '1'='1` en `username` la precedencia de `AND` ya lo rechaza hoy; `--` anula la comprobación de contraseña) |
| `username` `student`, `password` `' OR '1'='1` | 401, sin `token` |
| Ambos campos `' OR '1'='1` | 401, sin `token` |
| `username` `student'--` con contraseña incorrecta | 401, sin `token` (variante con comentario SQL, no listada en el Issue) |

## Risks / Trade-offs

- **Regresión en login legítimo** → las pruebas de caracterización del paso 1 se ejecutan antes y después; la consulta conserva su semántica (D2).
- **Prueba de inyección que pasa por la razón equivocada** (por ejemplo, un error 500 que devuelve 401) → verificar primero que fallan contra el código actual y que 401 no proviene de una excepción capturada.
- **Base compartida entre pruebas**: los usuarios semilla viven en `./data/workshop.db`; no se deben insertar ni modificar usuarios en las pruebas, para no contaminar entornos ni otras ejecuciones.
- **Contraseñas en texto plano siguen igual**: este cambio cierra la inyección, no el almacenamiento. Queda documentado como fuera de alcance.
- **El 401 sigue reflejando el usuario recibido**: se conserva por contrato; el contenido enviado por el cliente ya no afecta a la consulta, pero sigue apareciendo en la respuesta.
- **Trade-off**: no se separa `AuthResource` ni se refactoriza; el cambio es mínimo para facilitar la revisión, a costa de mantener deuda de clean code ya conocida.

## Migration Plan

- No hay migración de datos, esquema ni configuración; el cambio se despliega con la aplicación `auth/`.
- **Rollback**: revertir el commit de la corrección (paso 3). Las pruebas del paso 2 volverían a fallar, lo que lo hace detectable. Revertir reabre la vulnerabilidad, así que solo se justifica ante una regresión funcional del login legítimo, y debe acompañarse de un nuevo cambio que la corrija.
- Sin efecto en `api/` y `web/`: el formato del token y de la respuesta no cambia.
