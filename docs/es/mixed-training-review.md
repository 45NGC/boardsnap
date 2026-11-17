# Revisión acotada del entrenamiento mixto

**Español** | [English](../en/mixed-training-review.md)

La [prueba de excluir la imitación de piezas falsas en vacías](mixed-empty-guard-result.md) ha terminado: no mejora las predicciones finales del intento mixto. Se conserva phone-v1; no se inicia otro entrenamiento.

**Mantener `neural-phone-v1`. Hay una intervención concreta que merece una prueba
posterior: no conservar mediante destilación las piezas falsas del profesor sobre
vacías de entrenamiento verificadas. No se ha ejecutado esa prueba ni otro entrenamiento.**

Se reutilizaron las predicciones de las doce épocas, los objetivos del profesor
almacenados y los recortes existentes. No hubo inferencia nueva, cambios de pesos,
detector, preprocesado, particiones ni consulta de evaluación final.

- [Informe reproducible](../../data/reports/mixed-training-review-v1.json).
- [Galería local: fallos de validación y vacías de entrenamiento](../../.cache/mixed-review-v1/index.html).
- [Resultado del intento](mixed-training-result.md).

## Qué empeora y qué tienen en común los fallos

En la última época hay **12 casillas recuperadas, seis regresiones y dos cambios
entre clases incorrectas**. Las predicciones digitales coinciden íntegramente con
phone-v1. Las seis regresiones fotográficas están en cuatro imágenes:

| Foto | Casilla | Esperado → candidato | Revisión visual del recorte |
| --- | --- | --- | --- |
| chesscom-img_5397 | e3 | vacía → caballo negro | Madera oscura, muaré y pequeños fragmentos de flecha en las esquinas izquierdas |
| lichess-img_5390 | d8 | vacía → dama negra | Madera oscura con vetas/bandas; sin marca dentro de la casilla |
| lichess-img_5392 | c5 | vacía → dama negra | Madera oscura con bandas diagonales; sin pieza ni marca |
| lichess-img_5392 | a7 | peón negro → torre negra | Peón sombreado completo y centrado; cabeza, collar y base visibles |
| video-img_5404 | e4 | vacía → rey blanco | Fondo claro con interferencia de pantalla intensa y coloreada |
| video-img_5404 | e3 | vacía → caballo negro | Fondo verde oscuro con patrón periódico intenso |

Las cinco nuevas piezas falsas aparecen **desde la primera época y persisten en
las doce**. El cambio de peón a torre aparece en la segunda. Prolongar el mismo
entrenamiento no tiene una mejora observada que lo justifique. Los errores afectan
a varias clases, aunque domina la separación entre fondo y pieza.

## ¿Hay problemas de recorte o etiquetas?

Los modelos se compararon sobre los mismos archivos de casillas, obtenidos con
cuatro esquinas anotadas, no con detección automática. El análisis verifica hashes
y correspondencia de etiquetas; la galería reconstruye esos recortes sin cambiarlos.

La inspección de los cuatro tableros no muestra filas intercambiadas, piezas
cortadas por la división ni piezas vecinas que expliquen esas cinco vacías. En e3
de Chess.com hay una pequeña línea en el borde inferior y fragmentos de flecha;
no equivalen a un caballo. En a7 el peón conserva su silueta dentro de su casilla.
**No hay evidencia aquí para cambiar la geometría o la orientación.** Esto no es
una evaluación nueva del detector ni demuestra que cada límite sea perfecto.

La textura y la interferencia sí son visibles. No se ha separado causalmente
madera, muaré, reducción a 64×64 y superposiciones. Desenfocar indiscriminadamente
podría borrar peones finos; no se recomienda introducir un filtro sin una prueba
controlada que incluya piezas reales.

## No faltan vacías en general; hay una contradicción en su aprendizaje

La muestra fija contiene **19.409 vacías de 32.000 casillas (60,65 %)**. El repaso
fotográfico incluye:

| Grupo | Muestras vacías | Casillas vacías distintas por foto/casilla | Fotos muestreadas |
| --- | ---: | ---: | ---: |
| Fotos antiguas sin grupo específico de madera | 5.873 | 5.802 | 155 |
| Fotos antiguas de madera | 970 | 194 | 5 |
| Fotos nuevas dirigidas | 2.720 | 867 | 24 |

Repetir una casilla no añade diversidad: las 970 vacías de madera son 194 casillas
muestreadas cinco veces. Los nombres de los grupos no clasifican todas las texturas
ni anotan las marcas a nivel de casilla. Hay material parecido a los fallos, pero
estos recuentos no demuestran cobertura suficiente de todas las interferencias.

El profesor es phone-v1. La destilación intenta conservar su distribución de
predicciones además de aprender la etiqueta correcta. En los objetivos guardados:

- **71 de 27.200 exposiciones** del profesor contradicen la etiqueta; son 59
  casillas distintas, todas fotográficas. No hay discrepancias en las 16.000
  muestras digitales seleccionadas.
- **19 exposiciones corresponden a siete vacías** que el profesor trata como
  piezas. Se revisaron visualmente las siete y la etiqueta vacía es coherente.
- En madera, `lichess-photo-42` d8 y `lichess-photo-44` d8 se predicen como dama
  negra; `lichess-photo-44` e8 como rey blanco. Cada una aparece cinco veces.
  Los recortes de d8 contienen vetas/bandas parecidas al fallo de validación d8.
- Las otras cuatro son `lichess-photo-39` e5, `video-photo-45` d6,
  `chesscom-photo-38` d6 y `video-photo-39` d4: fondos con interferencia, una vez
  cada una. El informe conserva la predicción, ruta y probabilidad a temperatura 2.

**Esto no significa que se hayan cambiado las etiquetas a piezas.** La pérdida
supervisada sigue enseñando «vacía», pero el término de conservación se opone a
alejarse de una distribución errónea. En el estado inicial la destilación tiene
pérdida cero porque profesor y alumno coinciden; el conflicto aparece al intentar
corregir esa distribución. Es una contradicción de objetivos comprobable, no una
prueba causal de que explique las seis regresiones. Las otras 52 casillas de
conflicto no vacías no se han vuelto a revisar visualmente en este análisis.

También hay un equilibrio que conviene vigilar: los pesos inversos de frecuencia
dan a vacía aproximadamente el **7,69 % de la suma nominal de pesos**, aunque sea
el 60,65 % de los ejemplos; una etiqueta de dama negra pesa 48,52 veces más por
muestra. Es intencional para proteger clases raras. No son magnitudes de gradiente
medidas: influyen la normalización por lote y la destilación. No basta para afirmar
que el ponderado es incorrecto ni para cambiarlo a la vez que otra variable.

## Intervención propuesta en esta revisión (ejecutada posteriormente)

1. Conservar la receta, muestra de 32.000 casillas, semilla, pesos de clases,
   particiones, 12 épocas y referencia inicial phone-v1 del intento anterior.
2. Cambiar únicamente la máscara de destilación con una regla general:
   `old_teacher_mask & ~((label == empty) & (teacher_argmax != empty))`.
   Se aplica a entrenamiento, nunca a nombres o resultados de validación.
3. Mantener la pérdida supervisada sobre **todas** las casillas. En esta muestra se
   excluyen de imitación 19 exposiciones (siete vacías verificadas), quedando
   **27.181**. No se eliminan imágenes, etiquetas ni los ejemplos con piezas finas;
   tampoco se altera la imitación digital. Los otros conflictos quedan intactos
   para aislar este único cambio.
4. Antes de ejecutar, fijar un nuevo plan y directorio; conservar el intento mixto
   anterior como control. Reutilizar sus datos y objetivos guardados; no continuar
   desde los pesos rechazados de la época 12.
5. Comparar las mismas validaciones completas: piezas falsas y omitidas, clases,
   fotos exactas, aciertos digitales y pérdidas individuales. Una mejora útil debe
   reducir las falsas piezas frente a las ocho del intento mixto sin sacrificar
   sus recuperaciones. Eso **no equivale a aceptación**: para sustituir phone-v1
   siguen vigentes los criterios originales (incluidos no perder sus aciertos,
   no superar sus tres falsas piezas y mejorar las fotos completas).
6. Si el cambio no ayuda, detener esa hipótesis. No repetir semillas, ampliar
   épocas o bajar umbrales después de ver el resultado. Entonces decidir, mediante
   un nuevo plan, entre datos negativos más diversos o revisar el equilibrio de
   la pérdida; no cambiar ambas cosas a ciegas.

**No pediría más fotos todavía ni cambiaría la arquitectura.** La referencia ya
resolvía estas seis casillas; no se ha demostrado una falta de capacidad de la red.
El ajuste propuesto es pequeño y medible, pero puede ser insuficiente: afecta a
solo el 0,07 % de las exposiciones del profesor y no aborda directamente el peón
confundido con torre. No promete alcanzar el umbral ni recuperar todas las fotos.

La procedencia antigua sigue parcialmente desconocida; posiciones diferentes no
prueban partidas independientes. La validación ya consultada sigue siendo material
de selección, y no sustituye la evaluación final independiente.

## Reproducción

```bash
python -m tools.review_mixed_training
python -m pytest tests/test_mixed_training_review.py -q
```

Pasan cuatro pruebas del análisis: repetición frente a identidad, exclusión de
objetivos nuevos sin profesor, rechazo de validación, coherencia de objetivos
repetidos y correspondencia de etiquetas. Se ha ejecutado el análisis real contra
los artefactos guardados. Esta revisión no cambia el entrenador ni los modelos.
