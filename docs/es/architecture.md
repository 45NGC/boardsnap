# Arquitectura propuesta

[English](../en/architecture.md) | **Español** · [Inicio](README.md)

Esta es la distribución de responsabilidades. La entrada, la detección, la
normalización, la segmentación, la orientación y la
serialización de salida están implementadas; el resto del flujo sigue previsto.
El repositorio inicial contenía únicamente README, licencia y un `.gitignore`
genérico de Python; no existía código de reconocimiento que conservar o migrar.

Se usa un único paquete, `boardsnap`, bajo `src/`. Contiene `__init__.py`
y `output.py`, que valida y serializa una matriz ya clasificada, además de
`image_input.py`, que carga PNG/JPEG y lanza errores estructurados de entrada.
`detection.py` localiza la cuadrícula del primer perfil y devuelve `BoardBounds` inmutable.
`normalization.py` devuelve `NormalizedBoard` con píxeles escalados, una copia
independiente del origen a resolución completa y sus límites. `segmentation.py`
devuelve una matriz de 8 × 8 recortes independientes en orden visual; consulta
la [guía de normalización](normalization.md) para la gestión de imágenes y geometría.
`orientation.py` lee las coordenadas admitidas del origen conservado y reordena
las casillas. Sus plantillas de caracteres se instalan con el paquete y proceden
solo de datos de ajuste; consulta [orientación](orientation.md).
Los demás módulos se crearán al implementar cada responsabilidad; sus nombres son
orientativos. No se anticipan jerarquías de clases, registros de plugins ni
servicios. La
[guía de empaquetado de PyPA](https://packaging.python.org/en/latest/tutorials/packaging-projects/)
describe esta organización y la configuración mediante `pyproject.toml`.

## Flujo previsto

```text
Adaptador (CLI; integración Flutter por decidir)
    → pipeline
        → image_input → detection → normalization → segmentation
        → classification → orientation → output
    → JSON
```

La normalización conserva las pistas de orientación en la copia completa del
origen, incluidos márgenes exteriores y etiquetas internas. `orientation` aplica
la correspondencia de casillas antes de generar la salida; la segmentación no
deduce coordenadas de ajedrez.

| Módulo | Responsabilidad prevista |
| --- | --- |
| `image_input` | Leer bytes o un archivo, decodificar la imagen y validar su contenido. Tratar la orientación del archivo antes del análisis. |
| `detection` | Localizar los límites de una cuadrícula de 8 × 8 sin modificar los píxeles de entrada. |
| `normalization` | Recortar el tablero y ajustar tamaño y geometría sin perder la correspondencia con la imagen original. |
| `segmentation` | Obtener exactamente 64 recortes, indexados por fila y columna en la vista de la imagen. |
| `classification` | Elegir una de 13 clases por recorte: vacío o una de las seis piezas de cada color. |
| `orientation` | Usar pistas verificables o la convención documentada para reordenar la matriz a coordenadas de ajedrez. |
| `output` | Comprobar la estructura de la matriz, comprimir casillas vacías y construir `piecePlacement` o el error acordado. |
| `pipeline` | Coordinar etapas y propagar fallos sin sustituirlos por posiciones inventadas. |
| `adapters` | Traducir la entrada externa y serializar la respuesta; la CLI será el primer adaptador. |

La entrada devuelve un objeto Pillow `Image.Image` RGB completamente cargado;
`ImageInputError.to_dict()` representa los fallos para los futuros adaptadores.
Las demás estructuras se elegirán al implementar sus etapas.
El núcleo no importará los adaptadores ni conocerá HTTP, Flutter o una interfaz
gráfica. El adaptador tampoco contendrá lógica de reconocimiento.

La salida verificará la sintaxis de la colocación, no la legalidad de una partida.
No se recolocarán piezas para forzar una posición legal ni se inventarán datos
como el turno o los derechos de enroque.

## Dependencias

Pillow decodifica y normaliza la entrada. `setuptools` es el backend de
construcción, `pytest` está en el extra de desarrollo y Playwright en el extra
opcional de captura, fuera del núcleo de reconocimiento. La configuración de
licencias incluye el archivo `LICENSE` existente en las distribuciones; se
requiere una versión de setuptools que admita `project.license-files`, según su
[documentación](https://setuptools.pypa.io/en/latest/userguide/pyproject_config.html).

OpenCV y NumPy implementan máscaras de color, regiones conectadas y validación
del patrón de 8 × 8 para la [detección](detection.md). La [guía de entrada](image-input.md)
concreta la decodificación. Solo se añaden dependencias de etapas implementadas.
No se incorpora ahora un framework de aprendizaje automático ni una biblioteca
de reglas de ajedrez para serializar un único campo.

PyTorch es un candidato para entrenar y ejecutar un clasificador de casillas con
13 clases. Su [guía oficial](https://docs.pytorch.org/tutorials/beginner/basics/intro.html)
describe el flujo de datos, construcción, entrenamiento y guardado de modelos.
En BoardSnap podría combinarse con OpenCV para localizar y normalizar el tablero.
La comparación inicial con plantillas no necesita una red neuronal; si se adopta
un modelo aprendido, harán falta datos etiquetados y una evaluación independiente.
La elección y la instalación de PyTorch se harán al abordar ese experimento.

## Integración externa

La futura CLI recibirá una ruta y emitirá JSON. Será un consumidor del núcleo,
no una decisión sobre cómo ejecutará Python la app Flutter. Servicio remoto,
proceso local u otra vía deberán decidirse expresamente según las plataformas
y restricciones de chess-scanner. Hasta entonces no habrá servidor, endpoints,
SDK de Flutter ni código de despliegue.
