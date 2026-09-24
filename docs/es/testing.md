# Plan de pruebas

[English](../en/testing.md) | **Español** · [Inicio](README.md)

En esta iteración solo se configura pytest. No hay pruebas implementadas ni
imágenes; `python -m pytest` y `python -m pytest --collect-only` terminarán con
código `5` hasta que se añadan casos reales.

La configuración en `pyproject.toml` limita el descubrimiento a `tests/`, usa
importación `importlib` y rechaza opciones o marcadores desconocidos. Instalar
antes el paquete con `python -m pip install -e '.[dev]'` permite probarlo sin
añadir manualmente `src/` a `sys.path`.

## Casos que se incorporarán con cada implementación

| Área | Evidencia prevista |
| --- | --- |
| Entrada | Archivos inexistentes, contenido vacío o corrupto y formatos admitidos. |
| Detección | Tablero completo con y sin márgenes, límites anotados y ejemplos negativos sin tablero. |
| Normalización y segmentación | Exactamente 64 recortes con límites y orden correctos. |
| Orientación | Una posición asimétrica en ambas vistas con coordenadas, y casos sin pistas que comprueben la convención `a8` arriba a la izquierda. |
| Clasificación | Las 13 clases, sobre casillas claras y oscuras, por perfil y resolución. |
| Colocación | Posición inicial, filas vacías y mixtas, compresión de huecos y orden de filas/columnas; ausencia de los otros campos FEN. |
| Recorrido completo | Igualdad exacta del JSON con colocaciones anotadas independientemente; errores sin posición inventada. |
| CLI | JSON en stdout, diagnósticos en stderr y códigos de salida del contrato. |

Las matrices construidas manualmente serán entradas de pruebas unitarias de
serialización y orientación, no sustitutos de la evaluación del reconocimiento.
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

Son selectores preparados para las pruebas futuras; actualmente tampoco
seleccionan casos. No se altera el código de salida para ocultar esa ausencia.
