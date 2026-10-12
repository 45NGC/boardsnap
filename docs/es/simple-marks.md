# Resaltados y marcas sencillas

[English](../en/simple-marks.md) | **Español** · [Inicio](README.md)

El paso 7 incorpora variantes controladas de último movimiento (`last-move`),
selección (`selection`), jaque (`check`), círculos (`circle`) y puntos (`move-dot`),
importación de partidas externas revisadas y un modelo separado para CPU.
La salida sigue teniendo exclusivamente `piecePlacement`. La CLI y el pipeline
usan plantillas por defecto; para probar la red nueva hay que cargar su modelo.

## Qué se ha generado y medido

Las 3600 capturas limpias originales se conservan. El corpus derivado contiene
esos 3600 controles y **7200 imágenes marcadas**: cinco condiciones sobre 1440
capturas. Una regla determinista basada en SHA-256 elige una vista/tamaño existente
por posición y combinación de estilos, cubriendo las 80 posiciones y 18
combinaciones de piezas/fondo. Aparecen ambas orientaciones y tamaños, pero no
todas las combinaciones posibles de marcas, tamaños y vistas.

Cada PNG tiene una anotación con posición, grupo, partición, configuración
original, identificador de la pareja limpia, límites, SHA-256, coordenadas de las
marcas, colores RGBA y versión del generador. Las marcas se dibujan sobre la
**imagen completa antes de normalizar**. Se respeta la orientación y se conservan
las piezas y etiquetas originales.

Son **superposiciones sintéticas con transparencia**, que también tiñen las
piezas. No reproducen exactamente las capas nativas que cada plataforma coloca
debajo de ellas. Las casillas de último movimiento, puntos y jaque son pruebas
visuales: no afirman que ese movimiento o jaque sea legal. El jaque se coloca
sobre reyes; las demás marcas se distribuyen entre clases y fondos, para evitar
que predominen las casillas vacías. Círculos y puntos marcan hasta seis casillas.
Este generador utiliza colores, opacidades y geometrías fijas. Quedan por evaluar
otros colores, grosores, marcas combinadas y las aplicaciones móviles nativas.

El [informe del corpus](../../data/reports/digital-marks-v1.json) registra
7560 tableros de entrenamiento, 1620 de validación y 1620 de evaluación. Se
heredan las particiones y grupos originales. En entrenamiento aparece cada clase
sobre ambos fondos para las marcas aplicables. En selección falta una dama blanca
sobre fondo oscuro en validación y un rey negro sobre oscuro en evaluación;
se documenta el hueco sin modificar el conjunto tras evaluarlo. La cobertura del
jaque se limita, por su significado, a los dos colores de rey.

Para entrenar se mantienen todas las casillas limpias y, en cada variante, las
marcadas. Los resaltados rectangulares incluyen también las vecinas inmediatas,
porque el escalado LANCZOS puede mezclar píxeles en sus bordes. Así no se repiten
cinco veces todas las casillas intactas. Se utilizan **194720 casillas de
entrenamiento**, con pesos por frecuencia de clase calculados solo sobre ellas.
Validación y evaluación conservan **las 64 casillas** de cada tablero, sin
equilibrarlas ni muestrearlas. El modelo se selecciona únicamente con validación.

La [configuración fija](../../tools/train-marks-v1.json) entrena desde cero la
red existente de 39709 parámetros durante 20 épocas, con semilla 20261013 y CPU.
Se seleccionó la época 19: 1620/1620 tableros de validación correctos. Se conserva
el modelo limpio como referencia y no se cambia el backend predeterminado.

Una [segunda ejecución completa](../../data/reports/neural-marks-v1-reproducibility.json)
reprodujo exactamente todos los pesos seleccionados y las métricas de validación
de cada época. Los metadatos identifican el código utilizado en cada ejecución;
no se afirma igualdad de los hashes de los archivos completos. La reproducción
se limita a la CPU y versiones de software registradas.

La [evaluación reservada](../../data/reports/neural-marks-v1-evaluation.json)
compara las mismas imágenes y parejas. Con límites de tablero verificados:

| Condición | Modelo limpio: tableros correctos | Modelo con marcas: tableros correctos |
| --- | ---: | ---: |
| Limpias | 540/540 | 540/540 |
| Último movimiento | 214/216 | 216/216 |
| Selección | 216/216 | 216/216 |
| Jaque | 215/216 | 216/216 |
| Círculos | 197/216 | 216/216 |
| Puntos | 142/216 | 216/216 |

El candidato también acierta los 1620 tableros usando **límites detectados**.
Todos los rectángulos detectados quedan a un máximo de dos píxeles de la
referencia. El informe separa detección, clasificación, errores por clase,
regresiones de las parejas y tipos de marca. La rama con detección decodifica el
PNG, detecta usando únicamente píxeles, normaliza y clasifica en orden canónico.
Los límites anotados solo sirven para medir la detección y para la prueba aislada
del clasificador: no corrigen límites detectados incorrectamente.

Son **12 posiciones reservadas de tres grupos**, representadas con muchas
variantes de diseños conocidos. Demuestra una mejora en estas marcas controladas
y ausencia de regresión limpia; no garantiza cualquier captura real ni flechas.

## Reproducir o probar el modelo

Se utiliza el entorno existente con `.[ml]`, sin nuevas bibliotecas. Ejecuta desde
la raíz del repositorio. Las carpetas de destino deben ser nuevas; los resultados
de esta ejecución ya existen localmente en las rutas siguientes.

```bash
python -m tools.build_marked_dataset --clean-dataset .cache/digital-square-corpus-v1 --captures .cache/digital-marked-captures-v1 --output .cache/digital-marked-squares-v1 --report data/reports/digital-marks-v1.json
python -m tools.train_neural --dataset .cache/digital-marked-squares-v1 --run .cache/neural-marks-v1 --config tools/train-marks-v1.json --marked-cells-only
python -m tools.evaluate_marks --dataset .cache/digital-marked-squares-v1 --baseline .cache/neural-clean-v1/best.pt --candidate .cache/neural-marks-v1/best.pt --split evaluation --output data/reports/neural-marks-v1-evaluation.json
python -m pytest tests/test_board_marks.py tests/test_real_positions.py
```

```python
from boardsnap.neural import NeuralClassifier

model = NeuralClassifier(".cache/neural-marks-v1/best.pt")
print(model.recognize_image("imagen.png", orientation="white-bottom"))
```

Para nuevas capturas de las plataformas, `tools/capture-marks.example.json` añade
`marks` a cada configuración. `conditions` debe coincidir con los tipos de marca
y su orden de dibujo. Cada marca tiene `kind`, casillas algebraicas distintas en
`squares` y cuatro enteros `rgba`. Último movimiento requiere dos casillas;
selección, una; jaque, una casilla ocupada por un rey.

```bash
python -m tools.capture_batch capture tools/capture-marks.example.json --output-root .cache/marked-example --validate-only
python -m tools.capture_batch capture tools/capture-marks.example.json --output-root .cache/marked-example
PLAYWRIGHT_BROWSERS_PATH="$PWD/.cache/ms-playwright" BOARDSNAP_BROWSER_TESTS=1 python -m pytest tests/test_capture_sites.py
```

El navegador sigue comprobando el tablero limpio, las piezas, el estilo y la
geometría antes y después de capturarlo. Las marcas nativas no solicitadas se
rechazan u ocultan como indica la guía de captura. Después se añaden las marcas
controladas y se registran `controlledMarks`, el hash del PNG limpio y la
procedencia sintética. Las pruebas locales de Chromium cubren las dos plataformas
y vistas, pero no verifican sus marcas nativas actuales. Las 7200 variantes se
generaron desde PNG ya auditados, sin volver a contactar con las plataformas.
Imágenes, recortes y pesos permanecen en `.cache/`, fuera de Git.

## Capturas reales: revisar antes de clasificar

Las 20 capturas reales siguen **sin posiciones de piezas verificadas**. No han
entrenado este modelo ni forman parte de sus resultados de clasificación.
Una predicción no debe convertirse en etiqueta sin comprobarla independientemente.

Ya hay un borrador en `.cache/real-captures/review-v1.json`. Para preparar otro sin
sobrescribir el trabajo de revisión:

```bash
python -m tools.prepare_real_reviews --output .cache/real-captures/new-review.json
```

Se conservan los hashes y límites revisados para detección. Antes de consultar
sus etiquetas se asignan las partidas 001–002 de cada plataforma a entrenamiento,
003 a validación y las ya reservadas 004–005 a evaluación. Todas las capturas y
futuras variantes de cada partida deben conservar esa partición. El borrador no
se puede importar hasta completar la revisión.

Para cada imagen, compárala visualmente o utiliza su FEN/PGN de origen. Completa
`externalPosition.piecePlacement` y `reviewedPlacement` con el mismo primer campo
del FEN; indica `orientation`, nombre y fecha de la revisión y `reviewMethod`
(`manual-board-comparison`, `source-fen` o `source-pgn`). Después pon `reviewed: true`.
Revisa también las condiciones y los estilos conocidos. URL, fecha de captura o
versión del navegador desconocidas pueden permanecer en `null` con su explicación
en `provenanceNote`; no hay que inventarlas. Para importar solo algunas revisiones
completadas, copia esas muestras a una especificación con un `batchId` nuevo.

El esquema de importación **2** permite `externalPosition` con `positionId`,
`groupId`, `split` y `piecePlacement`, usando identificadores con prefijo `real-`.
Se conserva el esquema 1 para posiciones del plan. Una muestra no puede tener
ambas identidades. Se rechazan PNG alterados, revisión ausente, etiquetas
contradictorias, partidas o posiciones equivalentes que cruzan particiones e
intentos de entrenar con partidas reservadas para evaluación de detección.
Utiliza una raíz de importación común para comprobar también los lotes anteriores.
Las posiciones que coinciden con corpus antiguos o generados requieren revisar
su identidad original; no pueden entrar silenciosamente con otro identificador.

```bash
python -m tools.capture_batch import-real .cache/real-captures/review-v1.json --output-root .cache/reviewed-real --validate-only
python -m tools.capture_batch import-real .cache/real-captures/review-v1.json --output-root .cache/reviewed-real
python -m tools.build_real_squares --imports .cache/reviewed-real/digital-positions-v1 --output .cache/real-squares-v1
```

Tras revisarlas, añade `--real-dataset .cache/real-squares-v1` a un entrenamiento
**nuevo**. Se comprueba el aislamiento entre corpus, se mezclan únicamente los
recortes de entrenamiento/validación y se registran sus hashes. No se abren
recortes de evaluación para entrenar. Las flechas e insignias en entrenamiento
o validación se rechazan en esta etapa; las capturas de la partida 005 conservan
su partición reservada para trabajar después con flechas. Hasta revisar las
posiciones, esta parte del paso 7 con datos reales queda pendiente.
