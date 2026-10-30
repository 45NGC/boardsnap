# Datos fotográficos de entrenamiento y validación

[English](../en/phone-training-data.md) | **Español**

Las fotografías revisadas ya tienen un conjunto compatible con el cargador en
`.cache/phone-training-v1/`. La exportación por sí misma no entrenó ni modificó
modelos. El posterior [primer entrenamiento fotográfico](phone-training.md) ya
está completado.

| Partición | Fotografías | Casillas | Exportación |
| --- | ---: | ---: | --- |
| Entrenamiento | 160 | 10.240 | NPZ de desarrollo copiados sin cambiar ningún byte |
| Validación | 30 | 1.920 | Rectificados nuevos a partir de las cuatro esquinas revisadas |
| Evaluación final | 0 | 0 | No se ha consultado |

`lichess-photo-8` sigue excluida por la animación de captura ambigua. Se conservan
los manifiestos originales, fotografías, imágenes de revisión y
`.cache/phone-squares-v1/`. El [plan de particiones fijado](../../data/manifests/phone-training-v1.json)
registra la migración explícita de desarrollo a entrenamiento, todos los
identificadores incluidos, la exclusión y los hashes SHA-256 de los tres
documentos de origen.

## Archivos

- `verified.jsonl`: índice conjunto de 190 tableros que consume el cargador.
- `training.jsonl` y `validation.jsonl`: índices separados de esos mismos registros.
- `training/*.npz` y `validation/*.npz`: 64 imágenes RGB de 64×64 píxeles y
  sus 64 etiquetas por fotografía. El orden de clases está en `dataset.json`.
- `dataset.json`: preprocesado, recuentos, cobertura por clase y fondo,
  procedencia, hashes de índices e indicadores de disponibilidad.
- `partition-plan.json`: copia del plan fijado.
- `index.html` y `previews/`: las 64 casillas etiquetadas de cada tablero.

Cada registro conserva foto, procedencia, grupo original, posición canónica,
orientación, esquinas, revisión de anotaciones y hashes. Los registros de
entrenamiento añaden `sourceSplit: development` y `reusedFrom`.
El [informe de exportación](../../data/reports/phone-training-v1.json) se versiona;
las imágenes y el conjunto generado permanecen en `.cache`.

El [informe de comprobación del cargador](../../data/reports/phone-training-v1-verification.json)
confirma que ambas particiones completas cargan mediante `tools.neural_data`,
que los 160 archivos reutilizados son idénticos byte a byte y que los 30 archivos
de validación coinciden píxel a píxel con sus vistas rectificadas revisadas,
tras ordenar las casillas canónicamente.

## Separación y preprocesado

Todo el grupo original utilizable pasa a entrenamiento y todo el grupo nuevo
permanece en validación. Las posiciones relacionadas y sus variantes se mantienen
juntas. La separación de procedencias está confirmada por el usuario; no se
presentan las identidades desconocidas como verificadas independientemente.
La construcción rechaza familias de posiciones compartidas entre particiones,
partidas conocidas coincidentes, imágenes repetidas y etiquetas o revisiones incoherentes.

Validación utiliza el mismo preprocesado que los recortes originales: imagen RGB
completa, cuadrilátero revisado a 512×512 mediante interpolación lineal de OpenCV
y división en 8×8 casillas. Con negras abajo se invierte el orden de las casillas,
sin girar sus píxeles. Se conservan las 64 casillas, sin equilibrado ni aumentos.
Las frecuencias de validación deben mantenerse; el equilibrado futuro se aplica
solo al entrenamiento. Ambas particiones contienen las 13 clases sobre casillas
claras y oscuras, pero con frecuencias desiguales: en validación solo hay una
dama negra sobre casilla clara.

Los manifiestos e informes de entrada anteriores describen su estado previo a
la exportación y se conservan sin cambios. El nuevo conjunto y su informe son
los registros actuales: `readyForTraining` y `readyForValidation` son verdaderos.
Significan que están disponibles los datos e índices, no que el modelo cumpla
unos criterios de precisión. Los límites revisados no miden detección automática
de fotografías. Este piloto contiene solo fotos; mezclarlo con capturas digitales
requiere revisar solapamientos adicionales y fijar una configuración de entrenamiento.

## Comandos

Reproducir la exportación en una carpeta nueva; se rechazan destinos existentes:

```bash
python -m tools.build_phone_training_dataset --output .cache/phone-training-v2 --report .cache/phone-training-v2-report.json
```

El comando usa la misma receta `phone-training-v1`: cambiar solo la carpeta de
salida no crea una versión nueva de los datos. Los cambios de entrada requieren
un nuevo plan revisado. Un archivo corrupto, una entrada modificada o una revisión
desactualizada impiden publicar el resultado. La carpeta completa solo se publica
cuando pasan las comprobaciones.

El valor de `--dataset` para un futuro entrenamiento será `.cache/phone-training-v1`.
No hace falta iniciar un entrenamiento para comprobar los datos. Para consultar
los índices:

```bash
python -c 'from pathlib import Path; from tools.neural_data import read_index; m, rows = read_index(Path(".cache/phone-training-v1")); print(m["splitCounts"], len(rows))'
python -m pytest tests/test_phone_training_dataset.py tests/test_phone_squares.py tests/test_phone_validation.py -q
```

Entrenar y evaluar el modelo son tareas posteriores a esta exportación. Consulta
el [entrenamiento fotográfico completado](phone-training.md) para ver el modelo de
partida, configuración, resultados y comandos. Los modelos de capturas permanecen
intactos como referencias.
