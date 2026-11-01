# Calidad prioritaria para la primera versión

[English](../en/photo-quality.md) | **Español**

**Decisión: conservar el candidato digital y foto v1. Ningún cambio experimental
ha superado las comprobaciones para sustituirlos.** Esta revisión termina el
análisis y las pruebas acotadas de mejora; no declara resuelto el paso de calidad
fotográfica ni aceptada la primera versión. No se ha cambiado el reconocimiento
publicado, sus umbrales, las etiquetas o las particiones.

## Qué falla realmente

Se reutilizan las mediciones anteriores de capturas: el candidato digital conserva
3.131/3.132 posiciones de validación con recortes verificados y 29/30 capturas de
uso real por el recorrido completo. Son conjuntos distintos y ya consultados,
no nuevas pruebas independientes. Foto v1 obtiene 3.128/3.132 en esos recortes
 digitalizados: no debe sustituir al candidato digital.

En fotografías, el recorrido completo detecta 27/30 y acierta 19/30 posiciones;
los tres rechazos pertenecen al detector. En los 27 tableros devueltos hay 31
casillas incorrectas. Se priorizan:

1. **Peones y presencia de piezas.** Trece peones negros y cuatro blancos se
   confunden con vacías. `chesscom-img_5401` y `5402` concentran 18/31 errores.
   La [revisión visual del entrenamiento](../../data/reports/photo-training-style-audit-v1.json)
   no encontró el mismo diseño de peones de tallo fino entre las piezas
   representativas de las 160 fotos. Es una carencia de variedad relevante,
   no una prueba de que entrenar más tiempo vaya a resolverla.
2. **Piezas sombreadas y madera.** `5397–5398` suman cinco fallos. Sí existen
   diez fotos de entrenamiento con diseños similares, principalmente sobre
   fondos lisos: hacen falta combinaciones que separen diseño, textura y óptica.
3. **Reyes/damas y diseños redondeados de Lichess.** `5391–5392` suman cinco
   fallos. Hay diseños relacionados en entrenamiento; no afirmamos que falte
   toda la familia ni conocemos aún una única causa.
4. **Vídeos y muaré.** `video-img_5404` tiene dos errores de piezas; `5403`,
   `5406` y `5407` son rechazos geométricos. Cambiar el clasificador no corrige
   por sí solo esos rechazos.
5. **Flechas y resaltados.** En fotos, las posiciones completas correctas son
   9/12 con flechas y 17/26 con resaltados. Los grupos se solapan y contienen
   estilos y fallos geométricos diferentes: no se atribuye todo a las marcas.
   El único fallo de `5395` coincide con varias flechas sobre un peón.

Los 40 primeros ejemplos directos de Chess.com repiten una apariencia convencional;
55 fotos de esa plataforma no equivalen a 55 diseños diferentes. La auditoría
inspecciona peones, caballos y reyes representativos; no identifica temas oficiales
ni sustituye una revisión exhaustiva de cada pieza.

## Mejoras probadas y descartadas

Antes de sustituir nada se exigió ganar posiciones completas, conservar **cada**
posición antes correcta y no aumentar los errores de casilla. Se compararon
esquinas anotadas y automáticas, conservando las mismas imágenes y pesos.

| Prueba | Anotadas: exactas / errores de casilla | Automáticas: exactas / errores de casilla | Decisión |
| --- | --- | --- | --- |
| Referencia | 19/30 · 49 | 19/27 · 31 | Conservar |
| Rectificar a 1024 y reducir por área | 19/30 · 47 | 20/27 · 31 | Pierde dos posiciones anotadas |
| Rectificar a 2048 y reducir por área | 19/30 · 47 | 20/27 · 33 | Pierde dos y aumenta errores automáticos |
| Promediar logits original + 1024 | 19/30 · 47 | 20/27 · 29 | Pierde una posición anotada |

La mejora sobre `video-img_5404` no basta para activar un filtro general. El
promedio también pierde `video-img_5406` con esquinas correctas; no se introducen
reglas por nombre, posición esperada o tema para esconder esa regresión.
Las tres alternativas figuran en el [informe de remuestreo](../../data/reports/photo-resampling-validation-v1.json).

Después se ejecutó **un solo entrenamiento acotado de 12 épocas**, iniciado desde
foto v1, con una variante suave por tablero de entrenamiento: iluminación,
contraste, desenfoque leve e interferencia sinusoidal de baja amplitud. No es un
simulador físico de cámara. Las etiquetas, grupos y validación no se modificaron;
las predicciones del modelo anterior se conservaron como referencia mediante
destilación sobre los ejemplos originales de entrenamiento.

El candidato seleccionado de ese experimento acierta 19/30, pero baja de
1.871 a 1.864 casillas correctas y conserva solo 17 de las 19 posiciones antes
exactas. Pierde `lichess-img_5388` y `5390`. **Se rechaza**;
`.cache/neural-phone-robustness-v2/best.pt` es un experimento fallido, no el nuevo
modelo recomendado. No se justifica otra ronda con los mismos datos. Los pesos
anteriores permanecen intactos y no se tocó la evaluación final reservada.

## Qué recoger ahora y qué queda fuera

El siguiente paso útil es un lote dirigido, no otro lote grande indiscriminado:

- Primero, unas **8–12 fotos de entrenamiento** con el diseño de peones de
  `5401–5402`, desde al menos tres partidas o posiciones independientes. Incluir
  ambos colores de pieza, ambos fondos de casilla, vacías y dos fondos de tablero.
- Después, unas **6–8 fotos** de piezas sombreadas sobre madera y de los diseños
  Lichess que fallan, priorizando las combinaciones ausentes. Esta cantidad es
  orientativa, no garantía de precisión.
- Guardar una captura directa y su colocación para cada posición. Para estudiar
  muaré, repetir algunas posiciones a dos distancias/ángulos. Todas las variantes
  y posiciones de una partida siguen juntas; recoger además algunas partidas
  distintas para validación antes de entrenar. No mover las 30 fotos actuales.
- Fotografías con reflejos intensos que ocultan piezas, desenfoque fuerte, grandes
  recortes o perspectiva extrema pueden quedar fuera de esta primera versión.
  No hay mediciones que permitan declarar tolerancia general a reflejos o enfoque.

El criterio sigue siendo conservar los aciertos anteriores, mejorar las clases
prioritarias y medir posiciones completas por condición. El piloto actual permite
probar fotos con cuadrícula completa y perspectiva moderada, pero no promete
compatibilidad general con todos los estilos ni con cualquier foto de un vídeo.
La evidencia de fotos proviene del mismo dispositivo y contiene partidas relacionadas.

## Herramientas y verificación

El [informe conjunto](../../data/reports/photo-quality-review-v1.json) registra
confusiones por casilla, resultados por condición, referencias digitales, hashes,
historial del entrenamiento y rechazo del candidato. Las pruebas cubren cambios
de partición, transformaciones reproducibles, orden de casillas y el rechazo de
un candidato que gana tantas posiciones como pierde. Pasan 81 pruebas dirigidas.
No fue necesario repetir la evaluación digital completa: no cambian su código ni
sus pesos; sus cifras anteriores se identifican como mediciones reutilizadas.

Para volver a generar informes, usa rutas nuevas. No hace falta repetir ahora:

```bash
python -m tools.evaluate_photo_resampling --output .cache/photo-resampling-recheck.json
python -m tools.review_photo_quality --output .cache/photo-quality-recheck.json
python -m pytest tests/test_phone_robustness.py tests/test_photo_pipeline.py tests/test_cli.py tests/test_orientation_input.py -q
```

`tools.train_phone_robustness` conserva la receta del experimento descartado para
reproducibilidad y exige un directorio nuevo. No promueve ni configura modelos.
Para seguir probando fotos, conserva el comando existente:

```bash
boardsnap "mi-foto.jpg" --input-type photo --model .cache/neural-phone-v1/best.pt --orientation white-bottom
```
