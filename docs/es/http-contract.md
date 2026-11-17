# Contrato HTTP por modo y comprobación de paridad

**Español** | [English](../en/http-contract.md)

**El contrato v1 está implementado y la paridad con la CLI está verificada por HTTPS local.**
El [adaptador HTTP](http-server.md) supera ocho casos de paridad y trece pruebas
adicionales de solicitudes/CORS. La comprobación local no implica despliegue público
ni aceptación de precisión del modelo.

- [Contrato legible por herramientas](../../data/manifests/http-contract-v1.json).
- [Reglas sin framework](../../src/boardsnap/adapters/http_contract.py).
- [Configuración fija de modelos](local-trial.md).
- [Integración Flutter](flutter-integration.md).

## Petición

`POST /v1/recognize`, `Content-Type: multipart/form-data`, mediante HTTPS.
Solo se permite HTTP sin TLS para pruebas en loopback local.

| Campo | Tipo | Obligatorio | Valores |
| --- | --- | --- | --- |
| `image` | Archivo | Sí, exactamente uno | Contenido PNG o JPEG |
| `inputType` | Texto | Sí, exactamente uno | `digital`, `photo` |
| `orientation` | Texto | Sí, exactamente uno | `white-bottom`, `black-bottom`; `auto` solo en digital |

No hay valores implícitos para campos omitidos en HTTP. El núcleo y la CLI
conservan sus valores predeterminados; este contrato exige enviarlos.
`orientation` describe qué lado está abajo, no el turno. La opción explícita
prevalece sobre las coordenadas; `auto` digital mantiene la convención actual de
blancas abajo cuando las pistas no bastan.

El servidor rechaza campos desconocidos, repetidos, archivos adicionales o campos
textuales enviados como archivo con `INVALID_REQUEST` (400). El parser debe
conservar multiplicidades: convertir un formulario directamente en diccionario
ocultaría duplicados. `validate_fields` valida la lista de campos de texto y la
cantidad/tamaño de archivos; el adaptador futuro debe comprobar además los nombres
y tipos de partes del multipart.

El límite de imagen es **20 MiB (20.971.520 bytes)**, inclusive. El cuerpo multipart
completo tiene un límite de **21 MiB**, aplicado antes de almacenarlo íntegramente.
Un exceso produce `PAYLOAD_TOO_LARGE` (413). Una imagen de cero bytes con campos
válidos llega al decodificador: `INVALID_IMAGE` (422). Se identifica el formato por
contenido; no se confía en la extensión o el MIME anunciado para decidir que es válido.
Los límites de píxeles y formatos del decodificador existente siguen aplicándose.

El cliente nunca envía `model`, `profile`, rutas locales ni colocación esperada.
La configuración del servidor selecciona:

| inputType | Modelo de la prueba actual |
| --- | --- |
| `digital` | `neural-tolerance-v1-conservative/best.pt` |
| `photo` | `neural-mixed-sqrt-v1/last.pt`, experimental |

El adaptador llama al núcleo con `model`, `input_type` y `orientation` explícitos.
Verifica pesos/configuración al arrancar, conserva uno de cada modelo cargado si
procede y no utiliza `BOARDSNAP_MODEL` como sustituto silencioso. No ejecuta la CLI
por petición: esta se usa únicamente como referencia externa en las pruebas.
Las rutas completas y checksums figuran en `local-trial-v1.json`.

## Respuesta

Éxito: HTTP 200, `Content-Type: application/json` (se permite `charset=utf-8`):

```json
{"piecePlacement":"rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR"}
```

Solo el primer campo FEN, canónico y sin metadatos añadidos. Una colocación vacía
es válida si se reconoce realmente, nunca como sustituto de un error. No se exige
legalidad ajedrecística de la posición. El comprobador rechaza campos adicionales,
FEN completo, JSON con claves duplicadas y filas o compresión no válidas.

Errores: exactamente `{"error":{"code":"...","message":"..."}}`:

| Estado | Código |
| --- | --- |
| 400 | `INVALID_REQUEST` |
| 413 | `PAYLOAD_TOO_LARGE` |
| 422 | `INVALID_IMAGE`, `UNSUPPORTED_IMAGE`, `BOARD_NOT_FOUND` |
| 500 | `INPUT_READ_ERROR`, `PROCESSING_FAILED` |

`INPUT_READ_ERROR` describe aquí un fallo de lectura del temporal del servidor,
no la ruta del móvil. Excepciones internas deben convertirse a un error genérico
sin trazas. El cliente compara `code`; `message` puede cambiar. Los errores de
transporte que procedan de un proxy ajeno (por ejemplo una página HTML de timeout)
se tratan como fallo de integración, no como respuesta válida de BoardSnap.

En resultados de reconocimiento, incluidos errores de decodificación/detección,
se envían estas cabeceras diagnósticas:

- `X-BoardSnap-Model-SHA256`: hash del archivo de pesos elegido por modo.
- `X-BoardSnap-Config-SHA256`: hash de los bytes del archivo de configuración fijado.

Permiten comprobar versiones sin alterar el JSON. No son obligatorias si falla
la validación antes de poder seleccionar un modo. Para leerlas desde Flutter web,
el adaptador debe exponerlas mediante CORS a los orígenes configurados. El esquema
de autenticación, proxy, concurrencia y despliegue se concretará con el servidor.
Los temporales se eliminan tanto en éxito como en error; no se guardan imágenes
recibidas por defecto.

## Qué prueba está preparada

`tools.check_http_cli` prepara ocho casos con las imágenes de desarrollo ya
consultadas, sin evaluación final ni entrenamiento:

1. Captura digital con blancas abajo y otra con negras abajo.
2. Foto con blancas abajo y otra con negras abajo.
3. Imagen sin tablero en cada modo.
4. Archivo corrupto en cada modo.

Obtiene referencias usando `python -m boardsnap` y los pesos fijados por modo,
conserva hashes de imagen/configuración/modelo/código y reutiliza resultados de CLI
compatibles. Envía los mismos bytes por multipart al endpoint indicado, sin enviar
esquinas, nombres originales o posición esperada. Comprueba:

- Colocación HTTP exactamente igual a la CLI para la misma entrada.
- Mismo código de error; CLI 0/1 frente a HTTP 200/400/413/422/500 según contrato.
- JSON con esquema estricto y `Content-Type` correcto.
- Hashes de modelo y configuración en las cabeceras.

La paridad mide equivalencia entre interfaces, no precisión: ambas pueden coincidir
en una pieza incorrecta. Los tests de solicitud y tamaño cubren reglas del contrato;
el probe de ocho casos se complementa con `tools.check_http_requests`, que ya
comprueba en el adaptador real un archivo de más de 20 MiB, exceso de cuerpo total,
multipart malformado y otras validaciones. Véase el informe del servidor.

## Comandos

Desde el repositorio, con `.venv` activado:

```bash
python -m tools.check_http_cli --prepare-only
python -m pytest tests/test_http_contract.py tests/test_http_cli_probe.py tests/test_local_trial.py -q
```

Las referencias están en `.cache/http-cli-contract-v1/cli-references.json`.
Se han ejecutado las ocho llamadas reales y pasan **39 pruebas**: validación por
modo, orientaciones, duplicados, tamaño, esquemas, errores y detección de resultados
diferentes. Esas pruebas del probe usan un doble de transporte. Posteriormente se ejecutaron
también las pruebas del adaptador y las comprobaciones HTTPS reales, documentadas
en [http-server](http-server.md).

Con el adaptador arrancado y configurado con el mismo archivo y pesos:

```bash
python -m tools.check_http_cli --endpoint https://TU_SERVIDOR/v1/recognize
```

Ese comando envía las imágenes de desarrollo al destino indicado. Para un servidor
local puede usarse `http://127.0.0.1:8000/v1/recognize`. El comprobador no sigue
redirecciones y admite JSON de respuesta de hasta 1 MiB. El timeout del cliente es
90 segundos; es un límite de la herramienta, no una garantía de servicio.
Si falla una comparación, el comando termina con error y conserva las referencias
CLI. Si pasan todas, guarda `.cache/http-cli-contract-v1/http-comparison.json`.

**Estado actual: ocho casos de paridad HTTPS local pasan.** También pasan las
comprobaciones reales de multipart, tamaño y CORS, y las pruebas de limpieza y
errores internos. Quedan despliegue público y conexión de Flutter.
