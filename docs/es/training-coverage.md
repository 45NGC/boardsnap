# Inventario del material de entrenamiento disponible

**Español** | [English](../en/training-coverage.md)

Revisión del 14 de noviembre de 2026. **Podemos preparar el entrenamiento mixto
con los datos existentes; no hace falta pedir más fotos todavía.** El modelo
recomendado sigue siendo `neural-phone-v1`. Este inventario no inicia otro
entrenamiento ni demuestra una mejora del reconocimiento.

- [Informe con recuentos, ejemplos y hashes](../../data/reports/training-coverage-v1.json).
- [Galería local de entrenamiento](../../.cache/training-coverage-v1/index.html).
- [Revisión de fondos de las fotos antiguas](../../data/manifests/phone-training-backgrounds-v1.json).
- [Diagnóstico de las regresiones](targeted-photo-regressions.md).

## Qué tenemos, sin contar dos veces los corpus anteriores

| Fuente en `.cache` | Tableros de entrenamiento | Posiciones | Casillas almacenadas | Casillas con el selector existente |
| --- | ---: | ---: | ---: | ---: |
| `digital-style-squares-v2` | 14.616 | 56 | 935.424 | 314.346 |
| `arrowhead-training-squares-v1` | 1.144 | 56 | 73.216 | 6.437 |
| `phone-targeted-training-v1` | 184 | 161 | 11.776 | 11.776 |

El corpus digital principal ya reúne los corpus digitales anteriores: no se deben
sumar de nuevo. Sus variantes comparten 56 posiciones y 14 grupos; no son 14.616
situaciones independientes. El lote adicional de flechas utiliza esas mismas
posiciones y grupos. Hay 22 combinaciones digitales de piezas/fondo.

Las fotos son las 160 anteriores más las 24 nuevas: 153 posiciones antiguas y
ocho nuevas. Las antiguas conservan un grupo de procedencia sin resolver;
las nuevas, sus ocho grupos. No se han cambiado las particiones. La columna del
selector calcula `training_indices`: tableros limpios completos y casillas
marcadas con los márgenes de seguridad existentes. **No es una nueva selección
aplicada a los datos ni una receta de muestreo aprobada.**

Se comprobaron los hashes de los 15.944 archivos de casillas. No hay archivos con
el mismo hash entre las filas inventariadas; esto **no** implica que todas las
casillas tengan píxeles diferentes. Las variantes repiten muchos fondos y piezas.

## Flechas y marcas: hay ejemplos reutilizables

En el corpus digital principal:

| Condición de la casilla | Vacías | Ocupadas |
| --- | ---: | ---: |
| Tocada por una flecha | 26.466 | 9.607 |
| Punta de flecha | 4.388 | 1.772 |
| Inicio de flecha | 4.463 | 1.697 |
| Cruce de flechas | 918 | 314 |
| Flecha y otra marca en la misma casilla | 1.478 | 986 |
| Círculo | 1.729 | 6.895 |
| Último movimiento | 1.816 | 3.112 |
| Selección | 179 | 1.053 |
| Puntos de movimiento | 1.029 | 6.363 |

Las categorías se solapan: no deben sumarse. Se cuentan casillas con flechas a
partir de sus máscaras geométricas; los cruces requieren intersección de píxeles,
no solo dos flechas en el mismo tablero. Punta/inicio designan las casillas de los
extremos. Las marcas digitales son variantes controladas, no evidencia de todas
las marcas nativas de las plataformas.

Hay ejemplos de las 13 clases sobre ambos colores de casilla para puntas, inicios,
círculos, selección y combinaciones. Los cruces tienen huecos: torre blanca en
ambos colores, rey blanco en clara y dama negra en clara. Los resaltados de jaque
solo cubren reyes, como corresponde: las clases ausentes no son automáticamente
carencias que debamos rellenar con ejemplos artificiales incoherentes.

Los 11.088 tableros marcados del corpus principal tienen control limpio emparejado
en entrenamiento. Hay 3.528 controles limpios. El lote adicional de 1.144 flechas
aporta 88 puntas sobre vacías y 1.056 sobre piezas, con las 13 clases en ambos
fondos; sus controles pertenecen al corpus principal. Sirve también para conservar
piezas reales bajo flechas, no solo para enseñar al modelo a responder «vacía».

## Fotografías: madera y piezas finas

La revisión visual de las 160 fotos antiguas identifica madera visible en
`lichess-photo-40` a `lichess-photo-44`. Se distingue la veta del fondo de los
patrones de muaré de la pantalla. Las otras 155 se etiquetan «sin veta de madera
visible», lo cual no significa que sean limpias ni que carezcan de textura.

Con las seis fotos nuevas sobre madera hay **11 fotos, siete posiciones y 704
casillas**, de las que **404 están vacías: 209 claras y 195 oscuras**. Hay 300
ocupadas, pero faltan dama blanca sobre oscura, rey blanco sobre clara y caballo
negro sobre clara. Los tres grupos registrados no prueban tres partidas conocidas:
uno sigue siendo el grupo conservador de procedencia antigua sin resolver.

El lote nuevo incluye:

| Apariencia observada | Fotos / posiciones | Casillas vacías | Casillas ocupadas |
| --- | ---: | ---: | ---: |
| Peones de tallo fino (`cc-thin-stem`) | 12 / 4 | 444 | 324 |
| Piezas sombreadas (`cc-shaded`) | 6 / 2 | 210 | 174 |
| Corona redondeada (`lc-rounded-king`) | 6 / 2 | 213 | 171 |

Los peones finos tienen las 13 clases, pero falta rey blanco en casilla clara.
Las otras dos apariencias tienen más huecos por clase/color, detallados en el
informe. Los nombres son etiquetas visuales, no identificaciones oficiales nuevas.
Se conserva la auditoría anterior de diseños; no se han vuelto a identificar todos
los temas antiguos.

**Limitación importante:** las marcas de las fotos se anotaron a nivel de imagen,
no de casilla. Las 404 vacías de madera no equivalen a 404 vacías sin marcas, ni
las fotos con flechas aportan una cifra fiable de puntas sobre vacías. Hay además
fotos antiguas sin condiciones detalladas. El informe mantiene estos desconocidos;
no inventa etiquetas ni los interpreta como ausencia de marcas. La galería permite
revisar ejemplos con su posición, etiqueta y ruta trazables.

## Decisión y siguiente paso

1. Reutilizar controles limpios, marcas simples, puntas/inicios/cruces y piezas
   ocupadas de entrenamiento digital para evitar repetir el ajuste exclusivamente
   fotográfico que perdió tolerancia a superposiciones.
2. Mantener las fotos antiguas y las 24 dirigidas; dar presencia controlada a madera
   y peones finos, sin multiplicar indiscriminadamente sus pocas posiciones.
3. Preparar el conjunto mixto con cuotas por procedencia/condición. Incluso usando
   el selector existente quedan 320.783 casillas digitales frente a 11.776
   fotográficas: concatenarlas sin control puede volver a ocultar las carencias.
4. Antes de ensamblarlo, comprobar grupos, familias de posición y duplicados entre
   fuentes y contra la validación existente. Este inventario **no sustituye** esa
   comprobación ni autoriza mover los fallos de validación a entrenamiento.
5. Fijar la receta y los criterios antes de entrenar un candidato. Solo pedir datos
   adicionales si la validación demuestra que los huecos observados son relevantes.

Se conservaron todos los modelos, las etiquetas originales y las particiones.
No se ejecutó inferencia ni se abrieron imágenes de validación o evaluación final.
Solo se filtra por partición el índice digital compartido; no se estudian las
anotaciones reservadas. Pasan cinco pruebas del inventario: exclusión de particiones,
integridad del índice, geometría de marcas, condiciones desconocidas y recuentos.

```bash
python -m tools.inventory_training_coverage --gallery .cache/training-coverage-v1
python -m pytest tests/test_training_coverage_inventory.py -q
```

La [preparación del conjunto mixto](mixed-training.md) fija un muestreo 50 % digital / 50 % fotográfico, comprueba solapamientos con validación y exporta recortes reproducibles sin entrenar un modelo.
