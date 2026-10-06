# Normalización y división en casillas

[English](../en/normalization.md) | **Español** · [Inicio](README.md)

Tras la detección, `normalize_board(image, bounds)` recorta la cuadrícula y la
ajusta por defecto a **512 × 512 píxeles RGB**. `split_squares(board.image)`
devuelve una lista de **ocho filas de ocho imágenes RGB independientes de
64 × 64 píxeles**. Estas etapas utilizan Pillow, ya instalado, y no reconocen piezas.

## API de Python

```python
from contextlib import ExitStack

from boardsnap.image_input import read_image
from boardsnap.detection import detect_board
from boardsnap.normalization import normalize_board
from boardsnap.segmentation import split_squares

with ExitStack() as stack:
    source = stack.enter_context(read_image(
        "data/tuning/lichess-cburnett-brown-v1/pos-001-white.png"
    ))
    bounds = detect_board(source)
    board = stack.enter_context(normalize_board(source, bounds))
    squares = split_squares(board.image)
    for row in squares:
        for square in row:
            stack.enter_context(square)

    print(board.image.size)           # (512, 512)
    print(squares[0][0].size)          # (64, 64)
    print(board.source_bounds)        # Límites en la imagen decodificada
    # Usar squares para clasificar y board.source_image para orientar.
```

`ExitStack` cierra las imágenes al terminar el bloque. También puedes gestionarlas
manualmente: llama a `board.close()` y cierra cada casilla cuando termines.
El tablero normalizado posee dos imágenes; la entrada del usuario y los recortes
de casillas tienen sus propios píxeles independientes. Cerrar la entrada o el
tablero normalizado no invalida casillas ya extraídas. Los campos de la dataclass
son inmutables, pero los píxeles de Pillow siguen siendo modificables.

## Geometría y orden

`normalize_board(image, bounds, square_size=64)` acepta una imagen RGB decodificada
y `BoardBounds` con valores enteros. Los bordes derecho e inferior son exclusivos.
Los límites deben tener dimensiones positivas y estar completamente dentro de
la imagen; se rechazan los recortes inválidos en lugar de rellenarlos. El lado
de salida es `8 * square_size`, con `square_size` entero positivo. El valor inicial
de 64 píxeles es una decisión de implementación, no una garantía de precisión de
clasificación ni un tamaño elegido usando las imágenes de evaluación.

El recorte se escala mediante LANCZOS. Las pequeñas diferencias entre ancho y alto
admitidas por el detector se escalan independientemente para producir un cuadrado.
Esto no corrige perspectiva ni verifica que unos límites arbitrarios contengan
un tablero. El escalado puede mezclar colores en los bordes de las casillas;
la segmentación no vuelve a remuestrear la imagen.

`split_squares(image)` requiere una imagen RGB cuadrada con lado positivo divisible
por ocho. Para un lado de casilla `s`, fila `r` y columna `c`, el recorte es
`(c*s, r*s, (c+1)*s, (r+1)*s)`, con extremos finales exclusivos. Cada píxel
normalizado pertenece a una única casilla, sin huecos, solapamientos ni bordes
descartados.

Los índices siguen el **orden visual**, de arriba abajo y de izquierda a derecha,
empezando en cero. `squares[0][0]` es la casilla superior izquierda visible en
ambas orientaciones de ajedrez. Aquí no se gira, refleja ni invierte la matriz;
no se debe asumir que corresponde a `a8` hasta resolver la orientación.
Las coordenadas dibujadas dentro de las casillas permanecen en los recortes.

## Conservación de las pistas de orientación

`NormalizedBoard.source_image` es una copia completa de la entrada decodificada
a su resolución original, conservada antes de eliminar márgenes o escalar.
Mantiene las coordenadas exteriores e interiores sin intentar leerlas.
`source_bounds` ubica el tablero dentro de esa copia. La copia sobrevive a cambios
o al cierre de la entrada del usuario, a cambio de mantener una imagen completa
adicional en memoria.

Para una coordenada de borde normalizada `(u, v)` en un tablero de lado `N`, su
coordenada de borde en el origen es `(bounds.x + u * bounds.width / N,
bounds.y + v * bounds.height / N)`. Estas coordenadas se refieren a la imagen
decodificada después de normalizar EXIF, no a los píxeles sin corregir del archivo.
Es una correspondencia geométrica; LANCZOS utiliza píxeles vecinos al escalar.

La etapa separada de [orientación](orientation.md) examina las coordenadas
conservadas admitidas y reordena las casillas conforme al
[contrato de salida](output-contract.md). Si faltan pistas, aplica la convención
documentada de blancas abajo. Normalización y segmentación no la aplican ni añaden
campos al JSON público.

## Errores y límites

Los tipos de argumentos internos inválidos producen `TypeError`; los modos,
dimensiones, límites o tamaños de destino inválidos producen `ValueError`,
siguiendo las API internas existentes. No se devuelve un tablero parcial ni una
posición vacía sustitutiva. El futuro coordinador/adaptador deberá traducir los
fallos de procesamiento al contrato de errores de salida. No se incorpora ningún
código público nuevo en esta etapa.

Estas funciones asumen que la detección ha proporcionado una cuadrícula completa
y alineada. No amplían los estilos admitidos, eliminan resaltados ni reparan una
detección incorrecta. La clasificación, el OCR general de coordenadas, la corrección
de perspectiva y la CLI de reconocimiento siguen pendientes.

## Inspección visual

Desde la raíz del repositorio:

```bash
.venv/bin/python -m tools.preview_detection --squares
```

En `.cache/detection-preview/<perfil>/<captura>/` puedes abrir:

- `detection.png`: el rectángulo detectado sobre la imagen completa.
- `board.png`: el recorte sin escalar.
- `normalized.png`: el tablero de 512 × 512.
- `squares/row-0-col-0.png` hasta `squares/row-7-col-7.png`: las 64 casillas.

Los nombres usan índices visuales, no filas/columnas de ajedrez. El comando procesa
las imágenes de ajuste por defecto; también acepta una ruta de imagen concreta.
Al repetirlo se reemplazan las vistas de cada imagen procesada. Ejecutarlo sin
`--squares` elimina sus vistas anteriores de normalización y casillas. Los
originales se conservan y los resultados quedan en `.cache`, excluido de Git.
Las funciones del núcleo nunca guardan archivos automáticamente.

## Pruebas

```bash
python -m pytest tests/test_normalization.py tests/test_segmentation.py tests/test_preprocessing_images.py -m 'not evaluation'
python -m pytest tests/test_preprocessing_images.py -m evaluation
python -m pytest
```

Las pruebas sintéticas usan colores únicos por casilla, distribuciones asimétricas
y patrones de píxeles para comprobar límites exactos, orden intacto en ambas
vistas, 64 casillas, reconstrucción sin huecos ni solapamientos, tamaños de origen
impares, tamaños de destino personalizados, entradas inválidas e independencia
de las casillas y de las imágenes con pistas de orientación.

Las pruebas reales ejecutan entrada → detección → normalización → segmentación
en las 16 capturas de ajuste y las 4 reservadas, con marcadores separados. Los
recortes esperados usan los límites revisados existentes, no la salida del
detector. Se comprueba geometría y conservación de píxeles; no se mide precisión
de reconocimiento de piezas ni de orientación. Los parámetros se fijan antes de
ejecutar las imágenes reservadas y ningún recorte de evaluación se incorpora al
conjunto de ajuste.

Validación del 05-10-2026: pasan los 59 casos nuevos (39 sintéticos, 16 de ajuste
y 4 reservados). La batería completa pasa 346 casos y omite 7 pruebas opcionales
de navegador. Estos resultados no demuestran compatibilidad con otros estilos.
