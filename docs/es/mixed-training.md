# Preparación del conjunto mixto

**Español** | [English](../en/mixed-training.md)

Esta preparación combina las capturas digitales y las fotos ya anotadas, sin
entrenar otro modelo. Los datos originales, sus grupos y las dos validaciones
existentes se conservan. `neural-phone-v1` sigue siendo la referencia recomendada.

- [Plan y hashes de las fuentes](../../data/manifests/mixed-training-v1.json).
- [Informe de preparación y solapamientos](../../data/reports/mixed-training-v1.json).
- [Inventario previo](training-coverage.md).

## Proporciones explícitas

Se preparan **32.000 muestras de casilla**, con esta distribución inicial:

| Bloque | Muestras | Proporción |
| --- | ---: | ---: |
| Digitales limpios | 6.400 | 20 % |
| Digitales con marcas sencillas | 3.200 | 10 % |
| Digitales con flechas, cruces y combinaciones | 4.800 | 15 % |
| Lote adicional de puntas de flecha | 1.600 | 5 % |
| Fotos antiguas sin madera visible | 9.600 | 30 % |
| Fotos antiguas con madera | 1.600 | 5 % |
| Las 24 fotos dirigidas nuevas | 4.800 | 15 % |

Así, capturas y fotografías aportan un 50 % cada una. El material digital no domina
por tener muchas más variantes. Las fotos nuevas tienen presencia sin reemplazar
la mayor parte de la experiencia anterior. El bloque nuevo también contiene seis
fotos sobre madera: la madera no se limita al 5 % reservado a las antiguas.

**Estas cuotas son una receta inicial, no proporciones óptimas demostradas.** Las
cinco fotos antiguas sobre madera reciben repetición deliberada; habrá que comprobar
sobreajuste. Las 32.000 muestras no son 32.000 casillas independientes o diferentes.
El informe distingue muestras, pares tablero/casilla únicos, tableros y posiciones.

Dentro de cada bloque se reparte el presupuesto de forma equilibrada por grupo,
posición, combinación de estilo y variante. Los restos se asignan con semilla fija,
sin favorecer siempre al primer identificador. Se barajan las casillas elegibles
antes de repetirlas. Para las variantes digitales marcadas se reutiliza
`training_indices`, incluidos sus márgenes de seguridad; para fotos y controles
limpios se conservan las 64 casillas. No se añaden transformaciones, pérdidas ni
ponderaciones por clase. La semilla inicial es `20261114`.

El grupo antiguo de procedencia sin resolver sigue siendo un grupo conservador,
no una partida conocida. Equilibrarlo por posición no crea procedencias nuevas ni
permite separar sus fotos entre entrenamiento y validación.

## Comprobaciones contra validación

El conjunto protegido reúne las **3.132 capturas digitales y 30 fotos** de
validación ya utilizadas en el desarrollo. Se comprueban, entre todas las fuentes:

- Identificador de grupo y de posición.
- Familia de colocaciones, incluyendo giros, reflejos e intercambio de colores.
- Partida o vídeo identificados, cuando existe ese dato.
- Hashes disponibles de imágenes originales, imágenes fuente y normalizadas.
- Hash de los archivos de casillas y de sus píxeles canónicos completos decodificados.

Una coincidencia bloquea la preparación: no se mueve ni se elimina silenciosamente
una imagen o una variante para esconderla. Si ocurre, se debe revisar el grupo
completo antes de preparar otro conjunto. También se rechazan archivos de
entrenamiento duplicados para evitar ponderarlos accidentalmente dos veces.

No se observan solapamientos en estas comprobaciones. **Esto no prueba la
independencia de las partidas cuya procedencia desconocemos**, ni detecta cualquier
copia aproximada con otra compresión o encuadre. Las posiciones y los hashes ayudan,
pero no sustituyen esos datos de origen. Se conservan las limitaciones de la
auditoría anterior. Esta validación es material de selección de modelos, no una
nueva evaluación final independiente.

La validación no se equilibra: cada tablero conserva su registro original y sus
64 casillas. El índice mixto añade una referencia a su corpus de origen sin
modificar el registro. No se abren recortes de evaluación final ni se ejecuta
inferencia.

## Archivos preparados

En `.cache/mixed-training-v1/`:

- `dataset.json`: cuotas, recuentos, auditoría y hashes.
- `training-boards.jsonl`: inventario de tableros elegibles, casillas utilizables y
  referencias a archivos originales; incluye sus etiquetas, grupo y partición.
- `validation.jsonl`: referencias a los registros originales de validación.
- `sampling-epoch-000.npz`: pareja índice de tablero / índice de casilla para cada muestra.
- `training-images.npy`: 32.000 recortes RGB `uint8`, de 64 × 64, copiados sin cambios.
- `training-labels.npy`: sus 32.000 clases, con el orden de clases habitual.

Los índices conservan acceso al material completo. La muestra inicial es
reproducible; `sample_epoch` permite producir otra distribución con las mismas
cuotas cambiando el número de época. Cambiarla posteriormente requiere materializar
sus recortes y conservar su trazabilidad; el entrenador antiguo no lo hace por sí
solo. No se han duplicado todos los corpus ni modificado los archivos NPZ originales.

El formato mixto tiene un lector propio; no debe pasarse directamente al anterior
`load_split`, que interpreta todos los tableros con la misma frecuencia. Para
comprobar la carga, desde el repositorio:

```python
from pathlib import Path
from tools.prepare_mixed_training import load_prepared_epoch

images, labels = load_prepared_epoch(Path('.cache/mixed-training-v1'))
print(images.shape, labels.shape)  # (32000, 64, 64, 3), (32000,)
```

El lector comprueba los hashes antes de devolver matrices de solo lectura. El
siguiente paso será conectar esta mezcla al entrenamiento, fijar su configuración
y los criterios de conservación de aciertos antes de ejecutar un candidato.
**Todavía no se ha entrenado ni se ha sustituido ningún modelo.**

Para reproducir en una carpeta nueva, sin sobrescribir el conjunto preparado:

```bash
python -m tools.prepare_mixed_training --output .cache/mixed-training-v1-reproduction --report .cache/mixed-training-v1-reproduction-report.json
python -m pytest tests/test_mixed_training.py tests/test_training_coverage_inventory.py tests/test_targeted_photo_overlap.py -q
```

## Verificación realizada

Pasan **24 pruebas dirigidas**. Además se cargó el conjunto preparado en modo de
solo lectura, se comprobaron las 32.000 etiquetas y las cuotas exactas, y se
compararon recortes exportados con los originales de cada uno de los siete bloques.
Todos los bloques muestreados contienen las 13 clases. La muestra incluye 27.290
pares tablero/casilla distintos; el resto son repeticiones deliberadas.

Los 3.162 registros de validación coinciden con sus originales y los hashes de
los modelos de referencia y del candidato descartado siguen intactos. Persisten
141 fotos de entrenamiento y 20 de validación sin identificador de procedencia
verificado: por eso el informe declara ausencia de solapamientos observados, no
independencia de fuentes completamente demostrada.

El [plan de configuración y aceptación del entrenamiento mixto](mixed-training-plan.md) fija un intento de 12 épocas, límites separados para fotos/capturas y requisitos de CPU y CLI. El entrenamiento no ha comenzado.
