# Revisión del piloto training2

[English](../en/targeted-photo-intake.md) | **Español**

El 12 de noviembre de 2026 se recibieron y revisaron **24 fotografías y 16
capturas directas**, distribuidas en ocho posiciones. El piloto inicial tenía
18 fotos y 12 capturas; las series 7 y 8 añaden seis fotos y cuatro referencias
dirigidas a los caballos blancos que faltaban. Las 24 fotos son utilizables
para continuar la preparación: muestran la cuadrícula completa, coinciden en
piezas y orientación con sus referencias y aportan perspectiva, muaré y marcas.
**No hace falta repetir este lote.** Esta revisión no mide aciertos del modelo.

- [Inventario emparejado y transcripciones](../../data/manifests/phone-targeted-intake-v1.json).
- [Informe de cobertura y carencias](../../data/reports/phone-targeted-intake-v1.json).
- [Galería local: fotos y referencias por posición](../../.cache/phone-targeted-v1/review/index.html).
- Originales: `.cache/real-use-tests/training2/position1/` hasta `position8/`.

## Lo recibido

| Serie | Apariencia observada | Fondo | Orientación | Foto frontal / oblicua / con marcas |
| --- | --- | --- | --- | --- |
| 1 | `cc-thin-stem` | Morado liso | Negras abajo | `IMG_5470` / `5471` / `5472` |
| 2 | `cc-thin-stem` | Marrón liso | Negras abajo | `IMG_5473` / `5474` / `5475` |
| 3 | `cc-shaded` | Marrón liso | Negras abajo | `IMG_5476` / `5477` / `5478` |
| 4 | `cc-shaded` | Madera | Blancas abajo | `IMG_5479` / `5480` / `5481` |
| 5 | `lc-rounded-king` | Madera | Blancas abajo | `IMG_5482` / `5483` / `5485` |
| 6 | `lc-rounded-king` | Marrón liso | Negras abajo | `IMG_5486` / `5487` / `5488` |
| 7 | `cc-thin-stem` | Morado liso | Blancas abajo | `IMG_5490` / `5491` / `5492` |
| 8 | `cc-thin-stem` | Marrón liso | Blancas abajo | `IMG_5493` / `5494` / `5495` |

El salto de numeración de 5483 a 5485 no implica una foto ausente: hay tres fotos
en esa serie. Todas son originales HEIC de iPhone 8, de 3024×4032 píxeles una vez
aplicada la orientación del archivo. Se conservaron los originales y se generaron
PNG RGB sRGB sin pérdida y copias JPG para consulta, reutilizando el conversor
existente. Cada archivo y su derivado PNG tienen hash registrado.

La primera captura PNG de cada carpeta corresponde a las primeras dos fotos;
la segunda corresponde a la foto con marcas. Se transcribieron visualmente las
ocho posiciones desde las capturas y se contrastaron con las fotos, sin emplear
predicciones como etiquetas. El manifiesto conserva filas visuales, orientación y
`piecePlacement` canónico. La revisión es del asistente; `userVerified` permanece
en `false`.

## Diferencias respecto al plan

- Las series 1 y 2 tienen negras abajo. Las nuevas series 7 y 8 incorporan
  blancas abajo para ese mismo diseño y ambos fondos.
- Las series 3 y 4 intercambian los fondos previstos y cambian las vistas. Se
  registraron las combinaciones reales sin renombrar ni mover los originales.
- Las dieciséis fotos de base conservan **resaltados de última jugada**. La serie 6
  también tiene indicación de jaque. No se etiquetan como completamente limpias.
- Las ocho fotos adicionales incluyen flechas; varias tienen cruces o combinaciones
  densas. Lichess también aporta círculos. Son casos útiles, pero falta una
  comparación controlada con marcas más sencillas.
- En las series 1 y 8 cambia el sentido de inclinación entre la foto oblicua y la
  marcada. No se atribuirá una diferencia de reconocimiento únicamente a las marcas.
- Se observa muaré y variación de perspectiva/color en las fotos. No se dispone
  de medidas de iluminación ni de distancias para cuantificar esos factores.
- Las apariencias coinciden visualmente con las referencias seleccionadas; los
  nombres oficiales de los selectores siguen pendientes porque no se aportaron
  capturas de ajustes. No se deducen nombres oficiales a partir del parecido.
- En la serie 7 se superponen varias flechas verticales en la columna f. El
  manifiesto conserva como pendientes los emparejamientos de origen/destino que
  no se distinguen con seguridad; la captura es la referencia de las marcas.
  Esa incertidumbre no afecta a la colocación de piezas transcrita.

## Cobertura y ampliación dirigida

Se cuentan **512 casillas de ocho posiciones distintas**, una vez por posición.
Las variantes fotográficas y las capturas no multiplican esa diversidad.

| Apariencia | Clases presentes | Carencia principal |
| --- | ---: | --- |
| Peones finos | 13/13 | Falta rey blanco sobre casilla clara |
| Piezas sombreadas | 13/13 | Faltan damas/reyes en algunos colores de casilla |
| Rey redondeado | 13/13 | Faltan torres/damas/reyes en algunos colores de casilla |

Las trece clases aparecen en el lote conjunto. Para cada diseño, estas son las
combinaciones ausentes; mayúsculas indican piezas blancas, minúsculas negras:

| Apariencia | Clase y color de casilla ausentes |
| --- | --- |
| `cc-thin-stem` | `K`: clara |
| `cc-shaded` | `Q`, `K`, `q`: clara; `k`: oscura |
| `lc-rounded-king` | `R`, `K`, `q`: clara; `Q`, `k`: oscura |

`N` = caballo, `B` = alfil, `R` = torre, `Q` = dama y `K` = rey. Ambos colores
de peón y las casillas vacías sí aparecen sobre casillas claras y oscuras en cada
grupo. Presencia no significa cantidad suficiente ni precisión demostrada.

La ampliación **resuelve la ausencia de caballos blancos en los datos**: las
posiciones 7 y 8 contienen un caballo blanco en c3 (oscura) y otro en f3 (clara).
Son dos ejemplos por color de casilla, contados por posición, sobre ambos fondos.
También cubren los huecos anteriores de alfiles y damas de este diseño. Esto
completa la presencia de las trece clases en cada apariencia, sin demostrar aún
que el modelo las reconozca correctamente.

No hace falta otra recogida para cerrar esta ampliación. La geometría de las
24 fotos quedó revisada el 13 de noviembre de 2026. Para futuras ampliaciones quedan los
huecos de la tabla, bases sin ningún resaltado y parejas con una marca sencilla
manteniendo el encuadre. El informe conserva el resumen de las primeras seis
posiciones para poder comprobar qué aportaron las nuevas; sus registros anteriores
de imágenes y sesiones no se modificaron.

## Procedencia y estado de preparación

Se leyeron de las fotos seis partidas distintas de Chess.com:
`186750194058`, `186559752718`, `187062563830`, `187014017568`,
`186984581962` y `186840071668`.
El usuario confirmó que las series 5 y 6 son partidas distintas de Lichess; sus
identificadores no son visibles. Cada partida tiene un grupo propio y todas sus
fotos/referencias se mantienen juntas.

No se encontraron archivos duplicados ni coincidencias de familia de posición
con las 191 fotos registradas anteriormente; tampoco coincidencias entre los
seis identificadores de Chess.com y los identificadores conocidos de ese lote.
Esta comprobación se limita a los manifiestos fotográficos anteriores: la
procedencia incompleta y los demás corpus todavía requieren revisión antes de
asignar entrenamiento. No demuestra independencia para una evaluación final.

La **revisión de las parejas y la geometría está completada**. El 13 de noviembre
de 2026 se anotaron las cuatro esquinas de cada foto y se revisaron visualmente
los 24 tableros rectificados frente a la foto original, la captura directa y el
diagrama de etiquetas. El detector existente propuso las esquinas; cada propuesta
se inspeccionó antes de aprobarla. No hizo falta ajustar esquinas manualmente.
Es una revisión visual del asistente, no una evaluación independiente del detector
ni una referencia con precisión subpíxel.

Las coordenadas corresponden a la imagen RGB completa tras aplicar su orientación
EXIF, en orden **superior izquierda, superior derecha, inferior derecha e inferior
izquierda**. Describen la vista fotografiada, independientemente de qué color esté
abajo. Se mantienen visibles y alineadas las ocho filas y columnas; no se observaron
piezas cortadas ni etiquetas desplazadas. Se conservan el muaré, las flechas, los
resaltados y las variaciones de color.

## Casillas preparadas

- [Galería de geometría y casillas etiquetadas](../../.cache/phone-targeted-squares-v1/index.html).
- [Informe de exportación](../../data/reports/phone-targeted-squares-v1.json).
- Arrays locales: `.cache/phone-targeted-squares-v1/development/*.npz`.
- Índice local: `.cache/phone-targeted-squares-v1/verified.jsonl`.

Se han generado **1.536 recortes RGB de 64×64 píxeles**, 64 por cada una de las
24 fotos, con las 13 clases presentes. Cada tablero se rectifica a 512×512 con
interpolación lineal de OpenCV. Las casillas siguen el orden a8..h1; con negras
abajo se reordenan las casillas completas sin girar los dibujos de las piezas.
Las 16 capturas siguen como referencias y no se incorporan automáticamente como
tableros de entrenamiento. Se conservan las ocho posiciones y los ocho grupos.
No se aplica equilibrado ni división aleatoria por casilla.

La exportación conserva hashes de fotos y referencias, esquinas, etiquetas,
orientación, procedencia, grupo, condiciones y checksums de los arrays. Una huella
de revisión invalida la aprobación si cambia la geometría, la pareja, las etiquetas
o el grupo. Los archivos alterados, las revisiones ausentes y las asociaciones
incoherentes impiden publicar el conjunto. La exportación es atómica y rechaza
sobrescribir un destino existente.

Para reproducirla en otra carpeta (requiere las imágenes locales):

```bash
python -m tools.build_targeted_photo_squares --output .cache/phone-targeted-squares-rebuild
```

Pruebas de preparación:

```bash
python -m pytest tests/test_targeted_photo_squares.py tests/test_phone_squares.py tests/test_phone_geometry.py -q
```

Los recortes están preparados para montar el conjunto de entrenamiento y
permanecen como **desarrollo**, con `readyForTraining: false`: esta exportación
no asigna por sí misma las fotos al entrenamiento. La comprobación de
solapamientos siguiente está completada, con incertidumbre de procedencia restante.
No se han modificado particiones antiguas ni modelos ni ejecutado entrenamiento
o evaluación final. Esta tarea no mide precisión ni declara nueva compatibilidad.

## Solapamientos con la validación existente — 13 de noviembre de 2026

[Informe detallado reproducible](../../data/reports/phone-targeted-overlap-v1.json).
Se compararon las 24 fotos y sus 16 referencias con las **30 fotografías de
validación existentes**: archivos originales, archivos normalizados y píxeles RGB.
Las ocho posiciones se compararon en orden canónico y mediante la comprobación
conservadora de familias existente (giros, reflejos e intercambio de colores).
También se compararon los identificadores de procedencia conocidos, distinguiendo
la plataforma.

| Comprobación | Resultado |
| --- | --- |
| Originales, archivos normalizados o píxeles duplicados frente a validación fotográfica | 0 |
| Posiciones o familias de posición coincidentes frente a validación fotográfica | 0 |
| Partidas/vídeos identificados compartidos frente a validación fotográfica | 0 |
| Familias coincidentes con las 12 posiciones de validación digital generada | 0 |
| Familias o procedencias identificadas coincidentes con las 161 fotos anteriores de desarrollo | 0 |

La posición de validación fotográfica más parecida difiere en **16–31 casillas**,
según la posición nueva. Es una comprobación aproximada de similitud, no una
prueba de partidas distintas ni una distancia en jugadas legales. La comparación
con desarrollo utiliza sus anotaciones existentes; solo se volvieron a verificar
los archivos del lote nuevo y de validación fotográfica.

Las seis partidas nuevas identificadas de Chess.com son distintas de las cinco
partidas identificadas en validación (10 fotos). Las series nuevas 5/6 de Lichess
no tienen identificador, y **20 fotos de validación** tampoco tienen un identificador
verificado de partida/vídeo. No podemos comparar completamente su procedencia.
La confirmación del usuario establece que las series 5 y 6 son partidas distintas
entre sí, no que sean distintas de todas las fuentes anteriores.

**Decisión:** no se ha encontrado un conflicto que obligue a retirar fotos.
Al preparar el siguiente plan de entrenamiento, mantendremos cada grupo junto,
documentaremos la incertidumbre restante y conservaremos la validación fuera del
entrenamiento. Que ambos conjuntos tengan los mismos estilos de piezas y fondos
es deseable; lo que debemos evitar es repartir el mismo ejemplo, sus variantes
o material relacionado de una partida entre ambos conjuntos. Esta validación ya
consultada sirve para desarrollo, no para declarar una aceptación independiente.
No se ha ejecutado ningún modelo ni consultado la evaluación final reservada.

Para repetir la comprobación (requiere las imágenes locales):

```bash
python -m tools.audit_targeted_photo_overlap
python -m pytest tests/test_targeted_photo_overlap.py -q
```

## Entrenamiento posterior

Los recortes revisados se asignaron después al entrenamiento mediante un plan
separado. Véase el [entrenamiento y la comparación completados](targeted-photo-training.md).
El inventario y la exportación originales conservan su condición de desarrollo,
sus revisiones y sus hashes.
