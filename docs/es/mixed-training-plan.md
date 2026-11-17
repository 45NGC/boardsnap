# Configuración y aceptación del entrenamiento mixto

El [resultado del entrenamiento mixto](mixed-training-result.md) completa las 12 épocas fijadas. La última conserva las predicciones digitales, pero pierde una foto y aumenta las piezas falsas; se mantiene phone-v1.

**Español** | [English](../en/mixed-training-plan.md)

Plan fijado el **14 de noviembre de 2026**, antes de ejecutar el nuevo entrenamiento.
Su objetivo es mejorar el clasificador fotográfico conservando los aciertos de
`neural-phone-v1`, también sobre capturas. No implica sustituir el modelo digital
conservador ni aceptar una versión final de la aplicación.

- [Plan ejecutable y fuentes congeladas](../../data/manifests/neural-mixed-v1-plan.json).
- [Comprobación previa](../../data/reports/neural-mixed-v1-preflight.json).
- [Preparación de la mezcla](mixed-training.md).

## Configuración del único intento

| Elemento | Valor |
| --- | --- |
| Inicialización | `.cache/neural-phone-v1/best.pt`, con SHA-256 fijado |
| Arquitectura | `small-square-cnn-v1`, sin cambios |
| Entrada | RGB de 64 × 64; `uint8` → NCHW `float32` / 255 |
| Datos | Las 32.000 muestras ya preparadas; 50 % digital y 50 % foto |
| Épocas máximas | 12 |
| Lote | 256 casillas |
| Optimizador | AdamW nuevo, tasa `0.00002`, weight decay `0.0001` |
| Semilla | `20261114` |
| Ejecución | CPU, cuatro hilos, algoritmos deterministas |
| Nuevas transformaciones | Ninguna |
| Remuestreo entre épocas | Ninguno; se baraja la misma muestra con semilla + época |

Se parte del modelo estable, no del candidato descartado. La tasa es menor que
los `0.00005` del intento anterior; junto con el horizonte acotado, busca limitar
cambios bruscos. Esto no garantiza menos errores ni permite atribuir una futura
mejora a un único factor.

La pérdida supervisada conserva la entropía cruzada con frecuencia inversa de
clase, calculada **solo con las 32.000 etiquetas de entrenamiento**. Los recuentos
y los trece pesos exactos están fijados en el plan. No se vuelven a equilibrar
las clases mediante otro muestreo.

Se añade destilación del mismo `phone-v1`, con temperatura 2 y peso 1, sobre
**27.200 muestras antiguas**, incluidas las digitales. Esto amplía el repaso que
faltaba en el ajuste exclusivamente fotográfico. Las **4.800 muestras de las fotos
nuevas** usan únicamente sus etiquetas: no se obliga al modelo a reproducir los
errores anteriores sobre los estilos que queremos aprender. No se utiliza un
segundo profesor ni predicciones de validación como objetivos de entrenamiento.

La cuota de madera antigua repite cinco fotos; existe riesgo de sobreajuste. Las
proporciones, el ritmo de aprendizaje y el horizonte son decisiones iniciales
conservadoras, no parámetros óptimos demostrados.

## Referencias y límites de calidad

Las cifras proceden de predicciones existentes sobre **límites verificados**;
no son resultados del detector ni de la CLI completa.

| Medida | Fotos | Capturas digitales |
| --- | ---: | ---: |
| Tableros de validación | 30 | 3.132 |
| Tableros correctos con la referencia | 19 | 3.128 |
| Casillas correctas con la referencia | 1.871 / 1.920 | 200.444 / 200.448 |
| Vacías convertidas en piezas | 3 | 1 |
| Piezas reales convertidas en vacías | 26 | 0 |

Para superar la parte de precisión, el candidato deberá cumplir **todo** esto:

1. Alcanzar **al menos 20/30 fotos completas correctas** y conservar individualmente
   las 19 anteriores. No basta ganar una foto y perder otra.
2. Conservar individualmente las **3.128 capturas correctas** de `phone-v1`.
3. No bajar del número de casillas correctas de referencia en ninguno de los dos
   dominios; tampoco aumentar las piezas falsas ni las piezas que desaparecen.
4. No reducir los aciertos de ninguna de las 13 clases dentro de cada dominio.
   Como las etiquetas y sus frecuencias permanecen fijas, esto equivale a no bajar
   el recall por clase. Se informarán también precisión y matriz de confusión.
5. No empeorar tableros/casillas correctos ni falsas/ausentes dentro de los grupos
   fijados: plataforma, orientación, condición visual y, en fotos, apariencia y
   fondo; en digital, configuración de piezas/fondo/interfaz/marcas. Las condiciones
   pueden solaparse; sus resultados no se suman.

Son criterios estrictos. Si la mejora exige intercambiar aciertos por errores,
este candidato no se dará por aceptado. Cualquier decisión posterior de cambiar
la política deberá explicarse y registrarse como otra revisión, no hacerse después
de ver resultados para dar por bueno el intento.

## Selección de la época

Después de cada época se medirán ambos conjuntos de validación completos, sin
cambiar sus 64 casillas ni sus distribuciones. Primero se descartan las épocas
que incumplan los límites de conservación anteriores. Entre las restantes se
prioriza, en este orden:

1. Tableros fotográficos completos correctos.
2. Recall medio de las clases fotográficas.
3. Casillas fotográficas correctas.
4. Tableros digitales completos correctos.
5. Casillas digitales correctas.

En empate se conserva la época más temprana. Una época segura que siga en 19/30
puede ser el mejor punto de control, pero **no cumple la mejora necesaria para
promoverse**. Si ninguna época es segura, no se genera un `best.pt` promocionable.
El selector antiguo de `fit` no basta: sumar controles de ambos dominios permitiría
ocultar pérdidas fotográficas entre miles de capturas digitales.

Se guardarán configuración, hashes, pesos, optimizador, estado aleatorio, historial
y estado de selección. Una interrupción se reanuda desde el último punto completo;
no reinicia épocas terminadas ni amplía el máximo de doce. No hay búsqueda automática
de hiperparámetros ni nuevos intentos dentro de este plan.

## Comprobaciones posteriores del candidato seleccionado

Superar precisión **no** autoriza por sí solo sustituir el modelo. También se exige:

- **CPU comparable:** misma máquina, entorno y cuatro hilos; un modelo por proceso,
  una entrada congelada de 64 casillas, 20 calentamientos y 100 mediciones en cada
  uno de tres procesos nuevos por modelo. Se usa la mediana de las tres medianas,
  la mediana de los tres p95 y la mediana del pico RSS de los procesos. Ninguna
  puede superar **1,25 veces** la referencia. Incluye preprocesado/clasificador,
  pero no lectura, detección ni rectificación. El RSS de las comparaciones antiguas,
  que cargaban dos modelos y el corpus, no sirve como referencia de este límite.
- **Recorrido completo:** conservar las posiciones que la referencia ya resolvía
  mediante CLI en los casos de desarrollo/regresión existentes. Mantener detección,
  negativos, orientación, JSON exclusivamente con `piecePlacement`, errores y códigos
  de salida. Reutilizar resultados compatibles; si están obsoletos, comparar ambos
  modelos con el mismo código antes de decidir.
- **Resultados desglosados:** registrar cada casilla cambiada y las ganancias/pérdidas
  por condición. Los aciertos en las 24 fotos entrenadas son diagnósticos de
  entrenamiento, no prueba de generalización.

Si falta evidencia, el estado es pendiente; si falla una condición, se conserva
`phone-v1`. Las imágenes finales independientes permanecen reservadas. Esta validación
ya consultada sirve para seleccionar candidatos, no para declarar aceptada la versión.

## Estado al congelar el plan (registro histórico)

La comprobación previa verifica pesos de referencia, datos, etiquetas, cuotas,
frecuencias de clase, correspondencia de las predicciones guardadas y sus hashes.
No ejecuta inferencia ni entrenamiento. Las pruebas de política cubren pérdidas
ocultas por promedios, clases, condiciones y cambios de etiquetas. Aplicar estas
reglas a las predicciones guardadas del candidato anterior vuelve a rechazarlo por
las dos fotos y nueve capturas perdidas, sin repetir aquella evaluación.

**El plan está preparado; falta conectar el lector mixto y estas reglas al ejecutor
reanudable antes de lanzar el entrenamiento.** Los pesos actuales permanecen intactos.
No existe todavía un nuevo modelo que probar.

```bash
python -m tools.mixed_training_policy
python -m pytest tests/test_mixed_training_policy.py tests/test_mixed_training.py -q
```
