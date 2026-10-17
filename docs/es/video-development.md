# Casos de desarrollo revisados de vídeos y páginas

[English](../en/video-development.md) | **Español** · [Inicio](README.md)

El [manifiesto v2](../../data/manifests/video-development-v2.json) contiene
**15 capturas de 13 posiciones distintas**. El usuario confirmó que únicamente
`chesscom-video-001`, `002` y `003` comparten posición. Hay diez imágenes de vídeos
de Chess.com, tres de vídeos de Lichess y una de página de cada plataforma.
El registro inicial midió v8 sin cambios en el motor. El paso posterior de
localización mejora la detección conservando el mismo modelo y las anotaciones.

Los tres PNG originales se conservan en `data/development/video-cases-v1/`; las
doce incorporaciones son copias intactas en `data/development/video-cases-v2/`.
Los originales de caché no cambian. Se conservan el [manifiesto v1](../../data/manifests/video-development-v1.json)
y el [informe de tres imágenes](../../data/reports/video-development-v1-baseline.json),
y v2 registra el hash del manifiesto anterior.

## Anotaciones revisadas

Cada muestra registra hash, ruta original, colocación, orientación, límites
visibles/nominales revisados, condiciones y grupo de origen. Las piezas se
transcribieron visualmente antes de medir el modelo, y los bordes se comprobaron
en líneas de píxeles, sin copiarlos del detector. El FEN visible de la página de
Lichess también permite contrastar su colocación; no se guardan los demás campos
FEN. Es una revisión del asistente, no una anotación humana independiente.

El usuario confirmó expresamente **blancas abajo** en `chesscom-video-009`, `010`
y `chesscom-page-001`, que no tienen coordenadas visibles. Las otras vistas se
comprobaron mediante sus coordenadas. Los nombres exactos de temas, URL, marcas
temporales y jugadas permanecen desconocidos, sin inventarlos.

Los rectángulos son `[izquierda, arriba, derecha, abajo]`, con derecha y abajo excluidos.

| Imagen | Orientación | Rectángulo visible revisado |
| --- | --- | --- |
| chesscom-video-001 | `black-bottom` | `[35, 17, 435, 417]` |
| chesscom-video-002 | `black-bottom` | `[0, 1, 399, 401]` |
| chesscom-video-003 | `black-bottom` | `[2, 2, 299, 299]` |
| chesscom-video-004 | `black-bottom` | `[35, 14, 435, 414]` |
| chesscom-video-005 | `black-bottom` | `[28, 8, 428, 408]` |
| chesscom-video-006 | `white-bottom` | `[41, 11, 417, 387]` |
| chesscom-video-007 | `black-bottom` | `[15, 13, 573, 570]` |
| chesscom-video-008 | `black-bottom` | `[22, 16, 580, 573]` |
| chesscom-video-009 | `white-bottom` | `[13, 23, 467, 481]` |
| chesscom-video-010 | `white-bottom` | `[12, 2, 466, 460]` |
| lichess-video-001 | `white-bottom` | `[15, 11, 903, 899]` |
| lichess-video-002 | `white-bottom` | `[14, 8, 594, 586]` |
| lichess-video-003 | `white-bottom` | `[28, 14, 608, 592]` |
| chesscom-page-001 | `white-bottom` | `[9, 10, 257, 258]` |
| lichess-page-001 | `white-bottom` | `[55, 23, 1143, 1111]` |

La 002 coincide píxel a píxel con el recorte `[36, 16, 437, 420]` de la 001. Su
cuadrícula nominal es `[-1, 1, 399, 401]`: falta una columna de píxeles del borde
izquierdo. El rectángulo visible es `[0, 1, 399, 401]`; no se reconstruyen píxeles.
Es un caso para estudiar los límites, no evidencia de compatibilidad con casillas
ausentes. Algunos vídeos nuevos tienen una ligera diferencia de escala horizontal
y vertical, y texturas. Lichess vídeo 001 incluye el cursor sobre una pieza; la
página de Lichess incluye flechas superpuestas sobre la dama y casillas resaltadas.

## Grupos e independencia

Todos los casos son **development-regression**: nunca evaluación final independiente
ni datos importados automáticamente al entrenamiento. Los tres primeros conservan
su identificador de posición compartido. Cada captura nueva tiene una posición
propia, como confirmó el usuario.
Posiciones diferentes no demuestran partidas diferentes: no se aportaron URL/PGN ni
la relación entre partidas. Por precaución, todas las muestras de Chess.com quedan
en el grupo existente `real-chesscom-video-game-001`, y Lichess utiliza
`real-lichess-development-unresolved`. Son **dos agrupaciones conservadoras por
plataforma, no una afirmación de que existan dos partidas independientes**. Las
imágenes relacionadas futuras seguirán en desarrollo; se podrá precisar el grupo
cuando se confirme su procedencia.

El cargador comprueba hashes, límites, coherencia de posición/grupo y el recorte
exacto conocido. La aceptación rechaza estas familias de posiciones aunque se
renombren, reflejen, giren o intercambien colores, y excluye los grupos conocidos.
No se pueden identificar automáticamente posiciones relacionadas desconocidas sin
su procedencia. El corpus final reservado no se ha capturado ni evaluado.

## Referencia histórica de v8 antes del cambio de localización

El [informe de 15 imágenes](../../data/reports/video-development-v2-baseline.json)
registra **5/15 detecciones precisas** y **5/15 aciertos del recorrido completo**.
Nueve imágenes devuelven `BOARD_NOT_FOUND`; la 002 devuelve límites con un error
máximo de 3 píxeles. Con límites visibles revisados, la clasificación acierta
**13/15 imágenes**. La 009 y la 010 siguen teniendo piezas incorrectas: este lote
ampliado no permite atribuir todos los fallos exclusivamente al detector. Hay que
medir por separado geometría/remuestreo y robustez de clasificación en los siguientes pasos.

| Imagen | Detección con tolerancia de 2 px | Clasificación con límites revisados | Recorrido completo |
| --- | --- | --- | --- |
| chesscom-video-001 | Falla | Correcto | Falla |
| chesscom-video-002 | Falla | Correcto | Falla |
| chesscom-video-003 | Correcto | Correcto | Correcto |
| chesscom-video-004 | Falla | Correcto | Falla |
| chesscom-video-005 | Falla | Correcto | Falla |
| chesscom-video-006 | Falla | Correcto | Falla |
| chesscom-video-007 | Correcto | Correcto | Correcto |
| chesscom-video-008 | Correcto | Correcto | Correcto |
| chesscom-video-009 | Falla | Falla | Falla |
| chesscom-video-010 | Falla | Falla | Falla |
| lichess-video-001 | Correcto | Correcto | Correcto |
| lichess-video-002 | Falla | Correcto | Falla |
| lichess-video-003 | Falla | Correcto | Falla |
| chesscom-page-001 | Correcto | Correcto | Correcto |
| lichess-page-001 | Falla | Correcto | Falla |

## Paso 2: localización dentro de fondos complejos

El [nuevo informe](../../data/reports/video-development-v2-localization.json) usa
las mismas 15 imágenes, etiquetas y pesos v8. El detector ahora propone rectángulos
a partir de líneas interiores regulares aunque los bordes se unan al fondo.
Conserva las comprobaciones geométricas y de alternancia, y añade controles de
casillas exteriores completas y de continuación visible hacia cuadrículas mayores.
Consulta [detección](detection.md) para el algoritmo y sus límites de búsqueda.

| Medición | Antes | Después |
| --- | ---: | ---: |
| Rectángulos con error máximo de 2 píxeles | 5/15 | 11/15 |
| Colocación exacta con límites revisados | 13/15 | 13/15 |
| Colocación exacta mediante el recorrido completo | 5/15 | 12/15 |

`chesscom-video-001` se localiza en `[35, 17, 435, 418]` (error máximo de 1 píxel)
y devuelve la colocación esperada. La 003 conserva su rectángulo y colocación
exactos. También pasan a localizarse correctamente 004, 005, 006, Lichess vídeo 002
y la página de Lichess, con colocaciones correctas. Se mantienen los cinco casos
que ya funcionaban.

Al terminar el paso 2 quedaban pendientes concretos: la 002 seguía usando la alternativa imprecisa de
imagen completa; Lichess vídeo 003 devuelve ya la posición correcta, pero tiene
un error de 3 píxeles en el rectángulo. Chess.com vídeos 009/010 siguen fallando en
localización y también en clasificación con límites revisados. Son trabajos
posteriores de geometría y clasificación; no se cambian las anotaciones para
adaptarlas a las predicciones. Las pruebas con fallo esperado estricto registran
esos cuatro casos de rectángulo, dos de clasificación con límites revisados y tres
del recorrido completo. El paso siguiente actualiza este estado.

La [repetición del corpus anterior de detección](../../data/reports/digital-detection-v3-localization-regression.json)
conserva los 28 rectángulos y rechaza los 28 negativos con tablero eliminado.
Las pruebas también rechazan los 15 fondos de vídeos/páginas tras retirar sus
tableros, comprueban copias de la 001 redimensionadas y trasladadas, y usan fondos
sintéticos conectados con texto, varios tableros, otras dimensiones y tableros
incompletos. Estos controles no demuestran ausencia de falsos positivos en
cualquier captura futura.

Todos los informes siguen siendo pruebas de desarrollo/regresión. No se ha
consultado el conjunto final reservado ni reentrenado el clasificador. El JSON
público de reconocimiento no cambia.

La suite completa con el modelo v8 local supera **1490 pruebas**, con 36 pruebas
opcionales de navegador omitidas y 11 fallos esperados (las nueve comprobaciones
de desarrollo anteriores y dos casos experimentales de diagramas de libros).

La [repetición completa de regresiones de v8](../../data/reports/neural-styles-v8-localization-regression.json)
conserva **3456/3456 tableros exactos y 221184/221184 casillas correctas**, tanto con
límites revisados como detectados. Los 3456 rectángulos permanecen dentro de dos
píxeles. Son variantes de 12 posiciones ya consultadas, no una evaluación final
independiente. Los hashes de datos/modelos y todas las métricas agregadas del
candidato coinciden con el informe histórico de v8; el nuevo registra el hash
del detector actualizado.

## Paso 3: ajuste de bordes visibles

El [informe de límites](../../data/reports/video-development-v2-bounds.json) registra
**13/15 detecciones precisas y 13/15 posiciones exactas del recorrido completo**,
frente a 11/15 y 12/15 tras el paso 2. La clasificación con límites revisados sigue
en 13/15: no cambian pesos, etiquetas, imágenes de entrada ni preprocesado del clasificador.

La 002 devuelve automáticamente los límites visibles **`[0, 1, 399, 401]`** y la
colocación correcta con v8. No se reconstruye la columna izquierda que falta.
La 001 y la 003 siguen devolviendo la misma posición esperada; añadir márgenes
asimétricos a las tres conserva el resultado. Lichess vídeo 003 ahora coincide
con su rectángulo revisado `[28, 14, 608, 592]`. Chess.com vídeo 003 conserva un
error de un píxel respecto a su anotación (`[2, 2, 298, 299]` detectado), sin
modificar la referencia para adaptarla al detector.

El marco de una imagen casi cuadrada ya no se acepta únicamente porque su patrón
global parezca de 8x8. Debe permitir ajustar líneas interiores, localizar bordes
visibles y comprobar la alineación con las ocho filas y columnas. Se comprueba
también el rectángulo finalmente seleccionado. Consulta [detección](detection.md#límites-visibles-antes-de-dividir-en-casillas)
para los límites, incluida la tolerancia de un píxel y el refinado opcional de
propuestas que ya estaban validadas.

Los vídeos de Chess.com **009/010 siguen pendientes**, tanto en detección como en
clasificación con límites revisados. Seis comprobaciones con fallo esperado
estricto conservan esa distinción; no hay nuevo entrenamiento ni se declara
compatibilidad general con vídeos. El [corpus anterior de detección](../../data/reports/digital-detection-v4-bounds-regression.json)
conserva sus 28/28 rectángulos y rechaza 28/28 negativos con el tablero eliminado.
Los seis fallos originales de flechas/tableros recortados también conservan sus
colocaciones correctas.

La suite completa con v8 supera ahora **1552 pruebas**, con 36 pruebas opcionales
de navegador omitidas y ocho fallos esperados (seis comprobaciones de la 009/010
y dos casos experimentales de libros). Las nuevas pruebas geométricas cubren un
píxel recortado en cada uno de los cuatro lados, rechazan recortes mayores con/sin
márgenes y comprueban dimensiones no múltiplos de ocho y dos métodos de remuestreo.
Nueve pruebas neuronales confirman la posición compartida entre 001/002/003 con
tres configuraciones de márgenes.

La [regresión completa de reconocimiento](../../data/reports/neural-styles-v8-bounds-regression.json)
conserva **3456/3456 tableros exactos y 221184/221184 casillas correctas**, tanto
con límites revisados como detectados. Los 3456 rectángulos detectados mantienen
un error máximo de dos píxeles, incluidas imágenes limpias, marcas sencillas y
flechas. Son variantes de 12 posiciones ya consultadas, no evidencia final
independiente. Los hashes del modelo y los datos, y todas las métricas agregadas
del candidato, coinciden con el informe del paso 2; los hashes del código
identifican el detector actualizado.

```bash
python -m tools.development_cases --model .cache/neural-styles-v8/best.pt --output .cache/bounds-step3/video-recheck.json
BOARDSNAP_TEST_MODEL=.cache/neural-styles-v8/best.pt python -m pytest tests/test_detection_bounds.py tests/test_video_development.py
python -m tools.preview_detection data/development/video-cases-v1/chesscom-video-002.png --output-dir .cache/bounds-step3/preview --squares
boardsnap .cache/real-use-tests/chesscom-video-002.png --model .cache/neural-styles-v8/best.pt --orientation black-bottom
```

Para reproducir la regresión completa de reconocimiento:

```bash
python -m tools.evaluate_marks --dataset .cache/digital-style-squares-v2 --baseline .cache/neural-arrows-v1/best.pt --candidate .cache/neural-styles-v8/best.pt --baseline-name arrowBaseline --candidate-name styleCandidate --split evaluation --regression --output .cache/bounds-step3/corpus-recheck.json
```

El comando de casos de desarrollo sigue terminando con código 1 por la 009/010;
`boardsnap` devuelve únicamente el `piecePlacement` correcto. Siguen siendo muestras consultadas de
desarrollo/regresión. El conjunto final independiente permanece sin consultar.

## Reproducir y ampliar

El manifiesto predeterminado es ahora v2. Para los tres casos originales, añade
`--manifest data/manifests/video-development-v1.json`. Desde la raíz del repositorio:

```bash
python -m tools.development_cases --output .cache/video-detection.json
python -m tools.development_cases --model .cache/neural-styles-v8/best.pt --output .cache/video-v8.json
python -m pytest tests/test_video_development.py
BOARDSNAP_TEST_MODEL=.cache/neural-styles-v8/best.pt python -m pytest tests/test_video_development.py
# Controles sintéticos de fondos conectados y suite completa
python -m pytest tests/test_detection_clutter.py
BOARDSNAP_TEST_MODEL=.cache/neural-styles-v8/best.pt python -m pytest
# Ver el rectángulo corregido de la 001 y sus casillas (salida local ignorada)
python -m tools.preview_detection data/development/video-cases-v1/chesscom-video-001.png --output-dir .cache/localization-step2/preview --squares
# Repetir el corpus de reconocimiento ya consultado con los mismos modelos
python -m tools.evaluate_marks --dataset .cache/digital-style-squares-v2 --baseline .cache/neural-arrows-v1/best.pt --candidate .cache/neural-styles-v8/best.pt --baseline-name arrowBaseline --candidate-name styleCandidate --split evaluation --regression --output .cache/localization-step2/corpus-recheck.json
```

El evaluador devuelve **1 mientras falle algún caso medido**. Sin `--model` mide
solo detección y no necesita Torch. Con modelo separa clasificación con límites
revisados del recorrido de producción; los límites esperados nunca guían la
detección de producción. Los informes fijan hashes de datos, modelo, código y herramienta.
Los fallos conocidos del comportamiento deseado usan `xfail` estricto: una mejora
produce `XPASS` y obliga a retirar la marca. Los tests neuronales requieren
`BOARDSNAP_TEST_MODEL`; una ruta indicada pero inválida falla en vez de omitirse.

No hacen falta más capturas para empezar las correcciones del detector. Guarda
los nuevos originales en `.cache/real-use-tests/`, con URL y momento del vídeo o
enlace de partida cuando sea posible. Originales y recortes siguen siendo variantes
relacionadas; los casos positivos normales deben conservar todos los bordes.
Mantén controles que funcionan junto con los fallos. Por ejemplo:
`chesscom-video-game-002-frame-001-original.png` y
`chesscom-video-game-002-frame-001-crop.png`. Los archivos nuevos quedan pendientes
de revisión y nunca pasan automáticamente a evaluación final.
