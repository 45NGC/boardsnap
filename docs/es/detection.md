# Detección del tablero

[English](../en/detection.md) | **Español** · [Inicio](README.md)

`boardsnap.detection.detect_board(image)` localiza una cuadrícula completa de
8 × 8, alineada con la imagen, en una imagen RGB de Pillow. Ahora combina
candidatos por colores conocidos con una **vía estructural independiente de la
paleta**. Solo lee píxeles: no usa nombres, anotaciones, navegador ni posiciones
conocidas.

```python
from boardsnap.image_input import read_image
from boardsnap.detection import BoardDetectionError, detect_board

with read_image("image.png") as image:
    try:
        bounds = detect_board(image)
        print(bounds.as_box())  # (left, top, right, bottom)
    except BoardDetectionError as error:
        print(error.to_dict())
```

`BoardBounds` contiene `x`, `y`, `width`, `height` enteros en píxeles de entrada;
los bordes derecho e inferior son exclusivos. `read_image` normaliza EXIF antes.
El detector conserva la imagen y no recorta, resuelve la orientación ni clasifica
piezas. Los límites son datos internos; la salida pública del reconocimiento
sigue conteniendo exclusivamente `piecePlacement`.

## Funcionamiento

1. Se conservan las máscaras de las paletas conocidas como propuestas. Su
   comprobación estricta de alternancia en todas las casillas mantiene los
   límites exactos de los temas anteriores.
2. Independientemente, se buscan bordes RGB conectados. Las diferencias RGB
   conservan algunos límites entre colores de brillo parecido que se perderían
   en gris. Un pequeño suavizado y cierre morfológico eliminan separaciones
   mínimas; las regiones aproximadamente cuadradas proponen la geometría.
3. Se localizan siete límites interiores por eje. Se ajusta un espaciado regular
   con al menos cinco picos coincidentes: las bases de piezas o los textos pueden
   producir picos más fuertes que uno o dos bordes reales. Se refinan los límites
   en píxeles originales y se rechaza extrapolar fuera de la imagen.
4. Se divide cada candidato en 8 × 8. Se muestrea el borde interior de cada casilla
   para reducir la interferencia de piezas y flechas finas. Se estiman los dos
   aspectos alternos del fondo a partir de la imagen, sin colores RGB prefijados.
   Se exigen al menos 52 casillas coherentes y cinco por fila y columna.
5. También se requieren cambios sostenidos en los límites previstos de la
   cuadrícula, en ambos ejes. Deben coincidir alternancia, regularidad y bordes;
   un marco cuadrado o una tabla con líneas no bastan.
6. Se agrupan propuestas del mismo rectángulo. Se devuelve un tablero, o un error
   estructurado si hay cero o varios. La búsqueda estructural se ejecuta incluso
   cuando funciona la paleta, para no ignorar un segundo tablero de otro color.

Las propuestas usan imágenes de hasta 1600 píxeles en el lado mayor; el refinado
conserva coordenadas originales y muestrea filas para limitar la memoria. El
mínimo de tablero original es 128 píxeles, pero además se exigen 24 píxeles a
escala de propuesta. Por ello pueden perderse tableros pequeños dentro de imágenes
muy grandes. Son técnicas deterministas de OpenCV/NumPy; no se entrena un modelo
ni se añaden dependencias o PyTorch.

Los perfiles digitales comparten esta vía estructural. El perfil sigue aportando
propuestas por paleta y, en otras etapas, plantillas de orientación y piezas.
**Detectar un tema nuevo no implica reconocer sus piezas.** El perfil experimental
de libros conserva su detector independiente con marco; consulta [perfiles](profiles.md).

## Previsualización y medición independiente

```bash
# Capturas reales, sin clasificar piezas
python -m tools.preview_detection .cache/real-captures --output-dir .cache/detection-real
# Corpus de desarrollo versionado
python -m tools.preview_detection data/detection/development --output-dir .cache/detection-development
# Solo métricas de límites; partición explícita
python -m tools.evaluate_detection --split development
python -m tools.evaluate_detection --split evaluation
```

Las carpetas contienen `detection.png` (rectángulo sobre la imagen completa) y
`board.png` (recorte sin marcas añadidas). Los originales no cambian. Entrada y
salida no pueden solaparse. Al repetir se sustituyen las vistas; los fallos borran
las anteriores para no mostrar resultados obsoletos. El comando devuelve 1 si
falla alguna imagen. `--squares` añade normalización/casillas; `--recognition`
activa expresamente la clasificación separada.

El evaluador genera un **informe de detección**, no el JSON de reconocimiento.
Comprueba hashes y mide error máximo de borde e intersección sobre unión (IoU)
por rectángulo, además de contar fallos. También elimina el tablero anotado de
una copia y comprueba que se rechaza la interfaz restante. `--output ruta.json`
guarda el informe. Devuelve 1 si hay límites ausentes/imprecisos o falsos positivos
en esos negativos. No ejecuta la clasificación.

## Conjunto revisado y resultados

El [manifiesto](../../data/manifests/digital-detection-v1.json) contiene **28 PNG
originales** con rectángulos enteros revisados y hashes SHA-256 conservados:

| Partición | Imágenes | Grupos de origen | Contenido |
| --- | ---: | ---: | --- |
| Desarrollo | 20 | 7 | Partidas reales 001–003 de cada plataforma y ocho capturas automatizadas de estilos de un grupo previo de entrenamiento |
| Evaluación | 8 | 4 | Partidas reales 004–005 de cada plataforma, con flechas, círculos y casillas destacadas |

Las capturas automatizadas cubren Lichess verde/Merida y morado/Alpha, y Chess.com
azul/Classic y marrón/Bases, desde ambos lados. Las reales usan los tableros
marrones aportados e incluyen el último movimiento resaltado; no se aportaron
nombres exactos de temas ni URL/FEN/PGN. Se copian intactas a
`data/detection/development/` y `tests/fixtures/detection/held-out/` para que las
pruebas no dependan de `.cache/`. Son **muestras solo de detección**; no se importan
al plan de 80 posiciones ni se utilizan para construir plantillas de piezas.

Los rectángulos reales se introdujeron tras revisión visual del asistente y se
comprobaron en líneas de píxeles de los bordes. Los automatizados se redondearon
desde las anotaciones DOM y se revisaron visualmente. Ninguno utiliza la salida
del detector como referencia. No es un estudio independiente de anotación humana.
Cada partida y sus variantes permanecen en la misma partición; el reparto y el
**máximo de 2 píxeles de error** se fijaron antes de ejecutar los casos reservados.
La inspección para anotar no equivale a recogida a ciegas. Cuatro partidas de
evaluación siguen siendo una muestra pequeña.

Los [informes de desarrollo](../../data/reports/digital-detection-v1-development.json)
y [evaluación](../../data/reports/digital-detection-v1-evaluation.json) registran
la precisión sobre originales separada del reconocimiento. Incluyen hashes del
manifiesto y del detector para poder rastrear cambios.

Originales medidos: **20/20 rectángulos de desarrollo y 8/8 de evaluación**,
error máximo respecto a los límites enteros de **0 píxeles**, IoU media **1,0**.
Se rechazaron los 28 negativos con el tablero eliminado. Pasan los 64 casos
reservados de regresión (40 variantes nuevas y 24 anteriores); derivan de pocas
imágenes de origen, no son 64 capturas independientes.


```bash
python -m pytest tests/test_detection.py tests/test_detection_structure.py tests/test_detection_images.py tests/test_detection_corpus.py -m 'not evaluation'
python -m pytest tests/test_detection_images.py tests/test_detection_corpus.py -m evaluation
python -m pytest
```

Las pruebas incluyen paletas nuevas, texturas generadas, formas que simulan piezas,
resaltados, flechas, bordes, márgenes, tamaños hasta 2400 píxeles, varios tableros,
cuadrados sólidos, ruido, rayas, casillas no alternas, tablas de líneas, otras
dimensiones e incompletos. Las imágenes reales tienen variantes recortadas,
reducidas, desplazadas y sin tablero; se generan en memoria dentro de la partición
original. **La evidencia de texturas es sintética**: no valida un catálogo real de
madera o mármol. Se conservan las referencias marrones originales y las regresiones
de los demás perfiles.

## Errores y limitaciones

`BoardDetectionError` expone `code`, `message` en inglés y `to_dict()`:

```json
{"error": {"code": "BOARD_NOT_FOUND", "message": "No supported chessboard was detected in the image."}}
```

`BOARD_NOT_FOUND` significa que no se aceptó ninguna cuadrícula, incluidas las
condiciones no admitidas; `UNSUPPORTED_IMAGE`, que se aceptaron varias. Entradas
que no son Pillow o RGB producen `TypeError` y `ValueError`. No se devuelven
confianzas ni posiciones inventadas.

Se siguen esperando tableros 2D completos, alineados y aproximadamente cuadrados.
Pueden fallar perspectiva, giros arbitrarios, oclusión importante, texturas fuertes,
poco contraste o bordes unidos a la interfaz. Tolerar algunas casillas alteradas
no garantiza admitir cualquier superposición. Un damero vacío de 8 × 8 no se
distingue visualmente de un tablero vacío en esta etapa. Tampoco siempre puede
distinguirse una cuadrícula mayor recortada exactamente a ocho filas/columnas
completas. Los negativos no demuestran el rechazo de toda superficie ajena.

Faltan más temas reales, interfaces móviles nativas y negativos independientes.
La ampliación de detección no cambia el alcance medido de clasificación ni
promete reconocimiento completo de capturas con marcas.
