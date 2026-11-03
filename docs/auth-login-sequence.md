# Auth Login Sequence Report

## Endpoint
- `POST /auth/login`
- Request type: `LoginRequest`
- Response: JSON

## Participants
- `Client`: sends the login request and receives the response.
- `AuthResource`: validates required request values, coordinates credential lookup, creates the response, and handles exceptions.
- `LegacyDatabase`: looks up a user by credentials.
- `LegacyTokenUtil`: creates a token for the authenticated username and role.
- `StringEscapeUtils`: escapes the user's display name for the response.

## Interaction outcomes
- Null request, missing username, or missing password: `400`.
- Credentials not found: `401`.
- User found: token creation, display-name escaping, then `200`.
- Exception during login: `500`.

## Source
- `auth/src/main/java/com/bcp/workshop/auth/AuthResource.java`
