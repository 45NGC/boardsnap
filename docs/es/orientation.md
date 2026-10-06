# Orientación del tablero

[English](../en/orientation.md) | **Español** · [Inicio](README.md)

`detect_orientation(board)` lee las coordenadas en los píxeles del origen a
resolución completa conservado por `normalize_board`. Devuelve `"white-bottom"`
o `"black-bottom"`. `to_canonical(matrix, orientation)` transforma una matriz
de 8 × 8 en orden visual al orden de ajedrez: filas 8 a 1, columnas a a h.

## Alcance y método actuales

La primera implementación lee **letras interiores en el borde inferior y números
interiores en el borde derecho** de `lichess-cburnett-brown-v1`. Es un lector
de plantillas para `abcdefgh12345678`, no OCR general. Utiliza Pillow, NumPy y
OpenCV ya instalados; no necesita ejecutables de OCR, servicios de red ni PyTorch.

1. Localizar pequeñas regiones de etiquetas relativas a los límites detectados,
   en la imagen decodificada original, excluyendo la sombra exterior del tablero.
2. Exigir un fondo conocido del perfil brown y extraer el texto contrastante en
   escala de grises, tolerando el suavizado subpíxel de colores.
3. Comparar la silueta con ejemplos incluidos en el paquete, conservando sus
   proporciones. Aceptar solo una coincidencia por solapamiento de al menos 0,78
   con una ventaja mínima de 0,05 sobre el siguiente carácter. Son umbrales internos,
   no puntuaciones de confianza en la salida.
4. Exigir al menos **cuatro coordenadas legibles**, todas coherentes con una vista.
   Con blancas abajo, las letras son `abcdefgh` y los números `87654321`;
   con negras abajo se invierten ambas secuencias. Puede bastar un solo eje.
5. Si faltan etiquetas, son insuficientes, ilegibles, están fuera de lugar o se
   contradicen, devolver **blancas abajo**, conforme al contrato de salida.

La identidad de piezas, las casillas ocupadas, la alternancia de colores, los
textos de interfaz fuera de estas regiones, los nombres de archivo, las anotaciones
y los metadatos no determinan la orientación. Un tablero sin etiquetas visto desde
negras también usa la convención de blancas: puede ser incorrecta, pero es
determinista y no solicita confirmación.

Los 32 ejemplos de caracteres proceden **únicamente de la posición vacía de ajuste
`pos-004` en ambas vistas**. El recurso instalado registra procedencia y hashes
y se incluye en el wheel. El motor no lee carpetas de ajuste/evaluación al ejecutarse.
Consulta la [procedencia](../../src/boardsnap/assets/README.md). Para regenerarlo:

```bash
.venv/bin/python -m tools.build_coordinate_templates
```

El lector no admite coordenadas en márgenes exteriores, otras fuentes o
distribuciones, otros temas, imágenes giradas/reflejadas ni etiquetas de libros.
Estas pistas pueden ser ilegibles y activar la convención. Los tableros de origen
con menos de 256 píxeles por lado y los caracteres extraídos con menos de 6 píxeles
de alto se consideran ilegibles. Conservar el origen evita perder etiquetas al
normalizar a un tamaño pequeño, pero no recupera texto ausente de la entrada.
Otras fuentes y representaciones requieren nuevos ejemplos de ajuste y evaluación
separada; escalar muestras no demuestra compatibilidad con tamaños renderizados
independientemente.

## API de Python y gestión de imágenes

```python
from contextlib import ExitStack

from boardsnap.image_input import read_image
from boardsnap.detection import detect_board
from boardsnap.normalization import normalize_board
from boardsnap.segmentation import split_squares
from boardsnap.orientation import detect_orientation, to_canonical

with ExitStack() as stack:
    image = stack.enter_context(read_image(
        "data/tuning/lichess-cburnett-brown-v1/pos-002-black.png"
    ))
    board = stack.enter_context(normalize_board(image, detect_board(image)))
    visual = split_squares(board.image)
    for row in visual:
        for square in row:
            stack.enter_context(square)
    orientation = detect_orientation(board)
    canonical = to_canonical(visual, orientation)
    # canonical[0][0] corresponde a a8; los dibujos no se giran.
```

`to_canonical` admite matrices y filas en listas o tuplas, con valores arbitrarios
en las casillas. Con blancas abajo copia los contenedores; con negras abajo invierte
ambos ejes. Las casillas se comparten, no se copian ni giran. La matriz de entrada
no se modifica. Los recortes siguen siendo responsabilidad del usuario y deben
cerrarse solo una vez. La misma transformación puede aplicarse a una matriz de
símbolos ya clasificada antes de `build_result`. Esta etapa no clasifica piezas.

Los tipos internos inválidos producen `TypeError`; las dimensiones, límites,
modo o valores de orientación inválidos producen `ValueError`. La ausencia de
etiquetas no es un error. El [contrato JSON](output-contract.md) no cambia:
la orientación es un dato interno, no un campo nuevo, puntuación de confianza
ni solicitud de confirmación.

## Vistas previas y pruebas

```bash
.venv/bin/python -m tools.preview_detection --orientation
python -m pytest tests/test_orientation.py tests/test_orientation_images.py -m 'not evaluation'
python -m pytest tests/test_orientation_images.py -m evaluation
python -m pytest
```

La opción incluye las vistas de casillas y guarda `orientation.txt` y `canonical.png`
en `.cache/detection-preview/<perfil>/<captura>/`. Esta última se construye con los
recortes reordenados sin girar caracteres ni piezas. Las coordenadas impresas
siguen dentro de sus recortes y conservan su ubicación en cada casilla; es una
imagen de depuración, no un tablero dibujado de nuevo. Ejecutar sin la opción
elimina las vistas de orientación anteriores de cada imagen procesada.

Las pruebas unitarias comprueban la política de coherencia/convención (con un
lector de caracteres sustituido explícitamente), píxeles sin etiquetas, las
64 correspondencias, gestión de imágenes y entradas inválidas. Las pruebas con
píxeles usan las 16 capturas de ajuste y las 4 reservadas con ocho variantes:
original, recorte, marco desplazado, píxeles duplicados, sin etiquetas, solo letras,
solo números y una etiqueta restante. Un caso real con ejes contradictorios
también comprueba la convención. Las coordenadas y las piezas son independientes:
las matrices esperadas proceden de anotaciones y prueban la transformación entre
etapas, no el reconocimiento de piezas. Las posiciones asimétricas en ambas vistas
deben producir la misma matriz canónica y `piecePlacement` con coordenadas legibles.

Plantillas, umbrales y expectativas de las variantes se fijan con datos de ajuste
antes de evaluar los reservados. Las variantes permanecen en su partición y las
imágenes derivadas de evaluación se generan solo en memoria. Ningún recorte de
evaluación se convierte en plantilla.

Validación del 07-10-2026: **200 casos nuevos superados** (38 unitarios, 130 de
desarrollo y 32 reservados). Las cuatro capturas reservadas originales coinciden
con la orientación anotada. Los 32 casos representan dos posiciones en ambas
vistas y derivados, no 32 escenas independientes. No se cambiaron umbrales ni
plantillas después de evaluar los reservados. La batería completa pasa 546 casos
y omite 7 opcionales de navegador. También se comprobaron los recursos del wheel
y la lectura de coordenadas fuera del directorio de trabajo del repositorio.
Estos resultados no demuestran OCR general ni reconocimiento de piezas.
