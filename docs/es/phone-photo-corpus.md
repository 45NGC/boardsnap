# Corpus de fotografías de pantallas

[English](../en/phone-photo-corpus.md) | **Español**

## Estado — 28 de octubre de 2026

Las **161 fotografías son suficientes para empezar el piloto de geometría**.
Todavía no constituyen un conjunto listo para entrenar ni una demostración de
compatibilidad fotográfica. No se ha ejecutado reconocimiento ni entrenamiento
en esta revisión; los modelos y la entrada de producción siguen intactos.

| Procedencia según carpeta | Fotos | Revisión ampliada | Colocaciones transcritas |
| --- | ---: | ---: | ---: |
| Chess.com | 55 | 55 | 55 |
| Lichess | 53 | 53 | 52 |
| Vídeos | 53 | 53 | 53 |
| Total | 161 | 161 | 160 |

Se ha completado la revisión ampliada de todas las fotos activas: **160 tienen
colocación transcrita y una es ambigua**. Las orientaciones son 89 con blancas
abajo (incluida la ambigua) y 72 con negras abajo, determinadas por las
coordenadas visibles del borde.

- `IMG_5205.HEIC`: eliminada por el usuario y retirada del inventario activo.
  Se conserva un registro de retirada con el hash y el motivo, sin reutilizar
  su copia derivada como muestra activa.
- `lichess-photo-8.HEIC`: rey negro y torre blanca superpuestos en f7 durante una
  animación de captura. Tiene orientación, pero `piecePlacement: null`.
  Se conserva como ambigua, fuera de los ejemplos con colocación completa.
  Si quieres reemplazarla, pausa la reproducción y espera a que termine el
  movimiento antes de fotografiar.

Los 161 originales y sus PNG conservan sus hashes. No hay duplicados exactos
de archivo. Los EXIF identifican un **iPhone 8** en todos ellos. No se han
recibido capturas directas de referencia, FEN ni PGN. Los originales presentes
se conservan sin modificaciones.

La ampliación del 27 de octubre incorpora **72 fotos** (25 de Chess.com,
23 de Lichess y 24 de vídeos), todas transcritas visualmente y convertidas a
JPG/PNG. Se conservan los 89 registros anteriores y los bytes de sus imágenes.
No se han usado predicciones del modelo como etiquetas.

## Archivos y comandos

- Originales: `.cache/real-use-tests/phone-photos/`.
- Copias y hojas de contacto: `.cache/phone-photos-v1/`.
- Copias JPG para revisar: `.cache/phone-photos-v1/jpg/`, separadas en
  `chesscom`, `lichess` y `video`, con los nombres legibles y extensión `.jpg`.
- Abre `.cache/phone-photos-v1/index.html` en el navegador para relacionar cada
  nombre original con su copia de tamaño completo, estado, orientación y colocación.
- [Inventario y anotaciones](../../data/manifests/phone-photos-v1.json).
- [Informe de integridad y cobertura](../../data/reports/phone-photos-intake-v1.json).

Los originales se llaman `chesscom-photo-1.HEIC` a `chesscom-photo-55.HEIC`,
`lichess-photo-1.HEIC` a `lichess-photo-53.HEIC` y `video-photo-1.HEIC` a
`video-photo-53.HEIC`, en sus carpetas respectivas. La numeración sigue el orden
de los antiguos nombres de cámara. El manifiesto conserva `previousOriginalPath`
y los identificadores estables; el mapa local está en
`.cache/real-use-tests/phone-photos/rename-map.json`. Las copias PNG conservan sus
nombres internos y la página de revisión muestra los nombres nuevos. Para nuevas
tomas, continúa desde 56, 54 y 54 respectivamente, sin renumerar las existentes.

El 24 de octubre se exportaron las 89 fotos a JPEG sRGB de tamaño completo,
calidad 95 y sin submuestreo de color. Las 72 nuevas recibieron la misma
conversión el 27 de octubre. La página de revisión enlaza los 161 JPG.
`jpg/export.json` registra la correspondencia y los hashes. Son copias con
compresión para consulta: los HEIC originales y los PNG vinculados a las
anotaciones permanecen intactos. No cuentan como nuevas muestras ni cambian el
formato de los otros corpus del proyecto.

Las imágenes siguen ignoradas por Git. Manifiesto e informe son versionables;
no contienen GPS ni volcados completos de EXIF. El conversor utiliza el extra
opcional `photos`, separado de las dependencias del motor:

```bash
python -m pip install -e '.[photos]'
```

Este lote ya está preparado. Para comprobarlo sin repetir la conversión:

```bash
python -m tools.prepare_phone_photos audit --manifest data/manifests/phone-photos-v1.json --report data/reports/phone-photos-intake-v1.json
```

Para preparar un lote desde cero, usa destinos nuevos. La herramienta rechaza
sobrescribir revisiones existentes o escribir dentro de los originales:

```bash
python -m tools.prepare_phone_photos prepare --source .cache/real-use-tests/phone-photos --output .cache/phone-photos-v1 --manifest data/manifests/phone-photos-v1.json
```

Las copias mantienen el tamaño completo, aplican la orientación del archivo y
convierten el perfil ICC a RGB sRGB. Sin perfil, se registra la suposición sRGB.
No se recortan, rectifican ni enfocan. Los PNG derivados **no son capturas
directas de referencia**. Hay hashes de originales y copias, dimensiones y
metadatos de conversión. La CLI de producción sigue aceptando PNG/JPEG:
instalar este extra no añade HEIC ni corrección de perspectiva al motor.

## Etiquetas del piloto

Son **transcripciones visuales del asistente**, sin utilizar predicciones de
BoardSnap y con `userVerified: false`. Contienen únicamente la colocación de
piezas de a8 a h1 y, por separado, orientación y procedencia de la anotación.
No se inventan turno, enroques ni captura al paso. Estas anotaciones internas no
cambian el contrato JSON de salida.

La revisión del 23 de octubre añadió 71 transcripciones y una marca de
ambigüedad a las 17 transcripciones anteriores. Las nuevas etiquetas incluyen
`visualRows`: filas de arriba abajo y columnas de izquierda a derecha **tal
como aparecen en la foto**, con mayúsculas para piezas blancas. No es un FEN
canónico cuando las negras están abajo. El auditor comprueba que invertir
ambos ejes en ese caso produce exactamente `piecePlacement`.
Las 72 etiquetas añadidas el 27 de octubre también incluyen estas filas visuales.
La orientación describe la vista, no el turno.

Las 160 colocaciones contienen **10240 casillas** y cubren las 13 clases sobre
ambos colores canónicos. Hay **153 colocaciones distintas**, sin que eso implique
153 partidas independientes. Se han registrado siete parejas de posiciones iguales:

- `video-photo-9` / `video-photo-10`.
- `video-photo-14` / `video-photo-15`.
- `video-photo-16` / `video-photo-18`.
- `video-photo-26` / `video-photo-27`.
- `chesscom-photo-26` / `lichess-photo-1`, entre Chess.com y Lichess.
- `lichess-photo-31` / `lichess-photo-39`, con fondo azul y verde.
- `video-photo-37` / `video-photo-40`, sin flechas y con flechas.

La cobertura sigue desequilibrada: solo 19 reyes blancos en casillas claras
y 23 damas negras en casillas claras. Los recuentos incluyen posiciones
relacionadas y variantes; no son métricas de precisión ni muestras independientes.
Se comprobaron el formato de ocho filas, la conversión de orientación y la
integridad de los archivos. La revisión visual del asistente no sustituye una
segunda revisión independiente de las etiquetas antes de entrenar.

## Revisión de transcripciones y esquinas

El 28 de octubre se contrastaron las **161 fotos rectificadas** con diagramas
construidos a partir de las transcripciones existentes. Las 160 colocaciones y
sus orientaciones coincidieron con las piezas visibles; no fue necesario
cambiar ninguna. `lichess-photo-8` sigue siendo ambigua y queda excluida de
clasificación. Es una segunda pasada visual del asistente, **no una revisión
humana independiente**: `userVerified` sigue siendo `false`.

Las **161 fotos tienen cuatro esquinas anotadas** en `boardCorners`. Son
coordenadas `[x, y]` de los límites de la cuadrícula en el PNG RGB completo,
después de aplicar la orientación EXIF. El origen es la esquina superior
izquierda de la imagen, x crece hacia la derecha e y hacia abajo. El orden es
**superior izquierda, superior derecha, inferior derecha, inferior izquierda**,
independientemente de si las blancas o las negras están abajo. No incluyen
relojes ni márgenes de la interfaz. No se debe aplicar EXIF de nuevo.

Se propusieron cuadriláteros mediante contornos y se ajustaron con las líneas
interiores; después se revisaron visualmente los recortes y su alineación en
ocho filas y columnas. En `video-photo-45` se corrigió manualmente una propuesta
que incluía márgenes izquierdo e inferior, y se volvió a revisar el resultado.
En `lichess-photo-22`, la esquina superior derecha toca el borde de la imagen:
se acotó a él una extrapolación de unos dos píxeles de la imagen completa.
No puede descartarse un recorte mínimo de esa esquina; queda documentado en
su anotación y no debe usarse como ejemplo de borde completamente despejado.

`geometryReview` vincula las esquinas con el hash del PNG y registra el método,
fecha y autor. `label.rectifiedReview` conserva la colocación, orientación y
esquinas revisadas. El auditor rechaza coordenadas inválidas o cruzadas y
revisiones que ya no correspondan a la imagen, geometría o etiqueta actuales.
Estas esquinas son referencias para preparar los datos: **no son resultados
del detector fotográfico** ni demuestran que la CLI reconozca estas fotos.

Abre `.cache/phone-photos-v1/geometry/index.html` para ver, en cada fila,
la foto con su cuadrilátero, el tablero rectificado y el diagrama transcrito.
La página habitual `.cache/phone-photos-v1/index.html` también enlaza la
comparación de cada foto. Para regenerar las vistas desde las anotaciones:

```bash
python -m tools.review_phone_geometry
```

La herramienta verifica los hashes y genera vistas de revisión de 512×512,
con interpolación lineal y en el orden visual de la fotografía. No gira las
piezas ni cambia los originales. Los PNG rectificados y `geometry/export.json`
son artefactos locales de revisión; todavía no son un conjunto de casillas
particionado para entrenamiento. No se ha entrenado ni modificado ningún modelo.

Los [recortes de las 160 fotos válidas](phone-squares.md) ya están preparados: 10.240 casillas con trazabilidad, todas en desarrollo. La validación separada por procedencia sigue pendiente.

## Grupos y particiones

**161 desarrollo, 0 entrenamiento, 0 validación y 0 evaluación final.**
Es un estado provisional seguro, no una división de entrenamiento terminada.

Hay secuencias de partidas relacionadas y un contexto de vídeo compartido.
Sus procedencias no se han registrado sistemáticamente. No se puede asumir
independencia por tener posiciones distintas o pertenecer a carpetas distintas.
Todo el lote comparte `phone-photos-unresolved-origin-v1`; el auditor rechaza
mover registros aislados a otra partición. Los entrenadores no deben consumir
este formato de recepción.

Antes de entrenar, hay que identificar partidas/vídeos, unir sus variantes,
comprobar coincidencias con corpus anteriores y fijar una nueva versión de las
particiones. La posición inicial de `video-photo-4` ya es contenido conocido. No se
ha consultado el conjunto final reservado para este inventario.

Si no se recupera la procedencia, este lote puede seguir como desarrollo.
Para validar harán falta nuevas series de partidas identificadas y separadas
desde su recogida. La evaluación final independiente se recogerá después,
con el candidato y los criterios fijados.

Ya hay algunas pistas de procedencia registradas: seis identificadores de
partida se leen en las direcciones del navegador de las fotos nuevas de
Chess.com; los jugadores y títulos de vídeos aportan pistas parciales en otras.
Son observaciones visuales, no descargas verificadas ni pruebas de independencia
respecto al corpus anterior. El usuario no puede recuperar más información de
procedencia, por lo que se mantiene el grupo conservador de desarrollo.

En `video-photo-37`–`45` y `48`–`53`, las etiquetas describen el **tablero
central grande**; aparecen otros tableros en el vídeo o las recomendaciones.
Se registra en `source.targetBoard` y `multiple-visible-boards`. Las esquinas
anotadas señalan ese tablero. No demuestra que la CLI actual admita automáticamente
imágenes con varios tableros.

## Qué conviene añadir

**No hacen falta más fotos antes del piloto de geometría.** El nuevo lote añade
fondos azules y verdes, texturas de madera, varias siluetas de piezas distintas,
ambas orientaciones, flechas, resaltados de jaque y puntos de movimientos.
Los nombres oficiales de los temas siguen sin confirmarse. Se mantiene el
iPhone 8 y un entorno de monitor parecido; hay moiré y bandas de color.

Con las etiquetas y esquinas revisadas, el siguiente paso es preparar la
rectificación y exportación de casillas bajo una política de particiones segura.
Si las mediciones posteriores muestran carencias, añadir ejemplos dirigidos de partidas o vídeos
identificados, otros ángulos, iluminación, pantallas o cámaras y negativos
separados (sin tablero o con tablero cortado). Conservar una captura directa
cuando sea posible; transcribir la posición no recupera los píxeles ni la
procedencia que faltan.

La toma ambigua ya está excluida de clasificación. Para cerrar la fase 5
quedan establecer particiones seguras por procedencia y preparar el formato
que consumirá el entrenamiento. Si no se recuperan
las identidades, este corpus puede quedarse en desarrollo y recoger nuevas
series identificadas para validar. La cantidad de fotos no garantiza precisión.

## Verificación

```bash
python -m pytest tests/test_phone_geometry.py tests/test_phone_photos.py tests/test_image_input.py tests/test_real_positions.py -q
```

87 pruebas pasaron, incluido el caso HEIC del extra `photos`. Cubren conservación
de originales, orientación EXIF, conversión, hashes, rechazo de sobrescrituras,
etiquetas ambiguas, coherencia entre lectura visual y orientación y bloqueo de
particiones no revisadas. También comprueban el orden y la validez de las
esquinas, revisiones desactualizadas y la correspondencia de las 64 casillas
al rectificar una imagen sintética con perspectiva. HEIC se omite si no
está instalado el extra. La prueba del manifiesto no necesita imágenes locales;
el auditor sí comprueba los 161 originales y PNG. Son verificaciones de datos,
no mediciones del reconocimiento fotográfico.
