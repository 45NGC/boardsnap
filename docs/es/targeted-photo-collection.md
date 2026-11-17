# Recogida fotográfica dirigida

[English](../en/targeted-photo-collection.md) | **Español**

**Piloto y ampliación recibidos y revisados:** hay 24 fotos y 16 capturas en `training2`.
Consulta el [resultado de la revisión](targeted-photo-intake.md) antes de tomar
más imágenes. Las instrucciones siguientes conservan el plan original; la
revisión registra las orientaciones y fondos realmente recibidos.

La comprobación inicial del
5 de noviembre de 2026 encontró los mismos 191 originales registrados (161 de
desarrollo y 30 de validación), sin archivos nuevos, ausentes o con hashes
distintos en `.cache/real-use-tests/phone-photos/`. No se ha entrenado ni ejecutado
inferencia. El [plan del piloto](../../data/manifests/photo-targeted-pilot-v1.json)
registra objetivos de recogida, no muestras recibidas ni etiquetas verificadas.

## Qué fotografías hacen falta

Empezamos con **18 fotos de seis posiciones distintas**, más **12 capturas
directas**: una limpia y otra marcada por posición. Los cambios de cámara no
cuentan como posiciones nuevas. Este piloto cubre seis de las catorce combinaciones
del [catálogo](photo-catalogue.md), priorizando sus carencias medidas.

| Carpeta | Apariencia | Fondo | Vista solicitada | Atención especial |
| --- | --- | --- | --- | --- |
| `session-01` | `cc-thin-stem`, Chess.com | Morado de referencia | Blancas abajo | Peones finos de ambos colores, caballos y casillas vacías |
| `session-02` | `cc-thin-stem`, Chess.com | `brown` | Negras abajo | Peones avanzados sobre ambos colores de casilla |
| `session-03` | `cc-shaded`, Chess.com | Madera de referencia | Blancas abajo | Torres blancas, caballos, alfiles negros y damas |
| `session-04` | `cc-shaded`, Chess.com | `brown` | Negras abajo | Las mismas familias sobre fondo liso; distinguir color |
| `session-05` | `lc-rounded-king`, Lichess | Madera de referencia | Blancas abajo | Rey blanco, damas, caballos y casillas vacías |
| `session-06` | `lc-rounded-king`, Lichess | `brown` | Negras abajo | Piezas de ambos colores y fondos de casilla distintos |

Los nombres son **apariencias visuales**, todavía no selectores oficiales.
Abre [las referencias locales](../../.cache/phone-targeted-v1/index.html) para
ver las fotos que queremos complementar. Guarda también una captura de los
ajustes donde se vean el juego de piezas y el fondo elegidos. Si no localizas
alguno, aporta primero esa captura de ajustes; no hace falta tomar muchas fotos
de un estilo parecido sin confirmar que es el mismo. La página local enlaza las
fotos antiguas; no las copia a entrenamiento ni las cuenta como datos nuevos.

Escoge nuevas posiciones con suficientes piezas y casillas vacías. A lo largo de
las dos posiciones de cada diseño interesa ver ambos colores de pieza sobre
casillas claras y oscuras, especialmente las piezas de la última columna.
No exigimos que una sola posición contenga todas las combinaciones. Puedes usar
un editor si resulta más fácil documentar la posición y modificar las marcas.

## Cómo tomar cada serie

1. Deja el tablero completo, sin animaciones, con la orientación de la tabla.
   Guarda una **captura de pantalla directa limpia** como `reference-clean.png`.
   Un recorte o una rectificación de una foto no sirve como captura directa.
2. Haz `photo-01`: aproximadamente frontal, distancia cómoda e iluminación difusa.
3. Sin cambiar piezas, fondo ni orientación, haz `photo-02`: ángulo lateral
   moderado, distancia algo diferente y una variación suave de luz. Mantén todas
   las esquinas visibles y las piezas legibles. Anota qué has cambiado realmente.
4. Mantén el encuadre, distancia y luz de `photo-02` y añade marcas habituales:
   último movimiento, selección o puntos de movimientos; una flecha sencilla es
   opcional. Guarda `reference-marked.png` y haz `photo-03`. La colocación debe
   seguir siendo idéntica. No ejecutes otra jugada para conseguir un resaltado:
   usa una posición de análisis/editor o registra otra serie si las piezas cambian.

Distribuye las marcas entre casillas vacías y ocupadas, claras y oscuras. Conserva
la lista de casillas o extremos de flecha. No tapes por completo las piezas.
Los pares 02/03 permiten comparar marcas con geometría similar; 01/02 combinan
varias condiciones y no permiten atribuir un fallo exclusivamente a la luz o al
ángulo. No hay que producir reflejos fuertes ni desenfoque deliberado.

## Dónde guardarlas

Las seis carpetas ya están preparadas localmente:

```text
.cache/phone-targeted-v1/incoming/session-01/
  photos/
    photo-01.jpg
    photo-02.jpg
    photo-03.jpg
  references/
    reference-clean.png
    reference-marked.png
    settings.png
  session.json
```

Repite hasta `session-06`. Los nombres de fotos son sugeridos; puedes conservar
los nombres de cámara. Mantén la extensión real: JPG o HEIC son válidos como
originales, **renombrar `.HEIC` a `.jpg` no convierte la imagen**. Para las
referencias, conserva el formato real de captura sin recomprimirlo.

`session.json` separa lo solicitado (`requested`) de lo observado (`observed`),
que permanece vacío hasta la recogida. Puedes rellenarlo o dejar un `notes.txt`
con el juego/fondo elegido, orientación, enlace o identificador de partida/vídeo,
minuto y qué series están relacionadas. Basta una etiqueta como `partida-A` para
relacionar varias series; no es obligatorio tener un enlace. Si utilizas editor,
guarda la colocación o el FEN de referencia en las notas. Si no sabes obtenerlo,
la captura directa permitirá transcribirlo y revisarlo después. El campo interno
`piecePlacement` contendrá solo la colocación, nunca los seis campos del FEN.

No hace falta que anotes las cuatro esquinas ahora. Se revisarán junto con las
piezas y la correspondencia foto/captura al recibir el piloto. Estas carpetas son
una zona de recogida, no un índice de entrenamiento: no ejecutes el conversor
genérico sobre toda la carpeta, porque mezclaría capturas de referencia con fotos.
El importador existente se reutilizará con los originales fotográficos separados
y el emparejamiento revisado.

## Revisión antes de ampliar

- Comprobar identidad del estilo y del fondo, posición, orientación, tablero
  completo y correspondencia exacta con la captura directa.
- Anotar esquinas y condiciones observadas; separar fotos ambiguas o con animación.
  Las predicciones del modelo no serán etiquetas.
- Contar las trece clases por diseño y color de casilla; revisar especialmente
  peones, color de caballos/alfiles y casillas vacías con marcas o textura.
- Buscar duplicados y coincidencias de posición y procedencia con los manifiestos
  actuales. Misma partida/vídeo y todas sus variantes permanecen juntas. Una
  carpeta de sesión **no equivale** a una procedencia independiente.
- Mantener inicialmente el lote como desarrollo pendiente de asignación; no
  repartir fotos o casillas al azar. Si aparece relación con validación existente,
  se conserva esa partición y no se añade a entrenamiento. La procedencia dudosa
  queda agrupada conservadoramente.
- Informar cuántas fotos son utilizables y qué clases, fondos o condiciones faltan.
  Solo entonces decidir el siguiente lote; 18 fotos no garantizan cobertura.

Los controles actuales se conservan: `video-img_5406` introducía un caballo
negro falso en h8 y `video-img_5404` introducía torre/alfil falsos, no caballos.
Sus estilos no coinciden necesariamente con este piloto. Las casillas vacías
nuevas sirven para estudiar el problema, no para declarar resueltos esos casos.
`chesscom-img_5396` y `5399` siguen siendo controles positivos del recorte.
La comparación posterior separará geometría automática y esquinas revisadas.

El piloto y la ampliación de caballos blancos ya fueron aportados por el usuario.
El siguiente trabajo es anotar las esquinas; la revisión enumera los huecos restantes.
Los cuatro estilos convencionales del catálogo siguen como referencias existentes;
su ampliación y las combinaciones aún no recogidas quedan pendientes. No se han
cambiado modelos, particiones anteriores, criterios de aceptación ni evaluación final.
