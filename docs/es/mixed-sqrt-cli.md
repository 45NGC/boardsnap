# Comparación del candidato fotográfico mediante la CLI

**Español** | [English](../en/mixed-sqrt-cli.md)

**La mejora fotográfica se mantiene con detección automática, pero el candidato
pierde dos capturas digitales reales. No debe sustituir globalmente a phone-v1.**
La comparación utiliza `neural-phone-v1/best.pt` y el punto de control experimental
`neural-mixed-sqrt-v1/last.pt`; no modifica pesos ni configuración de la aplicación.

- [Informe por imagen, salidas y comprobaciones](../../data/reports/mixed-sqrt-cli-v1.json).
- [Resultado con esquinas anotadas](mixed-sqrt-result.md).
- Herramienta: `python -m tools.compare_mixed_cli`.

## Alcance y reutilización

Se compararon 30 fotos de validación ya consultadas y 36 capturas digitales únicas:
las 30 capturas reales anotadas y los seis fallos originales expuestos. Las otras
15 entradas del manifiesto de vídeos repiten imágenes de las 30 reales; se verifican
por hash y orientación, se conservan sus alias y se cuentan una sola vez.

Las capturas reales se habían trasladado a
`.cache/real-use-tests/computer-screenshots/`. La herramienta resuelve ese traslado
solo si los píxeles conservan el hash anotado y registra ambas rutas. No cambia
los manifiestos históricos ni utiliza imágenes nuevas sin posición revisada.

El informe de CLI fotográfica de phone-v1, `photo-pipeline-validation-v2.json`,
seguía siendo compatible: se verificaron modelo, código, manifiesto, informe de
detección y hashes de las imágenes. Se reutilizó. Para el candidato se ejecutó la
CLI en cada foto y se contrastó su resultado con los recortes automáticos del
informe geométrico existente. Los recortes anotados se midieron con la herramienta
existente como control de esa comparación; no se repitió el corpus de clasificación
completo de 3.132 capturas.

Cada captura digital se procesó con ambos modelos mediante `python -m boardsnap`,
orientación explícita y sin pasar límites ni posición esperada al programa. Se
comprueban JSON exacto, códigos 0/1 y stderr vacío. La salida correcta contiene solo
`piecePlacement`; los fallos contienen `error` con `code` y `message`. Las ejecuciones
se guardan individualmente en `.cache/mixed-sqrt-cli-v1/` para reutilizarlas por
hash de imagen/modelo/código, orientación y modo.

Son datos de desarrollo y regresión, incluidos los seis fallos originales ya
consultados que proceden de una antigua partición de evaluación. **No se accedió
a la evaluación final independiente.** Los resultados no demuestran independencia
entre partidas ni compatibilidad con todos los estilos.

## Resultado fotográfico

| Medida | phone-v1 | Raíz cuadrada |
| --- | ---: | ---: |
| Fotos con tablero detectado | 29/30 | 29/30 |
| Fotos completas correctas, detección automática | 20/30 | **22/30** |
| Fotos completas correctas, esquinas anotadas | 19/30 | 20/30 |
| Casillas correctas entre las 29 detectadas | 1.824/1.856 | **1.839/1.856** |
| Vacías convertidas en piezas, detectadas | 3 | **2** |
| Piezas omitidas, detectadas | 18 | **8** |

El candidato conserva los veinte aciertos automáticos de phone-v1 y recupera
`chesscom-img_5398` y `video-img_5406`. Por categoría: Chess.com 5→6/10,
Lichess 8→8/10 y vídeos 7→8/10. `video-img_5403` sigue sin detectarse con ambos.
Se cuenta como fallo entre las 30 fotos, no se oculta en el denominador.

Siguen incorrectas `chesscom-img_5395`, `5397`, `5401`, `5402`,
`lichess-img_5391`, `5392` y `video-img_5404`, además del fallo de detección.
El informe conserva las colocaciones esperadas y obtenidas.

Los recuentos automáticos de falsas piezas (3→2) difieren de los anotados (3→5):
los recortes de entrada son distintos. No se deben mezclar ambos experimentos.
La detección y rectificación son independientes del modelo de clasificación;
el análisis no atribuye esas diferencias a una mejora del detector.

## Resultado digital

| Medida | phone-v1 | Raíz cuadrada |
| --- | ---: | ---: |
| Tableros detectados | 36/36 | 36/36 |
| Capturas completas correctas | **35/36** | 33/36 |
| Casillas correctas | **2.302/2.304** | 2.299/2.304 |
| Vacías convertidas en piezas | 2 | 4 |
| Piezas omitidas | 0 | 0 |
| Seis casos originales completos | 6/6 | 6/6 |

No hay capturas completas recuperadas; se pierden dos:

| Captura | Casilla | Esperado | phone-v1 | Candidato |
| --- | --- | --- | --- | --- |
| real-use-6 | b8 | vacía | vacía | peón negro |
| real-use-12 | d3 | alfil blanco | alfil blanco | dama blanca |
| real-use-4 | e3 | vacía | vacía | caballo negro |
| real-use-4 | a5 | vacía | rey negro | caballo negro |

`real-use-4` ya era incorrecta; cambia una clase errónea y añade otro error.
Las capturas no forman parte de las 3.132 variantes de clasificación medidas
durante el entrenamiento. Por eso conservar aquellas predicciones no garantizaba
conservar este lote real. No se ha reentrenado ni cambiado el detector para resolverlo.

## Verificaciones, decisión y siguiente paso

Pasan seis pruebas de la herramienta de comparación. Todas las ejecuciones reales
completadas respetan el contrato de salida. Un negativo blanco de 400×400 se
rechaza con `BOARD_NOT_FOUND`, código 1, en digital y fotografía con ambos modelos.
Es un control acotado, no una repetición exhaustiva de todos los negativos del detector.
Los modelos y el código de producción conservan sus hashes. Los tiempos guardados
incluyen arranque de Python y carga de modelo; **no son un benchmark aislado de CPU**.

Recomiendo mantener phone-v1 como referencia y conservar el modelo raíz cuadrada
como candidato **fotográfico experimental**. Su mejora en estas fotos no resuelve
el incumplimiento de los criterios con esquinas anotadas ni las regresiones reales
digitales. No hay promoción automática ni declaración de aceptación final.

El siguiente paso útil, antes de la integración Flutter, es medir tiempo y memoria
en CPU y fijar una configuración de prueba con selección explícita de modo y
modelo: referencia digital estable y candidato fotográfico experimental. Ese paso
requiere comprobar los modelos elegidos y documentar la configuración; este informe
no introduce selección automática ni inicia otro entrenamiento.

## Reproducción

```bash
# Solo si falta el informe del candidato; preserva el informe anterior de phone-v1.
python -m tools.evaluate_photo_pipeline --detection-report data/reports/photo-detection-validation-v2.json --model .cache/neural-mixed-sqrt-v1/last.pt --output .cache/neural-mixed-sqrt-v1/photo-cli-validation.json
# Reutiliza ejecuciones digitales compatibles y el informe fotográfico ya guardado.
python -m tools.compare_mixed_cli
python -m pytest tests/test_compare_mixed_cli.py -q
```
