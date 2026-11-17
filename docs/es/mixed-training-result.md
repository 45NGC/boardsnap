# Resultado del entrenamiento mixto

**Español** | [English](../en/mixed-training-result.md)

**El intento terminó sus 12 épocas y se rechaza para sustitución. Se conserva
`.cache/neural-phone-v1/best.pt`.** No se ampliaron las épocas ni se modificaron
las cuotas, los umbrales o el conjunto de validación después de ver resultados.

- [Plan congelado](mixed-training-plan.md).
- [Informe con historial, clases, condiciones y casillas cambiadas](../../data/reports/neural-mixed-v1.json).
- [Historial local completo](../../.cache/neural-mixed-v1/training.json).

## Qué se implementó y ejecutó

`tools/train_mixed.py` conecta el lector del conjunto mixto, la destilación de las
27.200 muestras antiguas y las reglas de selección por dominio y condición.
Las 4.800 muestras nuevas se aprenden con sus etiquetas. Se reutiliza la muestra
fija de 32.000 casillas y el preprocesado original, sin nuevas transformaciones.

Se ejecutó **un único entrenamiento real de doce épocas**, con un total de
aproximadamente 87 segundos en sus ciclos de entrenamiento y validación. La
preparación de cachés y las comprobaciones de archivos quedan fuera de esa cifra.
Las pruebas del ejecutor utilizan datos sintéticos pequeños; no son experimentos
adicionales sobre el corpus real.

La validación se procesa por lotes desde una caché en disco de los mismos recortes
verificados; no se vuelve a detectar ni recortar el tablero y no se abren imágenes
finales reservadas. El profesor también tiene una caché, limitada a entrenamiento.

Cada época completa guarda predicciones, diagnóstico de aceptación, pesos,
optimizador, estado aleatorio e historial. La reanudación exige la misma receta,
datos, código y entorno, y reutiliza las cachés comprobadas por hash. Ninguna época
cumplió todos los límites, por lo que **no se generó `best.pt`**.

## Resultado de la última época: diagnóstico, no selección

Las últimas tres épocas llegan a 20/30 fotos y 3.128/3.132 capturas, pero no pasan
los límites de conservación. La tabla describe específicamente la época 12:

| Medida | `phone-v1` | Época 12 |
| --- | ---: | ---: |
| Fotos completas correctas | 19/30 | 20/30 |
| Casillas fotográficas correctas | 1.871/1.920 | 1.877/1.920 |
| Vacías fotográficas convertidas en piezas | 3 | 8 |
| Piezas fotográficas convertidas en vacías | 26 | 19 |
| Capturas digitales completas correctas | 3.128/3.132 | 3.128/3.132 |
| Casillas digitales correctas | 200.444/200.448 | 200.444/200.448 |

En la época 12 **todas las predicciones digitales coinciden con la referencia**,
incluidos sus cuatro errores. Se conservaron los aciertos digitales, pero no todos
los fotográficos:

- Se recuperan `chesscom-img_5399` y `video-img_5403` completas.
- Se pierde `lichess-img_5390`: d8 vacía vuelve a clasificarse como dama negra.
- Aparecen otras piezas falsas en imágenes que ya tenían errores:
  `chesscom-img_5397` e3 → caballo negro; `lichess-img_5392` c5 → dama negra;
  `video-img_5404` e4 → rey blanco y e3 → caballo negro.
- También empeora a7 de `lichess-img_5392`: peón negro → torre negra.
- Se recuperan varias piezas de las fotos de peones finos `5401` y `5402`, sin
  llegar a resolver sus posiciones completas. El informe conserva cada casilla.

Por eso no basta el aumento neto de una foto correcta: se ganan dos pero se pierde
una anteriormente resuelta. Las falsas piezas aumentan, baja el recall de vacías
y empeoran grupos fotográficos. El candidato no supera la política fijada.

## Qué queda guardado

En `.cache/neural-mixed-v1/`:

- `execution.json`: hashes de plan, ejecutor, referencia, datos y entorno.
- `last.pt`: punto de control completo de la época 12, **solo para diagnóstico o
  trazabilidad; no es un modelo recomendado**.
- `epoch-001-validation.json` … `epoch-012-validation.json`: predicciones completas
  y reglas comprobadas tras cada época.
- `training.json`: historial y decisión de conservar la referencia.
- Cachés de validación y objetivos del profesor con sus comprobaciones de integridad.

Los datos, modelos de referencia, clasificador digital conservador y plan originales
permanecen intactos. No se cambia el comportamiento de la CLI ni su configuración.

## Verificación y decisión

Pasan **26 pruebas dirigidas**, incluyendo cuotas/particiones, límites de aceptación,
selección solo de épocas admisibles, conservación del primer empate, máscaras del
profesor, reutilización de cachés y reanudación equivalente a ejecución continua.
También se comprueba que reanudar una ejecución completa no repite épocas y que
el punto de control real puede cargarse con el formato del clasificador.

**CPU y regresiones completas de CLI no se ejecutaron para promocionar este intento**:
ninguna época pasó el filtro previo de calidad. No están aprobadas ni se consideran
necesarias para justificar el rechazo. La evaluación final independiente sigue
sin utilizarse. Los 30 tableros fotográficos son validación ya consultada, no una
nueva estimación independiente de generalización.

El siguiente trabajo útil es revisar la separación entre vacía y pieza sobre
texturas/muaré, reutilizando estas predicciones y los datos de entrenamiento. La
mezcla conserva los aciertos digitales al final del intento, pero no resuelve por
sí sola esa confusión fotográfica. No recomiendo prolongar este entrenamiento ni
iniciar otro sin un diagnóstico concreto. Para seguir usando BoardSnap, conserva
el comando habitual con `--model .cache/neural-phone-v1/best.pt`.

Comandos de mantenimiento, no de inicio de otro experimento:

```bash
# Solo si una ejecución idéntica se hubiera interrumpido; una completa no se prolonga.
python -m tools.train_mixed --resume
# Rehacer el resumen a partir de predicciones guardadas, sin inferencia.
python -m tools.report_mixed_training
python -m pytest tests/test_train_mixed.py tests/test_mixed_training_policy.py tests/test_mixed_training.py -q
```

La [revisión acotada del entrenamiento mixto](mixed-training-review.md) identifica objetivos de destilación contradictorios en vacías verificadas y propone una prueba con un único cambio. No se ha iniciado otro entrenamiento.
