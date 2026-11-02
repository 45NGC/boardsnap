# Recuperación geométrica de fotografías

[English](../en/photo-recovery.md) | **Español**

Se acepta una corrección acotada del detector fotográfico: recupera dos fotos de
validación y una posición completa adicional, conservando todos los resultados
anteriores. **Se mantienen los pesos de foto v1 y el candidato digital.** No se
han repetido entrenamientos ni aplicado los experimentos descartados en la
[revisión de calidad](photo-quality.md).

## Causa y corrección

En `video-img_5406` había propuestas geométricas válidas, pero el ajuste de las
intersecciones desplazaba el borde inferior hacia la interfaz. Si ningún resultado
del recorrido anterior se acepta, ahora se puede recuperar una propuesta medida
cuando el ajuste la haya desplazado como máximo **una décima de casilla**.
La propuesta original debe superar por sí misma las comprobaciones completas de
cuadrícula, bordes y ausencia de continuación exterior.

En `video-img_5407` el marco claro se mezcla con las casillas claras: el borde
exterior aparece como segmentos del tamaño de una casilla. Tras fallar los métodos
anteriores, una búsqueda adicional admite segmentos más cortos para proponer
cuadriláteros. Se mantienen el ajuste interior y todos los filtros de aceptación.
No se reconstruyen bordes ausentes ni se elige según el nombre o la posición esperada.

Las recuperaciones se ejecutan solo cuando no hay un tablero aceptado por el
recorrido original. No se modifican detección digital, rectificación, clasificador,
orientación, etiquetas ni particiones.

## Mediciones reutilizables

| Comprobación | Antes | Después |
| --- | ---: | ---: |
| Desarrollo: detección dentro del criterio | 132/161 | 134/161 |
| Validación consultada: detección dentro del criterio | 27/30 | 29/30 |
| Validación consultada: posiciones exactas mediante CLI | 19/30 | 20/30 |
| Controles negativos construidos rechazados | 18/18 | 18/18 |

El [informe de comparación](../../data/reports/photo-recovery-comparison-v2.json)
verifica identidad de imágenes, grupos, particiones, políticas y hashes del código
y modelo. Todas las esquinas devueltas previamente son idénticas y las 27 posiciones
que devolvía la CLI permanecen iguales, incluidas las 19 correctas. No hay nuevas
detecciones fuera de tolerancia: IoU ≥ 0,95, error de esquina ≤ 1 % del lado y
desplazamiento máximo de la cuadrícula ≤ 8 % de casilla.

Ahora se aciertan **1.824/1.856 casillas** de las 29 fotos detectadas. Antes eran
1.697/1.728 de 27 fotos: los denominadores cambian y no deben compararse como si
fueran las mismas imágenes. Con esquinas anotadas siguen siendo 1.871/1.920 y 19/30
posiciones completas. El informe del recorrido registra resultados por clase.

Verificación: 355 pruebas de regresión superadas y tres omitidas por falta de
capturas locales antiguas; además, 11 pruebas nuevas del detector y ocho de la
comparación superadas. Se comprueban las dos fotos recuperadas, su rechazo al
ocultar una franja de 14/64 de la primera columna, otras franjas exteriores,
cuadrículas 7×7/9×9 y el límite de recuperación. Las 30 fotos se ejecutaron mediante
la CLI real, comprobando JSON, stderr y códigos de salida.

La búsqueda adicional aumenta el coste de algunos rechazos. En desarrollo se
registraron mediana de 0,61 s y p95 de 5,15 s de detección, con otras comprobaciones
en ejecución: son tiempos diagnósticos, no un benchmark aislado de aceptación.

## Límites y siguiente paso

- `video-img_5407` ya devuelve la posición completa correcta automáticamente.
- `video-img_5406` se detecta dentro de tolerancia, pero aparece un caballo negro
  falso en **h8**; con esquinas anotadas su clasificación era correcta.
- `video-img_5403` continúa sin detección. Persisten los fallos de peones finos,
  piezas sombreadas/texturas y algunas imágenes con muaré o marcas.

No se afirma tolerancia general al desenfoque, reflejos, flechas u oclusiones. La
prioridad posterior es añadir ejemplos dirigidos de los estilos que faltan y medir
las confusiones, conservando el modelo actual como referencia. Este avance mejora
el recorrido disponible, pero **20/30 no declara aceptada la versión fotográfica**.

Este lote ya estaba consultado y se ha usado para desarrollar la corrección.
La evaluación final independiente permanece sin utilizar; no se presenta esta
mejora como una nueva prueba independiente.

## Uso y reproducción

El comando no cambia:

```bash
boardsnap "mi-foto.jpg" --input-type photo --model .cache/neural-phone-v1/best.pt --orientation white-bottom
```

Usa `black-bottom` cuando corresponda. La salida correcta sigue teniendo solo
`piecePlacement`; se conservan los errores estructurados.

Los informes v1 se conservan. Los v2 son las nuevas mediciones, no modelos nuevos.
Para comparar los informes existentes sin inferencia ni entrenamiento:

```bash
python -m tools.compare_photo_recovery --output .cache/photo-recovery-comparison.json
```

Para repetir las mediciones deliberadamente, elige rutas de salida nuevas:

```bash
python -m tools.evaluate_photo_detection --manifest data/manifests/phone-photos-v1.json --output .cache/photo-development-recheck.json
python -m tools.evaluate_photo_detection --manifest data/manifests/phone-validation-v1.json --output .cache/photo-validation-recheck.json
python -m tools.evaluate_photo_detection --manifest data/manifests/phone-photos-v1.json --controls-only --output .cache/photo-controls-recheck.json
python -m tools.evaluate_photo_pipeline --detection-report .cache/photo-validation-recheck.json --model .cache/neural-phone-v1/best.pt --output .cache/photo-pipeline-recheck.json
```
