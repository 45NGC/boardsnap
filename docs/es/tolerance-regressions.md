# Análisis de las 11 regresiones de tolerancia

[English](../en/tolerance-regressions.md) · [Paso 4](classifier-tolerance.md)

**Recomendación: mantener el candidato actual**,
`.cache/neural-tolerance-v1-conservative/best.pt`, y conservar v8 como referencia.
No se han entrenado modelos, sustituido pesos ni modificado el reconocimiento de
producción. La alternativa sencilla comprobada pierde muchas más mejoras de las
que recupera. Estas pérdidas merecen seguimiento, pero no justifican detener el
siguiente paso ni introducir una regla especial para estas imágenes.

## Evidencia y alcance

Se reutiliza la [comparación completa existente](../../data/reports/neural-tolerance-validation.json).
Solo se reproducen las 11 transiciones de tablero completo correcto con v8 a
incorrecto con el candidato. Se comprueban sus originales, controles limpios,
recortes, logits internos y detección. Una prueba adicional utiliza únicamente
las 11 pérdidas y los 674 aciertos nuevos ya identificados en ese informe.

El [informe detallado](../../data/reports/neural-tolerance-loss-analysis.json)
registra imágenes, hashes, casillas, condiciones, coordenadas, predicciones y
resultados de la alternativa. Todo pertenece a **validación ya consultada**;
no es una evaluación final independiente. Las 11 pérdidas de tablero completo
no enumeran necesariamente todos los cambios de casilla en tableros que ambos
modelos ya reconocían incorrectamente.

## Qué tienen en común

Todas las imágenes tienen piezas **Neo de Chess.com**, fondo **azul**, interfaz
`chesscom-analysis` de navegador de escritorio, orientación `black-bottom` y
un tablero de **704 × 704 píxeles**, con casillas de 88 píxeles.

| Posición | Variantes | Perturbación | Casilla | Error |
| --- | ---: | --- | --- | --- |
| `digital-034` | 1, círculo | Arriba 2 px | g2 | Alfil blanco → dama blanca |
| `digital-070` | 1, círculo | Arriba 2 px | d3 | Alfil blanco → dama blanca |
| `digital-035` | 1, limpia | Bordes asimétricos | h1 | Alfil blanco → dama blanca |
| `digital-036` | 8 | Bordes asimétricos | h1 | Alfil blanco → dama blanca |

Las ocho variantes de `digital-036` son limpia, última jugada, selección, jaque,
flecha sobre vacío, flecha sobre pieza, flechas cruzadas y combinación de marcas.
Son **cuatro posiciones de dos grupos**: 034/035/036 pertenecen a `sequence-009`
y 070 a `sequence-018`. No son 11 ejemplos independientes.

Cada tablero falla en **una sola casilla**, siempre un alfil blanco sobre fondo
claro. No hay cambios de color, piezas vacías confundidas ni otros tipos de pieza
en estas 11 pérdidas. Los nueve casos de h1 reutilizan esencialmente la misma
imagen local: ocho recortes son idénticos byte a byte; la variante combinada
cambia un solo píxel frente a su control limpio. En total hay cuatro hashes de
recorte distintos entre las once casillas fallidas.

Por tanto, las flechas que aparecen en varias capturas **no son la causa local de
los errores de h1**: el recorte del alfil es idéntico al limpio, salvo ese píxel en
la combinación. Los dos casos restantes sí tienen un círculo verde alrededor del
alfil: cambian 1152 y 1151 de los 4096 píxeles respecto al control sin círculo.

## Límites y mecanismo probable

Los límites originales, con derecha/abajo exclusivos, son `(228, 66, 932, 770)`.

| Escenario | Desplazamiento izquierda/arriba/derecha/abajo | Recorte resultante |
| --- | --- | --- |
| `shift-y-2` | `(0, -2, 0, -2)` | `(228, 64, 932, 768)`, 704 × 704 |
| `asymmetric-2` | `(1, -2, 2, -1)` | `(229, 64, 934, 769)`, 705 × 705 |

Son errores pequeños y plausibles de localización: como máximo 2 píxeles por
borde, un 0,284 % del lado del tablero o un 2,27 % de una casilla. El desplazamiento
vertical equivale aproximadamente a 1,45 píxeles tras normalizar cada casilla a
64 × 64. La perturbación asimétrica también introduce un cambio de escala del
0,142 % y desplaza el centro 1,5 píxeles a la derecha y arriba. No sale de la
captura ni elimina información distintiva del alfil.

La inspección visual muestra una franja del borde o de la casilla contigua
incorporada al recorte y un pequeño desplazamiento de la silueta. En h1, que es
la esquina superior izquierda en esta orientación, también aparece la etiqueta
«1». La evidencia es compatible con sensibilidad al encuadre y al remuestreo,
combinada con un pequeño cambio de la frontera de decisión al mezclar pesos.
**No demuestra que la etiqueta, la franja o el círculo sean por sí solos la causa**;
no se ha realizado una ablación de cada elemento.

Los márgenes internos entre el logit del alfil y el mejor competidor muestran lo
cerca que estaban estas entradas de cambiar de clase. No son probabilidades ni
campos añadidos a la salida pública:

| Recorte perturbado | Margen v8 | Margen candidato |
| --- | ---: | ---: |
| g2 con círculo | +1,2530 | −0,2327 |
| d3 con círculo | +1,3495 | −0,1336 |
| h1, caso limpio | +0,0415 | −0,0985 |

Con los límites originales, el candidato tiene márgenes entre +22,42 y +30,55
en esas mismas casillas y reconoce correctamente los 11 tableros completos.
Además, el detector actual devuelve **exactamente los límites originales en las
11 imágenes**. Son fallos de tolerancia inducidos; no son fallos actuales del
recorrido automático sobre esos PNG originales.

El patrón tampoco implica que el candidato haya empeorado globalmente en alfiles:
entre todas las variantes perturbadas aplicables ya medidas, acierta **46348/47228**
alfiles blancos frente a **46189/47228** de v8. Las confusiones alfil blanco → dama
blanca bajan de 167 a 161. Esta mejora agregada no elimina las once pérdidas locales.

## Corrección sencilla comprobada

Se reconstruyó en memoria la mezcla de **6,25 % del entrenamiento y 93,75 % de v8**,
utilizando los pesos existentes. El candidato actual usa 12,5 % y 87,5 %.
No se entrenó ni guardó otro modelo. Esa fracción menor ya estaba incluida en la
selección anterior; el diagnóstico añade el detalle de las pérdidas y ganancias.

- Recupera **2/11** pérdidas: los dos alfiles con círculo.
- No recupera los nueve casos de h1.
- Pierde **400/674** tableros perturbados que el candidato actual había recuperado.
- En el bloque de selección anterior ya obtenía 6006/6264 tableros correctos,
  frente a 6037/6264 del candidato actual.

Este subconjunto dirigido basta para descartar que esa sustitución conserve las
mejoras, pero **no estima su resultado en toda la validación**. Por eso no se ha
repetido una evaluación completa de la alternativa.

No se ha encontrado una corrección sencilla que pueda declararse segura. Volver
a los límites anotados resuelve los once casos, pero esos límites no están
disponibles en una imagen nueva. Desplazar siempre el recorte trasladaría el
error a tableros bien localizados. Forzar dama → alfil, recortar bordes de todas
las casillas o recurrir a v8 según un umbral necesitaría controles sobre damas
reales y el resto del corpus; no está justificado aplicarlo por estos ejemplos.
La prueba realizada tampoco descarta que otra técnica pueda mejorar en el futuro.

## Decisión y seguimiento

Mantener el candidato: conserva los originales y las regresiones comprobadas y
su saldo sigue siendo **674 ganancias menos 11 pérdidas = 663** tableros
perturbados adicionales correctos. Aceptar provisionalmente estas limitaciones
no equivale a declarar aceptada la versión digital.

No está demostrada la necesidad de otro entrenamiento ahora. Si este patrón
aparece en capturas nuevas con detección real, el trabajo siguiente sería ampliar
**solo entrenamiento** con alfiles y damas Neo sobre ambos fondos, círculos,
coordenadas y pequeños errores de borde. Deben conservarse grupos y particiones;
no copiar estas posiciones de validación al entrenamiento ni ajustar una regla
para h1. Cualquier sustitución deberá conservar las mejoras y superar la
validación y las regresiones completas correspondientes.

## Reproducción

Con los corpus y modelos locales existentes:

```bash
python -m tools.analyze_tolerance_regressions
python -m pytest tests/test_tolerance_loss_analysis.py
```

La herramienta verifica hashes de modelos, fuentes, índice y código de la
comparación original. El mosaico de recortes se guarda en
`.cache/tolerance-loss-analysis/regression-crops.png`; los datos y pesos permanecen
en caché. No modifica la CLI ni su contrato de `piecePlacement`.
