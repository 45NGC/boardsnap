# Conjunto de casillas fotográficas

[English](../en/phone-squares.md) | **Español**

El [corpus fotográfico revisado](phone-photo-corpus.md) tiene una exportación de
**160 tableros × 64 casillas = 10.240 recortes RGB**. Se excluye la animación
ambigua de `lichess-photo-8`. No se ha entrenado ni modificado ningún modelo.

**Actualización del 2026-10-30:** el [conjunto de entrenamiento](phone-training-data.md)
reutiliza estos 160 archivos y añade 30 tableros nuevos de validación. La
exportación de desarrollo descrita abajo se conserva como referencia original.

## Archivos y comandos

Abre `.cache/phone-squares-v1/index.html` para inspeccionar los recortes con su
casilla y etiqueta. Los píxeles se muestran intactos; las etiquetas se dibujan
fuera de cada recorte. Cada tablero tiene un archivo comprimido `.npz` en
`development/` que contiene:

- `images`: 64 recortes RGB de 64×64 píxeles, `uint8`, forma `(64, 64, 64, 3)`.
- `class_ids`: 64 etiquetas con el orden de las 13 clases utilizado en el proyecto.

Son archivos agrupados, no 10.240 imágenes sueltas. Es la misma representación
de matrices que utilizan las herramientas del clasificador.
`verified.jsonl` relaciona cada casilla con la foto, posición, orientación,
grupo de procedencia, hashes del original y PNG, esquinas y revisión de etiquetas.
También registra sus coordenadas canónicas y visuales dentro del tablero.
`dataset.json` describe el preprocesado, la cobertura y los hashes.
El resumen versionado está en [phone-squares-v1.json](../../data/reports/phone-squares-v1.json).

Para construir una nueva versión desde las anotaciones revisadas:

```bash
python -m tools.build_phone_squares --output .cache/phone-squares-v2 --report data/reports/phone-squares-v2.json
```

La herramienta rechaza destinos existentes. Audita las entradas, comprueba las
matrices guardadas y publica la carpeta solo cuando termina la construcción.
Una revisión ausente o desactualizada, o un archivo alterado, impide publicarla.

## Geometría y etiquetas

Cada PNG RGB completo se rectifica a 512×512 a partir de sus cuatro esquinas
revisadas, con interpolación lineal de OpenCV. Después se divide en ocho filas
y ocho columnas. La salida va de a8 a h1. Con negras abajo se invierte únicamente
el orden de las casillas en ambos ejes; los píxeles de las piezas no se giran.
Se conservan resaltados, flechas, moiré y coordenadas visibles.

Son **recortes con geometría de referencia**, destinados al desarrollo del
clasificador. No miden la detección automática de fotos ni el recorrido completo.
No se aplica equilibrado, aumento de datos, inferencia ni etiquetado mediante
predicciones. Los recuentos claro/oscuro describen la paridad canónica de las
casillas, no sus colores RGB. La esquina al borde de `lichess-photo-22` conserva
su limitación documentada en el índice de recortes.

## Estado de las particiones

| Asignación | Tableros | Casillas |
| --- | ---: | ---: |
| Desarrollo | 160 | 10.240 |
| Entrenamiento | 0 | 0 |
| Validación | 0 | 0 |
| Evaluación final | 0 | 0 |

**Esta tabla describe la exportación original de desarrollo.** La nueva
[exportación para entrenar](phone-training-data.md) contiene 160 tableros de
entrenamiento y 30 de validación, sin modificar los archivos anteriores.
`partition-plan.json` registra el grupo conservador, los identificadores de todas
las fotos (incluida la excluida), las pistas de partidas y los requisitos de
validación. Los seis identificadores visibles de Chess.com no demuestran que
esas partidas sean independientes de las fotos sin identificar o del corpus
anterior. Una carpeta, estilo, posición o fecha distintos no bastan para separar.

Las 161 fotos originales mantienen `phone-photos-unresolved-origin-v1` y `development`.
Las posiciones iguales y sus variantes siguen juntas. Los cargadores de
entrenamiento rechazan esta partición; `readyForTraining` es `false`.
No hay que cambiar las cadenas de partición manualmente para saltarse la comprobación.

Para establecer la validación:

1. Recoger nuevas series de partidas o vídeos identificados, guardando URL, ID
   o un identificador local como `partida-01`, y conservar esa identidad para
   todas las fotos y variantes. Los identificadores locales deben representar
   grupos reales de procedencia.
2. Asignar partidas/vídeos completos a validación antes de recortar o seleccionar
   modelos.
3. Revisar procedencias y posiciones iguales o equivalentes frente a desarrollo
   y corpus anteriores; mantener juntas las muestras relacionadas. No consultar
   la evaluación final reservada para ajustar esta decisión.
4. Revisar colocación, orientación y esquinas, y fijar un manifiesto de particiones
   versionado. Cubrir las plataformas, estilos y condiciones fotográficas objetivo.
5. Exportar esa partición aprobada para las herramientas de entrenamiento,
   conservando las frecuencias de validación. Solo entrenamiento podrá equilibrarse
   o ampliarse con transformaciones posteriormente.

El lote actual puede mantenerse como desarrollo o convertirse en entrenamiento
mediante una migración explícita de particiones. No puede proporcionar también
validación independiente reteniendo fotos o casillas al azar. La evaluación final
se recogerá después y por separado.

## Nuevo lote para validación (2026-10-29)

Se han recibido 30 fotos nuevas destinadas a validación: 10 de Lichess
(`IMG_5383`–`IMG_5392`), 10 de Chess.com (`IMG_5393`–`IMG_5402`) y 10 de vídeos
(`IMG_5403`–`IMG_5413`, excepto `IMG_5408`). Se mantienen separadas del manifiesto
original de desarrollo y de sus recortes.

- Galería y copias JPG a tamaño completo: `.cache/phone-validation-v1/index.html`.
- Manifiesto: [phone-validation-v1.json](../../data/manifests/phone-validation-v1.json).
- Comprobaciones de entrada: [phone-validation-intake-v1.json](../../data/reports/phone-validation-intake-v1.json).

Se conservan los originales HEIC y copias PNG RGB normalizadas a tamaño completo.
El usuario confirma que eligió partidas y vídeos distintos de los del lote
anterior, aunque podría repetirse alguna posición por casualidad. Se registra
como procedencia declarada por el usuario, sin presentarla como una comprobación
independiente. Las 30 fotos comparten el grupo conservador
`phone-validation-batch-v1`: no significa que sean de una única partida ni que
representen 30 fuentes independientes. Todo el lote queda fuera del entrenamiento.
Tras revisar las anotaciones y los solapamientos, los 30 registros tienen
`split: validation`. El manifiesto original de 161 fotos de desarrollo no cambia.

Se han revisado visualmente las **30 colocaciones y las 120 esquinas** en las
fotos originales y rectificadas: 22 con blancas abajo y 8 con negras abajo. El
diagrama junto a cada tablero procede de la transcripción, no de una predicción.
Las esquinas son coordenadas de píxeles de la imagen RGB completa, con EXIF ya
aplicado, en orden superior izquierda/derecha e inferior derecha/izquierda.
Excluyen la interfaz y los márgenes externos de coordenadas. La rectificación
conserva la vista fotografiada; la colocación se guarda en orden canónico de a8
a h1. La revisión es del asistente, sin una segunda anotación humana independiente.

Las 30 posiciones distintas contienen **1.920 casillas etiquetadas**, con las 13
clases sobre ambas paridades de casilla. No hay posiciones iguales ni familias
equivalentes (giros, reflejos y cambio de colores) respecto a las 160 posiciones
legibles de desarrollo, ni coincidencias entre los identificadores conocidos de
partidas de Chess.com. Esto no demuestra independencia para partidas sin
identificar o posiciones ausentes del lote anterior. Se registran las cinco
partidas de Chess.com visibles en las direcciones, parejas de jugadores de
Lichess y títulos de vídeos relacionados. En `IMG_5404` se anota solo el diagrama
digital y en `IMG_5406`, el tablero principal grande, no las miniaturas laterales.

La cobertura es desigual: solo hay una dama negra sobre casilla clara y dos
reyes negros sobre casilla oscura. Sirven para el piloto, pero no permiten
afirmar una precisión bien medida para esas combinaciones.

La galería comparativa está en `.cache/phone-validation-v1/geometry/index.html`.
El [informe de anotaciones](../../data/reports/phone-validation-annotations-v1.json)
recoge cobertura, comprobación de archivos y solapamientos. Para repetir las
comprobaciones y regenerar la galería:

```bash
python -m tools.review_phone_validation --output .cache/phone-validation-v1/geometry --report data/reports/phone-validation-annotations-v1.json
```

La posterior [exportación para entrenar](phone-training-data.md) ya contiene
las casillas de validación e índices compatibles con el cargador. El manifiesto
de anotaciones conserva su estado previo a esa exportación; los indicadores del
nuevo conjunto describen la disponibilidad actual. No se ha ejecutado inferencia,
entrenamiento ni evaluación final reservada. Las anotaciones no miden la
detección automática de fotografías.

## Comprobaciones

```bash
python -m pytest tests/test_phone_validation.py tests/test_phone_squares.py tests/test_phone_geometry.py tests/test_phone_photos.py -q
```

Las pruebas cubren las 64 casillas, orden con negras abajo sin girar píxeles,
conservación de originales, exclusiones ambiguas, revisiones desactualizadas,
publicación completa, rechazo de sobrescritura y de particiones no aprobadas.
