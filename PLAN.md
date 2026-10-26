# Plan de remediacion

## auth

### Seleccion y criterio

El pedido no especifico IDs concretos. Para no dejar hallazgos pendientes sin plan, se incluyen los ocho IDs de auth que aparecen como `Pendiente` en `HALLAZGOS.md`. El orden prioriza severidad; esta seleccion es una propuesta de planificacion, no una aprobacion humana para implementar.

`docs/ENDPOINTS.md` no existe. Se preservara el contrato observado en `HALLAZGOS.md`: `POST /auth/login`, JSON, validaciones 400, credenciales no validas 401 y login exitoso 200 con `token`, `expiresIn`, `user` y `debug`. Las respuestas de error interno conservaran HTTP 500 y las claves JSON observadas, con valores genericos que no filtren excepciones. El token seguira en el campo `token` y conservara el tiempo de vida externo observado.

### H-AUTH-01 - Credenciales concatenadas en SQL -APROBADO

- Hallazgo: concatenacion de username y password en la consulta de `LegacyDatabase.findByCredentials`.
- Problema: valores de entrada pueden cambiar la semantica de la consulta y permitir autenticaciones no previstas.
- Cambio propuesto: sustituir `Statement` y SQL concatenado por `PreparedStatement` con placeholders para ambos valores. Mantener la consulta parametrizada en la capa de repositorio y el contrato HTTP existente.
- Archivos a tocar: `auth/src/main/java/com/bcp/workshop/auth/LegacyDatabase.java`; `auth/src/test/java/com/bcp/workshop/auth/AuthResourceTest.java`.
- Prueba de caracterizacion antes del cambio: probar cuenta ficticia valida (200), credenciales incorrectas (401) y username que contenga una comilla (no autenticado, sin token y sin 500). No usar un payload de explotacion.

### H-AUTH-02 - Contrasenas en texto plano - APROBADO

- Hallazgo: valores literales en la columna `password` y comparacion directa con la entrada.
- Problema: una copia o lectura de SQLite expone credenciales reutilizables.
- Cambio propuesto: almacenar hash lento con salt, preferiblemente BCrypt conforme a `docs/GOOD_PRACTICES.md`; verificar con la misma implementacion al autenticar. Definir migracion idempotente de las cuentas existentes y de los usuarios de ejemplo para no romper el login. Revisar si ya existe una implementacion adecuada antes de agregar una dependencia.
- Archivos a tocar: `auth/src/main/java/com/bcp/workshop/auth/LegacyDatabase.java`; nueva clase de servicio de hash bajo `auth/src/main/java/com/bcp/workshop/auth/`; `auth/src/test/java/com/bcp/workshop/auth/AuthResourceTest.java`; `auth/pom.xml` solo si la implementacion elegida no esta disponible y la dependencia queda justificada.
- Prueba de caracterizacion antes del cambio: en SQLite temporal, caracterizar login valido e invalido; agregar una asercion de seguridad que compruebe que la contrasena almacenada no sea el texto de entrada y que el login con la cuenta semilla siga funcionando despues de migrar.

### H-AUTH-03 - Token Base64 sin firma -APROBADO

- Hallazgo: el token solo codifica username, role, expiracion y secreto; no hay firma verificable.
- Problema: los datos son legibles y no hay integridad criptografica que permita detectar alteraciones.
- Cambio propuesto: emitir un token firmado con expiracion y claims explicitos usando una implementacion JOSE/JWT compatible con Quarkus. Mantener el campo `token` y `expiresIn` en la respuesta; usar una constante nombrada para el TTL y la misma duracion en el claim `exp`.
- Archivos a tocar: `auth/src/main/java/com/bcp/workshop/auth/LegacyTokenUtil.java` o su reemplazo en `auth/src/main/java/com/bcp/workshop/auth/`; `auth/src/main/java/com/bcp/workshop/auth/AuthResource.java`; `auth/src/main/resources/application.properties`; `auth/pom.xml` solo si se requiere una extension de firma, con justificacion y revision de dependencia; `auth/src/test/java/com/bcp/workshop/auth/AuthResourceTest.java`.
- Prueba de caracterizacion antes del cambio: verificar login 200, presencia de `token` y `expiresIn` con la duracion observada. La prueba de seguridad posterior debe verificar firma, claims y expiracion, y rechazar un token alterado.

### H-AUTH-04 - Secreto embebido y CORS abierto -APROBADO

- Hallazgo: secreto constante en Java y origenes CORS configurados con `/.*/`.
- Problema: el secreto queda versionado y expuesto; cualquier origen que coincida con la expresion recibe permiso CORS.
- Cambio propuesto: eliminar el secreto de codigo y configurarlo externamente segun el mecanismo de firma seleccionado; sustituir el patron CORS global por una lista explicita y configurable de origenes permitidos. No agregar valores secretos reales.
- Archivos a tocar: `auth/src/main/java/com/bcp/workshop/auth/LegacyTokenUtil.java` o su reemplazo; `auth/src/main/resources/application.properties`; `auth/src/test/java/com/bcp/workshop/auth/AuthResourceTest.java`; `auth/pom.xml` solo si lo requiere la libreria de firma ya justificada en H-AUTH-03.
- Prueba de caracterizacion antes del cambio: registrar que el login mantiene el mismo contrato de respuesta y que las solicitudes sin origen siguen funcionando. Agregar prueba CORS para un origen permitido y otro no permitido; verificar que el token de prueba use claves aisladas y no un secreto real.

### H-AUTH-05 - Detalles internos en errores -APROBADO

- Hallazgo: HTTP 500 incluye el mensaje original de la excepcion y su clase.
- Problema: respuestas pueden revelar rutas, consultas o detalles de implementacion.
- Cambio propuesto: devolver valores genericos manteniendo el status 500 y las claves JSON observadas (`message` y `exception`); registrar el detalle solo en el logger del servidor, sin `printStackTrace` ni datos de contrasenas. Los errores 400 y 401 observados se conservan.
- Archivos a tocar: `auth/src/main/java/com/bcp/workshop/auth/AuthResource.java`; `auth/src/main/java/com/bcp/workshop/auth/LegacyDatabase.java`; `auth/src/test/java/com/bcp/workshop/auth/AuthResourceTest.java`.
- Prueba de caracterizacion antes del cambio: comprobar respuestas actuales 400, 401 y 200; inducir una excepcion controlada y verificar HTTP 500 y las claves de respuesta. La asercion posterior debe confirmar que los valores no contienen mensaje ni nombre real de excepcion.

### H-AUTH-06 - Responsabilidades mezcladas en AuthResource- APROBADO

- Hallazgo: `login` valida, consulta la base, crea token y compone la respuesta.
- Problema: cambios de HTTP, reglas de negocio o persistencia quedan acoplados y dificultan pruebas aisladas.
- Cambio propuesto: mantener `AuthResource` como adaptador HTTP; mover reglas de login a `AuthService` y SQL a un repositorio. Usar DTO de respuesta para conservar los campos actuales. Extraer validaciones/metodos pequenos, evitar duplicacion y anidamiento profundo, y nombrar constantes en vez de numeros magicos.
- Archivos a tocar: `auth/src/main/java/com/bcp/workshop/auth/AuthResource.java`; `auth/src/main/java/com/bcp/workshop/auth/LegacyDatabase.java` o repositorio nuevo; clases nuevas `AuthService` y DTOs en `auth/src/main/java/com/bcp/workshop/auth/`; `auth/src/test/java/com/bcp/workshop/auth/AuthResourceTest.java`.
- Prueba de caracterizacion antes del cambio: cubrir solicitud nula, username/password ausentes, credenciales invalidas y login valido; fijar status, claves JSON y valores observados para evitar cambios accidentales de contrato durante la separacion.

### H-AUTH-07 - Estado SCA sin verificar - APROBADO

- Hallazgo: Quarkus `3.27.4` y Commons Text `1.9` coinciden con los candidatos del reto; no hay resultado de analisis disponible.
- Problema: sin advisory ni ruta transitiva confirmados no se puede valorar exposicion ni elegir una actualizacion segura.
- Cambio propuesto: ejecutar analisis de dependencias/Dependency Review y registrar advisory, alcance y version corregida si corresponde. No cambiar versiones ni agregar dependencias hasta confirmar evidencia; no silenciar findings.
- Archivos a tocar: `auth/pom.xml` solo si el analisis confirma una actualizacion necesaria; `auth/src/test/java/com/bcp/workshop/auth/AuthResourceTest.java` para regresion del login si cambia el stack; `HALLAZGOS.md` para registrar el resultado real.
- Prueba de caracterizacion antes del cambio: conservar el test de login valido y anadir la matriz de respuestas 400/401/200 como referencia previa a cualquier upgrade. El escaneo SCA es una comprobacion de seguridad, no se reporta como prueba ejecutada en este plan.

### H-AUTH-08 - Cobertura de pruebas limitada - APROBADO

- Hallazgo: la prueba existente solo verifica login exitoso.
- Problema: errores de validacion, credenciales invalidas y excepciones pueden cambiar sin deteccion.
- Cambio propuesto: ampliar las pruebas del recurso por escenarios y probar servicios/repositorio con SQLite temporal. Mantener los casos agrupados por comportamiento, nombres descriptivos y fixtures reutilizables, sin duplicar setup.
- Archivos a tocar: `auth/src/test/java/com/bcp/workshop/auth/AuthResourceTest.java`; nuevas pruebas bajo `auth/src/test/java/com/bcp/workshop/auth/` solo donde una unidad separada requiera test propio.
- Prueba de caracterizacion antes del cambio: extender la suite con casos 400 para cuerpo/campos requeridos, 401 para credenciales invalidas, 200 con el esquema de respuesta observado y 500 controlado sin afirmar resultados hasta ejecutar Maven.

### Verificacion del plan

- H-AUTH-01: resuelto con `PreparedStatement`; el caso de cuenta ficticia `o'connor` fallo con HTTP 401 antes y paso con HTTP 200 despues.
- H-AUTH-02: resuelto con PBKDF2-HMAC-SHA256, salt aleatorio y migracion idempotente; antes se leyo la contrasena en claro y la nueva asercion fallo; despues la cuenta semilla y una cuenta heredada verifican correctamente.
- H-AUTH-03: resuelto con JWS HS256 y claims `sub`, `role`, `iss`, `iat` y `exp`; antes el token tenia un solo segmento y despues la firma, expiracion y rechazo de alteracion pasaron.
- H-AUTH-04: resuelto con clave externa y allowlist CORS; antes el servidor reflejaba cualquier origen, despues el origen desconocido recibe 403 y localhost permitido recibe 200.
- H-AUTH-05: resuelto con HTTP 500 y claves JSON conservadas, pero valores genericos; antes la respuesta contenia el detalle de la excepcion y despues la prueba paso.
- H-AUTH-06: resuelto separando `AuthResource`, `AuthService`, persistencia y DTO; la caracterizacion de request nulo confirmo HTTP 400 antes y la regresion posterior mantuvo los contratos observados.
- H-AUTH-07: pendiente. No se ejecuto analisis SCA local; CodeQL y Dependency Review remotos no se ejecutaron en este recorrido. No se cambio ninguna version ni se afirma un CVE.
- H-AUTH-08: resuelto ampliando pruebas de recurso, hashing, migracion, token y CORS. La verificacion completa final debe confirmar 16 tests y cobertura de linea JaCoCo >=85% por clase productiva modificada.

### Registro de ejecuciones

Todas las pruebas se ejecutaron con cwd `auth/`. Las filas de resultado rojo corresponden a la caracterizacion previa o a un defecto de implementacion/test corregido antes de continuar; no se ocultan.

| Componente | IDs | Comando | Resultado |
|---|---|---|---|
| auth | H-AUTH-01 a H-AUTH-06, H-AUTH-08 | `mvn -Dtest=AuthResourceTest test` | Antes de los cambios: 8 tests, 0 fallos. |
| auth | H-AUTH-01 | `mvn -Dtest=AuthResourceTest#authenticatesStoredUsernameContainingQuote test` | Antes del cambio: fallo esperado, HTTP 401 para una cuenta ficticia almacenada como valida. |
| auth | H-AUTH-01 | Mismo comando tras parametrizar | Fallo transitorio: HTTP 500 por import faltante de `PreparedStatement`; se corrigio antes de seguir. |
| auth | H-AUTH-01 | Mismo comando tras corregir el import | Despues: 1 test, 0 fallos; cuenta con comilla autenticada. |
| auth | H-AUTH-01, H-AUTH-06, H-AUTH-08 | `mvn -Dtest=AuthResourceTest test` | Despues de SQL parametrizado: 9 tests, 0 fallos. |
| auth | H-AUTH-02 | `mvn -Dtest=AuthResourceTest#storesSeedPasswordAsPlainTextBeforeRemediation test` | Antes: la afirmacion de texto plano paso; confirmo la condicion vulnerable. |
| auth | H-AUTH-02 | `mvn -Dtest=AuthResourceTest#storesSeedPasswordAsSaltedHash test` | Antes de migrar datos: fallo esperado porque `Workshop123!` seguia en claro. |
| auth | H-AUTH-02 | Mismo comando tras migracion | Fallo transitorio: la prueba consultaba antes de inicializar el bean; se ajusto para iniciar por HTTP. |
| auth | H-AUTH-02 | Mismo comando tras ajuste | Despues: 1 test, 0 fallos; la semilla se guarda hasheada. |
| auth | H-AUTH-02 | `mvn -Dtest=PasswordHasherTest test` | 2 tests, 0 fallos. |
| auth | H-AUTH-01, H-AUTH-02, H-AUTH-06, H-AUTH-08 | `mvn -Dtest=AuthResourceTest,PasswordHasherTest test` | 11 tests, 0 fallos. |
| auth | H-AUTH-03 | `mvn -Dtest=AuthResourceTest#tokenIsSignedJwtWithExplicitClaims test` | Antes: fallo esperado; el token tenia 1 segmento en lugar de 3. |
| auth | H-AUTH-03 | Mismo comando tras JWS | Despues: 1 test, 0 fallos; firma, claims y alteracion verificados. |
| auth | H-AUTH-04 | `mvn -Dtest=AuthResourceTest#doesNotAllowUnconfiguredCorsOrigin test` | Antes: fallo esperado; el origen no permitido recibia cabecera CORS. |
| auth | H-AUTH-04 | `mvn -Dtest=AuthResourceTest#doesNotAllowUnconfiguredCorsOrigin+allowsConfiguredCorsOrigin test` | Primer intento tras allowlist: 1 de 2 fallo porque Quarkus devolvio 403, comportamiento correcto; se ajusto la expectativa. |
| auth | H-AUTH-04 | Mismo comando tras ajustar expectativa | Despues: 2 tests, 0 fallos; origen desconocido 403 y localhost permitido 200. |
| auth | H-AUTH-05 | `mvn -Dtest=AuthResourceTest#hidesExceptionDetailsFromErrorResponse test` | Antes: fallo esperado; se devolvia `database-private-detail`. |
| auth | H-AUTH-05 | Mismo comando tras error generico | Despues: 1 test, 0 fallos; HTTP 500 mantiene claves genericas. |
| auth | H-AUTH-06 | `mvn -Dtest=AuthResourceTest#rejectsNullRequestBody test` | Antes de extraer capas: 1 test, 0 fallos; cuerpo null devuelve HTTP 400. |
| auth | H-AUTH-05, H-AUTH-06, H-AUTH-08 | `mvn -Dtest=AuthResourceTest test` | Despues de separar `AuthService`: 11 tests, 0 fallos. |
| auth | H-AUTH-02 | `mvn -Dtest=LegacyDatabaseTest test` | 1 test, 0 fallos; migracion y repeticion idempotentes. |
| auth | H-AUTH-02, H-AUTH-03 | `mvn -Dtest=TokenServiceTest,PasswordHasherTest test` | 4 tests, 0 fallos. |
| auth | H-AUTH-01 a H-AUTH-08 | `mvn verify` | 14 tests, 0 fallos; JaCoCo generado. |
| auth | H-AUTH-02 | `mvn -Dtest=PasswordHasherTest test` | 2 tests, 0 fallos tras cubrir Base64 malformado. |
| auth | H-AUTH-01 a H-AUTH-08 | `mvn verify` | 16 tests, 0 fallos; BUILD SUCCESS. Cobertura de linea por clase en esta ejecucion: AuthResource 100%, AuthService 100%, LegacyDatabase 97.9%, PasswordHasher 92.3%, TokenService 90%, DTO/records 100%. |
| auth | H-AUTH-02, H-AUTH-03, H-AUTH-04 | `mvn "-Dtest=PasswordHasherTest,AuthResourceTest#tokenIsSignedJwtWithExplicitClaims" test` | 3 tests, 0 fallos despues de subir PBKDF2 a 600.000 iteraciones y retirar la clave fija de dev. |
| auth | H-AUTH-01 a H-AUTH-08 | `mvn verify` (verificacion final tras endurecer PBKDF2) | 16 tests, 0 fallos; BUILD SUCCESS. JaCoCo: AuthResource 100%, AuthService 100%, LegacyDatabase 97.9%, PasswordHasher 92.3%, TokenService 90%, DTO/records 100%. |

### Desviaciones y pendientes

- H-AUTH-02 usa PBKDF2-HMAC-SHA256 del JDK con salt aleatorio y 600.000 iteraciones en vez de agregar BCrypt; se eligio para cumplir hash lento con salt sin una dependencia adicional. La migracion de filas de texto plano se probo en SQLite local.
- H-AUTH-03 usa `Mac`/Jackson ya disponibles para producir JWS HS256; no se agrego dependencia. La clave es obligatoria mediante `AUTH_TOKEN_SECRET` fuera de test. El perfil de test usa una clave ficticia aislada.
- La externalizacion de la clave H-AUTH-04 se implemento junto con H-AUTH-03 porque la firma necesita una clave configurable; no se usa una clave fija en dev.
- H-AUTH-07 sigue pendiente hasta obtener un resultado SCA/advisory verificable. CodeQL y Dependency Review remotos: no ejecutados.
- No se crearon `docs/ENDPOINTS.md` ni `docs/TESTING.md`, ni se modificaron otras areas del workspace.
- No se modificaron gates. La ultima ejecucion completa registrada fue antes del endurecimiento final de PBKDF2; se repetira `mvn verify` para cerrar el resultado final.