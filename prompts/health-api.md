## Contexto
El componente `api` es una aplicación Python con FastAPI, definida en `api/app/main.py`. La aplicación se crea mediante `create_app(db_path, upload_dir)` y expone endpoints como `/api/tasks`, `/api/summary`, `/api/requirements` y `/api/backend-health`. Las pruebas usan `pytest`, `FastAPI TestClient` y una base de datos temporal.

## Objetivo
Agregar un endpoint público `GET /health` que informe cuántos fallos HTTP han ocurrido en los endpoints de la API desde que se inició la aplicación. Debe mostrar el total y el desglose por método HTTP y ruta.

Un fallo se define como una respuesta con código HTTP `>= 400` de una ruta existente. No contar las solicitudes a `/health` para evitar que el endpoint altere las métricas que reporta. El conteo debe mantenerse en memoria y reiniciarse al crear una nueva instancia de la aplicación.

Formato sugerido:
{
  "status": "ok",
  "totalFailures": 2,
  "failuresByEndpoint": [
    {"method": "GET", "path": "/api/tasks", "count": 1},
    {"method": "POST", "path": "/api/tasks", "count": 1}
  ]
}

## Restricciones
- Conserva los endpoints existentes y los formatos de respuesta usados por el frontend.
- No agregues dependencias, secretos ni valores de producción.
- No cambies la autenticación ni refactorices funcionalidades ajenas a este objetivo.
- Mantén el contador aislado por instancia de `create_app`; no uses estado global compartido entre aplicaciones o pruebas.
- Agrupa por ruta definida, no por valores variables de la URL.
- Sigue las convenciones del componente `api` y mantén el código sencillo y con responsabilidades claras.
- Agrega pruebas para el comportamiento nuevo. No silencies alertas ni reduzcas los quality gates.

## Criterios de aceptación
1. `GET /health` responde `200` sin requerir autenticación.
2. Una instancia nueva responde con `totalFailures: 0` y un desglose vacío.
3. Una respuesta `>= 400` de una ruta existente incrementa el total y el contador correspondiente.
4. Una respuesta exitosa no incrementa los contadores.
5. Las solicitudes a `/health` no incrementan los contadores.
6. Las pruebas verifican el total, el desglose por método y ruta, y el aislamiento entre instancias de `create_app`.
7. Las pruebas del componente `api` pasan y la cobertura del código modificado alcanza al menos 85%.
