# Conjunto de casillas etiquetadas

[English](../en/square-dataset.md) | **Español** · [Inicio](README.md)

El paso 6.3 genera casillas normalizadas a partir del [corpus limpio verificado](first-clean-corpus.md).
Prepara datos y registra el comportamiento de la detección; no entrena ni evalúa
un clasificador. Todavía no necesita PyTorch.

## Dos entradas separadas para las futuras mediciones

- **`verified`** utiliza los límites comprobados durante la captura. Sirve para
  entrenar el primer clasificador y medirlo independientemente de la detección.
- **`detected`** entrega la captura completa al detector existente y recorta sus
  límites. El detector recibe únicamente píxeles, con su perfil digital predeterminado;
  no recibe posición, anotaciones, tema ni rectángulo esperado. Permite medir el
  recorrido de detección/normalización/clasificación cuando exista el clasificador.
  Ambos modos usan la orientación explícita de la captura; aquí no se evalúa la
  lectura automática de coordenadas.

Ambos modos comparten imágenes de origen, etiquetas canónicas y particiones.
Deben mantenerse separados: los recortes detectados no son nuevos ejemplos
independientes de entrenamiento. Los límites incorrectos se comparan con la
referencia y se conservan sin corregir. Un fallo de detección genera un registro
de error sin recortes. No se sustituyen límites por los de referencia ni se
eliminan los fallos del denominador al medir posiciones completas. Las etiquetas
del modo detectado son los **objetivos esperados**, no una afirmación de que un
recorte mal localizado contiene esa pieza.

El informe recoge fallos y rectángulos a un píxel como máximo de la referencia
redondeada. El IoU y el error máximo por imagen están en `detected.jsonl`. Son
mediciones de preparación de datos, no nueva compatibilidad del clasificador.
No utilices resultados de evaluación final para ajustar detección o modelo.

## Contenido y preprocesado

El modo verificado contiene **230400 casillas** (3600 tableros × 64):

| Partición | Tableros | Casillas |
| --- | ---: | ---: |
| Entrenamiento | 2520 | 161280 |
| Validación | 540 | 34560 |
| Evaluación | 540 | 34560 |

Cada tablero se guarda en un archivo NumPy comprimido `.npz` con:

- `images`: `uint8`, forma `(64, 64, 64, 3)`, RGB con valores 0–255.
- `class_ids`: `uint8`, forma `(64,)`, siguiendo el orden de clases documentado.

El orden fijo es `empty, P, N, B, R, Q, K, p, n, b, r, q, k`. Mayúsculas para
blancas y minúsculas para negras. Estos metadatos son independientes del contrato
público JSON con `piecePlacement`.

Los límites de captura pueden ser fraccionarios. Se redondean **izquierda, arriba,
derecha y abajo** al entero más cercano, con empates al par, antes de normalizar.
Se recorta el tablero completo, se redimensiona a 512 × 512 con LANCZOS de Pillow
y se divide en 64 casillas de 64 × 64. Se conservan las coordenadas impresas; no
se borran marcas. Las casillas se ordenan de a8 a h1. Con negras abajo se invierte
el orden de filas y columnas **sin girar el dibujo de cada pieza**. Se utilizan
las mismas funciones de normalización y segmentación que en el reconocedor.

`verified.jsonl` y `detected.jsonl` contienen un registro por tablero de origen.
Cada registro conserva PNG y SHA-256, posición, grupo, partición, configuración,
orientación, colocación, límites de referencia y límites del recorte. Los registros
correctos enlazan el archivo de matrices y su hash e incluyen 64 `cells`: índice
canónico, casilla algebraica, etiqueta/clase, fondo claro/oscuro y fila/columna
visual de origen. La identidad de una casilla es `(boundsMode, image, index)`;
sus píxeles son `images[index]`. La procedencia y configuración completa siguen
en el JSON del PNG original. Ninguna casilla pierde su relación con el grupo.

`background` indica la paridad ajedrecística (a8 es clara), no un color estimado
visualmente. Los perfiles limpios seleccionados siguen esta convención.

## Resultados de esta construcción

Ambos modos completaron los 3600 tableros: **230400 casillas por modo**, con el
mismo reparto. No hubo fallos de detección y los 3600 rectángulos quedaron a un
píxel como máximo de las referencias redondeadas. Solo describe estas capturas
limpias automatizadas de escritorio, no superposiciones ni otras interfaces.

Las 26 combinaciones de clase/fondo aparecen en cada partición completa y en cada
configuración estándar. Sin embargo, el **subconjunto compacto está incompleto**:
faltan damas blancas sobre oscuro en entrenamiento/validación y reyes negros sobre
oscuro en evaluación, en las 18 combinaciones. Esos casos sí están en tamaño
estándar. No se han movido, sintetizado ni añadido ejemplos a validación/evaluación
para ocultar esos huecos. No se declara cobertura completa por tamaño; ampliarlo
requiere una nueva versión del plan de capturas que respete los grupos.

Entrenamiento contiene **111240 casillas vacías de 161280** (aproximadamente el
69%). La combinación clase/fondo menos representada procede de cinco posiciones
distintas de entrenamiento; en validación y evaluación el mínimo es dos. Esto
justifica probar un muestreador exclusivo de entrenamiento, no afirmar que el
conjunto inicial está equilibrado ni garantiza generalización.

## Distribución y equilibrado

Se conservan todas las casillas, incluidas las vacías repetidas. No se aplica
sobremuestreo, reducción, aumentos ni eliminación de duplicados. Validación y
evaluación conservan su distribución de origen. Las posiciones relacionadas y
cada estilo/tamaño/orientación siguen en la partición de su grupo. Nunca repartas
los recortes al azar ni utilices solo duplicados de píxeles para decidir particiones.

El [informe de construcción](../../data/reports/digital-square-corpus-v1.json)
recoge cantidades por clase × fondo, partición y configuración, posiciones/grupos
únicos, combinaciones ausentes y posiciones distintas que aportan cada clase/fondo.
Muchas capturas no compensan tener pocas posiciones independientes.

Se incluyen pesos opcionales calculados **solo con entrenamiento verificado**:
`total_casillas_entrenamiento / (26 × cantidad_entrenamiento_de_clase_y_fondo)`.
No se aplican. Un futuro muestreador de entrenamiento podrá utilizarlos después
de compararlo en validación; una combinación ausente recibe `null`, no un peso
inventado. No aplicar estos ajustes a validación/evaluación ni calcularlos con ellas.

## Generar e inspeccionar

Desde la raíz del repositorio con el entorno Python existente. Deben estar los
PNG/JSON capturados: el informe subido a Git no basta. No necesita red ni navegador.

```bash
python -m tools.build_square_dataset --mode both --output-root .cache/digital-square-corpus-v1 --report data/reports/digital-square-corpus-v1.json
python -m pytest tests/test_square_dataset.py
```

`--mode verified` (predeterminado) genera únicamente los datos que aíslan al
clasificador; `--mode detected`, los recortes obtenidos por detección. Se publica
el conjunto completo de forma atómica, con `dataset.json`, un índice JSONL por
modo y matrices en `<modo>/<partición>/<configuración>/<posición>-<orientación>.npz`.
Etiquetas o hashes de origen incorrectos interrumpen la construcción sin publicar
una carpeta incompleta. No se sobrescriben destinos existentes: usa otra carpeta
para una nueva construcción. Los fallos esperados del detector se registran y
no se confunden con datos corruptos. Códigos de salida: 0 si termina y 1 si falla.

Puedes ver un recorte real de entrenamiento sin PyTorch:

```python
import json
from pathlib import Path
import numpy as np
from PIL import Image

root = Path('.cache/digital-square-corpus-v1')
with (root / 'verified.jsonl').open() as index:
    row = next(json.loads(line) for line in index
               if json.loads(line)['split'] == 'training')
with np.load(root / row['array'], allow_pickle=False) as board:
    print(row['cells'][0])  # etiqueta de a8 y coordenadas visuales de origen
    Image.fromarray(board['images'][0]).save('.cache/square-preview.png')
```

Matrices e índices permanecen en `.cache/`, ignorada por Git; se suben código,
pruebas, documentación e informe resumido. Conserva una copia antes de limpiar
la caché o reconstruye desde las capturas originales. El informe fija hashes de
metadatos, preprocesado, clases, código e índices. Cada índice fija sus matrices
y PNG originales mediante hashes.

Las pruebas cubren la identidad de las 64 casillas en ambas vistas, dibujos sin
girar, 13 etiquetas, paridad, límites fraccionarios, matrices guardadas, fuentes
alteradas, filtraciones, publicación atómica, límites detectados incorrectos/fallos
y pesos exclusivos de entrenamiento. La [primera red entrenada y su comparación independiente](neural-classifier.md)
ya utilizan este conjunto; las plantillas siguen siendo la opción predeterminada.
