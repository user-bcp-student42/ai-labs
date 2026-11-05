# Spec Delta

## Purpose
Define el comportamiento observable de `POST /auth/login` al verificar credenciales: autenticación correcta, rechazo de credenciales inválidas y resistencia a valores con sintaxis SQL.

## ADDED Requirements

### Requirement: Credenciales válidas inician sesión
El servicio SHALL responder 200 a `POST /auth/login` cuando `username` y `password` corresponden a un usuario registrado, con un `token` y los datos públicos del usuario.

#### Scenario: Login con credenciales válidas
- **WHEN** se envía `POST /auth/login` con `username` `student` y `password` `Workshop123!`
- **THEN** la respuesta es 200
- **AND** el cuerpo incluye `token`, `expiresIn` y `user` con `username` `student`, `displayName` y `role`

### Requirement: Credenciales inválidas se rechazan
El servicio SHALL responder 401 sin `token` cuando no existe un usuario con la combinación de `username` y `password` recibida.

#### Scenario: Contraseña incorrecta
- **WHEN** se envía `POST /auth/login` con `username` `student` y una contraseña distinta de la registrada
- **THEN** la respuesta es 401
- **AND** el cuerpo incluye `message` y no incluye `token`

#### Scenario: Usuario inexistente
- **WHEN** se envía `POST /auth/login` con un `username` que no está registrado
- **THEN** la respuesta es 401
- **AND** el cuerpo no incluye `token`

### Requirement: Las credenciales se tratan como datos
El servicio SHALL tratar `username` y `password` únicamente como valores a comparar; su contenido, incluida la sintaxis SQL, MUST NOT alterar la lógica de verificación ni el resultado de la autenticación.

#### Scenario: Inyección en el usuario
- **WHEN** se envía `POST /auth/login` con `username` `' OR 1=1--` y cualquier `password` no vacía
- **THEN** la respuesta es 401
- **AND** el cuerpo no incluye `token`

#### Scenario: Inyección en la contraseña
- **WHEN** se envía `POST /auth/login` con `username` `student` y `password` `' OR '1'='1`
- **THEN** la respuesta es 401
- **AND** el cuerpo no incluye `token`

#### Scenario: Inyección en ambos campos
- **WHEN** se envía `POST /auth/login` con `' OR '1'='1` como `username` y como `password`
- **THEN** la respuesta es 401
- **AND** el cuerpo no incluye `token`

#### Scenario: Comillas en un valor no malicioso
- **WHEN** se envía `POST /auth/login` con un `username` que contiene una comilla simple, como `o'brien`, y una contraseña no vacía
- **THEN** la respuesta es 401 y no un error 500
- **AND** el cuerpo no incluye `token`

### Requirement: Validación de campos obligatorios
El servicio SHALL responder 400 con `message` cuando el cuerpo falta, o cuando `username` o `password` están ausentes o vacíos, sin consultar credenciales.

#### Scenario: Usuario ausente o vacío
- **WHEN** se envía `POST /auth/login` sin `username` o con `username` vacío
- **THEN** la respuesta es 400
- **AND** el cuerpo incluye `message`

#### Scenario: Contraseña ausente o vacía
- **WHEN** se envía `POST /auth/login` con `username` válido y sin `password` o con `password` vacío
- **THEN** la respuesta es 400
- **AND** el cuerpo incluye `message`

### Requirement: Prueba automatizada del intento de inyección
La suite de pruebas de `auth/` SHALL incluir al menos una prueba que envíe un valor de inyección SQL a `POST /auth/login` y verifique la respuesta 401 sin `token`, y la suite completa MUST pasar al ejecutarse desde `auth/`.

#### Scenario: Suite protege contra regresión
- **WHEN** se ejecutan las pruebas de `auth/`
- **THEN** existe una prueba del intento de inyección que pasa
- **AND** las pruebas de login válido e inválido existentes siguen pasando
