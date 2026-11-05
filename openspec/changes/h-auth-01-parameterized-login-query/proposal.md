# Proposal

## Why

Issue [#22](https://github.com/user-bcp-student42/ai-labs/issues/22) (H-AUTH-01, componente `auth`, vulnerabilidad de severidad alta) documenta que la verificación de credenciales de `POST /auth/login` construye la consulta SQL concatenando `username` y `password` (evidencia: `auth/src/main/java/com/bcp/workshop/auth/LegacyDatabase.java:32`). Un valor como `' OR '1'='1` altera la consulta y permite iniciar sesión sin conocer la contraseña. Al ser la puerta de entrada que emite los tokens que consume `api/`, la omisión de la autenticación compromete a todo el sistema.

## What Changes

- Las credenciales recibidas en `POST /auth/login` se tratan siempre como datos, nunca como parte de la consulta: un valor con sintaxis SQL no puede cambiar el resultado de la verificación.
- Un intento de inyección (por ejemplo `' OR '1'='1` en usuario o contraseña) responde 401 y no devuelve `token`.
- Las credenciales válidas siguen autenticando con el mismo contrato de respuesta.
- Se exige una prueba automatizada del intento de inyección dentro de la suite de `auth/`.

No hay cambios incompatibles: el contrato externo de `POST /auth/login` se conserva.

## Capabilities

### New Capabilities
- `auth-login`: verificación de credenciales y emisión de sesión en `POST /auth/login`, incluyendo la resistencia a inyección y el contrato de respuesta que se preserva. No existen specs previas en `openspec/specs/`; esta es la primera y fija el comportamiento observado hoy como baseline.

### Modified Capabilities
<!-- Ninguna: no hay specs previas. -->

## Alcance

Dentro de alcance:
- Componente `auth/` únicamente.
- Comportamiento de `POST /auth/login` ante credenciales válidas, inválidas y con sintaxis SQL.
- Cobertura de prueba del intento de inyección en `AuthResourceTest` y ejecución de `mvn test` desde `auth/`.

Fuera de alcance:
- Almacenamiento o comparación de contraseñas (hoy en texto plano) y cualquier otro hallazgo de `auth/`.
- Formato, firma, contenido o expiración del token (`LegacyTokenUtil`).
- Campos de respuesta no relacionados con la inyección: `debug`, `expiresIn` y el detalle de errores 500.
- El mensaje del 401, que hoy incluye el usuario recibido; se conserva tal cual.
- Componentes `api/` y `web/`, `docs/ENDPOINTS.md`, `HALLAZGOS.md` y `PLAN.md`.
- Nuevos endpoints, bloqueo de cuentas, límites de intentos o cambios de esquema de base de datos.

## Comportamiento que debe preservarse

`docs/ENDPOINTS.md` documenta solo el componente `api` y no contiene sección para `/auth/login`. Por eso el baseline es el comportamiento observado en `AuthResource` y en `docs/auth-login-sequence.md`, junto con el Issue:

- Cuerpo ausente, `username` ausente o vacío, o `password` ausente o vacío: 400 con `message`.
- Credenciales no encontradas: 401 con `message` en la forma `Invalid user <usuario> or password`.
- Credenciales válidas (`student` / `Workshop123!`): 200 con `token`, `expiresIn`, `user.username`, `user.displayName` y `user.role`.
- Los errores inesperados siguen respondiendo 500.
- El contrato de `api/` no cambia: los tokens emitidos conservan `sub` y `role` (según `docs/ENDPOINTS.md`, sección de autenticación).

## Impact

- Código: solo `auth/` (verificación de credenciales y su suite de pruebas). No se toca código en este paso de propuesta.
- APIs: sin cambios en rutas, métodos ni formato de respuesta.
- Dependencias: ninguna nueva.
- Riesgo: un cambio que altere el trato de usuarios con caracteres especiales legítimos; los escenarios de la spec fijan que se rechazan con 401, sin error 500.
- Validación: pruebas de `auth/` con cobertura del código modificado de 85% o superior (`AGENTS.md`).
