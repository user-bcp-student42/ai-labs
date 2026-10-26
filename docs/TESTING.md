# Pruebas

## auth

Las pruebas se ejecutan con cwd `auth/`. La base de datos de Quarkus en perfil test se fija mediante Surefire a `target/auth-tests.db`; `AuthResourceTest` comprueba esa URL antes de hacer requests. `LegacyDatabaseTest` crea una SQLite con nombre aleatorio bajo `target/` y la elimina al finalizar. Así, las pruebas no usan `data/workshop.db` ni sobrescriben datos locales (`auth/pom.xml`, `auth/src/main/resources/application.properties`, `auth/src/test/java/com/bcp/workshop/auth/AuthResourceTest.java:31-44`, `auth/src/test/java/com/bcp/workshop/auth/LegacyDatabaseTest.java:18-64`).

### Matriz de casos

| endpoint | caso | tipo | resultado esperado |
|---|---|---|---|
| `POST /auth/login` | Cuenta semilla válida con `client` | Feliz | HTTP 200; token, expiración y usuario con el esquema documentado. H-AUTH-08 |
| `POST /auth/login` | Cuenta válida sin `client` | Borde | HTTP 200; `client` es opcional y no cambia la autenticación. H-AUTH-08 |
| `POST /auth/login` | Cuenta ficticia cuyo username almacenado contiene una comilla | Borde | HTTP 200; demuestra parámetros SQL enlazados. H-AUTH-01 |
| `POST /auth/login` | Username/password vacíos, solo espacios o ausentes | Borde/error | HTTP 400 con el mensaje correspondiente. H-AUTH-06, H-AUTH-08 |
| `POST /auth/login` | Cuerpo JSON `null` | Error | HTTP 400, `{"message":"Request is null"}`. H-AUTH-06 |
| `POST /auth/login` | Credenciales que no coinciden | Error | HTTP 401, mensaje de credenciales inválidas. H-AUTH-01, H-AUTH-02, H-AUTH-08 |
| `POST /auth/login` | Excepción inesperada inyectada en `AuthService` | Error | HTTP 500 con `message=Authentication failed` y `exception=InternalError`; sin detalles internos. H-AUTH-05 |
| `POST /auth/login` | Origen CORS no configurado | Error | HTTP 403, cuerpo vacío y sin `Access-Control-Allow-Origin`. H-AUTH-04 |
| `POST /auth/login` | Origen local configurado `http://localhost:4200` | Feliz/borde | HTTP 200 con `Access-Control-Allow-Origin` igual al origen permitido. H-AUTH-04 |
| `GET /q/health` | Servicio disponible, sin autenticación | Feliz | HTTP 200 y `status=UP`. H-AUTH-08 |
| `GET /q/health` | No hay checks propios registrados | Borde | HTTP 200 y `checks=[]`. H-AUTH-08 |

Las respuestas de Quarkus para JSON malformado, media types no soportados, rutas/métodos inexistentes y health `DOWN` están anotadas como preguntas abiertas en `docs/ENDPOINTS.md`; no se inventan casos ni cuerpos para ellas.

### Código de tests

Los métodos siguientes son fragmentos fieles de los tests ejecutables. Los archivos enlazados contienen el código completo y las aserciones auxiliares.

Login feliz (`auth/src/test/java/com/bcp/workshop/auth/AuthResourceTest.java:46-60`):

```java
@Test
void logsInWithWorkshopUser() {
    given()
            .contentType("application/json")
            .body("{\"username\":\"student\",\"password\":\"Workshop123!\",\"client\":\"angular-workshop\"}")
            .when().post("/auth/login")
            .then()
            .statusCode(200)
            .body("user.username", is("student"))
            .body("user.displayName", is("Workshop Student"))
            .body("user.role", is("STUDENT"))
            .body("expiresIn", is(3600))
            .body("debug", is("authenticated-with-legacy-flow"))
            .body("token", notNullValue());
}
```

Campos requeridos, incluido cuerpo nulo (`AuthResourceTest.java:116-183`):

```java
@Test
void rejectsNullRequestBody() {
    given()
            .contentType("application/json")
            .body("null")
            .when().post("/auth/login")
            .then()
            .statusCode(400)
            .body("message", is("Request is null"));
}

@Test
void rejectsWhitespaceOnlyCredentials() {
    given()
            .contentType("application/json")
            .body("{\"username\":\"   \",\"password\":\"Workshop123!\"}")
            .when().post("/auth/login")
            .then()
            .statusCode(400)
            .body("message", is("Username is required"));
}
```

Error 500 por excepción controlada a través del endpoint (`AuthResourceTest.java:271-287`):

```java
@Test
void hidesExceptionDetailsFromErrorResponse() {
    QuarkusMock.installMockForType(new AuthService() {
        @Override
        public LoginResponse login(LoginRequest request) {
            throw new IllegalStateException("database-private-detail");
        }
    }, AuthService.class);

    given()
            .contentType("application/json")
            .body("{\"username\":\"student\",\"password\":\"Workshop123!\"}")
            .when().post("/auth/login")
            .then()
            .statusCode(500)
            .body("message", is("Authentication failed"))
            .body("exception", is("InternalError"));
}
```

Health feliz y borde (`AuthResourceTest.java:290-306`):

```java
@Test
void healthEndpointReportsServiceUp() {
    given()
            .when().get("/q/health")
            .then()
            .statusCode(200)
            .body("status", is("UP"));
}

@Test
void healthEndpointReportsNoChecksWhenNoneAreRegistered() {
    given()
            .when().get("/q/health")
            .then()
            .statusCode(200)
            .body("checks", empty());
}
```

Cobertura de controles de seguridad adicionales: SQL y login con username citado en `auth/src/test/java/com/bcp/workshop/auth/AuthResourceTest.java:84-115`; hash y migración idempotente en `auth/src/test/java/com/bcp/workshop/auth/LegacyDatabaseTest.java:18-64` y `auth/src/test/java/com/bcp/workshop/auth/PasswordHasherTest.java:12-30`; firma, claims y alteración de JWT en `AuthResourceTest.java:203-244`; CORS permitido/denegado en `AuthResourceTest.java:246-269`; validación interna de token en `auth/src/test/java/com/bcp/workshop/auth/TokenServiceTest.java:12-35`.

### Ejecuciones y cobertura

| componente | IDs | comando | directorio | código de salida | resultado |
|---|---|---|---|---:|---|
| auth | H-AUTH-04, H-AUTH-05, H-AUTH-08 | `mvn "-Dtest=AuthResourceTest#healthEndpointReportsServiceUp+healthEndpointReportsNoChecksWhenNoneAreRegistered+hidesExceptionDetailsFromErrorResponse" test` | `auth/` | 0 | 3 tests, 0 fallos; health y error HTTP 500. |
| auth | H-AUTH-02 | `mvn "-Dtest=LegacyDatabaseTest" test` | `auth/` | 0 | 1 test, 0 fallos; migración idempotente usando SQLite aleatoria temporal. |
| auth | H-AUTH-08 | `mvn "-Dtest=PasswordHasherTest" test` | `auth/` | 0 | 2 tests, 0 fallos. |
| auth | H-AUTH-03 | `mvn "-Dtest=TokenServiceTest" test` | `auth/` | 0 | 2 tests, 0 fallos. |
| auth | H-AUTH-01 a H-AUTH-08 | `mvn "-Dtest=AuthResourceTest" test` | `auth/` | 0 | 14 tests, 0 fallos; incluye todos los estados HTTP documentados. |
| auth | H-AUTH-01 a H-AUTH-08 | `mvn verify` | `auth/` | 0 | 19 tests, 0 fallos; BUILD SUCCESS; JaCoCo generado. |

Método de medición: JaCoCo 0.8.12, contadores `LINE` del XML `auth/target/site/jacoco/jacoco.xml`, dividendo `covered / (covered + missed)` por clase productiva modificada. Resultado de la última ejecución: `AuthResource` 100%, `AuthService` 100%, `LegacyDatabase` 97,9%, `PasswordHasher` 92,3%, `TokenService` 91,3%; DTOs/records 100%. Todas las clases superan el gate local del 85%. Reporte navegable: `auth/target/site/jacoco/index.html`.

### Fallos corregidos durante esta ejecución

- El primer `mvn verify` tras aislar la base falló en `LegacyDatabaseTest` porque el driver SQLite no estaba registrado después del classloader Quarkus; se añadió carga explícita del driver y la prueba aislada pasó.
- En esa ejecución, la comprobación de firma usó la clave del entorno en lugar de la constante ficticia del test; el test ahora verifica con la configuración activa inyectada sin imprimirla.
- Tras ambas correcciones, el `mvn verify` final terminó con código 0 y 19 tests aprobados.

### Pendientes y preguntas abiertas

- H-AUTH-07 (SCA) sigue pendiente; no se ejecutaron análisis SCA, CodeQL ni Dependency Review.
- No se añadieron tests para errores del parser JSON, media types no soportados, rutas/métodos inexistentes ni health `DOWN`, porque sus status/cuerpos no están documentados ni verificados en `docs/ENDPOINTS.md`.

### Pruebas propuestas, no ejecutadas

- Acordar primero con el runtime/contrato los status y cuerpos para JSON malformado y `Content-Type` no soportado; después agregar un caso HTTP por cada comportamiento confirmado.
- Si se registra un `HealthCheck` propio, inducir un estado `DOWN` con una dependencia local controlada y comprobar el status/cuerpo que entonces establezca el contrato.
- No se proponen expectativas para 404/405 porque no son respuestas de los endpoints documentados y no se verificaron en este paso.