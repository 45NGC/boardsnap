# Corpus de fotografías de pantallas

[English](../en/phone-photo-corpus.md) | **Español**

## Estado — 22 de octubre de 2026

Las **90 fotografías son suficientes para empezar el piloto de geometría**.
Todavía no constituyen un conjunto listo para entrenar ni una demostración de
compatibilidad fotográfica. No se ha ejecutado reconocimiento ni entrenamiento
en esta revisión; los modelos y la entrada de producción siguen intactos.

| Procedencia según carpeta | Fotos | Revisión ampliada | Colocaciones transcritas |
| --- | ---: | ---: | ---: |
| Chess.com | 30 | 6 | 6 |
| Lichess | 30 | 6 | 6 |
| Vídeos | 30 | 6 | 5 |
| Total | 90 | 18 | 17 |

Se inspeccionaron las 90 en hojas de contacto y 18 en copias ampliadas. Las **72
restantes tienen etiquetas pendientes**, no predicciones. `IMG_5205.HEIC`
muestra una dama negra durante una animación, con varias siluetas entre casillas.
Se conserva como ambigua, sin colocación esperada. Para reemplazarla, pausa el
vídeo y espera a que termine el movimiento antes de fotografiar.

Todos los HEIC se decodifican, sin duplicados de archivo exactos. Los EXIF
identifican un **iPhone 8** en los 90. No se han recibido capturas directas de
referencia, FEN ni PGN. Los originales se conservan sin modificaciones.

## Archivos y comandos

- Originales: `.cache/real-use-tests/phone-photos/`.
- Copias y hojas de contacto: `.cache/phone-photos-v1/`.
- Abre `.cache/phone-photos-v1/index.html` en el navegador para relacionar cada
  nombre original con su PNG de tamaño completo.
- [Inventario y anotaciones](../../data/manifests/phone-photos-v1.json).
- [Informe de integridad y cobertura](../../data/reports/phone-photos-intake-v1.json).

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

| Carpeta | Archivos revisados en detalle |
| --- | --- |
| `chesscom-photos` | `IMG_5228`, `IMG_5234`, `IMG_5238`, `IMG_5246`, `IMG_5248`, `IMG_5257` |
| `lichess-photos` | `IMG_5258`, `IMG_5264`, `IMG_5267`, `IMG_5276`, `IMG_5283`, `IMG_5289` |
| `video-photos` | `IMG_5195`, `IMG_5197`, `IMG_5205` (ambigua), `IMG_5214`, `IMG_5220`, `IMG_5223` |

Las 17 colocaciones cubren 1088 casillas y las 13 clases sobre ambos colores
canónicos. No demuestra legibilidad ni precisión del modelo. En esta muestra
solo hay dos damas negras en casilla clara y tres reyes blancos en casilla
clara: no está equilibrada. Además, varias fotos pertenecen a secuencias
relacionadas, por lo que no representan ejemplos independientes.

Las cuatro esquinas siguen pendientes (`boardCorners: null`). Se anotarán
sobre los PNG completos para estudiar rectificación, sin sustituirlas por
rectángulos aproximados. Un tablero dibujado a partir de un FEN podría ayudar a
revisar las piezas, pero no sería una captura original.

## Grupos y particiones

**90 desarrollo, 0 entrenamiento, 0 validación y 0 evaluación final.**
Es un estado provisional seguro, no una división de entrenamiento terminada.

Hay secuencias de partidas relacionadas y un contexto de vídeo compartido.
Sus procedencias no se han registrado sistemáticamente. No se puede asumir
independencia por tener posiciones distintas o pertenecer a carpetas distintas.
Todo el lote comparte `phone-photos-unresolved-origin-v1`; el auditor rechaza
mover registros aislados a otra partición. Los entrenadores no deben consumir
este formato de recepción.

Antes de entrenar, hay que identificar partidas/vídeos, unir sus variantes,
comprobar coincidencias con corpus anteriores y fijar una nueva versión de las
particiones. La posición inicial de `IMG_5197` ya es contenido conocido. No se
ha consultado el conjunto final reservado para este inventario.

Si no se recupera la procedencia, este lote puede seguir como desarrollo.
Para validar harán falta nuevas series de partidas identificadas y separadas
desde su recogida. La evaluación final independiente se recogerá después,
con el candidato y los criterios fijados.

## Qué conviene añadir

No completaría las 200 repitiendo estas condiciones. Ya hay perspectiva, giro,
distancias distintas, aperturas, medio juego, finales, ambas orientaciones,
resaltados y algunas flechas. Hay bandas de color e interferencia al fotografiar
la pantalla (*moiré*). Predominan fondos marrones, pocos diseños y un entorno
de monitor parecido; los nombres exactos de los temas no están confirmados.

Después del piloto, priorizaría **20–30 fotos adicionales**, si hace falta
ampliar, de varias partidas o vídeos nuevos e identificados:

1. Otros fondos y juegos de piezas, sin cambiar todos los factores a la vez.
2. Otros ángulos, distancias e iluminación; otro monitor o teléfono si lo tienes.
3. Variantes de una posición con una foto frontal clara y una captura directa
   del ordenador cuando sea posible. Conserva enlace e instante; el FEN puede
   transcribirse después. Pausa animaciones y conserva el tablero completo.
4. Algunas fotos sin tablero o con tablero cortado, identificadas como negativos
   y separadas de las imágenes con colocación completa.

Es una propuesta para cubrir carencias, no una garantía de precisión. Para
cerrar la fase 5 quedan las otras 72 etiquetas, recuperar o sustituir referencias
cuando haya dudas y separar procedencias verificadas. El piloto ya permite
empezar a anotar esquinas y estudiar rectificación sin entrenar con dudas.

## Verificación

```bash
python -m pytest tests/test_phone_photos.py tests/test_image_input.py tests/test_real_positions.py -q
```

63 pruebas pasaron, incluido el caso HEIC del extra `photos`. Cubren conservación
de originales, orientación EXIF, conversión, hashes, rechazo de sobrescrituras,
etiquetas pendientes y bloqueo de particiones no revisadas. HEIC se omite si no
está instalado el extra. La prueba del manifiesto no necesita imágenes locales;
el auditor sí comprueba los 90 originales y PNG. Son verificaciones de datos,
no mediciones del reconocimiento fotográfico.
