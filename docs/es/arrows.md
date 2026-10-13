# Flechas y superposiciones combinadas

[English](../en/arrows.md) | **Español** · [Inicio](README.md)

El paso 8 amplía la [referencia de marcas sencillas](simple-marks.md) con flechas
y combinaciones controladas. Detección y clasificación siguen separadas. La
salida contiene únicamente `piecePlacement` y la CLI usa plantillas por defecto.

## Generación y trazabilidad

`tools/arrow_marks.py` admite flechas horizontales, verticales y diagonales,
además de recorridos de caballo en L con ambos órdenes de giro. Se dibujan cuerpo,
giro y punta triangular sobre la captura completa **antes de normalizar o dividir
en casillas**. La orientación cambia las coordenadas de la flecha sin girar los
dibujos de las piezas. Cada flecha tiene su propia capa transparente, por lo que
los colores se superponen en orden cuando se cruzan.

El piloto varía cuatro colores (verde, naranja, azul y rojo), tres grosores
(0.08, 0.14 y 0.22 del lado de una casilla) y tres valores alfa (96, 144 y 192).
Cada PNG registra extremos, recorrido, giro, RGBA, grosor y versión del generador.
Son superposiciones sintéticas sobre imágenes reales de las plataformas: no
reproducen exactamente todas sus flechas nativas ni afirman movimientos legales.

Se miden cuatro casos independientes:

| Caso | Significado |
| --- | --- |
| `arrow-empty` | Una flecha; todas las casillas bajo su cuerpo, giro y punta están vacías |
| `arrow-piece` | Una flecha atraviesa al menos una casilla ocupada |
| `arrow-crossed` | Dos flechas se cruzan realmente, en forma de cruz o X |
| `arrow-combined` | Una flecha con resaltados de último movimiento en sus extremos y un círculo en el destino |

Para comprobar la ocupación se utiliza toda la máscara dibujada, con un margen
de cuatro píxeles en tamaño normalizado para cubrir efectos del escalado. No basta
con que origen y destino estén vacíos. «Sobre una pieza» indica una casilla
ocupada, no un porcentaje medido de sus trazos distintivos. Si no existe una ruta
con las condiciones solicitadas, se registra y omite; nunca se etiqueta mal.

El [informe del corpus](../../data/reports/digital-arrows-v1.json) describe
**5760 imágenes nuevas**, derivadas de las mismas 1440 capturas del piloto, y los
**10800 controles limpios y con marcas sencillas**. No faltó ninguna ruta solicitada.
Se conservan las 80 posiciones, sus grupos y particiones: 11592 tableros de
entrenamiento, 2484 de validación y 2484 de evaluación. Aparecen ambas vistas y
tamaños y las 18 combinaciones de piezas/fondo. Se heredan `pairId`, grupo,
partición y posición; las anotaciones añaden `overlayCase`, `arrowCoverage` y el
hash del PNG limpio original.

Las direcciones y condiciones se eligen de forma reproducible antes de entrenar,
sin utilizar predicciones. Se registran recuentos por clase, fondo y partición.
Es un piloto delimitado, no todas las combinaciones de colores, grosores,
posiciones, vistas y estilos. Estos cuatro casos no demuestran compatibilidad
con cualquier cantidad de flechas, aplicaciones nativas o cruces que además
lleven otras marcas.

## Entrenamiento y evaluación

La [configuración fija](../../tools/train-arrows-v1.json) entrena desde cero la
misma red pequeña para CPU durante 30 épocas. Se conservan todas las casillas
limpias de entrenamiento; las variantes aportan las afectadas, incluidas las
atravesadas por el cuerpo de la flecha y el margen del escalado. Los pesos de la
pérdida se calculan solo con entrenamiento. Validación y evaluación mantienen
las 64 casillas de cada imagen sin equilibrado ni muestreo.

`--preserve-controls` selecciona primero por **tableros completos correctos de
validación limpios y con marcas sencillas**, después por acierto total, promedio
de sensibilidad por clase y pérdida. Así una mejora global con flechas no oculta
una regresión de los controles durante la selección. Los checkpoints guardan el
hash de esa selección de controles y rechazan cambios al reanudar. Una prueba
compara exactamente los pesos de entrenamiento seguido e interrumpido. La
evaluación no se utiliza para seleccionar el modelo.

Esta ejecución utilizó 233957 casillas de entrenamiento de 11592 tableros.
Se seleccionó la época 30: 2484/2484 tableros de validación, incluidos los 1620
controles limpios y sencillos. El archivo es `.cache/neural-arrows-v1/best.pt`;
sus metadatos fijan preprocesado, clases, hashes de datos/índice, configuración
y hashes del código utilizado.

El [informe comparativo](../../data/reports/neural-arrows-v1-evaluation.json)
compara el modelo del paso 7 y el candidato nuevo sobre los mismos píxeles.
Incluye métricas por clase, posiciones completas, parejas limpias/marcadas,
resultados por caso y por dirección. Los subconjuntos de direcciones pueden
solaparse en los cruces; los casos independientes sí permiten sumar los totales.

Resultados medidos de evaluación (capturas completas correctas):

| Caso | Paso 7, límites verificados | Modelo con flechas, límites verificados | Modelo con flechas, límites detectados |
| --- | ---: | ---: | ---: |
| Limpias | 540/540 | 540/540 | 540/540 |
| Marcas sencillas, los cinco tipos | 1080/1080 | 1080/1080 | 1080/1080 |
| Flecha sobre casillas vacías | 183/216 | 216/216 | 216/216 |
| Flecha sobre casillas ocupadas | 188/216 | 216/216 | 216/216 |
| Flechas cruzadas | 136/216 | 216/216 | 216/216 |
| Flecha + resaltados + círculo | 175/216 | 216/216 | 216/216 |
| **Total** | **2302/2484** | **2484/2484** | **2484/2484** |

El candidato clasifica correctamente las 158976 casillas en ambas ramas, sin
regresión en ninguna de las seis categorías de control. También acierta los
cuatro subconjuntos de direcciones. La detección queda a dos píxeles o menos de
la referencia en todas las imágenes, incluidas las 864 variantes con flechas.
El modelo del paso 7 obtiene 2303/2484 usando límites detectados; pequeñas
diferencias en el recorte pueden cambiar sus predicciones, de ahí las dos ramas.
El detector no se ha modificado en este hito.

Son **12 posiciones reservadas de tres grupos de origen**, renderizadas en muchas
variantes, no 2484 posiciones independientes ni una garantía para cualquier marca
nativa. También se comprobó la API pública `NeuralClassifier.recognize_image`
con 16 imágenes: ambas plataformas, cuatro casos y ambas vistas. Todas devolvieron
el `piecePlacement` esperado, sin campos adicionales.

Los límites verificados aíslan la clasificación. La otra rama detecta solo con
píxeles, compara el rectángulo con la referencia y normaliza/clasifica sin
corregirlo. Un fallo de detección cuenta como un tablero y 64 casillas incorrectos.
Se separan los fallos de detección de los errores de clasificación con límites
correctos, y se registran las regresiones de cada control anterior por separado.

No se borran flechas ni se aplica enmascarado o reconstrucción de píxeles. La
referencia actual aprende con la marca visible. Antes de adoptar una eliminación,
habría que demostrar una mejora en validación sin borrar trazos ni empeorar las
imágenes limpias.

## Comandos

Utiliza el entorno existente con el extra `ml`, desde la raíz del repositorio.
Los destinos deben ser nuevos; las rutas indicadas ya contienen esta ejecución.

```bash
python -m tools.build_arrow_dataset --parent-dataset .cache/digital-marked-squares-v1 --captures .cache/digital-arrow-captures-v1 --output .cache/digital-arrow-squares-v1 --report data/reports/digital-arrows-v1.json
python -m tools.train_neural --dataset .cache/digital-arrow-squares-v1 --run .cache/neural-arrows-v1 --config tools/train-arrows-v1.json --marked-cells-only --preserve-controls
python -m tools.evaluate_marks --dataset .cache/digital-arrow-squares-v1 --baseline .cache/neural-marks-v1/best.pt --candidate .cache/neural-arrows-v1/best.pt --baseline-name simpleMarksBaseline --candidate-name arrowCandidate --split evaluation --output data/reports/neural-arrows-v1-evaluation.json
python -m pytest tests/test_arrow_marks.py
```

Para mediciones de desarrollo, utiliza `--split validation` y otro archivo de
salida. Fija los ajustes antes de consultar evaluación. Estas posiciones se han
reutilizado entre hitos: para una versión final seguirá haciendo falta un corpus
nuevo de aceptación, sin considerar cada comparación repetida una prueba ciega.

```python
from boardsnap.neural import NeuralClassifier

model = NeuralClassifier(".cache/neural-arrows-v1/best.pt")
result = model.recognize_image("imagen.png", orientation="white-bottom")
```

Las imágenes, recortes y pesos permanecen en `.cache/`, fuera de Git. Los modelos
anteriores se conservan. La receta de captura también permite añadir flechas a
nuevos tableros verificados de las plataformas:

```bash
python -m tools.capture_batch capture tools/capture-arrows.example.json --output-root .cache/arrow-example --validate-only
python -m tools.capture_batch capture tools/capture-arrows.example.json --output-root .cache/arrow-example
PLAYWRIGHT_BROWSERS_PATH="$PWD/.cache/ms-playwright" BOARDSNAP_BROWSER_TESTS=1 python -m pytest tests/test_capture_sites.py
```

Una flecha contiene `kind: "arrow"`, casillas `from`/`to`, `path: "straight"` o
`"knight"`, `width` (0.04–0.30 del lado de una casilla) y RGBA. Para caballo se
añade `bend: "horizontal-first"` o `"vertical-first"`. Los extremos de una flecha
recta deben estar alineados horizontal, vertical o diagonalmente. Se permiten
varias flechas; `conditions` incluye cada tipo una sola vez, en orden de aparición.

El navegador sigue verificando posición, geometría y recursos del tablero limpio
antes y después de la captura, y después registra la transformación sintética.
No acepta silenciosamente marcas nativas inesperadas. Las pruebas de navegador
usan páginas locales de ambas plataformas y vistas; el corpus principal reutiliza
PNG auditados anteriormente.

## Límites y capturas reales

**No se garantiza recuperar una pieza cuya información distintiva esté totalmente
tapada.** Una marca opaca puede producir los mismos píxeles visibles para posiciones
distintas. No se añaden campos del FEN, confianza ni suposiciones de legalidad para
compensarlo.

Las 20 capturas reales aún necesitan posiciones verificadas de forma independiente.
Sus referencias de detección no demuestran reconocimiento de flechas. Continúa el
[flujo de revisión e importación](simple-marks.md#capturas-reales-revisar-antes-de-clasificar).
Ahora se admiten capturas revisadas con flechas mediante `--real-dataset`, respetando
sus particiones y la reserva de la partida 005. Las insignias siguen fuera del
alcance. Esta ejecución no entrena ni atribuye resultados de clasificación a
capturas reales sin revisar, tableros físicos o diagramas de libros.
