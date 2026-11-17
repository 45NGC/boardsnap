# Resultado del ponderado por raíz cuadrada

**Español** | [English](../en/mixed-sqrt-result.md)

**Hay una mejora parcial, pero ninguna época cumple todos los criterios.**
Se conserva phone-v1 como referencia. El nuevo modelo se guarda únicamente como
experimental, sin cambiar la CLI ni los modelos anteriores.

- [Plan fijado antes de ejecutar](../../data/manifests/neural-mixed-sqrt-v1-plan.json).
- [Informe por época, clase, apariencia y casilla](../../data/reports/neural-mixed-sqrt-v1.json).
- [Control: mismo entrenamiento con ponderado inverso](mixed-empty-guard-result.md).

## Qué se probó

Se completó **un único entrenamiento de 12 épocas el 16 de noviembre de 2026**.
Los pesos pasan de `N / (13 * frecuencia)` a `sqrt(N / (13 * frecuencia))`,
calculados exclusivamente con las etiquetas de las mismas 32.000 muestras.
La relación de pesos dama negra/vacía baja de **48,52 a 6,97**. No se buscaron otros
exponentes ni se ajustó la fórmula tras consultar resultados.

La reducción `mean` de CrossEntropyLoss divide por la suma de pesos de las etiquetas
del lote; multiplicar todos los pesos por una constante no cambia esta pérdida.
Por eso no se añadió otra normalización como variable experimental.

El control directo es `neural-mixed-empty-guard-v1`: conserva la exclusión de las
19 exposiciones de vacías con profesor erróneo y las 27.181 muestras restantes con
destilación. No se vuelve a cambiar esa máscara. Todas las casillas conservan la
pérdida supervisada. Datos, particiones, inicialización phone-v1, semilla, red,
preprocesado, optimizador, doce épocas y criterios siguen iguales.
Se reutilizan las cachés existentes, sin repetir la inferencia del profesor ni
reconstruir recortes. La comprobación de datos original permanece intacta; la nueva
fórmula tiene su propia comprobación contra los recuentos de entrenamiento.

## Última época: diagnóstico, no selección de un modelo aceptado

| Medida | phone-v1 | Control inverso con máscara corregida | Raíz cuadrada |
| --- | ---: | ---: | ---: |
| Fotos completas correctas | 19/30 | 20/30 | 20/30 |
| Casillas fotográficas correctas | 1.871/1.920 | 1.877/1.920 | 1.880/1.920 |
| Vacías fotográficas convertidas en piezas | 3 | 8 | 5 |
| Piezas fotográficas omitidas | 26 | 19 | 19 |
| Peones fotográficos omitidos | 19/370 | 13/370 | 13/370 |
| Capturas digitales completas correctas | 3.128/3.132 | 3.128/3.132 | 3.128/3.132 |
| Casillas digitales correctas | 200.444/200.448 | 200.444/200.448 | 200.444/200.448 |

La última época conserva **todas las fotos completas que acertaba phone-v1** y
recupera `video-img_5403`. Todas las predicciones digitales finales coinciden con
phone-v1 y el control. No son nuevas pruebas independientes de generalización.

Frente al control, cambia cinco casillas:

| Imagen y casilla | Cambio | Resultado |
| --- | --- | --- |
| chesscom-img_5397 e3 | caballo negro → vacía | Recuperación |
| lichess-img_5390 d8 | dama negra → vacía | Recuperación; vuelve a acertar la foto completa |
| video-img_5404 e3 | caballo negro → vacía | Recuperación |
| chesscom-img_5401 b2 | torre blanca → peón blanco | Recuperación |
| chesscom-img_5399 f8 | alfil negro → alfil blanco | Regresión frente al control; phone-v1 también fallaba aquí |

Persisten tres regresiones por casilla respecto a phone-v1: `lichess-img_5392`
a7 (peón negro → torre negra) y c5 (vacía → dama negra), y `video-img_5404`
e4 (vacía → rey blanco). Pertenecen a fotos que phone-v1 ya fallaba en otras casillas;
por eso no se pierde ninguna de sus fotos completas.

La época 11 llegó a 21/30 fotos y 1.881 casillas correctas, pero seguía teniendo
cinco piezas falsas y tampoco era admisible. En la época 12 vuelve la confusión de
color del alfil de f8. No se eligió la época 11 ignorando los criterios ni se
reentrenó para recuperar sus pesos: la política solo exporta `best.pt` si es segura.
El informe conserva las predicciones de todas las épocas.

## Peones finos y limitaciones

En las **dos fotos** etiquetadas como `cc-thin-stem` hay 22 peones:

| Medida | phone-v1 | Control | Raíz cuadrada |
| --- | ---: | ---: | ---: |
| Casillas correctas | 105/128 | 112/128 | 113/128 |
| Peones omitidos | 16/22 | 11/22 | 11/22 |
| Peones confundidos con otra pieza/color | 5 | 5 | 4 |
| Fotos completas correctas | 0/2 | 0/2 | 0/2 |

Reducir el contraste de pesos no aumenta las omisiones en estos casos y recupera
un peón confundido con torre. Eso no demuestra cobertura suficiente de ese estilo:
las dos posiciones siguen incorrectas y la muestra es pequeña.

El descenso de piezas falsas es evidencia favorable a esta intervención en la
validación consultada. No demuestra que el ponderado fuera la única causa ni que
la fórmula sea óptima. Tampoco autoriza a buscar más exponentes automáticamente.

## Decisión y siguiente paso

No se sustituyen modelos: siguen fallando el límite de falsas piezas (5 frente a
3), la conservación del acierto de la clase vacía y algunos grupos de condiciones.
Las reglas originales no se relajan. La mejora sí merece conservarse como resultado
experimental; los siguientes pasos no deben volver a partir de cero.

Antes de decidir si usar este candidato como opción experimental de la app,
recomiendo comparar el recorrido completo de CLI con phone-v1 en las capturas y
fotos de desarrollo conocidas. Eso comprobaría si la mejora con esquinas anotadas
se mantiene con detección automática. No equivale a aceptación final ni requiere
otro entrenamiento. Las tres regresiones restantes quedan identificadas para
preparar datos dirigidos posteriormente.

## Artefactos y comprobaciones

En `.cache/neural-mixed-sqrt-v1/` están `last.pt`, `training.json`, `execution.json`,
`mask-audit.json` y las doce predicciones por época. **No hay `best.pt`**.
El punto de control final carga con el lector habitual, pero no es una versión
promovida. Los modelos y planes anteriores conservan sus hashes.

Pasan **28 pruebas dirigidas** de fórmula, aislamiento del cambio, protección del
control, máscara, entrenador/reanudación, criterios y diagnóstico de omisiones.
Los ciclos de entrenamiento y validación suman aproximadamente 94 segundos;
no es un benchmark de inferencia. La comparación usa predicciones guardadas.

**Pendientes:** rendimiento CPU y regresiones completas de CLI para este candidato.
No se ejecutaron las comprobaciones de promoción porque no supera el filtro de
calidad. No se ha consultado la evaluación final independiente.

```bash
# Solo reconstruye el informe desde predicciones guardadas.
python -m tools.report_mixed_sqrt
# Solo para reanudar una interrupción del mismo intento, sin ampliar épocas.
python -m tools.train_mixed_sqrt --resume
```

La [comparación mediante la CLI](mixed-sqrt-cli.md) confirma una mejora de 20 a 22 fotos completas, pero pierde dos capturas digitales reales. El candidato sigue siendo fotográfico experimental.
