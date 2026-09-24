# Arquitectura propuesta

[English](../en/architecture.md) | **Español** · [Inicio](README.md)

Esta es la distribución de responsabilidades prevista, no una API implementada.
El repositorio inicial contenía únicamente README, licencia y un `.gitignore`
genérico de Python; no existía código de reconocimiento que conservar o migrar.

Se usa un único paquete, `boardsnap`, bajo `src/`. Esta base solo contiene
`__init__.py`, que identifica el paquete Python. Los módulos de la propuesta
siguiente se crearán al implementar cada responsabilidad; sus nombres son
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

Las pistas de orientación se conservarán desde la entrada y la detección.
`orientation` aplicará la correspondencia de casillas antes de generar la salida.

| Módulo | Responsabilidad prevista |
| --- | --- |
| `image_input` | Leer bytes o un archivo, decodificar la imagen y validar su contenido. Tratar la orientación del archivo antes del análisis. |
| `detection` | Localizar los límites de una cuadrícula de 8 × 8 y conservar las coordenadas visibles del margen, antes de recortarlas. |
| `normalization` | Recortar el tablero y ajustar tamaño y geometría sin perder la correspondencia con la imagen original. |
| `segmentation` | Obtener exactamente 64 recortes, indexados por fila y columna en la vista de la imagen. |
| `classification` | Elegir una de 13 clases por recorte: vacío o una de las seis piezas de cada color. |
| `orientation` | Usar pistas verificables o la convención documentada para reordenar la matriz a coordenadas de ajedrez. |
| `output` | Comprobar la estructura de la matriz, comprimir casillas vacías y construir `piecePlacement` o el error acordado. |
| `pipeline` | Coordinar etapas y propagar fallos sin sustituirlos por posiciones inventadas. |
| `adapters` | Traducir la entrada externa y serializar la respuesta; la CLI será el primer adaptador. |

Las estructuras internas se elegirán al implementar cada etapa. No se fijan
todavía clases públicas ni una representación de imagen ligada a una biblioteca.
El núcleo no importará los adaptadores ni conocerá HTTP, Flutter o una interfaz
gráfica. El adaptador tampoco contendrá lógica de reconocimiento.

La salida verificará la sintaxis de la colocación, no la legalidad de una partida.
No se recolocarán piezas para forzar una posición legal ni se inventarán datos
como el turno o los derechos de enroque.

## Dependencias

La base no requiere bibliotecas en ejecución. `setuptools` es el backend de
construcción y `pytest` es el único extra de desarrollo. La configuración de
licencias incluye el archivo `LICENSE` existente en las distribuciones; se
requiere una versión de setuptools que admita `project.license-files`, según su
[documentación](https://setuptools.pypa.io/en/latest/userguide/pyproject_config.html).

Al trabajar con imágenes se evaluarán Pillow para decodificación y OpenCV con
NumPy para geometría y plantillas. Solo se añadirán las dependencias utilizadas.
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
