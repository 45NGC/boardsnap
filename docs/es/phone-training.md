# Primer clasificador fotográfico

[English](../en/phone-training.md) | **Español**

El primer entrenamiento fotográfico está terminado. Los pesos experimentales son
`.cache/neural-phone-v1/best.pt`. **No sustituyen** al candidato digital
`.cache/neural-tolerance-v1-conservative/best.pt`; v8 tampoco se ha modificado.
Este entrenamiento no implementa la detección automática con perspectiva.

## Datos y selección

Se reutilizó el [conjunto revisado](phone-training-data.md): 160 fotos para
entrenamiento (10.240 casillas) y 30 para validación (1.920 casillas). No se
repitieron recortes ni se cambiaron particiones. No se accedió a la evaluación
final. La separación de procedencias conserva la confirmación del usuario y las
limitaciones documentadas. No aparecen familias de posiciones compartidas entre
entrenamiento fotográfico y validación digital, ni entre validación fotográfica y
entrenamiento digital, en digital-style-squares-v2. Eso no demuestra independencia
de las procedencias desconocidas.

Se partió del candidato de tolerancia con el entrenador determinista existente
en CPU y un optimizador AdamW nuevo. La [configuración](../../tools/train-phone-v1.json)
fija semilla 20261030, 20 épocas, lotes de 256, tasa de aprendizaje 0,0001,
regularización 0,0001 y cuatro hilos. Los pesos de clases se calculan únicamente
con entrenamiento. Este primer piloto utiliza solo fotos, sin aumentos ni mezcla
de ejemplos digitales durante el entrenamiento.

La selección prioriza tableros completos correctos en validación, después
recuperación media por clase y pérdida. **Se seleccionó la época 1**: las
posteriores no mejoraron. `best.pt` contiene ese estado; `last.pt` sirve para
reanudar, no es el modelo que debes utilizar. Estos resultados no justifican
simplemente añadir más épocas.

## Resultados medidos

Ambos modelos reciben los mismos recortes con límites revisados. Se mide
clasificación, **no detección automática de fotografías completas**.

| Validación | Referencia digital | Foto v1 |
| --- | ---: | ---: |
| Fotos: tableros completos correctos | 18/30 | 19/30 |
| Fotos: casillas correctas | 1.863/1.920 (97,03 %) | 1.871/1.920 (97,45 %) |
| Digital: tableros completos correctos | 3.131/3.132 | 3.128/3.132 |
| Digital: casillas correctas | 200.447/200.448 | 200.444/200.448 |

Foto v1 recupera `chesscom-img_5400` y conserva todas las fotos que antes eran
correctas. Todavía falla en 11 posiciones completas: siete de Chess.com, dos de
Lichess y dos de vídeos. Los aciertos por categoría son 3/10, 8/10 y 8/10.
Empeoran tres tableros digitales: dos variantes limpias Chess.com bases/brown y
una variante Lichess staunty/brown con flechas combinadas. La mejora fotográfica
no justifica sustituir globalmente el modelo digital.

El [informe versionado](../../data/reports/neural-phone-v1.json) conserva historial,
hashes, precisión y recuperación por clase, matrices de confusión, resultados por
categoría/condición, ganancias/pérdidas y las 49 casillas fotográficas incorrectas.
Los registros completos están en
`.cache/neural-phone-v1/{phone,digital}-validation.json`. No se tomaron decisiones
consultando la evaluación final reservada.

En esta CPU, la mediana de clasificación de 64 casillas con el modelo cargado fue
aproximadamente 1,41 ms en fotos y 1,59 ms en recortes digitales. No incluye lectura,
rectificación ni detección. El máximo de memoria del proceso comparativo fue de
unos 330 MiB y 1.196 MiB: incluye ambos modelos, importaciones e índices; no es
la memoria del modelo aislado ni una medición en un teléfono móvil.

## Probar una imagen nueva

Desde la raíz del repositorio y con `.venv` activado, puedes seleccionar el modelo
experimental en la CLI existente:

```bash
boardsnap "mi-foto.jpg" --model .cache/neural-phone-v1/best.pt --orientation white-bottom
```

Este comando sigue utilizando el **detector digital**. Si devuelve
`BOARD_NOT_FOUND` con una foto inclinada, no habrá llegado a probar el clasificador.
Utiliza PNG/JPEG; convierte HEIC a JPEG previamente. Cambia a `black-bottom`
cuando las negras estén abajo.

Para probar las piezas independientemente del detector, utiliza la herramienta
de desarrollo con cuatro esquinas manuales, medidas sobre la imagen completa
después de aplicar la orientación EXIF:

```bash
python -m tools.recognize_photo "mi-foto.jpg" --model .cache/neural-phone-v1/best.pt --orientation white-bottom --corners 120 80 900 100 920 880 100 900
```

**Esas coordenadas son un ejemplo: sustituye los ocho números por los de tu foto.**
Orden: superior izquierda, superior derecha, inferior derecha e inferior izquierda,
cada punto como x y. Marca los límites de la cuadrícula, excluyendo marco y
coordenadas. La herramienta corrige la perspectiva y aplica el mismo preprocesado
del entrenamiento. No busca las esquinas ni consulta etiquetas.

También puedes proporcionar un tablero cuadrado ya rectificado y sin márgenes:

```bash
python -m tools.recognize_photo "tablero-rectificado.png" --model .cache/neural-phone-v1/best.pt --orientation white-bottom --rectified
```

Recortar una región cuadrada de una foto inclinada no equivale a rectificarla.
Esta opción presupone que la imagen contiene exactamente la cuadrícula completa,
con al menos 128 píxeles por lado. Ambos modos devuelven solo `piecePlacement` o
errores estructurados de entrada/modelo/geometría. Código de salida: 0 si procesa,
1 ante esos errores y 2 si la invocación es inválida.

## Reproducción y siguientes pasos

El entrenamiento ya está terminado; no lo repitas para utilizar el modelo. Para
reproducirlo deliberadamente, elige una carpeta nueva:

```bash
python -m tools.train_neural --dataset .cache/phone-training-v1 --run .cache/neural-phone-v1-reproduction --config tools/train-phone-v1.json --initialize-from .cache/neural-tolerance-v1-conservative/best.pt
python -m tools.compare_validation --dataset .cache/phone-training-v1 --baseline .cache/neural-tolerance-v1-conservative/best.pt --candidate .cache/neural-phone-v1/best.pt --output .cache/phone-validation-recheck.json
python -m tools.compare_validation --dataset .cache/digital-style-squares-v2 --baseline .cache/neural-tolerance-v1-conservative/best.pt --candidate .cache/neural-phone-v1/best.pt --output .cache/digital-validation-recheck.json
python -m pytest tests/test_phone_inference.py tests/test_neural.py tests/test_phone_training_dataset.py tests/test_phone_squares.py tests/test_phone_geometry.py -q
```

Pasan las 71 pruebas dirigidas y la inferencia con esquinas manuales coincide con
posiciones conocidas al ejecutar la CLI en ambas orientaciones. El siguiente paso
es revisar los estilos fotográficos que fallan y estudiar una mezcla auditada con
datos digitales antes de buscar un sustituto común. Quedan pendientes la
localización automática en fotos y la aceptación final independiente. Las nuevas
pruebas inspeccionadas se conservarán como material de desarrollo.
