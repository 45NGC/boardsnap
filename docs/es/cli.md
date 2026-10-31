# Reconocimiento desde la terminal

[English](../en/cli.md) | **Español** · [Inicio](README.md)

La CLI es un adaptador separado sobre `boardsnap.pipeline.recognize_image`. El núcleo
ya conecta lectura, detección, normalización, segmentación, orientación, clasificación
y `build_result`. La CLI no duplica el reconocimiento, y el núcleo no importa
adaptadores ni depende de Flutter o de un framework web.

## Instalación y uso

Para fotografías de pantallas, el [recorrido fotográfico](photo-pipeline.md)
añade detección de esquinas y corrección de perspectiva:

```bash
boardsnap "mi-foto.jpg" --input-type photo --model .cache/neural-phone-v1/best.pt --orientation white-bottom
```

Exige orientación explícita (`white-bottom` o `black-bottom`) y un modelo neuronal;
no admite `auto` ni `--profile`. Sin `--input-type photo` se conserva el recorrido digital.

Desde la raíz del repositorio, con el entorno existente:

```bash
source .venv/bin/activate
python -m pip install -e '.[dev]'
boardsnap data/tuning/lichess-cburnett-brown-v1/pos-001-white.png
```

Hay que reinstalar una vez al añadir el punto de entrada del comando; después,
la instalación editable refleja los cambios de código Python. Si ya están las
dependencias, `python -m pip install --no-deps -e .` también registra el comando.
No se requiere ninguna dependencia de ejecución nueva. Sin activar el entorno,
puedes usar `.venv/bin/boardsnap`.

Salida esperada del ejemplo:

```json
{"piecePlacement": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR"}
```

La ejecución como módulo es equivalente:

```bash
python -m boardsnap data/tuning/lichess-cburnett-brown-v1/pos-001-white.png
boardsnap --help
boardsnap "path with spaces/image.png"
boardsnap -- -image.png
```

Usa `--` si el nombre empieza por guion. Se admite exactamente una ruta de imagen;
no se ofrece procesamiento por lotes, imágenes por stdin, HTTP ni integración
Flutter. Las rutas relativas parten del directorio de trabajo actual y los
recursos instalados funcionan fuera del repositorio. El comando no guarda vistas
previas ni modifica las entradas.

## Configuración del modelo multitema

Con el extra `ml` instalado, configura una ruta absoluta al modelo una vez y envía
solo imagen y vista:

```bash
export BOARDSNAP_MODEL="$PWD/.cache/neural-styles-v2/best.pt"
boardsnap imagen.png --orientation black-bottom
```

`--model RUTA` prevalece sobre el entorno para una ejecución puntual. Un `--profile`
explícito selecciona las plantillas e ignora esa variable; no se puede combinar
con `--model`. Sin modelo configurado se conserva el comportamiento anterior.
Un modelo configurado inválido devuelve `PROCESSING_FAILED`, sin volver a plantillas.
Consulta la [ampliación de estilos](style-expansion.md) para el alcance medido y la API.

## Opción de orientación

Usa `--orientation white-bottom`, `--orientation black-bottom` o `--orientation auto`.
Por defecto se utiliza `auto`: leer coordenadas y asumir blancas abajo si no son
utilizables. Los valores explícitos omiten esa lectura y prevalecen sobre etiquetas
contradictorias. Describen la vista, nunca el turno. Se pueden combinar con
`--profile` y mantienen exactamente el mismo JSON de respuesta.

```bash
boardsnap imagen.png --orientation black-bottom
boardsnap imagen.png --profile chesscom-default-green-v1 --orientation white-bottom
```

Los valores inválidos o la opción sin valor terminan con código 2, sin JSON ni
stdout, antes de abrir la imagen. Consulta la [semántica y pruebas](orientation.md).

## Canales de salida y códigos del proceso

| Invocación | stdout | stderr | Código |
| --- | --- | --- | --- |
| Imagen reconocida | Un objeto JSON de éxito y salto de línea | Normalmente vacío | 0 |
| Fallo de imagen/procesamiento | Un objeto JSON de error y salto de línea | Diagnósticos si procede | 1 |
| Falta ruta, sobran argumentos u opción desconocida | Vacío | Uso/error | 2 |
| `--help` | Texto de ayuda, no JSON | Vacío | 0 |

La respuesta respeta el [contrato de salida](output-contract.md): solo
`piecePlacement` en éxito, o solo `error` con `code` y `message` al fallar. Se
devuelve únicamente el primer campo FEN. Un archivo inexistente es un fallo de
procesamiento (`INPUT_READ_ERROR`, código 1), no de sintaxis de argumentos.

El adaptador serializa las excepciones conocidas sin cambiarlas. Otras excepciones
durante el reconocimiento se convierten en `PROCESSING_FAILED`, con el mensaje
`Could not recognize the image.`; el tipo y los detalles aparecen solo en stderr.
Las escrituras Python a stdout dentro del reconocimiento se redirigen a stderr
para no contaminar el JSON. La API Python del núcleo conserva sus excepciones
originales. Eventos de control como Ctrl+C no se convierten en errores de imagen.

```bash
boardsnap image.png > result.json 2> diagnostics.log
echo $?
```

Ejecuta `echo $?` inmediatamente después del comando para consultar su código.
Un error no incluye posiciones parciales, confianza ni un tablero vacío inventado.

## Cobertura y pruebas

Selecciona [plantillas](profiles.md) con `--profile ID`; si se omite y no hay modelo
configurado, se mantiene brown/cburnett. Los tres perfiles digitales tienen evaluación sobre un corpus
pequeño; el perfil de libros es experimental, con dos posiciones completas
fallidas. Un ID desconocido es error de uso (salida 2). El [transporte Flutter](flutter-integration.md)
se documenta aparte; la CLI no inicia un servidor.

```bash
boardsnap imagen.png --profile chesscom-default-green-v1
```

```bash
python -m pytest tests/test_cli.py tests/test_cli_process.py
python -m pytest
```

Las pruebas ejecutan ambos puntos de entrada como procesos desde otro directorio.
Las 16 capturas de ajuste y las 4 reservadas se copian a nombres anónimos sin
anotaciones adjuntas; se compara la salida exacta, incluido el salto final y la
ausencia de diagnósticos en stderr. También se prueban archivos inexistentes,
directorios, entradas vacías/corruptas, formato no admitido, ausencia/multiplicidad
de tableros, ayuda, argumentos inválidos y rutas con espacios, Unicode o guion
inicial. Las pruebas unitarias del adaptador inyectan errores y mensajes para
comprobar códigos, fallos inesperados, restauración de canales y propagación del
control del proceso; esas inyecciones no miden precisión del reconocimiento.

Referencia de la etapa del perfil original: pasan las **74 pruebas de CLI** (10 unitarias, 56 de
integración y 8 de procesos con imágenes reservadas). En aquella etapa la batería completa superó
**781 pruebas**, con 7 opcionales de navegador omitidas. Se comprobaron el comando
instalado y el módulo sin modificar plantillas ni datos de evaluación.
