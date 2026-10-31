# Reconocimiento fotográfico automático

[English](../en/photo-pipeline.md) | **Español**

El recorrido fotográfico ya conecta entrada RGB, detección de cuatro esquinas,
corrección de perspectiva, 64 recortes, clasificador neuronal y colocación canónica.
Es experimental y se selecciona expresamente; el recorrido digital sigue siendo
el predeterminado. Durante el reconocimiento no se leen esquinas manuales ni
archivos de anotaciones.

## Probar una fotografía

Con el entorno virtual activado y el modelo fotográfico existente:

```bash
boardsnap ".cache/real-use-tests/mi-foto.jpg" --input-type photo --model .cache/neural-phone-v1/best.pt --orientation white-bottom
```

Usa `black-bottom` cuando corresponda. La orientación describe la vista del tablero,
no quién tiene el turno. El modo fotográfico exige orientación explícita: todavía
no se ha validado la lectura de coordenadas con perspectiva. Rechaza `auto` y
`--profile` como invocaciones inválidas. Si omites `--model`, puede usarse
`BOARDSNAP_MODEL`; no se descarga ni se elige un modelo de la caché automáticamente.
Selecciona expresamente el modelo fotográfico; este trabajo no sustituye al digital.
Se admiten PNG/JPEG con la normalización EXIF existente; convierte HEIC previamente.

Desde Python:

```python
from boardsnap.pipeline import recognize_image

result = recognize_image("foto.jpg", input_type="photo",
                         model=".cache/neural-phone-v1/best.pt",
                         orientation="black-bottom")
```

El éxito sigue conteniendo exclusivamente `piecePlacement`. Los fallos de entrada,
detección y modelo mantienen errores estructurados y código de salida 1. Los
argumentos inválidos producen código 2 y mensajes en stderr; los diagnósticos del
procesamiento tampoco se mezclan con el JSON de stdout. La API Python propaga las
excepciones de cada etapa o `ValueError` para configuraciones inválidas.

## Geometría y preprocesado

`rectify_board` pertenece al núcleo instalable, sin dependencias de herramientas
de desarrollo. Transforma los bordes SI/SD/ID/II en una imagen RGB de 512×512 con
interpolación bilineal de OpenCV, como en el entrenamiento. Rechaza esquinas no
finitas, invertidas, degeneradas o exteriores a la imagen; no rellena casillas
que falten. Conserva la vista y la dirección de los dibujos. Para negras abajo
solo se invierte el **orden de las casillas** clasificadas; no se giran las piezas.

Las pruebas comparan los 64 recortes píxel a píxel con la implementación original
de anotación/exportación, para ambas orientaciones y con perspectiva. No se
modifica el original; la inferencia fotográfica libera sus imágenes y recortes
incluso si falla una etapa.

El [diagnóstico del detector](photo-detection.md) sigue permitiendo ver contornos
y recortes rectificados. Su JSON es distinto del contrato de reconocimiento.

## Validación y límites

El informe es [photo-pipeline-validation-v1.json](../../data/reports/photo-pipeline-validation-v1.json).
Ejecuta las 30 fotos de validación ya consultadas mediante la CLI real y compara
con la clasificación usando esquinas revisadas. Reutiliza el informe geométrico
congelado para comparar recortes, verifica los hashes del detector, manifiesto e
imágenes y exige que coincidan las predicciones de la CLI. Registra los hashes del
modelo y del código. Es validación, no aceptación final independiente; no se ha
reentrenado el modelo.

| Procedencia | Detectadas | Posiciones exactas con esquinas anotadas | Posiciones exactas por CLI |
| --- | ---: | ---: | ---: |
| Chess.com | 10/10 | 3/10 | 5/10 |
| Lichess | 10/10 | 8/10 | 8/10 |
| Vídeos | 7/10 | 8/10 | 6/10 |
| Total | 27/30 | 19/30 | 19/30 |

La igualdad del total no implica que sean los mismos aciertos: los recortes
automáticos recuperan `chesscom-img_5396` y `chesscom-img_5399`; el detector rechaza
`video-img_5406` y `video-img_5407`, cuyas piezas acertaba con esquinas anotadas.
El tercer rechazo, `video-img_5403`, ya tenía errores de clasificación. En las
27 imágenes detectadas no se pierde ninguna posición antes correcta y se ganan
esas dos. No se ha ajustado el detector ni el modelo usando estos resultados.

Con límites anotados acierta 1.871/1.920 casillas (97,45 %). La clasificación
automática acierta 1.697/1.728 (98,21 %) **solo entre las 27 imágenes detectadas**;
los porcentajes tienen conjuntos distintos y no demuestran por sí solos una mejora.
El informe incluye métricas por clase y diferencias de píxeles entre los recortes.

Verificación: 184 pruebas del conjunto de integración y regresión superadas (ocho
pruebas de evaluación excluidas); 48 comprobaciones dirigidas del clasificador y
recorrido fotográfico superadas, y 27 pruebas fotográficas tras completar los
controles de la herramienta de comparación. Estos conjuntos se solapan. También
se comprobó el comando instalado `boardsnap` con una foto y una posición conocida.

Para reproducirlo deliberadamente con una ruta nueva:

```bash
python -m tools.evaluate_photo_pipeline --model .cache/neural-phone-v1/best.pt --output .cache/photo-pipeline-recheck.json
python -m pytest tests/test_photo_pipeline.py tests/test_photo_detection.py tests/test_cli.py tests/test_orientation_input.py tests/test_phone_inference.py tests/test_phone_geometry.py tests/test_phone_squares.py tests/test_cli_process.py -m "not evaluation" -q
```

Detección y clasificación son fuentes de error distintas. Que el comando termine
correctamente no garantiza que todas las piezas sean correctas. Se sigue exigiendo
perspectiva moderada y una cuadrícula completa visible; los reflejos intensos,
oclusiones, distorsiones y algunas fotos de vídeos quedan fuera de la cobertura.
Sigue vigente el [diagnóstico del clasificador](phone-classifier-analysis.md).
Quedan aparte la aceptación final, distribución del modelo e integración con Flutter;
no se ha usado el conjunto final reservado.
