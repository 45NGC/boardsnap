# Recuperación acotada de bordes y cuadrícula

[English](../en/border-grid-recovery.md) · [Diagnóstico previo](video-009-010-diagnosis.md)

La 009 y la 010 se reconocen ahora mediante el recorrido automático con v8 y con
el candidato de tolerancia, sin modificar sus pesos. La corrección está en el
detector: separa la evidencia del perímetro visible del rectángulo geométrico
que se necesita para dividir el tablero en 64 casillas uniformes.

## Condiciones de recuperación

Las rutas anteriores conservan sus filtros y tienen prioridad. La recuperación
solo se intenta cuando ninguna produce un tablero. Requiere:

1. Una propuesta basada en líneas interiores, con las siete divisiones de cada
   eje alineadas y con contraste suficiente. No basta el consenso de cinco líneas
   que se permite para proponer rectángulos en la ruta habitual.
2. El patrón alterno 8 × 8 dentro de la cuadrícula y cuatro bordes visibles que
   superen la comprobación estructural exterior original.
3. Un único borde visible desplazado hacia dentro más de un píxel respecto a la
   cuadrícula. El desplazamiento máximo es `min(6, floor(lado_de_casilla × 0.08))`
   píxeles de entrada: cuatro píxeles para estos tableros. Los demás bordes solo
   pueden diferir un píxel por rasterizado; tampoco se permite expansión mayor.
4. Una cuadrícula íntegramente dentro de la imagen, con píxeles exteriores
   disponibles, y sin continuación que indique una cuadrícula de más de 8 × 8.

`_BorderGrid` conserva separadas las geometrías `grid` y `visible`. Después de
validar el borde visible, se devuelve **grid** para normalizar y dividir. No se
vuelve a ajustar al perímetro visible, porque eso repetiría el desalineamiento.
No se rellenan píxeles, reconstruyen piezas ni consultan etiquetas, nombres de
archivo o modelos para detectar el tablero. El JSON público sigue conteniendo
únicamente `piecePlacement`, o el error estructurado correspondiente.

Esta excepción admite una franja exterior estrecha, no celdas ausentes. No puede
distinguir universalmente el origen de unos pocos píxeles ocultos —marco, sombra
o recorte—. La cobertura se limita a la evidencia y al margen descritos; no se
promete recuperar tableros arbitrariamente cortados ni diseños desconocidos.

## Anotaciones y resultados

El manifiesto histórico se conserva intacto. La [referencia de geometría](../../data/manifests/video-grid-geometry-v1.json)
registra por separado el borde visible y las siete líneas medidas antes de esta
corrección. Sus hashes la vinculan al diagnóstico y a las imágenes originales;
solo la usan pruebas e informes, nunca el detector.

| Captura | Perímetro visible | Geometría de división |
| --- | --- | --- |
| 009 | `(13, 23, 467, 481)` | `(10, 24, 466, 480)` |
| 010 | `(12, 2, 466, 460)` | `(9, 3, 465, 459)` |

Los informes mantienen la clasificación con el rectángulo visible como control
histórico: sigue fallando al dividir ese rectángulo uniformemente. Añaden
`gridBoundsRecognition` para medir el clasificador con geometría alineada, y
comparan la detección con esa misma referencia. No se han ocultado los resultados
anteriores ni cambiado las posiciones esperadas.

Los [15 casos con v8](../../data/reports/video-development-v2-border-v8.json) y
los [15 casos con el candidato](../../data/reports/video-development-v2-border-tolerance.json)
superan detección, clasificación con geometría de referencia y recorrido completo.
Se mantienen la 001/002/003 y los seis fallos originales, comprobados de nuevo con
[v8](../../data/reports/digital-regressions-border-v8.json) y con el
[candidato](../../data/reports/digital-regressions-border-tolerance.json).

La prueba de la CLI usa nombres de archivo ajenos al corpus, otro directorio de
trabajo y ninguna anotación junto al PNG. Exige salida JSON exacta, código 0 y
stderr vacío en 009/010 con ambos modelos. El control de 14 píxeles ocultos exige
`BOARD_NOT_FOUND`, código 1 y stderr vacío.

## Regresiones y límites de la comprobación

La batería incluye los controles de 8 y 14 píxeles ocultos en cada borde de ambas
capturas, recuperación rotada/trasladada, colores sintéticos diferentes, franjas
que exceden el límite, varios bordes afectados, recortes que salen del encuadre,
tableros incompletos existentes, otras dimensiones, múltiples tableros y negativos
sin tablero. Los casos que ya tenían una detección aceptada no invocan la nueva
recuperación.

Se comprueban las regresiones relevantes del detector y de la CLI, junto con los
casos reales y los seis fallos. **No se repite en este cambio el recorrido neuronal
sobre las 3456 imágenes del corpus completo**: las rutas que ya devolvían un
tablero conservan su comportamiento. Ese recorrido integral sigue perteneciendo
al cierre del candidato; tampoco se ejecutan aceptación final ni distribución.
Los conjuntos antiguos consultados se consideran regresión, no evidencia final
independiente.

El [registro de validación](../../data/reports/border-grid-recovery-validation.json)
vincula los informes y hashes. La batería amplia registró 668 pruebas correctas y
dos controles históricos de rectángulo visible como fallos esperados. Tras
convertirlos en comprobaciones explícitas de borde/cuadrícula, la batería final
de vídeos pasó sus 118 pruebas sin fallos esperados. Las pruebas amplias incluyen
la CLI con ambos modelos y los controles negativos descritos arriba.

## Comandos

```bash
boardsnap .cache/real-use-tests/real-use-19.png --model .cache/neural-tolerance-v1-conservative/best.pt --orientation white-bottom
boardsnap .cache/real-use-tests/real-use-20.png --model .cache/neural-tolerance-v1-conservative/best.pt --orientation white-bottom
python -m tools.development_cases --model .cache/neural-tolerance-v1-conservative/best.pt --grid-references data/manifests/video-grid-geometry-v1.json --output .cache/border-grid-development.json
python -m pytest tests/test_detection_border_grid.py
BOARDSNAP_TEST_MODEL=.cache/neural-tolerance-v1-conservative/best.pt python -m pytest tests/test_detection*.py tests/test_video_development.py tests/test_cli.py tests/test_cli_process.py
```

Para contrastar v8, cambia únicamente `--model` o `BOARDSNAP_TEST_MODEL` por
`.cache/neural-styles-v8/best.pt`. Sin `--grid-references`, la herramienta de
medición conserva la referencia visible histórica; puede informar diferencias
geométricas aun cuando la posición reconocida sea correcta.
