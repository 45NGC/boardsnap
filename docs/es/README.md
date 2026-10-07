# BoardSnap

[English](../en/README.md) | **Español**

`boardsnap` será un motor Python que recibe una imagen de un tablero de ajedrez
digital o un diagrama de libro y devuelve una única colocación de piezas para
la aplicación Flutter **chess-scanner**.

**Estado: flujo Python y CLI JSON con tres perfiles digitales evaluados.**
La [guía de perfiles](profiles.md) describe brown/cburnett, blue/cburnett y el
estilo verde capturado de Chess.com. El perfil de libros es **experimental**:
126/128 casillas reservadas correctas, pero 0/2 posiciones completas. Hay 65
imágenes (51 de ajuste y 14 reservadas). La [integración Flutter](flutter-integration.md)
se documenta mediante un futuro adaptador HTTPS para Android, iOS y web; no está implementada.

La [entrada de imágenes](image-input.md) lee PNG/JPEG estáticos como imágenes
RGB cargadas y ofrece errores estructurados mediante `ImageInputError`.
La [detección](detection.md) devuelve los límites de la cuadrícula brown de lichess.
La [normalización y segmentación](normalization.md) producen una matriz de 8 × 8
recortes RGB de 64 × 64, conservando el origen completo para orientar después.
La [orientación](orientation.md) lee las coordenadas interiores del perfil y
ordena las casillas, asumiendo blancas abajo cuando no hay pistas utilizables.
El [clasificador](classification.md) reconoce trece clases con plantillas de ajuste.
`boardsnap.pipeline.recognize_image(path)` devuelve la colocación de piezas.
La [CLI](cli.md) ofrece `boardsnap imagen.png` con JSON y códigos de salida.
El primer conjunto contiene 20 PNG anotados
(16 de ajuste y 4 de evaluación) del perfil `lichess-cburnett-brown-v1`.
Los ejemplos JSON describen el contrato de salida;
no representan resultados del reconocimiento de imágenes.

Una [herramienta de captura](capture-data.md) separada recoge imágenes y etiquetas
conocidas del editor de lichess. Utiliza el extra opcional de dependencias `capture`.

## Alcance

El motor localizará un tablero, lo recortará y normalizará, lo dividirá en
64 casillas, identificará piezas y resolverá la orientación antes de serializar
la posición. La salida contendrá exclusivamente el primer campo del FEN:

```json
{
  "piecePlacement": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR"
}
```

No habrá interfaz, editor, análisis de partidas, turno, enroque ni captura al
paso. Tampoco se devolverán puntuaciones de confianza, casillas dudosas,
alternativas ni solicitudes de confirmación. Las correcciones de piezas
corresponderán al editor de chess-scanner.

El [contrato de salida](output-contract.md) define el orden de las casillas,
la orientación por defecto y los errores estructurados. El [diseño Flutter](flutter-integration.md)
propone HTTPS; el núcleo sigue independiente de Flutter y de frameworks web.

La [explicación de output.py](output-walkthrough.md) recorre el código de la
función de salida paso a paso, con ejemplos de validación y compresión de huecos.

## Instalación para desarrollo

Requiere Python **3.11 o posterior**, `pip` y soporte de `venv`. Desde la raíz
del repositorio, en una shell POSIX:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
python -c "import boardsnap; print(boardsnap.__file__)"
```

Si la distribución de Python no incluye `ensurepip`, instala el soporte de
entornos virtuales de tu sistema antes de crear `.venv`.

Pillow decodifica imágenes; NumPy y OpenCV sin interfaz gráfica permiten detectar
el tablero. `setuptools` construye el paquete y el extra `dev` instala `pytest`.
PyTorch todavía no se ha añadido; su comparación posterior puede usar este mismo perfil.

## Estructura

```text
src/boardsnap/
    __init__.py
    output.py            # Validación de matrices y serialización de la colocación
    image_input.py       # Decodificación PNG/JPEG, normalización RGB y errores
    profiles.py          # Colores, recursos y coordenadas de cada perfil
    detection.py         # Límites de cuadrícula del perfil elegido
    normalization.py     # Escalado y conservación de pistas de orientación
    segmentation.py      # 64 recortes independientes en orden visual
    orientation.py       # Lectura de coordenadas y orden canónico
    assets/              # Plantillas de coordenadas extraídas de datos de ajuste
    classification.py    # Referencia de plantillas para trece clases
    pipeline.py          # API Python de imagen a piecePlacement
    adapters/cli.py       # CLI JSON separada del reconocimiento
    __main__.py          # Entrada python -m boardsnap
tools/                   # Capturas y vistas previas de detección/casillas
docs/
    en/                 # Documentación en inglés
    es/                 # Documentación en español
data/manifests/          # Manifiesto fijo y asignación de particiones
data/tuning/             # 51 imágenes de ajuste y anotaciones
tests/
    README.md
    test_output.py       # Especificación de salida previa a la implementación
    test_dataset.py      # Integridad de imágenes, anotaciones y particiones
    fixtures/evaluation/ # 14 imágenes reservadas y anotaciones
```

La [arquitectura](architecture.md) describe el flujo y la separación de
responsabilidades. Todas las etapas del núcleo y su coordinación están implementadas para el primer perfil. La
[hoja de ruta](roadmap.md) compara enfoques y fija las siguientes iteraciones.
Las guías de [datos de ajuste](tuning-data.md) e
[imágenes de evaluación](evaluation-data.md) describen las particiones actuales.
Ambos idiomas contienen los mismos documentos; al cambiar el contrato o el
alcance, se actualizarán las dos versiones.

El código, los comentarios, la configuración y los archivos generales del
proyecto se escriben en inglés. El contenido en español se limita a la
documentación de `docs/es/`.

## Pruebas

Después de instalar el extra `dev`:

```bash
python -m pytest
python -m pytest --collect-only
```

Las 53 pruebas de salida cubren la serialización y la validación de la matriz
interna, no el reconocimiento de imágenes ni la detección de orientación.
También se ejecutan las pruebas de validación de capturas. Las pruebas locales
opcionales con navegador requieren activación expresa; consulta la
[guía de captura](capture-data.md). Las pruebas de integridad de datos se ejecutan
por defecto y también con `python -m pytest -m evaluation`; no miden precisión
de reconocimiento.

La configuración está en `pyproject.toml`. Para ejecutar solo las primeras
pruebas unitarias:

```bash
python -m pytest -m unit
```

El [plan de pruebas](testing.md) incluye detección, orientación, piezas,
serialización y errores con posiciones conocidas. Las imágenes de evaluación
estarán separadas de las utilizadas para ajustar el reconocimiento.

## CLI

Después de instalar el paquete:

```bash
boardsnap imagen.png
```

El comando produce un objeto JSON por imagen sin depender de la integración con
Flutter. `python -m boardsnap imagen.png` es equivalente. Reinstala una vez el
paquete editable para registrar el comando. Consulta [uso, errores y códigos](cli.md).

## Estilos y limitaciones

Consulta los [perfiles evaluados](profiles.md) para los tres estilos digitales,
el experimento de libros, los resultados reservados y sus límites. Brown sigue
siendo el perfil predeterminado; selecciona los demás con `--profile`.

Quedan fuera las fotografías de tableros físicos con piezas tridimensionales.
No se presupone compatibilidad con cualquier diseño, color o resolución. Los
primeros perfiles tampoco cubrirán tableros parciales, animaciones, piezas
ocultas, flechas, múltiples tableros o imágenes muy inclinadas o degradadas.
Sin pistas de orientación se asumirá la vista con blancas abajo (`a8` arriba a
la izquierda); una imagen con negras abajo sin coordenadas puede quedar
invertida respecto a la posición real.

## Licencia

El repositorio incluye la [GNU Affero General Public License v3](../../LICENSE).
