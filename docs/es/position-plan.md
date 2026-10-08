# Plan de posiciones y particiones fijas

[English](../en/position-plan.md) | **Español** · [Inicio](README.md)

El [manifiesto digital-positions-v1](../../data/manifests/digital-positions-v1.json)
contiene **80 colocaciones canónicas distintas procedentes de 20 secuencias**,
repartidas antes de capturar imágenes o recortar casillas. El
[informe de cobertura](../../data/reports/digital-positions-v1-coverage.json)
mide presencia de etiquetas, no precisión del reconocimiento. Este hito no añade
capturas, plantillas, modelos entrenados ni perfiles de reconocimiento.

## Contenido del lote

| Partición | Grupos de origen | Posiciones distintas | Uso |
| --- | ---: | ---: | --- |
| `training` | 14 | 56 | Aprender parámetros; construir plantillas y desarrollar preprocesado |
| `validation` | 3 | 12 | Elegir umbrales, hiperparámetros y comparar modelos |
| `evaluation` | 3 | 12 | Medición final tras congelar implementación y decisiones |
| Total | 20 | 80 | Plan inicial de recogida, no garantía de precisión |

Cada secuencia aporta cuatro posiciones diferentes: apertura, posición
intermedia, final poco ocupado y posición inmediatamente posterior a una promoción.
Estas categorías pueden compartir etiquetas de densidad. Cada partición contiene
las doce clases de pieza/color y casillas vacías sobre ambos colores lógicos de
casilla, además de promociones de blancas y negras.

| Categoría | Entrenamiento | Validación | Evaluación | Regla de selección |
| --- | ---: | ---: | ---: | --- |
| Apertura | 14 | 3 | 3 | Tras 12 medias jugadas, al menos 28 casillas ocupadas |
| Posición intermedia | 14 | 3 | 3 | Al menos 32 medias jugadas, entre 12 y 26 casillas ocupadas |
| Final | 14 | 3 | 3 | Entre 3 y 10 casillas ocupadas; posición distinta de la promoción |
| Promoción | 14 | 3 | 3 | Inmediatamente después de una promoción legal; el lote incluye subpromociones |
| Muy ocupado | 14 | 3 | 4 | Al menos 28 casillas ocupadas |
| Poco ocupado | 18 | 4 | 4 | Como máximo 10 casillas ocupadas |

Los nombres de fase son reglas de muestreo, no anotaciones estratégicas de un
experto. Las filas de densidad se solapan con las demás; no hay que sumar todas
para calcular el tamaño del corpus. Los colores son los del ajedrez: a8 es clara
y a1 es oscura. Los temas y las superposiciones reales quedan por capturar.

## Origen reproducible y limitaciones

Son **secuencias sintéticas de movimientos legales** desde la posición inicial,
no partidas humanas descargadas ni resultados de reconocimiento inventados.
Se eligen movimientos legales con una semilla y pesos que favorecen capturas y
avances de peones para llegar a finales y promociones. No juegan ajedrez fuerte
ni representativo. Cada secuencia termina al obtener las cuatro posiciones
necesarias; no tiene por qué ser una partida terminada.

Cada origen registra semilla, inicio estándar y movimientos UCI. Cada posición
guarda grupo y número de media jugada. La comprobación opcional reconstruye los
movimientos, verifica su legalidad y compara cada tablero seleccionado con el
`piecePlacement` almacenado. Las reglas se usan exclusivamente en las herramientas
de datos, nunca para corregir la salida del reconocedor. No se añaden campos
adicionales de FEN a las etiquetas de imagen ni a la respuesta de la app.

Hay **20 grupos, no 80 partidas independientes**. Validación y evaluación solo
tienen tres grupos cada una. Más temas y dos orientaciones producen más imágenes,
no más posiciones ni grupos independientes. Es una base para capturas y
experimentos, pero necesita capturas reales independientes y más grupos antes
de declarar compatibilidad amplia.

El generador utiliza los [movimientos legales y tableros de python-chess](https://python-chess.readthedocs.io/en/latest/core.html)
mediante la dependencia opcional fijada `chess==1.11.2`. No añade dependencias al
núcleo ni introduce PyTorch. Los movimientos UCI versionados son la evidencia
principal de procedencia aunque una futura implementación del generador aleatorio
de Python cambie la reproducción.

## Cómo se fijan las particiones

1. Generar secuencias con semillas a partir de `20261007`; rechazar secuencias
   incompletas, posiciones repetidas/transformadas y coincidencias con el corpus
   existente. Conservar los primeros veinte orígenes válidos.
2. Repartir grupos completos con semilla `1729`. Elegir la primera distribución
   mezclada 14/3/3 que tenga al menos **dos apariciones de cada clase sobre cada
   color de casilla en cada partición**, además de promociones de ambos colores.
   Solo se usan las etiquetas conocidas, antes de imágenes y experimentos.
3. Versionar las asignaciones. Nunca repartir imágenes o recortes de casillas
   por separado. Las pruebas de reproducción comparan el manifiesto completo.
4. Congelar antes de capturar. El comando de preparación rechaza sobrescribir
   archivos existentes; reproducir en una ruta nueva. Cambiar el plan requiere
   otra versión del conjunto y revisar la migración, no sustituirlo silenciosamente.

Cada grupo define la partición una sola vez, en `groups[].split`. Cada posición
tiene `positionId`, `groupId`, `ply`, `piecePlacement` y `categories`; no puede
sobrescribir la partición de su grupo. Todos sus temas, apps, orientaciones,
flechas, resaltados, tamaños, compresiones y recortes heredan esa identidad.

Importar partidas humanas necesitará un identificador estable de partida/origen,
deduplicación entre descargas y la misma regla de agrupación. Las posiciones
cercanas de una partida no deben repartirse entre entrenamiento y evaluación.
El esquema actual valida secuencias generadas; no implementa un importador PGN.

## Conservación del corpus anterior

Los cuatro manifiestos de perfiles existentes, incluido el experimento de libros,
están fijados por ruta y SHA-256 en `legacyExclusions`. Sus archivos, imágenes y
particiones permanecen iguales. El nuevo plan excluye sus posiciones y también
rotaciones, reflexiones e intercambios de color equivalentes. Es una exclusión
deliberadamente conservadora.

Los datos `tuning` siguen siendo de desarrollo. Si se reutilizan para modelos,
solo como entrenamiento adicional; no convertirlos en validación o evaluación
final independientes. Las imágenes antiguas de `evaluation` siguen reservadas
para regresión y no deben copiarse a entrenamiento. Los nuevos grupos
`evaluation` son distintos de aquellas pocas posiciones piloto, ya comprobadas
repetidamente. Actualizar expresamente las exclusiones al incorporar otro corpus.

## Cobertura y carencias detectadas

El informe cuenta apariciones, posiciones distintas y grupos distintos para cada
clase/color de casilla en cada partición. Repetir una pieza en cuatro posiciones
relacionadas no equivale a cuatro orígenes independientes. El SHA-256 del
manifiesto permite vincular el informe al plan exacto.

Se señalan ocho combinaciones porque tienen menos de cinco apariciones o menos
de tres grupos de origen:

| Partición | Clase / color de casilla | Casillas | Posiciones | Grupos |
| --- | --- | ---: | ---: | ---: |
| Validación | Dama blanca / oscura | 2 | 2 | 2 |
| Validación | Rey blanco / clara | 3 | 3 | 2 |
| Validación | Dama negra / clara | 2 | 2 | 1 |
| Evaluación | Dama blanca / oscura | 2 | 2 | 2 |
| Evaluación | Rey blanco / clara | 4 | 4 | 2 |
| Evaluación | Dama negra / clara | 3 | 3 | 2 |
| Evaluación | Dama negra / oscura | 4 | 4 | 2 |
| Evaluación | Rey negro / oscura | 3 | 3 | 2 |

Entrenamiento tiene las 26 combinaciones con al menos cinco apariciones y tres
grupos. Es una comprobación de cobertura, no una afirmación de tamaño suficiente.
Ni dos ni cinco son umbrales de precisión. Priorizar nuevos grupos independientes
para las combinaciones escasas cuando se amplíe el plan.

No mover grupos entre particiones para corregir carencias una vez empezado el
desarrollo. Si un fallo de evaluación final orienta el ajuste, retirar todo ese
grupo a desarrollo y conseguir orígenes independientes para evaluar una nueva
versión. No dejar sus otros temas/vistas dentro de evaluación.

## Comandos

Desde la raíz, con las dependencias habituales de desarrollo instaladas:

```bash
# Estructura, separación del corpus anterior y cobertura; solo biblioteca estándar.
python -m tools.position_dataset

# Dependencia opcional para generar y verificar los movimientos legales.
python -m pip install -e '.[dev,dataset]'
python -m tools.position_dataset --replay

# Reproducir en una ruta NUEVA y comparar con el plan congelado.
python -m tools.prepare_positions .cache/positions-reproduced.json
cmp data/manifests/digital-positions-v1.json .cache/positions-reproduced.json

# Guardar un informe local sin sustituir la evidencia versionada.
python -m tools.position_dataset --replay > .cache/positions-coverage.json
python -m pytest tests/test_position_dataset.py
```

La herramienta de validación emite JSON por stdout y errores por stderr
(código 2). Es un **informe de datos**, distinto de la respuesta del reconocedor
que contiene solo `piecePlacement`. Sin `.[dataset]` se ejecutan las pruebas
estructurales y se omite únicamente la de reproducción/legalidad. Las pruebas
cubren fugas entre particiones, etiquetas incorrectas, colores, clases ausentes,
identidad de variantes, informe congelado y reproducción.

## Capturar desde este plan

Utiliza [la herramienta de capturas configurables](configurable-capture.md) para
las tres particiones. Emplea `variant_identity` y `validate_variants` para heredar
sin cambios posición/grupo/partición, y añade hash del PNG, geometría comprobada,
estilo, orientación y procedencia. Los scripts originales siguen aceptando solo
los manifiestos anteriores de ajuste/evaluación.

El ejemplo recoge un pequeño piloto de entrenamiento con cuatro combinaciones;
amplía la receta al resto de posiciones y estilos tras revisarlo. El entrenamiento
y las plantillas deben usar solo training; la selección de modelos, validation;
evaluation sigue reservado hasta congelar las decisiones.
