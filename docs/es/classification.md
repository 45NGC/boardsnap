# Primera referencia de reconocimiento de piezas

[English](../en/classification.md) | **Español** · [Inicio](README.md)

El clasificador inicial de plantillas admite **piezas cburnett sobre el tablero
brown de lichess**. Elige una de trece clases por casilla: vacía (`None`), blancas
`PNBRQK` o negras `pnbrqk`. Utiliza solo píxeles, no anotaciones, posiciones
esperadas, nombres de archivo ni reglas de legalidad.

## API y método

`classify_square(square)` requiere una **imagen Pillow RGB de 64 × 64** y devuelve
un símbolo o `None`. `classify_squares(matrix)` acepta ocho filas de ocho imágenes
en listas/tuplas y devuelve ocho listas de ocho etiquetas en el mismo orden visual.
Las imágenes siguen abiertas, pertenecen al usuario y no se modifican. El orden
canónico corresponde a `to_canonical`, no al clasificador.

Se estima el fondo contando píxeles próximos a los dos colores del perfil brown.
Después se construyen dos canales: contraste más oscuro que el fondo y contraste
más claro. Así se comparan por separado siluetas/contornos y rellenos blancos.
Se excluyen los dos píxeles exteriores y las regiones de coordenadas de 16 × 16
de las esquinas superior derecha e inferior izquierda de todas las casillas.
También se descartan algunos píxeles de piezas: es una simplificación del perfil.

Se comparan las características con **26 plantillas**, una por clase y fondo,
mediante distancia cuadrática media. Gana la más cercana; los empates siguen el
orden fijo de las plantillas. No se devuelven confianza, candidatos alternativos
ni confirmaciones, y no se fuerza una posición legal. Un diseño desconocido puede
recibir una clase incorrecta: esta referencia no detecta todos los estilos
desconocidos. Una casilla vacía es una clase válida, nunca un sustituto de un error.

Se reutilizan las dependencias existentes. No se incorpora todavía una red
neuronal ni PyTorch para esta referencia.

## Datos y reproducibilidad

El generador selecciona el primer ejemplo de cada clase/fondo en orden estable
de archivo, fila y columna, usando **solo la partición fija de ajuste**. Sus
16 capturas contienen 1.024 casillas y cubren las 26 combinaciones. Las etiquetas
proceden de la colocación FEN conocida, transformada a la vista anotada. Para
extraer plantillas se usan límites anotados revisados/redondeados; al reconocer,
el detector calcula los límites a partir de píxeles.

`piece-templates.png` es un atlas de 128 × 832: columnas clara/oscura y filas
vacía, P, N, B, R, Q, K, p, n, b, r, q, k. `piece-templates.json` registra hashes
de imágenes y anotaciones, casillas de origen, recuentos por clase/fondo, ubicación
en el atlas y su hash. Ambos se instalan con el paquete y se leen mediante
`importlib.resources`; el motor no necesita los datos del repositorio al ejecutarse.
Consulta la [procedencia del arte](../../src/boardsnap/assets/README.md).

```bash
.venv/bin/python -m tools.build_piece_templates
```

No se usan píxeles ni etiquetas reservados para elegir plantillas o parámetros.
Las pruebas sobre imágenes de ajuste no son estimaciones independientes de
precisión, aunque excluyan el recorte exacto de la plantilla y compartan su posición.

## API de imagen a resultado

```python
from boardsnap.pipeline import recognize_image
from boardsnap.image_input import ImageInputError
from boardsnap.detection import BoardDetectionError
from boardsnap.classification import ClassificationError

try:
    result = recognize_image("data/tuning/lichess-cburnett-brown-v1/pos-002-black.png")
except (ImageInputError, BoardDetectionError, ClassificationError) as error:
    result = error.to_dict()
```

`recognize_image(path)` conecta entrada, detección, normalización, segmentación,
orientación, clasificación y salida, y cierra las imágenes propias al terminar
o fallar. El éxito es exactamente `{"piecePlacement": "..."}`. Propaga las
excepciones de cada etapa; el adaptador serializará `error.to_dict()`. Las
plantillas ausentes o corruptas producen `ClassificationError` con
`PROCESSING_FAILED`, nunca una posición vacía. Los tipos, modos y dimensiones
internos inválidos producen `TypeError`/`ValueError`. La [CLI registrada](cli.md)
serializa estos resultados. La integración con Flutter sigue por decidir.

## Protocolo fijado antes de evaluar los reservados

El criterio inicial es **ninguna casilla incorrecta y colocación exacta en todas
las capturas originales reservadas**. Se informa de las trece clases por fondo
claro/oscuro, precisión en casillas ocupadas, media de recuperación por clase
presente y coincidencia exacta de posiciones. La falta de ejemplos de una
clase/fondo debe ser visible, no contarse como precisión perfecta. Un fallo de
procesamiento cuenta como posición fallida y 64 casillas incorrectas en el informe.

Las pruebas unitarias cubren entradas inválidas, casillas vacías y distracciones
en las coordenadas, conservación de entradas y recursos dañados. Las pruebas
reales comparan cada casilla con su anotación, las 26 combinaciones en recortes
de ajuste distintos de las plantillas seleccionadas y el recorrido completo con
archivos anónimos sin anotaciones adjuntas. Se prueban originales, recortes del
tablero, marcos desplazados y píxeles duplicados. Cada variante conserva su
partición; los derivados de evaluación quedan en memoria o carpetas temporales
de pruebas y no se incorporan al ajuste.

```bash
python -m pytest tests/test_classification.py tests/test_classification_images.py -m 'not evaluation'
python -m pytest tests/test_classification_images.py -m evaluation
.venv/bin/python -m tools.evaluate_classification --split tuning --output .cache/classification/tuning.json
.venv/bin/python -m tools.evaluate_classification --split evaluation --output .cache/classification/evaluation.json
python -m pytest
```

Los informes miden el recorrido completo en orden canónico: los errores de
detección y orientación también afectan a las métricas por casilla. Las pruebas
aisladas del clasificador usan límites conocidos y etiquetas visuales para
distinguir esa etapa. Son informes de desarrollo, no respuestas de la aplicación.
El contrato JSON no cambia.

## Límites y comparación posterior con PyTorch

Es un corpus pequeño de distribución fija, no una evaluación representativa.
Los reservados son solo dos posiciones en ambas vistas. No demuestra fiabilidad
con otros temas, piezas, fuentes, tamaños renderizados independientemente,
compresión, resaltados, flechas, oclusiones ni libros. Detección y orientación
mantienen sus límites; si no se leen coordenadas, se asume blancas abajo.
No hay correcciones basadas en legalidad ajedrecística.

Se puede comparar PyTorch sobre este mismo perfil sin cubrir todos los temas.
Antes de entrenar, hay que crear una **división entrenamiento/validación dentro
de los datos de desarrollo por posición/grupo completo**, manteniendo juntas las
dos orientaciones, recortes, escalados y variantes sintéticas. Los grupos actuales
de evaluación siguen reservados. Hay que comprobar las trece clases y los fondos
en ambas particiones nuevas y recoger más posiciones independientes si faltan.

Entrenamiento ajusta pesos; validación elige hiperparámetros, aumentos de datos y
el punto de parada; evaluación mide el modelo congelado. No se debe dividir al
azar por casilla ni usar recortes reservados para aumentos o plantillas. Ocho
posiciones de ajuste no bastan para afirmar resultados robustos de una red.
Como esta evaluación ya se consulta en informes de desarrollo, conviene añadir
posiciones nuevas sin consultar para una comparación final más sólida. Se deben
comparar posiciones exactas, resultados por clase, latencia, tamaño de recursos
y mantenimiento con esta referencia congelada; PyTorch no garantiza una mejora.

## Resultados observados (07-10-2026)

- Ajuste: **16/16 imágenes exactas, 1.024/1.024 casillas**; solo resultados de desarrollo.
- Originales reservados: **4/4 imágenes exactas, 256/256 casillas**, incluidas 74/74
  ocupadas. La media de recuperación de las trece clases presentes es 1,0; sin fallos
  de procesamiento.
- Variantes reservadas: **16/16** resultados exactos (cuatro originales y sus tres
  derivados). Siguen siendo solo **dos posiciones independientes**, no dieciséis.
- No se cambiaron plantillas ni parámetros tras evaluar los reservados.

Ejemplos reservados y predicciones correctas (guion indica ausencia de ejemplos):

| Clase | Clara: aciertos/total | Oscura: aciertos/total | Total |
| --- | --- | --- | --- |
| vacía | 90/90 | 92/92 | 182/182 |
| P | 10/10 | 8/8 | 18/18 |
| N | 2/2 | 2/2 | 4/4 |
| B | 2/2 | 2/2 | 4/4 |
| R | 2/2 | 2/2 | 4/4 |
| Q | 2/2 | — | 2/2 |
| K | 2/2 | 2/2 | 4/4 |
| p | 10/10 | 10/10 | 20/20 |
| n | 2/2 | 2/2 | 4/4 |
| b | 2/2 | 2/2 | 4/4 |
| r | 2/2 | 2/2 | 4/4 |
| q | — | 2/2 | 2/2 |
| k | 2/2 | 2/2 | 4/4 |

Faltan ejemplos reservados de dama blanca en oscura y dama negra en clara. Solo
se comprueban en ajuste; su evaluación independiente requiere nuevas posiciones.
Los recuentos de confusión y procedencia están en los informes congelados de
[evaluación](../../data/reports/lichess-cburnett-brown-v1-classification-evaluation.json)
y [ajuste](../../data/reports/lichess-cburnett-brown-v1-classification-tuning.json).

## Inspección visual

```bash
.venv/bin/python -m tools.preview_detection --recognition
```

Incluye vistas de orientación/casillas y guarda `result.json` junto a ellas en
`.cache/detection-preview/<perfil>/<captura>/`, solo con `piecePlacement`. Repetir
sin `--recognition` elimina el resultado anterior de cada imagen procesada. Por
defecto usa solo capturas de ajuste y no modifica los originales. Esta utilidad
de desarrollo es independiente de la [CLI de JSON](cli.md).

Validación: pasan 161 pruebas nuevas (30 unitarias/informes, 111 de integración y
20 reservadas); la batería completa pasa **707 pruebas**, con 7 opcionales de
navegador omitidas.
