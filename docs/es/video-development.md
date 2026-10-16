# Casos de desarrollo revisados de vídeos y páginas

[English](../en/video-development.md) | **Español** · [Inicio](README.md)

El [manifiesto v2](../../data/manifests/video-development-v2.json) contiene
**15 capturas de 13 posiciones distintas**. El usuario confirmó que únicamente
`chesscom-video-001`, `002` y `003` comparten posición. Hay diez imágenes de vídeos
de Chess.com, tres de vídeos de Lichess y una de página de cada plataforma.
Este paso registra casos y mide el funcionamiento actual de v8; no corrige la
localización, no ajusta los límites ni reentrena el clasificador.

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

## Referencia actual de v8

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

## Reproducir y ampliar

El manifiesto predeterminado es ahora v2. Para los tres casos originales, añade
`--manifest data/manifests/video-development-v1.json`. Desde la raíz del repositorio:

```bash
python -m tools.development_cases --output .cache/video-detection.json
python -m tools.development_cases --model .cache/neural-styles-v8/best.pt --output .cache/video-v8.json
python -m pytest tests/test_video_development.py
BOARDSNAP_TEST_MODEL=.cache/neural-styles-v8/best.pt python -m pytest tests/test_video_development.py
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
