# Detección del tablero

[English](../en/detection.md) | **Español** · [Inicio](README.md)

`boardsnap.detection.detect_board(image)` localiza una cuadrícula completa de
8 × 8, alineada con los ejes, dentro de una imagen Pillow RGB decodificada.
Esta primera implementación se dirige al tablero brown del perfil
`lichess-cburnett-brown-v1`. Solo utiliza píxeles; no lee nombres de archivo,
anotaciones, manifiestos, estado del navegador ni una posición conocida.

```python
from boardsnap.image_input import read_image
from boardsnap.detection import BoardDetectionError, detect_board

with read_image("data/tuning/lichess-cburnett-brown-v1/pos-001-white.png") as image:
    try:
        bounds = detect_board(image)
        print(bounds)  # BoardBounds(x=190, y=158, width=584, height=584)
        print(bounds.as_box())  # (190, 158, 774, 742)
    except BoardDetectionError as error:
        print(error.to_dict())
```

`BoardBounds` es una dataclass inmutable con `x`, `y`, `width` y `height` enteros.
Las coordenadas corresponden a la imagen recibida, después de normalizar EXIF
si procede de `read_image`. Los bordes derecho e inferior son exclusivos.
`as_box()` proporciona coordenadas de recorte compatibles con Pillow. La función
conserva la imagen original y no recorta, normaliza, clasifica piezas ni resuelve
la orientación de ajedrez. Los límites son datos internos, no campos adicionales
del JSON público.

## Vistas previas

Desde la raíz del repositorio, genera vistas previas de todas las capturas de ajuste:

```bash
.venv/bin/python -m tools.preview_detection
```

Abre `.cache/detection-preview/lichess-cburnett-brown-v1/pos-001-white/`
en VS Code. Cada captura tiene su propia carpeta con `detection.png`
(la imagen completa con un rectángulo rojo alrededor de la cuadrícula detectada)
y `board.png` (el recorte sin marcas y a su resolución original). El comando
predeterminado procesa solo `data/tuning`; las imágenes de evaluación siguen
separadas.

Para inspeccionar una imagen concreta:

```bash
.venv/bin/python -m tools.preview_detection path/to/image.png
```

Una imagen suelta genera `.cache/detection-preview/image/`. También puedes indicar
una carpeta para recorrer sus PNG/JPEG y usar `--output-dir` para elegir otra
carpeta de salida. Las carpetas de entrada y salida no deben solaparse.
Al repetir el comando se reemplazan las vistas previas de cada imagen; los fallos
de entrada o detección muestran su código y se eliminan las vistas anteriores
de esa imagen. El comando termina con código 1 si alguna imagen falla.
Las capturas originales no se modifican.

Esta herramienta de desarrollo no reconoce piezas ni genera FEN. El detector
y los tests no guardan vistas previas automáticamente; ejecuta el comando
después de los cambios. La salida predeterminada está excluida de Git por estar
en `.cache`.

## Método y dependencias

1. Crear máscaras de los colores RGB claro y oscuro del perfil, con tolerancia
   de 12 por canal para variaciones de representación.
2. Unir las máscaras y cerrar pequeñas separaciones con un núcleo de 3 × 3.
   Buscar regiones conectadas mediante OpenCV y conservar candidatos casi
   cuadrados de al menos 128 píxeles por lado.
3. Dividir cada candidato geométricamente en 8 × 8 casillas. Cada interior debe
   conservar al menos un 25% del color esperado y como máximo un 10% del opuesto.
   Comprobar ambas alternancias posibles. Se permiten huecos ocupados por piezas.
4. Devolver el único candidato válido. Ninguno produce `BOARD_NOT_FOUND`;
   varios producen `UNSUPPORTED_IMAGE`, sin elegir uno arbitrariamente.

Son reglas fijas para el primer perfil, no un modelo aprendido. Se utilizan
[máscaras por rango](https://docs.opencv.org/4.x/da/d97/tutorial_threshold_inRange.html)
y [componentes conectados](https://docs.opencv.org/4.x/d3/dc0/group__imgproc__shape.html)
de OpenCV. NumPy contiene las matrices de píxeles; `opencv-python-headless`
evita depender de una interfaz gráfica. Se instalan con
`python -m pip install -e '.[dev]'`. Esta etapa no necesita PyTorch.

## Contrato de errores

`BoardDetectionError` ofrece `code`, `message` en inglés y `to_dict()`:

```json
{"error": {"code": "BOARD_NOT_FOUND", "message": "No supported chessboard was detected in the image."}}
```

También se produce este resultado si existe un tablero pero su estilo, escala
o estado no supera las comprobaciones. No demuestra que no haya un tablero.
`UNSUPPORTED_IMAGE` indica que se detectaron varias cuadrículas compatibles.
Una entrada que no sea Pillow produce `TypeError`; una imagen no RGB produce
`ValueError`. Los adaptadores siguen encargándose del transporte JSON. No se
devuelven confianza, posiciones parciales ni un tablero vacío inventado.

## Pruebas y alcance medido (01-10-2026)

```bash
# Desarrollo sin las imágenes reservadas
python -m pytest tests/test_detection.py tests/test_detection_images.py -m 'not evaluation'
# Casos reservados después de fijar los parámetros
python -m pytest tests/test_detection_images.py -m evaluation
python -m pytest
```

Los 35 casos unitarios sintéticos tienen ubicación y tamaño definidos
independientemente. Incluyen cuadrículas hasta el borde, desplazamientos, lados
de 128/193/256/584/1024 píxeles, oclusiones similares a piezas, rectángulos
distractores, franjas, imágenes uniformes, otras dimensiones de cuadrícula,
tableros incompletos, otra paleta y varios tableros. Prueban geometría, no piezas.

Las pruebas reales cubren las 16 capturas de ajuste y las 4 reservadas, cada una
con seis variantes: interfaz original, recorte del tablero, tablero de 192
píxeles, tablero de 960 píxeles, interfaz desplazada e interfaz sin tablero.
Las variantes permanecen en la partición original y se generan solo en memoria.
Los negativos conservan los menús y piezas de reserva reales. Las imágenes
escaladas o desplazadas son transformaciones controladas, no capturas independientes.

Antes de ejecutar la evaluación se fijó un criterio de **como máximo 2 píxeles
de error en cualquiera de los bordes**. Las referencias están en
[references.json](../../tests/fixtures/detection/references.json). Se revisaron
visualmente los bordes enteros, redondeados a partir de las anotaciones del DOM;
no constituyen una medición subpíxel independiente ni un estudio de etiquetado
humano. También se comparan los JSON originales con decimales. Las expectativas
transformadas proceden de la referencia y la transformación conocida, nunca del
resultado del detector.

Resultado: **131 casos de desarrollo y 24 reservados superados**. Las cuatro
capturas reservadas originales devolvieron `(190, 158, 774, 742)`, coincidiendo
exactamente con la referencia entera y con un error máximo de **0,46875 píxeles**
respecto a la anotación original con decimales. Los 24 casos representan solo
**dos posiciones**, sus dos orientaciones y derivados; no son 24 escenas
independientes. No se cambiaron parámetros tras consultar esos resultados.

## Limitaciones y siguiente paso

La cobertura se limita a este perfil de dos colores, con una única cuadrícula
completa, alineada y suficiente fondo visible. No se admiten otros temas,
libros, perspectiva, rotación arbitraria, superposiciones fuertes ni cambios
grandes de color. Regiones conectadas de colores coincidentes pegadas al tablero
pueden unirse a él y provocar un fallo. Una cuadrícula alterna corriente de
8 × 8 no se distingue visualmente de un tablero vacío en esta etapa y puede
aceptarse.

El conjunto inicial es pequeño y comparte una distribución de origen. Faltan
negativos más variados y capturas independientes de otros tamaños y ubicaciones
antes de afirmar generalización. La entrada lee JPEG, pero no se ha medido la
detección sobre JPEG comprimidos. El reconocimiento completo de piezas sigue
pendiente. La [normalización y segmentación](normalization.md) ya producen
64 recortes y conservan la imagen original completa para orientar. Añade
`--squares` al comando de vistas previas para ver `normalized.png` y `squares/`.
