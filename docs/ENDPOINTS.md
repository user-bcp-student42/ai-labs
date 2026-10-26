# Contratos HTTP

## auth

Las descripciones de `POST /auth/login` se contrastaron con el código actual y con solicitudes locales usando una SQLite temporal y una clave de prueba ficticia. `GET /q/health` se publica mediante SmallRye Health; no hay un `HealthCheck` propio en `auth/`.

### POST /auth/login

#### 1. Qué hace

Autentica a una persona usuaria de ReqFlow y, si sus credenciales son válidas, entrega un token firmado para que el componente cliente mantenga su sesión. La ruta consume y produce JSON (`auth/src/main/java/com/bcp/workshop/auth/AuthResource.java:14-25`).

#### 2. Autenticación requerida

No requiere autenticación previa ni un header `Authorization`; las credenciales se envían en el cuerpo. Requiere `Content-Type: application/json`. El servicio emite el token en la respuesta (`auth/src/main/java/com/bcp/workshop/auth/AuthResource.java:14-25`; `auth/src/main/java/com/bcp/workshop/auth/AuthService.java:15-32`).

#### 3. Request

| campo | tipo | obligatorio | descripción |
|---|---|---|---|
| `username` | string | Sí | Nombre de usuario. No puede ser nulo ni vacío después de recortar espacios. |
| `password` | string | Sí | Contraseña en texto del request; se verifica contra el hash almacenado. No puede ser nula ni vacía después de recortar espacios. |
| `client` | string | No | Campo aceptado por el DTO. El flujo actual no lo consulta ni define un efecto para su valor. |

Los campos corresponden a `auth/src/main/java/com/bcp/workshop/auth/LoginRequest.java:3-6`; las validaciones están en `auth/src/main/java/com/bcp/workshop/auth/AuthService.java:35-44` y la verificación de credenciales en `auth/src/main/java/com/bcp/workshop/auth/LegacyDatabase.java:81-96`.

Ejemplo JSON completo observado:

```json
{
  "username": "student",
  "password": "Workshop123!",
  "client": "angular-workshop"
}
```

Las credenciales de ejemplo son ficticias y están sembradas por `auth/src/main/java/com/bcp/workshop/auth/LegacyDatabase.java:22-24`.

#### 4. Response exitosa

Código: `200 OK` cuando las credenciales coinciden (`auth/src/main/java/com/bcp/workshop/auth/AuthResource.java:27`; verificado localmente).

| campo | tipo | descripción |
|---|---|---|
| `token` | string | JWS compacto con firma HS256. Incluye claims `sub`, `role`, `iss`, `iat` y `exp`. |
| `expiresIn` | integer | Tiempo de vida configurado del token, en segundos. El valor predeterminado es 3600. |
| `user` | object | Datos públicos de la persona autenticada. |
| `user.username` | string | Nombre de usuario. |
| `user.displayName` | string | Nombre para mostrar; se escapa con HTML4 antes de incluirlo. |
| `user.role` | string | Rol asignado a la cuenta. |
| `debug` | string | Indicador fijo que devuelve actualmente el servicio: `authenticated-with-legacy-flow`. |

La estructura se define en `auth/src/main/java/com/bcp/workshop/auth/LoginResponse.java:3-4`; se construye en `auth/src/main/java/com/bcp/workshop/auth/AuthService.java:22-32`. Los claims y la firma están en `auth/src/main/java/com/bcp/workshop/auth/TokenService.java:17-58`.

Ejemplo JSON completo recibido en la instancia local de documentación (el token es efímero y no debe reutilizarse):

```json
{
  "token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJzdHVkZW50IiwiaWF0IjoxNzkzMDUxMzE3LCJpc3MiOiJhaS1sYWJzLWF1dGgiLCJyb2xlIjoiU1RVREVOVCIsImV4cCI6MTc5MzA1NDkxN30.dHht9h1AEwT-lzm_AXzUYujtNAXI2g1CN4IgqUCmwtI",
  "expiresIn": 3600,
  "user": {
    "username": "student",
    "displayName": "Workshop Student",
    "role": "STUDENT"
  },
  "debug": "authenticated-with-legacy-flow"
}
```

#### 5. Respuestas de error

| código | cuándo ocurre | ejemplo de cuerpo |
|---|---|---|
| `400 Bad Request` | El cuerpo JSON es `null`. | `{"message":"Request is null"}` |
| `400 Bad Request` | `username` falta, es nulo o queda vacío tras recortar espacios. | `{"message":"Username is required"}` |
| `400 Bad Request` | `password` falta, es nula o queda vacía tras recortar espacios. | `{"message":"Password is required"}` |
| `401 Unauthorized` | No existe una cuenta que coincida con username y contraseña. El mensaje incluye el username recibido, no la contraseña. | `{"message":"Invalid user student or password"}` |
| `500 Internal Server Error` | Una excepción inesperada escapa del servicio de autenticación. La respuesta usa valores genéricos. | `{"message":"Authentication failed","exception":"InternalError"}` |
| `403 CORS Rejected` | La solicitud incluye un origen que no coincide con la allowlist CORS configurada. Quarkus responde sin cuerpo. | *(cuerpo vacío)* |

Los estados 400, 401 y 500 se manejan en `auth/src/main/java/com/bcp/workshop/auth/AuthResource.java:27-37`; las condiciones 400/401 se originan en `auth/src/main/java/com/bcp/workshop/auth/AuthService.java:35-46`. El rechazo CORS 403 fue observado localmente. Otros errores generados por el parser JSON o por el runtime HTTP no están mapeados expresamente por este recurso; ver preguntas abiertas.

#### 6. Notas de seguridad

- La consulta de usuario usa parámetros enlazados; las contraseñas persistidas se almacenan como PBKDF2-HMAC-SHA256 con salt aleatorio (`auth/src/main/java/com/bcp/workshop/auth/LegacyDatabase.java:45-96`; `auth/src/main/java/com/bcp/workshop/auth/PasswordHasher.java:13-60`).
- El token está firmado con HS256 y lleva `exp`; `expiresIn` y la expiración usan el TTL configurado (`auth/src/main/java/com/bcp/workshop/auth/TokenService.java:17-58`).
- Configura `AUTH_TOKEN_SECRET` con al menos 32 bytes UTF-8 antes de iniciar la aplicación. No hay una clave predeterminada de desarrollo; el perfil de test usa una clave ficticia. El emisor y TTL se pueden configurar con `AUTH_TOKEN_ISSUER` y `AUTH_TOKEN_TTL_SECONDS` (`auth/src/main/resources/application.properties:9-12`; `auth/src/main/java/com/bcp/workshop/auth/TokenService.java:27-40`).
- CORS solo permite los orígenes de `AUTH_CORS_ORIGINS`; el predeterminado local es `http://localhost:4200` (`auth/src/main/resources/application.properties:4-7`).
- Envía las credenciales solo por HTTPS fuera de un entorno local controlado. No registres contraseñas ni incluyas secretos reales en código, documentación o tests.

### GET /q/health

#### 1. Qué hace

Permite a una integración u orquestador comprobar si el servicio de autenticación informa que está disponible. La ruta la aporta la extensión `quarkus-smallrye-health` declarada en `auth/pom.xml:40`; no hay un endpoint health implementado en las clases Java de auth.

#### 2. Autenticación requerida

No requiere header `Authorization`; la solicitud local verificada fue un `GET` sin credenciales.

#### 3. Request

No tiene cuerpo ni parámetros definidos por el componente.

| campo | tipo | obligatorio | descripción |
|---|---|---|---|
| *(ninguno)* | — | — | No hay campos de request definidos por el código de auth. |

Ejemplo de request HTTP:

```http
GET /q/health HTTP/1.1
Host: localhost:8080
Accept: application/json
```

#### 4. Response exitosa

Código: `200 OK` cuando el estado observado es `UP` (verificado localmente).

| campo | tipo | descripción |
|---|---|---|
| `status` | string | Estado agregado de salud. El valor observado fue `UP`. |
| `checks` | array | Lista de checks reportados por SmallRye Health. En la ejecución observada no había checks registrados. La forma de un elemento no se define en código propio de auth. |

Ejemplo JSON completo observado:

```json
{
  "status": "UP",
  "checks": []
}
```

#### 5. Respuestas de error

No se observó una respuesta de error: la aplicación no registra checks propios y la comprobación local devolvió `200 UP`. No se documenta un código o cuerpo para un estado no saludable sin una comprobación que lo produzca.

#### 6. Notas de seguridad

- El endpoint informa salud del proceso y no es un mecanismo de autenticación ni debe usarse como prueba de que las credenciales o tokens de una cuenta son válidos.
- El status y cuerpo para checks fallidos dependen de SmallRye Health y no se verificaron porque auth no declara checks personalizados.

## Preguntas abiertas

- ¿Qué códigos y cuerpos genera el runtime Quarkus para JSON malformado, `Content-Type` ausente o no soportado y rutas/métodos no encontrados? `AuthResource` no los mapea expresamente y no se comprobaron.
- ¿Qué status y cuerpo debe documentarse para `/q/health` si una dependencia futura reporta `DOWN`? No hay `HealthCheck` propio ni se observó ese estado.
- ¿Debe retirarse el campo `debug` del contrato público? El código actual siempre lo devuelve y se documenta aquí sin asumir una decisión de producto.