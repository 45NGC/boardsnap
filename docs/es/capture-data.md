# Captura de muestras de lichess

[English](../en/capture-data.md) | **Español** · [Resumen](README.md)

`tools/capture_lichess.py` recoge capturas y anotaciones del
[editor real de lichess](https://lichess.org/editor). Es una herramienta del
repositorio, separada del motor instalado, y no reconoce imágenes.

## Instalación

Desde la raíz del repositorio:

```bash
source .venv/bin/activate
python -m pip install -e '.[dev,capture]'
export PLAYWRIGHT_BROWSERS_PATH="$PWD/.cache/ms-playwright"
python -m playwright install chromium
```

Playwright es una dependencia opcional; Chromium se descarga por separado.
Git ignora `.venv/` y `.cache/`. Vuelve a exportar la ruta del navegador en las
terminales nuevas antes de capturar o ejecutar las pruebas con navegador.
Linux puede necesitar las bibliotecas del sistema indicadas en la
[guía de instalación de Playwright](https://playwright.dev/python/docs/intro).
La herramienta usa un contexto de navegador nuevo, no tu perfil personal.
No requiere una cuenta de lichess.

## Preparar posiciones

Copia [`tools/capture.example.json`](../../tools/capture.example.json) a un
archivo JSON nuevo y edítalo. Sus 10 posiciones distintas producen 20 imágenes:
16 de ajuste y 4 de evaluación, manteniendo ambas orientaciones en la misma
partición. Incluyen aperturas, posiciones construidas de medio juego y finales,
un tablero vacío y un caso de piezas en las esquinas. Este lote más variado
comprueba la captura; no basta para entrenar un modelo ni medir la precisión
general del reconocimiento.

| Campo | Significado |
| --- | --- |
| `profileId` | Debe ser `lichess-cburnett-brown-v1` |
| `notes` | Notas opcionales de procedencia y permisos de recursos |
| `positions` | Lista no vacía de los objetos de posición siguientes |
| `positions[].groupId` | Identificador único en minúsculas: letras, números, `_`, `-`; 1–64 caracteres |
| `positions[].split` | `tuning` o `evaluation`, elegido antes de capturar |
| `positions[].piecePlacement` | Solo el primer campo del FEN, ordenado desde a8 hasta h1 |

No añadas turno, enroques ni otros campos del FEN. Se comprueba la sintaxis sin
exigir una posición legal. Las dos orientaciones se generan automáticamente.
Se rechazan grupos y posiciones duplicados, incluso entre particiones. Conserva
los futuros recortes y variantes en la partición de su grupo original. Las
posiciones relacionadas de una misma partida o fuente también deben compartir
partición; asígnalas tú porque la herramienta no puede deducir esas relaciones.
Más adelante separaremos entrenamiento y validación dentro de ajuste.

## Validar y capturar

Comprueba el manifiesto y los destinos sin abrir el navegador:

```bash
python -m tools.capture_lichess tools/capture.example.json --validate-only
```

Primero prueba con un directorio de salida temporal:

```bash
python -m tools.capture_lichess tools/capture.example.json --output-root /tmp/boardsnap-pilot
```

Añade `--headed` para ver Chromium (requiere una sesión gráfica). Después de
revisar la prueba, recoge el manifiesto completo dentro del repositorio
omitiendo `--output-root` y ejecutando desde la raíz del repositorio:

```bash
python -m tools.capture_lichess path/to/positions.json
```

Los destinos son `data/tuning/lichess-cburnett-brown-v1/` y
`tests/fixtures/evaluation/lichess-cburnett-brown-v1/`. Cada uno contiene un
`manifest.json` solo con sus propias posiciones y archivos como estos:

```text
pos-001-white.png
pos-001-white.json
pos-001-black.png
pos-001-black.json
```

Las capturas se preparan temporalmente y se publican después de completar todas
las capturas del navegador. Se rechazan los directorios del perfil existentes
en cualquiera de las particiones, incluso en ejecuciones posteriores. No hay
modo de sobrescritura, continuación ni ampliación. Prepara el manifiesto completo
antes de recoger un lote y utiliza raíces nuevas para experimentar. No mezcles
lotes separados sin comprobar sus grupos y posiciones entre particiones.

Códigos de salida: `0` éxito, `1` fallo de captura o dependencias, `2` argumentos
o manifiesto incorrectos, o destino existente. El progreso y los errores van a
stderr; stdout contiene un resumen breve. Es independiente de la futura CLI de
reconocimiento con salida JSON.

## Perfil y comprobaciones

El perfil fijo utiliza piezas cburnett en 2D, tablero brown, coordenadas
internas, esquema de color claro, idioma inglés, ventana de 1280 × 1000 y factor
de escala 1. Los valores iniciales del navegador nuevo proporcionan actualmente
esas piezas y tablero; el script los comprueba y se detiene si difieren.
El tablero conserva su tamaño nativo en la página.

Para cada orientación se comprueba el FEN del editor y la ubicación de las
piezas representadas, se espera a los recursos gráficos, se rechazan resaltados
y dibujos y se mide la cuadrícula. Se captura un PNG de la ventana mediante
las [capturas de Playwright](https://playwright.dev/python/docs/screenshots).
Los campos FEN/URL y el control de redimensionado del tablero se ocultan con
CSS visibility. Se conservan la cuadrícula y su distribución; los demás
controles y las piezas de reserva exteriores siguen visibles. No se giran PNG.

## Anotaciones

Cada JSON asociado contiene `image`, `profileId`, `groupId`, `split`,
`orientation`, `boardBounds`, `imageSize`, `piecePlacement`, `source` y `sha256`.
Son metadatos de las imágenes, no cambios en el contrato de salida del motor.

- `orientation` es `white-bottom` o `black-bottom`. `piecePlacement` es idéntico
  para la misma posición en ambas imágenes.
- `boardBounds` contiene `x`, `y`, `width`, `height` de la cuadrícula de
  64 casillas, sin márgenes exteriores. El origen es la esquina superior
  izquierda del PNG; x crece a la derecha e y hacia abajo. Los límites cubren
  `[x, x + width)` e `[y, y + height)`. Se conservan los decimales porque el
  navegador usa posiciones subpíxel. Con factor de escala 1 y capturas a escala
  CSS, las unidades son píxeles del PNG. Los futuros recortes enteros deben
  redondear hacia fuera.
- `imageSize` registra dimensiones del PNG; `source` registra URL, fecha UTC,
  versiones del navegador y Playwright, ajustes y modificaciones de página.
- `sha256` identifica los bytes exactos del PNG.

Las etiquetas proceden del manifiesto y se contrastan con el DOM. Esto prepara
datos, pero no es una prueba independiente de reconocimiento. Revisa las
capturas, orientación y límites, especialmente en evaluación. Las anotaciones
nunca deben ser entradas del reconocedor. Registra los permisos de las fuentes
y recursos antes de redistribuir capturas.

## Pruebas y limitaciones

Las pruebas habituales no abren navegadores ni acceden a la red:

```bash
python -m pytest
```

Después de instalar Chromium, activa expresamente las pruebas locales:

```bash
BOARDSNAP_BROWSER_TESTS=1 python -m pytest tests/test_capture_lichess.py -m integration
```

Estas pruebas interceptan las peticiones con una página HTML local. Comprueban
la creación del PNG, orientación, anotaciones y rechazo de posiciones, temas o
superposiciones incorrectos. No comprueban la disponibilidad de lichess.
Ejecuta una captura real pequeña cuando cambies el adaptador.

La herramienta depende del DOM, estilos y recursos actuales del editor de
lichess. Los cambios del sitio o fallos de red pueden requerir mantenimiento.
Las capturas son secuenciales con una pausa breve entre páginas; no se evitan
restricciones de acceso del sitio. Solo se admite este perfil de recogida de
datos. Recoger imágenes no significa que el motor reconozca ese estilo.
Otras resoluciones, temas, capturas móviles, casos negativos y diagramas de
libros quedan pendientes. Mantén separados [ajuste](tuning-data.md) y
[evaluación](evaluation-data.md).
