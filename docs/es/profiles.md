# Perfiles de reconocimiento evaluados

[English](../en/profiles.md) · [Resumen](README.md)

Cada perfil especifica el fondo, las plantillas de piezas y las coordenadas.
La selección es **explícita**: no se reconoce automáticamente el estilo.
Las llamadas existentes y `boardsnap imagen.png` siguen utilizando
`lichess-cburnett-brown-v1`. Otro diseño de piezas sobre un fondo compatible puede
producir piezas incorrectas; las plantillas no detectan estilos desconocidos.
La salida sigue siendo solo `piecePlacement` o un error estructurado.

## Cobertura y resultados medidos

Estos resultados corresponden a **posiciones reservadas**, después de fijar los
algoritmos y plantillas con los datos de ajuste. Los informes incluyen fallos,
clases, fondos y posiciones completas. Las métricas no se envían a la app.

| ID del perfil | Alcance | Imágenes de ajuste | Reservadas | Casillas reservadas correctas | Posiciones reservadas exactas |
| --- | --- | ---: | ---: | ---: | ---: |
| `lichess-cburnett-brown-v1` | Fondo brown y piezas cburnett existentes | 16 | 4 | 256/256 | 4/4 |
| `lichess-cburnett-blue-v1` | Fondo blue plano y piezas cburnett | 16 | 4 | 256/256 | 4/4 |
| `chesscom-default-green-v1` | Fondo verde y piezas predeterminadas capturadas el 2026-10-07 | 14 | 4 | 256/256 | 4/4 |
| `book-strategy-hatched-v1` | **Experimental**: edición ilustrada de Gutenberg de *Chess Strategy* | 5 | 2 | 126/128 | **0/2** |

Los tres perfiles digitales comparten **las mismas dos posiciones** reservadas,
cada una vista desde ambos lados. Son pilotos de regresión, no doce posiciones
independientes ni una demostración de precisión universal. El piloto de libros
tiene dos diagramas reservados distintos. En total hay 65 imágenes: 51 de ajuste
y 14 de evaluación. Las variantes de una posición mantienen la partición entre
perfiles, incluida la posición inicial compartida por el libro y las capturas.

Informes: [azul](../../data/reports/lichess-cburnett-blue-v1-classification-evaluation.json),
[Chess.com](../../data/reports/chesscom-default-green-v1-classification-evaluation.json),
[libro](../../data/reports/book-strategy-hatched-v1-classification-evaluation.json).
Los informes `-tuning.json` correspondientes registran 16/16, 14/14 y 5/5
posiciones completas correctas en ajuste.

El experimento de libros **no ha superado la aceptación de posiciones completas**.
Falla una pieza en cada imagen reservada. Ambos fallos siguen visibles como pruebas
`xfail` estrictas, además de las pruebas que conservan los resultados medidos.
No se modificaron umbrales ni plantillas después de consultar estos resultados.
Para mejorar el perfil hacen falta nuevos ejemplos de desarrollo; si se usan
estos fallos para ajustar, habrá que preparar otros diagramas independientes de
aceptación. No debe interpretarse el 126/128 como reconocimiento fiable de libros.

## Geometría, orientación y limitaciones

- Perfiles digitales: tableros completos y alineados, fondos uniformes, sin flechas,
  resaltados ni piezas tapadas. Las cuadrículas azules originales miden 584 px y
  las de Chess.com, 704 px. La regresión de ajuste también comprueba recortes
  trasladados al 75 % y 125 %. El mínimo geométrico sigue en 128 px; leer coordenadas
  requiere al menos 256 px y texto suficientemente definido. No son garantías de precisión.
- El azul necesita menor tolerancia de color que brown: de lo contrario, los
  márgenes grises se unen a las casillas claras y agrandan los límites detectados.
- Lichess sitúa las letras abajo a la izquierda y los números arriba a la derecha
  de las casillas del borde. Chess.com usa letras abajo a la derecha y números
  arriba a la izquierda. Cada perfil tiene máscaras propias, extraídas únicamente
  de las imágenes vacías de calibración de ajuste. Azul incluye 90 máscaras
  del original y de caracteres legibles al 75 % y 125 %; brown y Chess.com tienen
  32 máscaras cada uno.
- El perfil impreso busca un marco oscuro y comprueba la alternancia de brillo
  en los bordes de las casillas. Reduce la trama fina con un desenfoque y compara
  hasta cuatro ejemplos por clase/fondo, permitiendo pequeños desplazamientos.
  Sus 80 plantillas cubren las 13 clases en ambos fondos. Requiere conservar el
  marco, un diagrama casi cuadrado de al menos 256 px y los símbolos de esa edición.
  No se ha establecido soporte para páginas completas, corrección de perspectiva,
  otros libros ni otras fuentes tipográficas.
- En `orientation="auto"`, los diagramas impresos no tienen coordenadas y
  se asume blancas abajo. En imágenes digitales sin coordenadas legibles o con
  pistas contradictorias se aplica la misma convención. Los valores explícitos
  `white-bottom`/`black-bottom` omiten la lectura de coordenadas en cualquier
  perfil y prevalecen sobre las pistas de la imagen. No se deduce la orientación por las piezas.

El perfil solo cambia el procesamiento interno. No añade confianza, alternativas,
corrección de legalidad, estado de partida ni otros campos FEN. Si el procesamiento
del libro tiene éxito se devuelve la posición reconocida, aunque pueda contener
piezas erróneas que se corregirían en el editor. El estado experimental queda en
la documentación, sin introducir campos nuevos en el JSON.

## Comandos

```bash
boardsnap imagen.png --profile lichess-cburnett-blue-v1
boardsnap imagen.png --profile chesscom-default-green-v1
# Experimental: todavía no supera la aceptación de posiciones completas.
boardsnap diagrama.png --profile book-strategy-hatched-v1

python -m tools.preview_detection data/tuning/chesscom-default-green-v1 \
  --profile chesscom-default-green-v1 --recognition \
  --output-dir .cache/chesscom-preview

python -m tools.evaluate_classification --profile chesscom-default-green-v1 \
  --split evaluation --output .cache/chesscom-report.json
python -m pytest tests/test_profiles.py
```

En Python: `recognize_image(path, profile="...", orientation="auto")`.
El flujo también acepta `white-bottom`/`black-bottom` explícitos; consulta [orientación](orientation.md). Detección, orientación y
clasificación aceptan `profile`; la orientación explícita de entrada pertenece al flujo. Un perfil desconocido en la CLI es un
error de uso (salida 2, diagnóstico en stderr); en Python produce `ValueError`.
La herramienta de vistas previas usa por defecto la carpeta brown original,
para no procesar accidentalmente todos los temas con el mismo perfil.

## Recogida y reconstrucción

La herramienta opcional de Playwright permite repetir las capturas digitales:

```bash
python -m pip install -e '.[dev,capture]'
python -m playwright install chromium
python -m tools.capture_profiles lichess-cburnett-blue-v1 --output-root .cache/new-blue
python -m tools.capture_profiles chesscom-default-green-v1 --output-root .cache/new-chesscom
```

Si guardas los navegadores en `.cache/ms-playwright`, utiliza el mismo
`PLAYWRIGHT_BROWSERS_PATH` al instalar y al capturar. El lote se publica solo cuando
todas las imágenes superan la comprobación de piezas y geometría del DOM. No se
sobrescriben destinos existentes. El azul se selecciona en las preferencias de
lichess. Los recursos de Chess.com quedan fijados con los identificadores `9rdwe`
(tablero) y `ejgfv` (piezas); un cambio futuro debe evaluarse como otro perfil.
El nombre no promete soporte para cualquier tema verde ni cualquier predeterminado futuro.

Chess.com rechaza el diagnóstico ilegal de esquinas (`pos-005`), por lo que se
omite. La calibración vacía de ajuste (`pos-004`) elimina expresamente los nodos
de piezas del DOM: el editor de análisis sustituye un FEN vacío por la posición
inicial. Esa modificación queda anotada; no es una captura intacta de un tablero
vacío real. Las demás capturas verifican las piezas renderizadas. Ninguna imagen
reservada se crea pegando recortes de ajuste ni recoloreando otra imagen.

Los libros proceden de **diagramas JPEG realmente descargados**, decodificados
a RGB y guardados sin pérdidas adicionales en PNG. No se dibujaron con las
plantillas del reconocedor. Las anotaciones registran URL y hash originales,
posiciones transcritas manualmente y límites interiores aproximados revisados
visualmente. Ajuste: diagramas 1, 4, 5, 6 y 8. Evaluación: 3 y 7. El diagrama 2
contiene flechas y queda fuera del piloto. Consulta el
[manifiesto del libro](../../data/manifests/book-strategy-hatched-v1.json) y los
[avisos de procedencia](../../data/THIRD_PARTY_NOTICES.md).

Reconstrucción de las plantillas desde las particiones de ajuste incluidas:

```bash
python -m tools.build_piece_templates --profile lichess-cburnett-blue-v1
python -m tools.build_coordinate_templates --profile lichess-cburnett-blue-v1
python -m tools.build_piece_templates --profile chesscom-default-green-v1
python -m tools.build_coordinate_templates --profile chesscom-default-green-v1
python -m tools.build_piece_templates --profile book-strategy-hatched-v1
```

El libro no tiene plantillas de coordenadas. Los recursos incluyen hashes y
casillas de origen; durante el reconocimiento solo se consultan los recursos
instalados y los píxeles de entrada. Conserva los avisos de terceros con las
capturas y las plantillas derivadas.

Para añadir un perfil: reunir posiciones originales distintas y anotadas, fijar
particiones, cubrir clases/fondos y orientación, construir solo con ajuste,
congelar la implementación, evaluar posiciones completas y negativos, y conservar
las pruebas de los perfiles anteriores. Comparar PyTorch sigue siendo otro
experimento, separando entrenamiento, validación y evaluación final.
