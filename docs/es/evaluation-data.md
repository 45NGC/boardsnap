# Imágenes de evaluación

[English](../en/evaluation-data.md) | **Español** · [Inicio](README.md)

Esta guía describe la implementación original del perfil brown. Consulta los [perfiles evaluados](profiles.md) para los nuevos estilos digitales, el experimento de libros y la cobertura actual.

Ubicación: [`tests/fixtures/evaluation/`](../../tests/fixtures/evaluation/).

El primer perfil contiene cuatro PNG anotados: `pos-003` (final de peones) y
`pos-010` (medio juego construido), cada uno en ambas orientaciones. Se asignaron
a evaluación antes de capturar y solo se han usado para comprobar la herramienta
de captura, no para ajustar reconocimiento. Resérvalos de la creación de
plantillas, entrenamiento y elección de umbrales. Dos posiciones no permiten
establecer una precisión general.

El [manifiesto del conjunto](../../data/manifests/lichess-cburnett-brown-v1.json)
registra la separación y la revisión visual. Se contrastaron las etiquetas con
las capturas; los límites proceden del DOM y se comprobó visualmente la extensión
de la cuadrícula, sin medirlos independientemente con precisión subpíxel. Las
imágenes conservan metadatos originales y hashes. Las atribuciones están en los
[avisos de procedencia](../../data/THIRD_PARTY_NOTICES.md).

Cada caso tendrá una colocación `piecePlacement` anotada independientemente y
metadatos de procedencia, permiso de uso, estilo, resolución, orientación y grupo
de origen. Los casos negativos tendrán el error esperado. Para medir detección
se anotarán también los límites del tablero cuando exista.

La separación por posición e imagen original se hizo antes de generar variantes.
No compartir originales, recortes ni transformaciones con `data/tuning/`.
Las anotaciones son resultados esperados de prueba, nunca entradas del reconocedor.
Queda pendiente reunir imágenes negativas sin tablero y variaciones de tamaño
y ubicación de la cuadrícula.
