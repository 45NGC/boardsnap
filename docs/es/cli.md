# Reconocimiento desde la terminal

[English](../en/cli.md) | **Español** · [Inicio](README.md)

La CLI es un adaptador separado sobre `boardsnap.pipeline.recognize_image`. El núcleo
ya conecta lectura, detección, normalización, segmentación, orientación, clasificación
y `build_result`. La CLI no duplica el reconocimiento, y el núcleo no importa
adaptadores ni depende de Flutter o de un framework web.

## Instalación y uso

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

La CLI conserva el alcance del núcleo: el perfil inicial brown/cburnett de lichess,
con la convención de blancas abajo si no se leen coordenadas. Consulta los
[resultados y límites de clasificación](classification.md). Añadir el comando no
demuestra compatibilidad con estilos nuevos ni decide cómo se integrará Flutter.

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

Resultados verificados: pasan las **74 pruebas de CLI** (10 unitarias, 56 de
integración y 8 de procesos con imágenes reservadas). La batería completa pasa
**781 pruebas**, con 7 opcionales de navegador omitidas. Se comprobaron el comando
instalado y el módulo sin modificar plantillas ni datos de evaluación.
