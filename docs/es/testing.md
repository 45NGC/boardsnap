# Plan de pruebas

[English](../en/testing.md) | **Español** · [Inicio](README.md)

Las primeras pruebas unitarias están en [test_output.py](../../tests/test_output.py).
Los 53 casos pasan contra `boardsnap.output.build_result(board)`, implementada
en [output.py](../../src/boardsnap/output.py). Ya se incluyen las primeras
20 capturas anotadas; todavía no se ha añadido un modelo de reconocimiento.

Tanto `python -m pytest --collect-only` como `python -m pytest` terminan
correctamente con código `0`. Las pruebas de salida y datos se ejecutan
localmente. Los siete casos de integración con navegador se omiten salvo
activación expresa, descrita en la [guía de captura](capture-data.md).
Ninguna prueba simula resultados del reconocimiento.

La configuración en `pyproject.toml` limita el descubrimiento a `tests/`, usa
importación `importlib` y rechaza opciones o marcadores desconocidos. Instalar
antes el paquete con `python -m pip install -e '.[dev]'` permite probarlo sin
añadir manualmente `src/` a `sys.path`.

## Pruebas actuales de salida

El [contrato de salida](output-contract.md) especifica los valores de la matriz,
el orden, la forma del resultado y las excepciones de validación. La suite cubre:

- La posición inicial, un tablero vacío y una posición asimétrica, con
  diccionarios esperados exactos y sin campos adicionales.
- Los doce símbolos de piezas y un tablero lleno, sin comprobar legalidad.
- Huecos de una a ocho casillas, huecos iniciales y finales, varios huecos en
  una fila y reinicio del contador entre filas.
- Las cuatro esquinas, el orden canónico de filas y columnas, entradas con
  tuplas y conservación de la matriz original tras serializarla.
- Dimensiones incorrectas, incluidas matrices con filas desiguales que aun así
  contienen 64 casillas.
- Tipos incorrectos de tablero, fila y casilla, símbolos inválidos y valores
  vacíos distintos de `None`, que deben provocar las excepciones documentadas.

Los resultados esperados se escriben a mano y son independientes de la
implementación de producción. La función auxiliar de los datos de prueba solo
convierte puntos a `None`; no genera FEN ni simula reconocimiento. Las pruebas
del orden canónico no prueban la detección de orientación a partir de imágenes.

## Casos que se incorporarán con cada implementación

La entrada ya cuenta con 31 casos unitarios en
[test_image_input.py](../../tests/test_image_input.py). Distinguen acceso,
decodificación y entradas no admitidas, y comprueban normalización, EXIF,
transparencia e independencia de los píxeles respecto al archivo. Consulta la
[guía de entrada](image-input.md).

La normalización y segmentación tienen 39 casos unitarios sintéticos en
`test_normalization.py` y `test_segmentation.py`, más 16 casos de ajuste y
4 reservados en `test_preprocessing_images.py`. Comprueban límites exactos,
tamaños, 64 casillas en orden visual, reconstrucción sin píxeles omitidos ni
duplicados, entradas inválidas y conservación independiente del origen para
orientar. Consulta comandos y límites en la [guía de normalización](normalization.md).
La clasificación y la orientación de ajedrez siguen pendientes.

| Área | Evidencia prevista |
| --- | --- |
| Entrada | Archivos inexistentes, contenido vacío o corrupto y formatos admitidos. |
| Detección | Tablero completo con y sin márgenes, límites anotados y ejemplos negativos sin tablero. |
| Normalización y segmentación | Exactamente 64 recortes con límites y orden correctos. |
| Orientación | Una posición asimétrica en ambas vistas con coordenadas, y casos sin pistas que comprueben la convención `a8` arriba a la izquierda. |
| Clasificación | Las 13 clases, sobre casillas claras y oscuras, por perfil y resolución. |
| Recorrido completo | Igualdad exacta del JSON con colocaciones anotadas independientemente; errores sin posición inventada. |
| CLI | JSON en stdout, diagnósticos en stderr y códigos de salida del contrato. |

Las matrices construidas manualmente son entradas de pruebas unitarias de
serialización, no sustitutos de la evaluación del reconocimiento.
Una posición inicial por sí sola no basta para probar orientación: usar también
posiciones asimétricas y alejadas de la distribución inicial de las piezas.

## Particiones y comandos previstos

`data/tuning/` contiene 16 imágenes para plantillas, ajustes y futuros
experimentos. `tests/fixtures/evaluation/` contiene cuatro imágenes reservadas con sus
colocaciones esperadas; no se usarán para ajustar el motor. Los recortes y otras
variantes permanecerán en la partición de su imagen de origen. Se mantendrán
separadas también las posiciones fuente para evitar evaluar copias casi iguales.

Se han registrado los marcadores `unit`, `integration` y `evaluation`:

```bash
python -m pytest -m unit
python -m pytest -m integration
python -m pytest -m evaluation
```

El selector `unit` ejecuta pruebas de salida, entrada, detección sintética,
normalización, segmentación y manifiestos de captura. `integration` selecciona
detección y preprocesamiento sobre imágenes de ajuste
y pruebas opcionales del navegador. `evaluation` selecciona detección y preprocesamiento sobre
imágenes reservadas y las [pruebas de integridad](../../tests/test_dataset.py):
firma y dimensiones de PNG, hashes, anotaciones, límites dentro de la imagen,
parejas de orientaciones, coherencia de manifiestos y separación de posiciones
y grupos. No localizan tableros ni clasifican píxeles. Las futuras pruebas de
reconocimiento solo recibirán imágenes; las anotaciones serán resultados
esperados. La detección tiene resultados limitados documentados en la
[guía de detección](detection.md); el reconocimiento de piezas sigue pendiente.
