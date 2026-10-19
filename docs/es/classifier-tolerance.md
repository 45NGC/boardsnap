# Tolerancia del clasificador a errores de recorte

[English](../en/classifier-tolerance.md)

Este paso mide el clasificador por separado de la detección. El rectángulo
revisado es el control; modificarlo deliberadamente permite comprobar qué sucede
cuando el detector se equivoca ligeramente. No cambia el detector de producción,
la normalización, la orientación, el contrato JSON ni la selección predeterminada
del modelo. v8 se conserva sin modificaciones. Los vídeos de Chess.com 009/010
quedan como limitaciones conocidas aplazadas, fuera del objetivo de este experimento.

## Medición fija

`tools.evaluate_tolerance` utiliza las 3132 imágenes de validación (12 posiciones
de origen) de `digital-style-squares-v2`, separando imágenes limpias, marcas sencillas
y flechas. Para cada origen mide estos 14 casos:

- El rectángulo revisado con el preprocesado habitual de producción.
- Desplazamientos horizontales y verticales de -1, +1, -2 y +2 píxeles de entrada.
- Recortes que se contraen o amplían dos píxeles por cada borde.
- Cambios asimétricos de `(1, -2, 2, -1)` píxeles: izquierda/arriba/derecha/abajo.
- Redimensionado del tablero completo al 85% con interpolación bilineal o al 115%
  con bicúbica, seguido de la normalización LANCZOS y la extracción habituales.

Los desplazamientos se miden en píxeles de la captura: el mismo error afecta
proporcionalmente más a un tablero pequeño. Las variantes se generan antes de
dividir las casillas; la vista de negras invierte su orden sin girar las piezas.
Un recorte que sale de la imagen se registra como no aplicable, sin añadir píxeles
ni ajustar sus bordes silenciosamente. Las métricas `applicable` y por tipo de marca excluyen los recortes no aplicables.
La matriz `all` también los registra en la última columna como errores de
procesamiento; hay que separar su cantidad al interpretar la precisión del clasificador.

El informe incluye matrices de confusión por escenario, precisión y sensibilidad
por clase, tableros exactos, tipos de marca y controles correctos que dejan de
funcionar al perturbarlos. Al comparar dos modelos también enumera pérdidas y
ganancias por imagen: unos totales iguales no pueden ocultar regresiones. Los
hashes de datos, modelos y código permiten auditar la comparación. Son mediciones
de validación, no una evaluación final independiente.

## Entrenamiento y selección

`tools.train_tolerance` parte de v8 y conserva sus ejemplos de entrenamiento,
incluidas las variantes auditadas de puntas de flechas. Selecciona por hash aproximadamente una
cuarta parte de las rutas de entrenamiento y añade una perturbación del
tablero completo por origen, con sus 64 etiquetas. La elección es determinista y
no depende de las piezas esperadas ni de los errores del modelo. Solo se aplican
transformaciones que caben en la captura. Cada variante registra el hash de
origen, posición, grupo, partición, orientación, transformación y límites.

Los arrays originales de validación y sus frecuencias no cambian. Un bloque
separado y fijo añade una transformación aplicable por tablero de validación para
seleccionar el modelo. Ningún bloque de validación entra en el entrenamiento;
los arrays de evaluación permanecen sin abrir durante el entrenamiento y la selección. Las comprobaciones existentes de
particiones y grupos también protegen las combinaciones reservadas. Los arrays
preparados se respaldan en disco para limitar el consumo de RAM y se comprueban
sus hashes antes de reutilizarlos.

La configuración fija la semilla, ocho épocas y los parámetros del optimizador.
Los pesos por clase proceden exclusivamente del entrenamiento. La destilación
desde v8 se aplica solo a los ejemplos originales de entrenamiento; los recortes
nuevos utilizan sus etiquetas verificadas. Se selecciona primero por tableros
exactos de la validación original, después por todos los tableros de validación,
sensibilidad media por clase y pérdida. Los puntos de control permiten `--resume`
con los mismos datos y configuración. Terminar el entrenamiento no basta para
recomendar cambiar de modelo.

Una segunda selección compara mezclas fijas de los pesos de v8 y del modelo
entrenado (fracciones entrenadas 0, 0.0625, 0.125, 0.25, 0.5, 0.75 y 1). Descarta cualquier mezcla
que pierda un tablero original correcto de validación o reduzca el total de
casillas originales correctas. Entre las restantes aplica el mismo orden de
validación. El resultado es una sola red normal, sin ejecutar varios modelos
ni aumentar el coste de inferencia. El extremo v8 queda disponible si ninguna
mezcla mejora la tolerancia.

El criterio para recomendar el candidato es conservar los tableros originales
de validación que ya acertaba v8, mejorar la tolerancia por tablero completo, no
empeorar los totales de tableros/casillas en cada tipo de marca y mantener los
casos de desarrollo y regresión que funcionaban. El conjunto final independiente
queda reservado para el posterior paso de aceptación.

## Selección mediante validación

La [selección fijada](../../data/reports/neural-tolerance-candidate.json) elige
`.cache/neural-tolerance-v1-conservative/best.pt`: 87,5 % de los pesos de v8 y
12,5 % de la época 7 del primer entrenamiento. Conserva los 3131 tableros
originales de validación que ya acertaba; en el bloque fijo de perturbaciones
pasa de 2855 a 2906 tableros exactos sobre 3132. Son resultados de selección,
no de aceptación final.

El modelo entrenado sin mezclar perdía un tablero original correcto y se descartó.
También se completó un segundo entrenamiento, con menor tasa de aprendizaje y
mayor peso de destilación, utilizando los mismos datos. Su mejor mezcla admisible
logró 2897 tableros perturbados y no fue elegida. Se conservan los informes del
[primer entrenamiento](../../data/reports/neural-tolerance-v1-training.json),
[selección inicial](../../data/reports/neural-tolerance-v1-selection.json),
[selección conservadora](../../data/reports/neural-tolerance-v1-conservative-selection.json),
[segundo entrenamiento](../../data/reports/neural-tolerance-v2-training.json) y
[segunda selección](../../data/reports/neural-tolerance-v2-selection.json).
Todas las decisiones utilizaron validación antes de ejecutar las regresiones consultadas.

## Verificación completada

El [análisis de las 11 pérdidas](tolerance-regressions.md) identifica una confusión
local de alfil blanco con dama y recomienda conservar este candidato tras descartar
una mezcla más cercana a v8 que sacrificaba 400 aciertos nuevos.

La [comparación completa de validación](../../data/reports/neural-tolerance-validation.json)
cumple el criterio de desarrollo documentado. La tabla cuenta tableros completos
exactos; las variantes perturbadas proceden de las mismas 12 posiciones y no son
posiciones nuevas independientes.

| Medición | v8 | Candidato seleccionado |
| --- | ---: | ---: |
| Rectángulos originales de validación | 3131 / 3132 | 3131 / 3132 |
| Todas las variantes perturbadas aplicables | 36955 / 40236 (91,85 %) | 37618 / 40236 (93,49 %) |
| Desplazamiento horizontal +2 px | 2366 / 3084 | 2513 / 3084 |
| Desplazamiento horizontal -2 px | 2529 / 3084 | 2647 / 3084 |
| Bordes asimétricos | 2381 / 3084 | 2561 / 3084 |
| Contracción de 2 px | 2696 / 3132 | 2790 / 3132 |
| Ampliación de 2 px | 2747 / 3084 | 2796 / 3084 |
| Remuestreo, cada una de las dos variantes | 3131 / 3132 | 3131 / 3132 |

Hay 480 intentos de recorte no aplicables, excluidos de los totales aplicables.
El candidato comete 1506 errores menos de casilla en entradas perturbadas. Gana
674 tableros perturbados exactos, pero pierde 11 que v8 acertaba: mejora neta de
663, **no una mejora universal**. Conserva todos los tableros originales correctos
sin perturbación; cada categoría de imágenes limpias, marcas y flechas mejora
en conjunto. El informe conserva precisión y sensibilidad por clase, matrices
de confusión, todos los escenarios y las pérdidas individuales de la comparación.

Tras fijar el candidato, la [regresión del corpus consultado](../../data/reports/neural-tolerance-regression.json)
conserva 3456/3456 tableros y 221184/221184 casillas para ambos modelos con límites
verificados. Esta medida aísla la clasificación; no afirma haber repetido detección
y recorrido completo sobre las 3456 imágenes. El detector y el preprocesado de
producción no han cambiado. Los [seis fallos originales](../../data/reports/digital-regressions-tolerance.json)
superan las comprobaciones de límites y posición completa con el recorrido real.
Las [15 imágenes de desarrollo](../../data/reports/video-development-v2-tolerance.json)
conservan 13/15 en detección, clasificación con límites revisados y recorrido
completo; solo fallan los vídeos 009/010 aplazados. La CLI sobre el vídeo 002
también devuelve el JSON exacto esperado, código 0 y stderr vacío.

La ejecución completa de pruebas registró 1582 correctas, 36 omitidas y 8 fallos
esperados. Tras añadir el modo opcional de regresión con límites verificados,
la batería específica registró 107 correctas. El [registro de cierre](../../data/reports/neural-tolerance-summary.json)
enlaza las evidencias y sus hashes. El paso 4 queda terminado dentro de este
alcance medido; el siguiente paso aún debe repetir el corpus por el recorrido
completo y fijar el candidato de lanzamiento. No se ha ejecutado la aceptación
final independiente.

## Comandos

Desde la raíz del repositorio, con el extra `ml` instalado y los corpus locales
de capturas y casillas ya disponibles:

```bash
python -m tools.evaluate_tolerance --dataset .cache/digital-style-squares-v2 --model .cache/neural-styles-v8/best.pt --output .cache/tolerance-baseline.json
python -m tools.train_tolerance --dataset .cache/digital-style-squares-v2 --extra-training-dataset .cache/arrowhead-training-squares-v1 --cache .cache/tolerance-data-v1 --baseline .cache/neural-styles-v8/best.pt --run .cache/neural-tolerance-v1
python -m tools.select_tolerance --cache .cache/tolerance-data-v1 --baseline .cache/neural-styles-v8/best.pt --trained .cache/neural-tolerance-v1/best.pt --run .cache/neural-tolerance-v1-conservative
python -m tools.evaluate_tolerance --dataset .cache/digital-style-squares-v2 --model .cache/neural-styles-v8/best.pt --model .cache/neural-tolerance-v1-conservative/best.pt --output .cache/tolerance-comparison.json
python -m tools.evaluate_marks --dataset .cache/digital-style-squares-v2 --baseline .cache/neural-styles-v8/best.pt --candidate .cache/neural-tolerance-v1-conservative/best.pt --baseline-name v8 --candidate-name toleranceCandidate --split evaluation --regression --verified-only --output .cache/tolerance-regression.json
python -m tools.recheck_digital_regressions --model .cache/neural-tolerance-v1-conservative/best.pt --output .cache/tolerance-six-regressions.json
python -m pytest tests/test_bounds_tolerance.py tests/test_training_augmentation.py tests/test_neural.py
```

Los comandos que crean entrenamientos o selecciones requieren carpetas nuevas;
utiliza otro nombre para reproducir un ensayo existente. Añade `--resume` al
comando de entrenamiento para continuar una ejecución interrumpida con su
configuración original. El segundo ensayo utiliza `--config tools/train-tolerance-v2.json`
y las carpetas separadas `neural-tolerance-v2` / `neural-tolerance-v2-selected`.
La comparación de tolerancia devuelve código 1 si no cumple su criterio de validación.

Puedes probar el candidato seleccionado conservando v8 como referencia:

```bash
boardsnap .cache/real-use-tests/real-use-12.png --model .cache/neural-tolerance-v1-conservative/best.pt --orientation black-bottom
```

Conserva v8 y el candidato en carpetas diferentes. Los pesos, arrays preparados y
capturas permanecen en `.cache`, ignorada por Git; las herramientas reproducibles
y los informes medidos pertenecen al repositorio. El experimento no declara
compatibilidad general con vídeos ni aplicaciones móviles, y no permite recuperar
una pieza cuya información distintiva haya desaparecido de la imagen.
