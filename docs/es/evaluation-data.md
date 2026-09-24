# Imágenes de evaluación (pendientes)

[English](../en/evaluation-data.md) | **Español** · [Inicio](README.md)

Ubicación: [`tests/fixtures/evaluation/`](../../tests/fixtures/evaluation/).

Directorio reservado para imágenes que no se usarán para construir plantillas,
entrenar clasificadores ni elegir umbrales. Todavía no contiene imágenes ni
posiciones esperadas.

Cada caso tendrá una colocación `piecePlacement` anotada independientemente y
metadatos de procedencia, permiso de uso, estilo, resolución, orientación y grupo
de origen. Los casos negativos tendrán el error esperado. Para medir detección
se anotarán también los límites del tablero cuando exista.

La separación por posición e imagen original se hará antes de generar variantes.
No compartir originales, recortes ni transformaciones con `data/tuning/`.
Las anotaciones serán datos de prueba, no entradas del reconocedor.
