# Resultado de excluir la imitación de piezas falsas en vacías

**Español** | [English](../en/mixed-empty-guard-result.md)

**El cambio no mejora la validación. Se mantiene `.cache/neural-phone-v1/best.pt`.**
Se completó un único intento de 12 épocas el 16 de noviembre de 2026. Ninguna
época supera los criterios y no se exporta `best.pt`.

- [Plan congelado antes de ejecutar](../../data/manifests/neural-mixed-empty-guard-v1-plan.json).
- [Informe completo y comparación por época/casilla](../../data/reports/neural-mixed-empty-guard-v1.json).
- [Diagnóstico que motivó la prueba](mixed-training-review.md).
- [Intento mixto utilizado como control](mixed-training-result.md).

## Único cambio experimental

Se reutilizan la muestra fija de 32.000 casillas, sus etiquetas y particiones,
los objetivos guardados del profesor, los recortes de validación, phone-v1 como
inicialización, semilla, arquitectura, preprocesado, pesos de clases, optimizador,
12 épocas y criterios de selección. No se continúa desde el modelo rechazado.

La nueva máscara aplica una regla general basada solo en etiquetas de entrenamiento:

```python
old_teacher_mask & ~((label == empty) & (teacher_argmax != empty))
```

Se excluyen de la **imitación**, no del aprendizaje supervisado, las 19 exposiciones
de siete casillas vacías verificadas. Quedan 27.181 muestras con destilación y
4.819 únicamente supervisadas; las 32.000 conservan su etiqueta y pérdida
supervisada. El plan conserva los recuentos originales del conjunto de objetivos
del profesor en `loss`; los efectivos están en `intervention` y `mask-audit.json`.
No se excluyen los otros conflictos sobre piezas ocupadas ni se cambia el repaso
digital. El promedio del término de destilación se calcula sobre su nueva máscara,
como en el ejecutor original.

Se reutiliza sin modificar `run_epochs`, con sus comprobaciones por dominio y
condición, selección de épocas seguras y reanudación. El nuevo ejecutor verifica
que la receta científica no tenga otro cambio y que los excluidos coincidan con
las vacías revisadas. No contiene reglas por nombre de foto de validación.

## Resultado de la última época

La última época es un diagnóstico; **no es una selección de modelo aceptado**.

| Medida | phone-v1 | Mixto anterior | Mixto con nueva máscara |
| --- | ---: | ---: | ---: |
| Fotos completas correctas | 19/30 | 20/30 | 20/30 |
| Casillas fotográficas correctas | 1.871/1.920 | 1.877/1.920 | 1.877/1.920 |
| Vacías fotográficas convertidas en piezas | 3 | 8 | 8 |
| Piezas fotográficas convertidas en vacías | 26 | 19 | 19 |
| Capturas digitales completas correctas | 3.128/3.132 | 3.128/3.132 | 3.128/3.132 |
| Casillas digitales correctas | 200.444/200.448 | 200.444/200.448 | 200.444/200.448 |

Las **202.368 predicciones finales coinciden individualmente con el control
mixto**; no es solo igualdad de porcentajes. Se mantienen sus seis regresiones
fotográficas respecto a phone-v1, incluido a7 de `lichess-img_5392` (peón negro →
torre negra) y d8 de `lichess-img_5390` (vacía → dama negra).

La comparación de las doce épocas solo encuentra dos diferencias transitorias:

- Época 5: `chesscom-img_5398` e3, vacía → caballo negro con la nueva máscara;
  el control de esa misma época la acertaba.
- Época 10: `lichess-img_5388` d8, vacía → dama negra con la nueva máscara;
  el control de esa misma época la acertaba. Por eso el nuevo intento tarda una
  época más en alcanzar 20 fotos completas.

No hubo diferencias digitales entre los intentos en ninguna época. Los ciclos de
entrenamiento y validación suman aproximadamente 91 segundos, excluyendo la
verificación inicial de archivos y cachés; esto no es una medición de latencia de CLI.

## Qué demuestra y qué no

La contradicción entre etiqueta vacía y profesor erróneo existía y se ha eliminado
en las siete casillas previstas. **Eliminarla no fue suficiente para mejorar las
predicciones de validación bajo esta configuración.** No demuestra que la
destilación nunca influya, que el modelo necesite más capacidad ni que más épocas
vayan a resolverlo. No se ha medido de nuevo la clasificación del entrenamiento.

Se mantiene la decisión original: no sustituir phone-v1, no ampliar épocas, no
relajar umbrales después del resultado y no encadenar otro entrenamiento.
La siguiente decisión requerirá una hipótesis diferente y un plan explícito;
repetir este mismo ajuste no está justificado por los resultados.

## Artefactos y comprobaciones

En `.cache/neural-mixed-empty-guard-v1/` se guardan `execution.json`,
`mask-audit.json`, `training.json`, `last.pt` y las predicciones de las doce épocas.
`last.pt` es **solo diagnóstico**, no el modelo recomendado. Las dos cachés
se leen del intento anterior y se verifican por hash; no se duplican ni recalculan.
Los modelos y artefactos de referencia permanecen intactos.

Pasan **18 pruebas dirigidas**: máscara y ausencia de mutaciones, receta sin otros
cambios, reglas de aceptación, reanudación/selección del ejecutor y comparación
por imagen que detecta intercambios ocultos por agregados. También se comprueba
la carga real del punto de control y la integridad de las referencias.

Las pruebas de rendimiento CPU y regresiones completas de CLI para promoción
**no se ejecutaron**, porque ninguna época superó el filtro de calidad. No se ha
consultado la evaluación final independiente ni modificado el comportamiento de
la aplicación. La validación sigue siendo el conjunto ya consultado de selección.

```bash
# Rehacer el informe desde predicciones guardadas; no entrena ni ejecuta modelos.
python -m tools.report_mixed_empty_guard
# Solo ante una interrupción del mismo intento; no amplía una ejecución completa.
python -m tools.train_mixed_empty_guard --resume
```

La [prueba de ponderado por raíz cuadrada](mixed-sqrt-result.md) reduce las falsas piezas de 8 a 5 sin aumentar las omisiones frente al control. Es una mejora parcial; phone-v1 sigue como referencia y el nuevo modelo queda experimental.
