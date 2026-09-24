# Ejemplos de ajuste (pendientes)

[English](../en/tuning-data.md) | **Español** · [Inicio](README.md)

Ubicación: [`data/tuning/`](../../data/tuning/).

Directorio reservado para imágenes usadas al crear plantillas, ajustar
preprocesado y, en el futuro, entrenar o validar clasificadores. Todavía no
contiene muestras ni artefactos.

Al incorporar cada muestra, registrar identificador, procedencia, permiso de
uso, perfil visual, resolución, posición conocida, orientación y grupo de
origen. Todos sus recortes, aumentos y transformaciones pertenecerán a la misma
partición. Para modelos aprendidos se separará también validación de entrenamiento.

No copiar aquí imágenes de `tests/fixtures/evaluation/` conservándolas a la vez
como evaluación. Una muestra utilizada para ajustar ya no es una evaluación
independiente.
