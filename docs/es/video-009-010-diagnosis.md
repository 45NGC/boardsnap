# Diagnóstico de los vídeos 009 y 010

[English](../en/video-009-010-diagnosis.md) · [Corpus de desarrollo](video-development.md)

**Diagnóstico histórico anterior a la corrección.** La [recuperación acotada](border-grid-recovery.md)
ya resuelve ambas capturas en la CLI. El informe siguiente conserva el fallo anterior.

**Recomendación: corregir el tratamiento de la geometría antes de entrenar.**
Ambas posiciones se reconocen completas con **v8 y el candidato actual** al usar
la cuadrícula deducida de sus líneas interiores. El diagnóstico no cambia pesos,
producción ni anotaciones. La CLI sigue rechazando estas imágenes; los resultados
con recorte corregido son pruebas de diagnóstico, no una corrección desplegada.

La causa reproducida tiene dos partes: el detector rechaza la franja exterior
izquierda de una propuesta interior válida, y el rectángulo visible anotado no
es una buena referencia para dividir uniformemente las 64 casillas. Eso desplazaba
las piezas y hacía parecer que había un problema de reconocimiento de estilos.

## Datos y referencias

Se utilizan únicamente los dos PNG archivados en
`data/development/video-cases-v2`, sus etiquetas del manifiesto revisado y los pesos:

- v8: `.cache/neural-styles-v8/best.pt`.
- Candidato: `.cache/neural-tolerance-v1-conservative/best.pt`.

La orientación confirmada por el usuario es `white-bottom` en ambos casos.
El [informe reproducible](../../data/reports/video-009-010-diagnosis.json) conserva
hashes, trazas del detector, límites, posiciones, errores por casilla y controles
de interpolación. No se consulta el corpus final reservado ni se realiza ningún
entrenamiento. Las dos imágenes mantienen su grupo de desarrollo original.

## Detección: dónde se detiene

`detect_board` devuelve `BOARD_NOT_FOUND` en las dos capturas. El fondo de vídeo
conecta los contornos con el exterior y produce una región candidata del tamaño
de la imagen; ese primer ajuste no consigue una cuadrícula regular. Sin embargo,
la ruta `_interior_grid_candidates` **sí encuentra las siete líneas interiores**.
El ajuste posterior las sitúa a intervalos de 57 píxeles:

| Captura | Líneas verticales | Líneas horizontales |
| --- | --- | --- |
| 009 | 67, 124, 181, 238, 295, 352, 409 | 81, 138, 195, 252, 309, 366, 423 |
| 010 | 66, 123, 180, 237, 294, 351, 408 | 60, 117, 174, 231, 288, 345, 402 |

El patrón estructural interior se valida, pero
`_structural_pattern(..., complete_edges=True)` rechaza **el borde izquierdo**
antes de aceptar el tablero. La variante `_refine_grid(..., visible=True)` tampoco
logra devolver un rectángulo: su búsqueda local no confirma esa transición exterior.
No es un fallo de orientación ni una ausencia de líneas interiores.
En el borde izquierdo coinciden con el patrón 5 de 8 celdas en la 009 y 4 de 8
en la 010; el filtro exige al menos 6.

## Rectángulo visible frente a cuadrícula

Los extremos derecho e inferior de estas tablas son exclusivos.

| Captura | Rectángulo revisado actual | Cuadrícula estimada por las líneas |
| --- | --- | --- |
| 009 | `(13, 23, 467, 481)` — 454 × 458 | `(10, 24, 466, 480)` — 456 × 456 |
| 010 | `(12, 2, 466, 460)` — 454 × 458 | `(9, 3, 465, 459)` — 456 × 456 |

El manifiesto actual asigna el mismo rectángulo a `box` y `gridBox`. Esa igualdad
no describe bien estas capturas: la franja visible izquierda está desplazada
respecto a la extrapolación de las líneas. La diferencia no requiere reconstruir
una pieza ni añadir píxeles: ambos rectángulos estimados están dentro del PNG.
Contienen algunos píxeles de la franja exterior junto a la primera columna.

Dividir el rectángulo revisado da pasos horizontales de 56,75 píxeles, empezando
3 píxeles a la derecha del origen estimado. El desfase de las líneas internas va
de 2,75 a 1,25 píxeles. Para la primera casilla, el centro se desplaza aproximadamente
2,875 píxeles de entrada, unos 3,2 píxeles tras normalizar a 64 × 64. Es suficiente
para este clasificador sensible al encuadre.

La geometría interior es una inferencia comprobable de los píxeles, **no una nueva
anotación manual aprobada**. Se conserva el manifiesto original para dejar visible
la discrepancia. Antes de cambiar el contrato de límites debe revisarse el significado
de `box` y `gridBox`, incluida la franja parcialmente tapada o recortada. La imagen
sola no permite atribuirla con certeza al recorte del vídeo, una sombra o al montaje.

## Errores con los límites revisados

### Captura 009

Posición esperada:

```text
3rkb1r/pp2qpp1/7p/2pP4/4p1QP/2N1P1B1/PP3PP1/n1K3NR
```

| Casilla | Esperada | v8 | Candidato |
| --- | --- | --- | --- |
| a7 | Peón negro | Vacía | Vacía |
| b7 | Peón negro | Vacía | Vacía |
| c3 | Caballo blanco | Dama blanca | Dama blanca |
| a2 | Peón blanco | Vacía | Vacía |
| b2 | Peón blanco | Torre blanca | Correcta |

v8 acierta **59/64** casillas y el candidato **60/64**. Las casillas restantes
son correctas. El resaltado de última jugada está en c1/d1 y no explica estos errores.

### Captura 010

Posición esperada:

```text
8/8/8/p6p/P3K1kP/4P3/8/8
```

| Casilla | Esperada | v8 | Candidato |
| --- | --- | --- | --- |
| a5 | Peón negro | Vacía | Vacía |
| a4 | Peón blanco | Vacía | Vacía |

Ambos modelos aciertan **62/64**. El peón blanco de a4 tiene resaltado amarillo;
el peón negro de a5 no. El resaltado puede contribuir a la apariencia, pero no
es necesario eliminarlo para reconocer la posición.

## Controles que aíslan la causa

La cuadrícula candidata se obtiene automáticamente de los píxeles, sin utilizar
la posición esperada para elegirla. Se exige una única propuesta interior válida
para el diagnóstico; sigue marcada como rechazada por el filtro de producción.

| Recorte | 009 v8 / candidato | 010 v8 / candidato |
| --- | --- | --- |
| Rectángulo revisado + LANCZOS habitual | 5 / 4 errores | 2 / 2 errores |
| Cuadrícula interior, ambos ejes | **0 / 0** | **0 / 0** |
| Solo corregir eje horizontal, conservar límites verticales revisados | **0 / 0** | **0 / 0** |
| Rectángulo revisado + vecino más próximo | 8 / 4 errores | 2 / 2 errores |
| Rectángulo revisado + bilineal | 5 / 4 errores | 2 / 2 errores |
| Rectángulo revisado + bicúbica | 5 / 4 errores | 2 / 2 errores |

Esto demuestra que el ajuste horizontal es suficiente **en estas dos imágenes**.
No implica que cualquier recorte derivado de líneas sea seguro ni que todas las
capturas de vídeo vayan a funcionar.

- **Resolución:** hay aproximadamente 57 píxeles por casilla. Con los mismos píxeles,
  ambos modelos aciertan después del ajuste; aumentar la resolución no es necesario
  para estos casos. No se recupera información inventada.
- **Estilo:** el identificador de piezas no está confirmado en la procedencia.
  No se puede concluir que sea un estilo ausente del entrenamiento; el reconocimiento
  completo con los mismos pesos contradice que entrenarlo sea imprescindible aquí.
- **Colores y marcas:** permanecen intactos en los recortes que funcionan. No se
  necesita recolorear, borrar el resaltado o convertir la imagen a escala de grises.
- **Remuestreo:** cambiar solo la interpolación no soluciona el problema. La
  combinación de límites, división uniforme y remuestreo sí cambia el encuadre local.
- **Recorte:** es la explicación apoyada directamente por los controles y por
  la concentración de errores en las primeras columnas.

## Por qué no se ha relajado el detector

Eliminar `complete_edges=True` sería una modificación pequeña, pero no segura.
Como control, se ocultaron **14 píxeles de la primera columna** en cada imagen,
conservando las líneas interiores. El patrón estructural interior sigue dando
válido; la comprobación exterior lo rechaza. Aceptar una cuadrícula solo por sus
líneas interiores perdería esa protección frente a contenido parcial.

Este control comprueba la función de validación, no una evaluación completa de
falsos positivos. Basta para descartar eliminar ese filtro como arreglo de bajo
riesgo. Tampoco se ha aplicado un desplazamiento fijo de tres píxeles ni una regla
para estos nombres de archivo. No se declara ninguna mejora de producción y los
fallos esperados actuales se conservan.

## Siguiente paso recomendado

1. Revisar estas dos anotaciones para separar **superficie visible**, **cuadrícula
   geométrica** y cualquier franja tapada. Mantener posición, orientación y grupo.
2. Diseñar una recuperación acotada para propuestas con siete líneas consistentes
   por eje y una franja exterior estrecha: medir cuánto se aparta el borde visible
   del ajuste, exigir evidencia en los demás bordes y rechazar celdas ausentes.
   El límite admisible debe fijarse con validación, no para encajar estos dos PNG.
3. Conservar el origen y el paso de la cuadrícula al normalizar/dividir. No ajustar
   automáticamente la cuadrícula al borde visible si eso desalinearía sus casillas;
   no inventar ni rellenar contenido fuera de la imagen.
4. Probar ambos modelos: 009/010 completas correctas; conservar las otras 13 imágenes,
   los seis fallos originales y el corpus de regresión. Incluir controles con bordes,
   sombras y franjas de 1, 2, 4, 8 y 14 píxeles, tableros realmente cortados,
   cuadrículas mayores y negativos sin tablero. Medir límites visibles y alineación
   de cuadrícula por separado.

**No iniciar entrenamiento ahora.** Si persisten errores con geometría ya validada,
preparar entrenamiento adicional con posiciones distintas: peones blancos/negros,
caballos, damas y torres sobre ambos fondos; resaltados y sin ellos; capturas de
40–80 píxeles por casilla y variaciones leves de encuadre/remuestreo. Mantener estas
posiciones en desarrollo y agrupar las variantes por partida; el grupo de origen
actual es conservador y no debe reutilizarse como datos independientes. El riesgo
principal sería memorizar un estilo, fondo o desplazamiento, o perjudicar el corpus
limpio y con flechas. Validar por clase y tablero completo antes de comparar con
v8 y el candidato intactos. Esta es una contingencia, no una necesidad demostrada.

## Reproducción

```bash
python -m tools.analyze_video_failures
python -m pytest tests/test_video_failure_diagnosis.py
```

Los mosaicos y los límites superpuestos se guardan en
`.cache/video-failure-analysis/`. En las imágenes de límites, rojo representa el
rectángulo revisado y cian la cuadrícula estimada. El diagnóstico verifica hashes
y mantiene intacto el contrato público de `piecePlacement` y errores estructurados.
El comando genera ahora `current-diagnosis.json` en esa carpeta con el detector
actual; no sobrescribe el informe histórico anterior a la corrección.
