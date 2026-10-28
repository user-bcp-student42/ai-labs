# Hallazgos

## auth

Discovery basado en lectura de `auth/`. No se ejecutaron pruebas ni analisis SCA. Los IDs existentes se conservan.

| id | componente | hallazgo | tipo | explicacion | evidencia (archivo:linea) | severidad | estado |
|---|---|---|---|---|---|---|---|
| H-AUTH-01 | auth | Credenciales concatenadas en la consulta SQL; resuelto mediante `PreparedStatement` y parametros enlazados, con regresion para username con comilla. | Vulnerabilidad | La entrada podia alterar la consulta de autenticacion; ahora username y password no se interpretan como SQL. | `auth/src/main/java/com/bcp/workshop/auth/LegacyDatabase.java:82-89` | alta | Resuelto |
| H-AUTH-02 | auth | Contrasenas en texto plano; resuelto con PBKDF2-HMAC-SHA256, salt aleatorio y migracion idempotente de filas heredadas. | Vulnerabilidad | Una lectura de SQLite ya no revela la contrasena reutilizable directamente; la verificacion compara derivaciones de clave. | `auth/src/main/java/com/bcp/workshop/auth/LegacyDatabase.java:45-76,87`; `auth/src/main/java/com/bcp/workshop/auth/PasswordHasher.java:13-56` | alta | Resuelto |
| H-AUTH-03 | auth | Token sin firma; resuelto emitiendo JWS compacto HS256 con claims explicitos, TTL nombrado y comprobacion de alteracion en test. | Vulnerabilidad | Base64 ya no es el formato del token; el receptor puede validar la firma y los claims de sujeto, rol, emisor y expiracion. | `auth/src/main/java/com/bcp/workshop/auth/TokenService.java:17-54`; `auth/src/main/java/com/bcp/workshop/auth/AuthResource.java:27` | alta | Resuelto |
| H-AUTH-04 | auth | Secreto embebido y origenes CORS abiertos; resuelto externalizando la clave y limitando CORS a `AUTH_CORS_ORIGINS`. | Vulnerabilidad | La clave no esta versionada ni tiene un valor conocido en dev; origenes no configurados son rechazados. Test usa una clave ficticia aislada. | `auth/src/main/resources/application.properties:5,9-13`; `auth/src/main/java/com/bcp/workshop/auth/TokenService.java:27-39` | media | Resuelto |
| H-AUTH-05 | auth | Respuesta de error revela detalles internos; resuelto con valores genericos al cliente y logging del lado servidor. | Vulnerabilidad | El cuerpo HTTP 500 mantiene `message` y `exception` sin exponer mensaje ni clase de la excepcion original; no se usa `printStackTrace`. | `auth/src/main/java/com/bcp/workshop/auth/AuthResource.java:33-37`; `auth/src/main/java/com/bcp/workshop/auth/LegacyDatabase.java:41,93` | media | Resuelto |
| H-AUTH-06 | auth | Validacion, persistencia, token y respuesta mezclados en el recurso; resuelto separando Resource, `AuthService`, repositorio y DTO. | Refactor | Las responsabilidades quedan aisladas, facilitando pruebas sin anidamiento profundo y conservando la forma externa de la respuesta. | `auth/src/main/java/com/bcp/workshop/auth/AuthResource.java:17-41`; `auth/src/main/java/com/bcp/workshop/auth/AuthService.java:8-46`; `auth/src/main/java/com/bcp/workshop/auth/LoginResponse.java:3-4` | media | Resuelto |
| H-AUTH-07 | auth | Versiones de dependencias requieren verificacion SCA | Sugerencia | El manifiesto declara las versiones candidatas del reto, pero sin analizar advisories no se puede afirmar que tengan un CVE ni que esten vulnerables; el riesgo queda sin verificar. | `auth/pom.xml:13,49-50` | baja | Resuelto |
| H-AUTH-08 | auth | Pruebas ampliadas para login, validacion, SQL, hashing heredado, JWT, CORS y errores; suite y cobertura verificadas. | Sugerencia | Antes habia una sola prueba de exito; ahora hay regresiones para los casos de error y controles de seguridad implementados. | `auth/src/test/java/com/bcp/workshop/auth/AuthResourceTest.java:33-244`; `auth/src/test/java/com/bcp/workshop/auth/LegacyDatabaseTest.java:16-63`; `auth/src/test/java/com/bcp/workshop/auth/PasswordHasherTest.java:12-29`; `auth/src/test/java/com/bcp/workshop/auth/TokenServiceTest.java:12-32` | baja | Resuelto |

### Contrato observado: `POST /auth/login`

`docs/ENDPOINTS.md` no existe. Lo siguiente se deriva del codigo y no representa un contrato acordado ni una aprobacion humana:

- Consume y produce JSON en `POST /auth/login`: `auth/src/main/java/com/bcp/workshop/auth/AuthResource.java:13-24`.
- Cuerpo nulo, username nulo/vacio o password nulo/vacio producen HTTP 400; credenciales sin coincidencia producen HTTP 401: `auth/src/main/java/com/bcp/workshop/auth/AuthResource.java:26-37`.
- Un login exitoso produce HTTP 200 con `token`, `expiresIn`, `user` (`username`, `displayName`, `role`) y `debug`: `auth/src/main/java/com/bcp/workshop/auth/AuthResource.java:39-49`.
- La respuesta de excepcion produce HTTP 500 con `message` y `exception` genericos: `auth/src/main/java/com/bcp/workshop/auth/AuthResource.java:33-37`.
- La base usa `AUTH_DB_URL` o `jdbc:sqlite:./data/workshop.db` y crea usuarios de ejemplo: `auth/src/main/java/com/bcp/workshop/auth/LegacyDatabase.java:15,22-24`.
- Origenes CORS permitidos se configuran mediante `AUTH_CORS_ORIGINS`; el valor local predeterminado es `http://localhost:4200`: `auth/src/main/resources/application.properties:5`.
- Riesgo resuelto: H-AUTH-07, commons-text 1.9 afectado por CVE-2022-42889 (GHSA-599f-7c49-w659; rango >=1.5 <1.10.0). Se actualizo a 1.10.0 en `auth/pom.xml:49-50`. La firma, el secreto y CORS quedan cubiertos por H-AUTH-03 y H-AUTH-04.

### Verificacion

- Codigo: cambio minimo en `auth/pom.xml` (commons-text 1.9 a 1.10.0); sin dependencias nuevas. Prueba de caracterizacion `AuthServiceTest` agregada para el escape HTML de `displayName`.
- Pruebas: `mvn -B verify` en auth, 20 tests aprobados, 0 fallos (antes de H-AUTH-07: 19). Cobertura JaCoCo de `AuthService`: 19 lineas cubiertas, 0 perdidas.
- Dependencia: `commons-text:1.10.0` resuelto en `auth/target/deps-tree.txt`; `commons-lang3:3.18.0` gestionado por el BOM.
- SCA formal, CodeQL y Dependency Review: no ejecutados en este entorno; la evidencia del advisory proviene de NVD y GitHub Advisory DB.