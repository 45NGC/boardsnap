# Adaptador HTTP de BoardSnap

**Español** | [English](../en/http-server.md)

**El adaptador está implementado y su paridad con la CLI está comprobada mediante
HTTPS local.** Es una capa opcional en `boardsnap.adapters.http`; el núcleo no
depende de Starlette, Uvicorn ni Flutter. La comprobación local no es un despliegue
público ni la aceptación final del reconocimiento fotográfico.

- [Contrato por modo](http-contract.md).
- [Informe de verificación](../../data/reports/http-adapter-v1.json).
- [Informe general del proyecto](project-status.md).

## Instalar y arrancar

Desde el repositorio, con `.venv` activado:

```bash
python -m pip install -e ".[ml,server]"
boardsnap-http --config data/manifests/local-trial-v1.json --model-root . --port 8000 --allow-origin http://localhost:3000
```

Se enlaza por defecto a `127.0.0.1`, para desarrollo local. Cambia el origen CORS
por el origen exacto del cliente Flutter web, incluido el puerto. Se admite repetir
`--allow-origin`; no se admite `*`. No es necesario CORS para un cliente móvil
nativo, pero sí una URL que el dispositivo pueda alcanzar: el loopback de un móvil
no es el ordenador. El servidor usado para las pruebas se detiene al final de la
verificación; estos comandos lo vuelven a arrancar.

Con certificado y clave TLS:

```bash
boardsnap-http --config data/manifests/local-trial-v1.json --model-root . --port 8443 --ssl-certfile /ruta/cert.pem --ssl-keyfile /ruta/key.pem --allow-origin https://tu-app.example
```

Uvicorn proporciona TLS; alternativamente se puede terminar HTTPS en un proxy y
mantener el proceso Python en loopback. El adaptador no crea certificados públicos,
cuentas de alojamiento ni despliegues. La documentación oficial de [Uvicorn](https://uvicorn.dev/settings/)
describe las opciones de certificado y enlace.

## Modelos y procesamiento

Al crear la aplicación se lee la configuración fijada, se comprueban los SHA-256
y se cargan una vez ambos clasificadores. Un modelo ausente o modificado impide
arrancar; no hay descarga ni sustitución silenciosa. Las rutas se resuelven bajo
`--model-root`, independientemente del directorio de instalación del paquete.

- `digital`: `.cache/neural-tolerance-v1-conservative/best.pt`.
- `photo`: `.cache/neural-mixed-sqrt-v1/last.pt`, experimental.

Se reutiliza la misma clase `NeuralClassifier` que la CLI. Una petición válida
selecciona el método digital o fotográfico y transmite la orientación. El modelo
no recibe los nombres originales de los archivos, esquinas manuales ni etiquetas.
No se ejecuta un subproceso CLI para reconocer una petición.

La inferencia se ejecuta fuera del bucle asíncrono y se serializa a una petición
por proceso. El arranque usa cuatro hilos PyTorch y uno OpenCV, un trabajador
Uvicorn, límite de ocho conexiones/tareas simultáneas y keep-alive de cinco segundos.
El límite del servidor puede producir 503 de infraestructura si se satura; Flutter
debe manejar también respuestas de infraestructura y fallos de red, además de los
errores JSON de reconocimiento. No se ha probado carga sostenida ni capacidad de
servicio concurrente.

## Carga de archivos y limpieza

Se exige multipart y se preservan campos repetidos para rechazarlos. Starlette
limita a un archivo, dos campos y 4 KiB por campo textual. El cuerpo total se
cuenta mientras llega y se corta por encima de 21 MiB, con o sin Content-Length.
El archivo se limita a 20 MiB. No se confía en el nombre ni el MIME para validar
el contenido: se aplica el decodificador PNG/JPEG existente.

Los uploads del parser se cierran también ante fallo de análisis. El archivo de
trabajo se guarda en un directorio temporal independiente y se elimina en éxito,
error de reconocimiento o excepción inesperada. La finalización del hilo de
inferencia se protege frente a cancelación para no borrar su entrada antes de que
termine. No se conservan las imágenes recibidas por defecto. Estas reglas usan el
parser mantenido de [Starlette](https://starlette.dev/requests/), no un parser
multipart escrito específicamente para el proyecto.

Las excepciones conocidas conservan su código; las inesperadas se registran en
stderr y se devuelven como `PROCESSING_FAILED` sin trazas en el JSON. Las cabeceras
con hashes de modelo y configuración se exponen a los orígenes CORS configurados.
El cuerpo sigue conteniendo únicamente `piecePlacement` o `error`.

## Evidencia ejecutada

El 16 de noviembre de 2026 se arrancó el servidor real en
`https://localhost:8443/v1/recognize`, enlazado a loopback, con un certificado local
de prueba confiado expresamente por los clientes. **La validación del certificado
TLS permaneció activada.** No se publicaron puertos a Internet.

- Ocho casos coinciden con la CLI: digital/foto en ambas orientaciones, ausencia de
  tablero y archivo corrupto en cada modo. Coinciden posición o código de error,
  estado HTTP y hashes de modelo/configuración.
- Trece comprobaciones HTTPS reales: campos omitidos, orientación inválida, campo
  desconocido, duplicados, archivo extra, multipart malformado, tipo de cuerpo
  incorrecto, archivo vacío, GIF con nombre falso, límite de archivo, límite total,
  origen CORS autorizado y origen rechazado.
- **97 pruebas dirigidas** pasan: adaptador, contrato, probe, configuración local,
  CLI y recorrido fotográfico. Incluyen limpieza de temporales/archivos del parser,
  excepción inesperada, límite exacto, cuerpo transmitido sin Content-Length,
  modelos modificados y serialización de inferencia.
- `pip check` no encuentra dependencias incompatibles. El cliente de pruebas de
  Starlette emite un aviso de deprecación al usar httpx; las pruebas pasan con las
  versiones registradas. No se ha cambiado el cliente exclusivamente para ocultar
  ese aviso.

El informe registra versiones y hashes. Estas pruebas comprueban integración y
transporte, no vuelven a medir la precisión global ni consumen evaluación final.
No se entrenaron modelos. Las mediciones CPU anteriores eran de un único modelo
residente; no se presentan como un benchmark del servidor con ambos modelos o red.

## Repetir las pruebas

```bash
python -m pip install -e ".[dev,ml,server,server-test]"
python -m pytest tests/test_http_adapter.py tests/test_http_contract.py tests/test_http_cli_probe.py tests/test_local_trial.py tests/test_cli.py tests/test_photo_pipeline.py -q
python -m tools.check_http_cli --endpoint https://TU_SERVIDOR/v1/recognize
```

Para reproducir exclusivamente el certificado y servidor locales utilizados:

```bash
mkdir -p .cache/http-adapter-v1
openssl req -x509 -newkey rsa:2048 -nodes -keyout .cache/http-adapter-v1/key.pem -out .cache/http-adapter-v1/cert.pem -days 1 -subj /CN=localhost -addext 'subjectAltName=DNS:localhost,IP:127.0.0.1'
boardsnap-http --config data/manifests/local-trial-v1.json --model-root . --port 8443 --allow-origin https://scanner.example --ssl-certfile .cache/http-adapter-v1/cert.pem --ssl-keyfile .cache/http-adapter-v1/key.pem
```

En otra terminal, con `.venv` activado:

```bash
SSL_CERT_FILE="$PWD/.cache/http-adapter-v1/cert.pem" python -m tools.check_http_cli --endpoint https://localhost:8443/v1/recognize
python -m tools.check_http_requests --endpoint https://localhost:8443/v1/recognize --ca-file .cache/http-adapter-v1/cert.pem --output .cache/http-adapter-v1/request-checks.json
```

Los certificados locales caducan en un día; hay que regenerarlos para repetir la
prueba posteriormente. Claves y certificados permanecen en `.cache` ignorada.

## Pendiente antes de ofrecer un servicio público

Configurar alojamiento, dominio/certificado de confianza y origen Flutter web;
definir autenticación y cuotas si el servicio se abre; fijar tiempos de petición y
estrategia de cancelación/capacidad del despliegue; distribuir pesos y dependencias
con versiones; probar desde Android, iOS y web reales. La app debe permitir corregir
el resultado en el editor y tratar el modo fotográfico como experimental.
