# Primera referencia con PyTorch

[English](../en/neural-classifier.md) | **Español** · [Inicio](README.md)

El paso 6.4 añade un clasificador opcional en CPU y una comparación medida. La CLI
`boardsnap` y `pipeline.recognize_image` siguen utilizando plantillas. La red se
carga expresamente mediante `boardsnap.neural.NeuralClassifier`.

## Alcance y arquitectura

`small-square-cnn-v1` tiene **39709 parámetros**. Recibe recortes RGB de 64 × 64,
convierte uint8 NHWC a float32 NCHW y divide por 255. Aplica una reducción por
promedio de 2×, tres convoluciones 3×3 con paso 2 (8/16/32 canales y ReLU), una
capa oculta de 64 unidades y 13 salidas. Elige la clase de mayor valor; la salida
pública de reconocimiento sigue teniendo exclusivamente `piecePlacement`.

El orden fijo es `empty, P, N, B, R, Q, K, p, n, b, r, q, k`. La casilla vacía se
convierte a `None` para el generador de salida existente. Entrenamiento e inferencia
comparten el preprocesado: no redimensiona implícitamente, no intercambia canales
ni aplica aumentos. La normalización del tablero produce los recortes de 64 × 64.
No necesita pesos preentrenados, Torchvision, GPU ni servicios de red al reconocer.

## Datos y entrenamiento reproducible

El [conjunto de casillas](square-dataset.md) aporta 161280 ejemplos de entrenamiento
con límites verificados y 34560 de validación. El entrenamiento no abre archivos
de evaluación. Se verifican hashes de índices y matrices, etiquetas canónicas y
separación de posiciones/grupos. Se conservan las distribuciones originales y se
usa entropía cruzada ponderada por frecuencia inversa de clase, calculada solo
con entrenamiento. No se aplican los pesos opcionales de muestreo por clase/fondo
del paso 6.3.

La [configuración fijada](../../tools/train-clean-v1.json) usa semilla 20261009,
12 épocas, lotes de 512, AdamW con aprendizaje 0.002, decaimiento 0.0001 y cuatro
hilos de CPU. Cada época mezcla ejemplos con semilla + época. Se activan los
algoritmos deterministas de PyTorch y se fijan semillas de Python, NumPy y PyTorch.

Se selecciona el modelo con más **tableros completos correctos en validación**,
después mayor sensibilidad media por clase y después menor pérdida de validación
sin ponderar. Ante empate exacto se conserva la época anterior. No se elige por
aciertos de entrenamiento ni por evaluación final. La ejecución seleccionó la
época 12. Se fijaron ajustes y duración antes de consultar evaluación y no se
ajustó el modelo posteriormente a sus resultados.

Los checkpoints guardan pesos actuales, optimizador, época, estado aleatorio de
PyTorch, historial de validación y mejores pesos. `last.pt` se reemplaza de forma
atómica al completar cada época. Una interrupción a mitad de época reanuda desde
su inicio. Se rechazan cambios de configuración, datos o entorno al reanudar.
Las pruebas comparan exactamente pesos y validación de ejecuciones continuas y
reanudadas. La reproducibilidad se limita al software/CPU registrado, no a
cualquier versión de PyTorch o equipo. Los tiempos no son deterministas.

Una segunda ejecución completa de 12 épocas sobre el corpus real reprodujo
exactamente todos los pesos seleccionados, las métricas de validación de cada
época e incluso el SHA-256 del archivo guardado. El [registro de reproducción](../../data/reports/neural-clean-v1-reproducibility.json)
fija las dos ejecuciones y su entorno. Es una comprobación de reproducción,
no otra prueba de hiperparámetros.

## Instalación y comandos

Desde la raíz, con el entorno virtual existente. Para esta referencia Linux en
CPU, instala primero la distribución oficial para CPU:

```bash
python -m pip install 'torch==2.14.1' --index-url https://download.pytorch.org/whl/cpu
python -m pip install -e '.[dev,ml]'
python -m tools.train_neural --dataset .cache/digital-square-corpus-v1 --run .cache/neural-clean-v1
# Reanudar la misma ejecución después de una interrupción
python -m tools.train_neural --dataset .cache/digital-square-corpus-v1 --run .cache/neural-clean-v1 --resume
python -m pytest tests/test_neural.py
```

La ejecución completada ya existe localmente. Usa otra carpeta `--run` para una
reproducción independiente. Entrenar/evaluar requiere conservar las capturas y
el conjunto de casillas. Son herramientas del repositorio, separadas de la CLI
instalada de reconocimiento.

Cada ejecución guarda:

| Archivo | Contenido |
| --- | --- |
| `last.pt` | Checkpoint reanudable con optimizador y mejor estado |
| `best.pt` | Pesos seleccionados, arquitectura, clases, tamaño/preprocesado, hashes de datos, configuración y entorno |
| `training.json` | Historial, resultado seleccionado en validación y hash del modelo |

`best.pt` ocupa unos 161 KiB. Permanece en `.cache/`, ignorada por Git: subir código
e informes no distribuye los pesos. Conserva una copia del modelo y su informe.
Siguen aplicándose las condiciones de los datos y recursos originales; esta
referencia experimental no es un lanzamiento ni cambia licencias. No se descargan
modelos automáticamente.

La [guía de guardado de PyTorch](https://docs.pytorch.org/tutorials/beginner/saving_loading_models.html)
describe los diccionarios de pesos y checkpoints del optimizador. Aquí se carga
con `weights_only=True`, destino CPU, validación estricta y `eval()`; se utiliza
`inference_mode()` al reconocer. Un artefacto inválido genera `ClassificationError`
con el código existente `PROCESSING_FAILED`.

## Inferencia explícita en CPU

```python
from boardsnap.neural import NeuralClassifier

model = NeuralClassifier('.cache/neural-clean-v1/best.pt')
result = model.recognize_image('image.png', orientation='black-bottom')
print(result)  # únicamente {"piecePlacement": "..."}
```

Este método lee píxeles, ejecuta detección/normalización/segmentación y ordena las
predicciones según la vista indicada. Admite `white-bottom` y `black-bottom`;
no incorpora lectura automática de coordenadas. La API existente de plantillas
conserva `auto`. `predict_ids` recibe lotes uint8 y `classify_squares` una matriz
8×8 de recortes Pillow. Al reconocer no se consultan etiquetas de entrenamiento,
manifiestos de posiciones ni informes de evaluación.

## Evaluación y comparación

```bash
python -m tools.evaluate_neural --dataset .cache/digital-square-corpus-v1 --model .cache/neural-clean-v1/best.pt --split evaluation --output data/reports/neural-clean-v1-evaluation.json
```

El [informe medido](../../data/reports/neural-clean-v1-evaluation.json) fija hashes
del modelo y datos y recoge precisión, sensibilidad y F1 por clase, matriz de
confusión, tableros completos, posiciones base correctas en todas sus variantes
y resultados por configuración. Separa:

- Clasificación con límites verificados y exactamente los mismos recortes.
- Flujo real de imagen a colocación, leyendo el PNG original y detectando de nuevo.
  Los límites anotados no entran al reconocedor. Los fallos cuentan como tableros
  y casillas incorrectos, sin desaparecer del denominador.
- Subconjunto comparable con plantillas: brown/cburnett, blue/cburnett y green/Neo.
- Combinaciones adicionales, para las que no hay plantillas compatibles.

Ambos métodos acertaron **90/90 tableros completos en el subconjunto compartido**.
La red acertó también **450/450 de las combinaciones adicionales**: 540/540 capturas
y 34560/34560 casillas, tanto con límites verificados como con el flujo completo.
Cada clase obtuvo precisión y sensibilidad de 1.0. Son **12 posiciones base
reservadas, de tres grupos**, renderizadas en muchas variantes; no 540 posiciones
independientes. Los diseños y fondos también aparecen en entrenamiento. No mide
diseños desconocidos, marcas, partidas reales, apps nativas ni diagramas de libros.
Se mantienen los huecos de cobertura compacta documentados en el corpus.

El tiempo de clasificación excluye verificar/cargar los archivos de casillas;
el del flujo incluye lectura de PNG y todas las etapas. Se ofrecen mediana y
percentil 95 del subconjunto compartido por separado. Cada método se ejecuta en
un proceso nuevo. El máximo de memoria RSS incluye importaciones, índice de datos,
modelo y evaluación: **no es solo memoria de los pesos**. Los tiempos dependen
de la carga del equipo; acertar no demuestra cumplir cualquier límite de tiempo
o memoria de despliegue.


En esta CPU Intel Core i5-10400 (cuatro hilos PyTorch y uno OpenCV), las 90 imágenes
compartidas dieron estas mediciones, con modelos y caché de archivos calientes:

| Medición | Red | Plantillas |
| --- | ---: | ---: |
| Mediana de clasificación / tablero | 1.74 ms | 42.49 ms |
| Mediana del flujo completo / imagen | 127.01 ms | 158.19 ms |
| Máximo RSS del proceso de evaluación | 566.1 MiB | 209.0 MiB |

Las plantillas siguen siendo la opción predeterminada. Esta red proporciona una
referencia reproducible para los estilos limpios. Lo siguiente es ampliar pruebas
con capturas reales, resaltados y flechas, y decidir expresamente cómo exponer el
modelo en la CLI principal y en la aplicación.
