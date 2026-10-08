# Capturas configurables

[English](../en/configurable-capture.md)

El [primer corpus limpio de clasificación](first-clean-corpus.md) contiene 3600
capturas verificadas: seis juegos de piezas sobre tres fondos cada uno, ambas
orientaciones y dos tamaños. Sus 80 posiciones conservan las particiones fijadas
de entrenamiento/validación/evaluación. La comprobación separada de 36 imágenes
queda excluida. El entrenamiento del modelo sigue pendiente.

Ejecuta estas herramientas desde la raíz del repositorio. Recogen imágenes
etiquetadas; no añaden perfiles de reconocimiento ni entrenan un modelo. Los
comandos anteriores siguen disponibles para los conjuntos de dos particiones.

## Capturas limpias de las plataformas

Instala una vez la dependencia opcional de navegador:

```bash
python -m pip install -e '.[dev,capture]'
export PLAYWRIGHT_BROWSERS_PATH="$PWD/.cache/ms-playwright"
python -m playwright install chromium
python -m tools.capture_batch capture tools/capture-clean.example.json --output-root .cache/configurable-captures --validate-only
python -m tools.capture_batch capture tools/capture-clean.example.json --output-root .cache/configurable-captures
```

El ejemplo solicita **16 imágenes**: dos posiciones de entrenamiento, cuatro
configuraciones (Lichess verde/Merida y morado/Alpha; Chess.com azul/Classic y
marrón/Bases), cada una desde ambas orientaciones. Las dos posiciones pertenecen
al mismo grupo de origen: es un piloto para verificar la herramienta, no una
evaluación independiente de precisión. No se utilizan posiciones de evaluación
para depurar capturas. Git ignora los resultados de `.cache/`.
El [informe de verificación del piloto](../../data/reports/configurable-capture-pilot-v1.json)
registra hashes, configuración y procedencia de los 16 PNG locales sin subir
las capturas al repositorio. Otra comprobación añade dos imágenes con viewport
1024 × 900 y densidad 2 (PNG de 2048 × 1800), en `g1-size-pilot-v1`.

Copia la receta y elige otro `batchId` para ampliarla. Contiene exactamente:
`schemaVersion: 1`, `batchId`, `positionIds` y `configurations`.
Cada configuración especifica:

| Campo | Significado |
| --- | --- |
| `id` | Identificador único de configuración en minúsculas |
| `platform` | `lichess` o `chesscom` |
| `boardTheme`, `pieceSet` | Nombres independientes de estilos, en minúsculas con guiones |
| `orientations` | Una o ambas: `white-bottom`, `black-bottom` |
| `viewport` | `width` y `height` del navegador en píxeles CSS, enteros 320–2560 |
| `deviceScaleFactor` | 1, 2 o 3; píxeles guardados por píxel CSS |
| `conditions` | Actualmente exactamente `["clean"]` |

El viewport determina el tamaño adaptable del tablero; no fija su anchura exacta.
Un viewport pequeño puede fallar si no cabe todo el tablero. Sigue siendo web de
escritorio: estrechar la ventana no demuestra compatibilidad con apps móviles.
La disponibilidad de estilos se comprueba en la plataforma; aceptar un nombre
no implica reconocerlo. Un estilo no disponible falla sin sustituirlo por otro.
`--validate-only` comprueba la receta y las particiones sin consultar estilos
remotos. `--headed` muestra Chromium. Capturar requiere conexión a Internet.

La estructura de salida es:

```text
<output-root>/digital-positions-v1/<batchId>/
    batch.json
    <training|validation|evaluation>/<configurationId>/
        <positionId>-<orientation>.png
        <positionId>-<orientation>.json
```

Cada JSON conserva `piecePlacement` canónico, posición/grupo/partición heredados,
orientación, configuración, dimensiones y SHA-256 del PNG, límites en **píxeles
del PNG guardado**, URL de origen, versión del navegador, fecha UTC, recursos
gráficos y comprobaciones. Los límites pueden ser fraccionarios; derecha y abajo
son exclusivos (`x + width`, `y + height`). El lote guarda la receta y un hash
del manifiesto de posiciones. Se rechaza otro hash de plan bajo un
identificador de conjunto que ya tenga lotes. Nunca repartas por separado temas, orientaciones
o recortes de casillas.

La publicación es atómica: un fallo no deja un lote parcial. No se sobrescriben
lotes existentes; utiliza otro identificador. Un bloqueo por conjunto evita
publicaciones simultáneas. Códigos de salida: 0 correcto, 2 entrada/verificación
inválida, 1 otros fallos de navegador. El progreso va a stderr; stdout contiene
un mensaje de estado, no el contrato JSON de la CLI de reconocimiento.

## Qué se verifica realmente

Antes **y** después de la captura se comparan tipos/colores de piezas, sus casillas,
orientación, recursos gráficos efectivos de fondo y piezas, carga de imágenes,
visibilidad, tablero sin cubrir y ausencia de marcas visibles. Se rechazan piezas
en movimiento y cambios durante la captura. Se decodifica el PNG y se verifican
dimensiones y límites antes de guardarlo. El nombre mostrado por un selector no
basta para aceptar el estilo.

Lichess utiliza sus controles anónimos de apariencia y su manifiesto de recursos.
Chess.com consulta el catálogo público que carga su panel de ajustes del tablero,
acepta solo recursos web desbloqueados y piezas vistas desde arriba, y los aplica
al **renderizador local del tablero**. Guardar preferencias como visitante puede
fallar aunque el selector muestre el nombre solicitado. Así se evitan escrituras
de preferencias de cuenta y se verifican los recursos que realmente se dibujan.

Son páginas automatizadas modificadas: en Lichess se ocultan campos de respuesta
y control de tamaño; en Chess.com se cierran diálogos iniciales y de cookies, y se
ocultan flechas/resaltados/campos de respuesta. Las modificaciones quedan anotadas.
No son capturas intactas de uso real. Los adaptadores dependen del DOM y de las
API de recursos actuales y pueden necesitar mantenimiento si cambian las plataformas.
Generar marcas queda pendiente; solicitarlas al capturador automático provoca error.

## Importar capturas de uso real

Utiliza PNG originales tomados durante análisis o juego real, independientemente
del editor automatizado. Revisa manualmente posición, orientación, límites del
tablero completo, estilos, interfaz y marcas visibles; agrupa las posiciones
relacionadas de una misma partida. El comando no inventa ni aporta esas imágenes.

Actualmente `import-real` solo acepta posiciones del plan congelado. Para una
partida ajena al plan, primero habrá que ampliar el esquema para representar su
procedencia real y congelar el grupo y la partición. El validador actual solo
admite secuencias generadas; `--manifest` no evita esa restricción. No etiquetes
una posición distinta como una existente para conseguir que encaje.

Crea un JSON con `schemaVersion: 1`, un `batchId` nuevo y una lista `samples`.
Cada elemento debe contener:

- `id`, `positionId`, `image` (ruta relativa al JSON), `sha256` de los bytes originales.
- `orientation`, `reviewed: true`, `reviewedPlacement` (primer campo FEN canónico).
- `boardBounds: {"x": ..., "y": ..., "width": ..., "height": ...}` en píxeles originales.
- `configuration`: `platform`, `boardTheme`, `pieceSet`, `layoutId`, `conditions`.
  Las condiciones son `["clean"]` o las marcas observadas `arrows`, `highlights`,
  `badges`; nunca se combina clean con marcas.
- `source`: `url`, `capturedAt`, `client`, `clientVersion`, `sourceGroupId`,
  `reviewedBy`, `reviewedAt`. Usa fechas ISO UTC y un ID estable de partida/sesión.
  Clientes: `desktop-web`, `mobile-web`, `android-app`, `ios-app`.

```bash
sha256sum screenshots/original.png
python -m tools.capture_batch import-real review.json --output-root data/datasets --validate-only
python -m tools.capture_batch import-real review.json --output-root data/datasets
```

La revisión es una declaración humana, no una comprobación visual automática.
El hash asegura que no han cambiado los bytes revisados. El PNG se copia intacto
a `<split>/real-use/`; la procedencia indica revisión humana sin evidencia DOM.
Se rechazan etiquetas contradictorias de imágenes idénticas y grupos de partidas
que cruzan particiones, incluidos lotes anteriores **del mismo directorio raíz**.
Usa una única raíz de referencia: raíces distintas no permiten comprobar el
aislamiento global. Importar imágenes con marcas no implica poder reconocerlas.

Conserva las atribuciones de origen y recursos al incorporar un corpus a Git;
consulta los [avisos de terceros](../../data/THIRD_PARTY_NOTICES.md). El piloto
queda local hasta revisar su incorporación; las imágenes de reconocimiento
anteriores no cambian.

## Pruebas

```bash
python -m pytest tests/test_capture_batch.py tests/test_capture_sites.py
BOARDSNAP_BROWSER_TESTS=1 python -m pytest tests/test_capture_batch.py tests/test_capture_sites.py
python -m pytest
```

Las pruebas de navegador utilizan DOM y gráficos inventados locales con peticiones
interceptadas: ambas orientaciones, dos densidades de píxeles, recursos/piezas
incorrectos, recortes, diálogos, marcas y cambios durante la captura. Las pruebas
del catálogo rechazan estilos bloqueados, incompletos, sin web o en 3D. Las de
importación comprueban revisión, bytes originales, particiones heredadas,
fallos atómicos y aislamiento entre lotes. Miden integridad de la recogida, no
precisión del reconocimiento.
