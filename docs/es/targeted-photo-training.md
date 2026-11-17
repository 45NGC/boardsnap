# Entrenamiento fotográfico dirigido

**Español** | [English](../en/targeted-photo-training.md)

El 13 de noviembre de 2026 se completó un entrenamiento acotado. El candidato
está en `.cache/neural-phone-targeted-v1/best.pt`. **Conviene seguir usando
`.cache/neural-phone-v1/best.pt`: el candidato nuevo no se ha aceptado como
sustituto.** Mejora algunas clases, pero pierde tableros fotográficos y digitales
que antes eran correctos.

- [Plan de entrenamiento fijado](../../data/manifests/phone-targeted-training-v1.json).
- [Resultados, métricas por clase y cambios de predicción](../../data/reports/neural-phone-targeted-v1.json).
- [Revisión de parejas, geometría y solapamientos](targeted-photo-intake.md).

## Datos y reproducibilidad

El conjunto `.cache/phone-targeted-training-v1/` contiene **184 tableros de
entrenamiento (11.776 casillas)**: 160 fotos anteriores y las 24 nuevas.
Los **30 tableros de validación (1.920 casillas)** se mantienen intactos: el
checksum de su índice JSONL y todos sus archivos de recortes son idénticos a los
anteriores. Las 16 capturas emparejadas siguen como referencias.

Los ocho grupos nuevos se conservan juntos y se asignan al entrenamiento solo en
este plan derivado. Se preservan el inventario y la exportación originales de
desarrollo. No se encontraron solapamientos, pero los identificadores de origen
desconocidos impiden certificar completamente la independencia entre partidas.
Esta validación ya consultada sirve para desarrollo, no para aceptación final.

Se parte de **phone-v1**, no del experimento robustness-v2 que fue descartado.
Se reutiliza la CNN pequeña, entradas RGB de 64×64 y CPU, con semilla 20261113,
20 épocas, lotes de 256, AdamW con tasa de aprendizaje 0,00005 y regularización
0,0001. Los pesos por clase se calculan únicamente con etiquetas de entrenamiento.
La destilación conserva las predicciones de phone-v1 sobre las 160 fotos antiguas
(temperatura 2, peso 1); no se aplica a las fotos nuevas ni a validación.
No se introdujeron nuevas transformaciones de imágenes en este entrenamiento.

La selección prioriza conservar los 19 tableros de validación que phone-v1 ya
resolvía, después los tableros completos totales, el recall medio por clase y la
pérdida. Se seleccionó la **época 12**, que conserva 17 de esos 19 controles.
`last.pt` guarda la época 20 y el optimizador para reanudaciones; `best.pt` guarda
el candidato seleccionado. Seleccionar una época no significa aceptar el modelo.
El plan y el informe registran hashes de entradas, modelos y código.

## Comparación con phone-v1

Ambos modelos reciben los mismos recortes con geometría revisada para medir la
clasificación por separado.

| Medida | phone-v1 | Candidato dirigido |
| --- | ---: | ---: |
| Fotos de validación completamente correctas | 19/30 | 19/30 |
| Casillas correctas en validación fotográfica | 1.871/1.920 (97,45 %) | 1.873/1.920 (97,55 %) |
| Recall medio por clase en fotos | 94,15 % | 95,55 % |
| Capturas digitales completamente correctas | 3.128/3.132 | 3.119/3.132 |
| Casillas correctas en validación digital | 99,9980 % | 99,9930 % |

Fotos recuperadas: `chesscom-img_5399`, `video-img_5403`.
Fotos que empeoran: `lichess-img_5388`, `lichess-img_5390`.
En capturas digitales se pierden nueve tableros completos y no se recupera ninguno;
el informe contiene sus nombres.

Mejora el reconocimiento de peones, caballos y alfiles negros, entre otras clases,
pero las casillas vacías correctas bajan de **1.185/1.188 a 1.176/1.188**.
Esas piezas inexistentes perjudican el resultado del tablero completo.

En las **24 fotos nuevas de entrenamiento**, el acierto por casilla pasa del
**87,57 % al 97,53 %**, y los tableros completos de **2/24 a 7/24**. Esto mide
aprendizaje sobre ejemplos vistos, no generalización. Por apariencia, los tableros
completos pasan de 0/12 a 2/12 en piezas de peón fino, de 0/6 a 3/6 en piezas
sombreadas y se mantienen en 2/6 en las de rey con corona redondeada.

La mediana de clasificación de 64 casillas, con el modelo cargado, es de unos
**1,4 ms** en esta máquina. Excluye lectura del archivo, detección y rectificación.
El máximo de memoria del proceso fue de unos **333 MiB** en la comparación de
fotos y **1.196 MiB** en la digital: incluye ambos modelos, importaciones,
índices e informes; no representa la memoria del modelo aislado ni requisitos
para un teléfono.

## Comprobaciones y decisión

Han pasado 56 pruebas dirigidas de protección de particiones, exportación,
solapamientos, carga neuronal y reanudación. El modelo anterior conserva su hash.
La CLI completa sobre `position7-IMG_5490.png` terminó con código 0, exclusivamente
`piecePlacement` en stdout y stderr vacío. **La posición resultante fue incorrecta**:
la prueba confirma que se carga y ejecuta el candidato, no que acierte esa foto.

El candidato incumple los criterios de conservación fijados antes de entrenar.
Queda como experimento y phone-v1 sigue siendo la recomendación. Antes de otro
entrenamiento, conviene revisar las piezas falsas en casillas vacías y preparar
la incorporación de ejemplos digitales de **entrenamiento** junto a las fotos.
No deben trasladarse los fallos de validación al entrenamiento. No se ha utilizado
la evaluación final, distribuido pesos ni cambiado el detector o el modelo por
defecto.

## Comandos

El entrenamiento ya está guardado; no hace falta repetirlo para usar el modelo.
Para una prueba explícitamente experimental:

```bash
boardsnap "mi-foto.jpg" --input-type photo --model .cache/neural-phone-targeted-v1/best.pt --orientation white-bottom
```

El comando de entrenamiento usa el plan fijado y rechaza sobrescribir una ejecución:

```bash
python -m tools.train_targeted_photos
```

Ante una interrupción real, `--resume` reutiliza el punto de guardado y comprueba
la configuración. Para reproducirlo por separado se pueden añadir
`--dataset .cache/phone-targeted-training-rebuild --run .cache/neural-phone-targeted-rebuild`.
Se necesitan los manifiestos, informes, arrays y pesos anteriores locales.

```bash
python -m tools.compare_validation --dataset .cache/phone-targeted-training-v1 --baseline .cache/neural-phone-v1/best.pt --candidate .cache/neural-phone-targeted-v1/best.pt --output .cache/phone-targeted-comparison-recheck.json
python -m pytest tests/test_targeted_photo_training.py tests/test_targeted_photo_overlap.py tests/test_targeted_photo_squares.py tests/test_neural.py -q
```

El [diagnóstico de las regresiones](targeted-photo-regressions.md) revisa los once tableros perdidos, sus controles sin marcas y todas las casillas que cambiaron, sin otro entrenamiento.
