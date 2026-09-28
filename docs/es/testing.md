# Plan de pruebas

[English](../en/testing.md) | **Español** · [Inicio](README.md)

Las primeras pruebas unitarias están en [test_output.py](../../tests/test_output.py).
Los 53 casos pasan contra `boardsnap.output.build_result(board)`, implementada
en [output.py](../../src/boardsnap/output.py). No se han añadido modelos de
reconocimiento ni imágenes.

Tanto `python -m pytest --collect-only` como `python -m pytest` terminan
correctamente con código `0`. La suite comprueba la implementación real de
salida sin `skip`, `xfail` ni resultados simulados.

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

`data/tuning/` contendrá los ejemplos para plantillas, ajustes y futuro
entrenamiento. `tests/fixtures/evaluation/` contendrá imágenes reservadas con sus
colocaciones esperadas; no se usarán para ajustar el motor. Los recortes y otras
variantes permanecerán en la partición de su imagen de origen. Se mantendrán
separadas también las posiciones fuente para evitar evaluar copias casi iguales.

Se han registrado los marcadores `unit`, `integration` y `evaluation`:

```bash
python -m pytest -m unit
python -m pytest -m integration
python -m pytest -m evaluation
```

El selector `unit` ejecuta las pruebas actuales de salida. Todavía no hay
pruebas `integration` ni `evaluation`, por lo que esos selectores terminan con
código `5`. No se alteran los códigos de salida para ocultar pruebas o
funcionalidad pendientes.
