# Tasks

Issue: [#22](https://github.com/user-bcp-student42/ai-labs/issues/22) (H-AUTH-01). Alcance: solo `auth/`. Las pruebas se ejecutan desde `auth/` con `mvn test`.

## 1. Caracterización del comportamiento actual (sin tocar código de producción)

- [x] 1.1 En `AuthResourceTest`, añadir prueba de login válido de `student` / `Workshop123!` que verifique 200, `token`, `expiresIn`, `user.username`, `user.displayName` y `user.role`; verificar que pasa con `mvn test` contra el código actual.
- [x] 1.2 Añadir prueba de login válido de `trainer` / `Trainer123!` que verifique 200 y el `user.role` propio de ese usuario; verificar que pasa contra el código actual.
- [x] 1.3 Añadir prueba de contraseña incorrecta para `student` que verifique 401, `message` con la forma `Invalid user student or password` y ausencia de `token`; verificar que pasa contra el código actual.
- [x] 1.4 Añadir prueba de usuario inexistente que verifique 401 y ausencia de `token`; verificar que pasa contra el código actual.
- [x] 1.5 Añadir pruebas de 400 con `message` para `username` ausente, `username` en blanco, `password` ausente y `password` en blanco; verificar que pasan contra el código actual.
- [x] 1.6 Añadir prueba con `username` `o'brien` y contraseña no vacía que verifique 401 (no 500) y ausencia de `token`; verificar que pasa contra el código actual.
- [x] 1.7 Ejecutar `mvn test` desde `auth/` y verificar que toda la suite está en verde; hacer commit solo de `AuthResourceTest` en `feature/h-auth-01`.

## 2. Pruebas de inyección (deben fallar antes de la corrección)

- [x] 2.1 Añadir prueba con `username` `' OR 1=1--` y una contraseña cualquiera que verifique 401 y ausencia de `token`; verificar que falla contra el código actual.
- [x] 2.2 Añadir prueba con `username` `student` y `password` `' OR '1'='1` que verifique 401 y ausencia de `token`; verificar que falla contra el código actual.
- [x] 2.3 Añadir prueba con `' OR '1'='1` en ambos campos que verifique 401 y ausencia de `token`; verificar que falla contra el código actual.
- [x] 2.4 Añadir prueba con `username` `student'--` y contraseña incorrecta que verifique 401 y ausencia de `token`; verificar que falla contra el código actual.
- [x] 2.5 Confirmar en la salida de `mvn test` que cada fallo de 2.1 a 2.4 se debe a que la respuesta fue 200 con `token` y no a una excepción ni a un error de configuración; hacer commit solo de las pruebas.

## 3. Corrección en `LegacyDatabase.findByCredentials`

- [x] 3.1 Modificar únicamente `findByCredentials` para que `username` y `password` se enlacen como parámetros y no se concatenen en el SQL, conservando la misma condición, la firma, el retorno `null` sin coincidencia y el manejo de excepciones; verificar con `mvn test` desde `auth/` que pasan las pruebas de los grupos 1 y 2.
- [x] 3.2 Revisar el diff y verificar que no cambian `AuthResource`, `LegacyTokenUtil`, `pom.xml`, `application.properties`, ni archivos fuera de `auth/`.

## 4. Verificación final

- [x] 4.1 Ejecutar `mvn verify` desde `auth/` y verificar que la suite completa pasa; revisar el informe de JaCoCo y confirmar cobertura de 85% o más en el método modificado.
- [x] 4.2 Confirmar uno a uno los criterios de aceptación del Issue #22 contra la evidencia de las pruebas: uso de parámetros, login válido 200, inyección 401 sin `token`, e inclusión de la prueba de inyección en `AuthResourceTest`.
- [x] 4.3 Ejecutar `openspec validate h-auth-01-parameterized-login-query --strict` desde la raíz y verificar que el change sigue siendo válido.

## Workflow follow-up

- Abrir la PR del Issue #22 y archivar el change OpenSpec cuando se cumplan los requisitos de revisión del proyecto.
