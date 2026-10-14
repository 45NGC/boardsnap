# Reconocimiento multitema y segundo grupo de estilos

[English](../en/style-expansion.md) | **Español** · [Inicio](README.md)

El paso 9 separa la configuración del modelo de cada reconocimiento. La aplicación
envía imagen y orientación; el flujo neuronal no necesita seleccionar piezas ni
fondo. La respuesta sigue siendo solo `piecePlacement` o un error estructurado.
No se añade servidor HTTP ni cliente Flutter.

## Configurar una vez, reconocer con imagen y orientación

Instala el extra de aprendizaje y configura una ruta absoluta al modelo:

```bash
python -m pip install -e '.[dev,ml]'
export BOARDSNAP_MODEL="$PWD/.cache/neural-styles-v2/best.pt"
boardsnap imagen.png --orientation black-bottom
```

La llamada Python equivalente es:

```python
from boardsnap.pipeline import recognize_image
result = recognize_image("imagen.png", orientation="black-bottom")
```

Para una comparación puntual, utiliza `--model RUTA` o `model=RUTA`; prevalece
sobre `BOARDSNAP_MODEL`. Una aplicación persistente puede crear
`NeuralClassifier(RUTA)` una vez y reutilizar `recognize_image`, evitando cargar
los pesos en cada petición. La ruta pertenece a la configuración, no a los datos
de la imagen enviada. No hay descargas ni búsquedas automáticas dentro del repo.

Un `--profile` explícito selecciona las plantillas existentes para diagnóstico o
compatibilidad e ignora `BOARDSNAP_MODEL`. No se puede combinar con `--model`.
Sin modelo configurado ni perfil explícito se conserva brown/cburnett para las
instalaciones anteriores. Una ruta de modelo vacía, inexistente o incompatible
**da error**: no cambia silenciosamente de clasificador. PyTorch sigue siendo
opcional para utilizar solo plantillas.

La orientación explícita omite la lectura de coordenadas. El `auto` neuronal
prueba las distribuciones de coordenadas conocidas de Lichess y Chess.com con
contraste local, sin pedir un perfil de colores. Si no encuentra pistas legibles
y coherentes, conserva blancas abajo. No es OCR universal, especialmente sobre
texturas o letras diminutas; la orientación explícita es el uso previsto en la
aplicación. La detección digital mantiene el detector estructural y sus propuestas
internas por paleta, sin buscar el tema ni leer anotaciones durante el reconocimiento.

La lectura opcional acertó **604/648** vistas nuevas de validación con límites
verificados ([informe de orientación](../../data/reports/digital-styles-v2-orientation-validation.json)).
Por tanto, no se declara fiable para todas las condiciones nuevas. Las comparaciones
del modelo usan orientación explícita, también en las 44 imágenes donde `auto`
elegiría la vista incorrecta; ese parámetro forma parte de la petición prevista.

## Ampliación fijada y combinaciones reservadas

La [receta](../../tools/capture-digital-styles-v2.json) y la
[política](../../data/manifests/digital-styles-v2.json) delimitan este grupo:

| Plataforma | Piezas | Fondos de desarrollo | Combinación reservada |
| --- | --- | --- | --- |
| Lichess | Staunty | brown, wood4 | blue + Staunty |
| Chess.com | Alpha | green, wood | blue + Alpha |

Ambos juegos son nuevos respecto a los seis anteriores. Cada uno aparece sobre
dos fondos en entrenamiento y validación, incluida una textura de madera. El azul
ya aparece con otros diseños, pero las dos nuevas parejas azul/piezas no entran
ni en entrenamiento **ni en validación**. Solo se capturan sus posiciones originales
de evaluación. Ninguna imagen ya utilizada se declara inédita retroactivamente.

Se generan 860 pares PNG/JSON limpios: las 80 posiciones planificadas en las
combinaciones de desarrollo, ambas vistas y un representante compacto por grupo.
Las parejas reservadas aportan 60 imágenes de las 12 posiciones de evaluación.
Se comprueban posición, orientación, geometría y recursos realmente renderizados
antes y después de capturar; los lotes existentes se auditan al reanudar.

Un subconjunto determinista recibe los cinco tipos de marcas sencillas y cuatro
casos de flechas de los pasos 7–8, sobre la imagen completa antes de segmentar.
También se generan recortes de tablero de 384 píxeles y tableros de 256 píxeles
con márgenes controlados para medir tamaños y distribución. Son transformaciones
anotadas, **no pruebas de una aplicación móvil nativa ni de otra pantalla real de
partida**. Todas conservan posición, grupo y partición. El cargador rechaza las
parejas reservadas en desarrollo aunque se regenere el hash del índice.

Las variantes de distribución controlada son imágenes limpias. Su acierto no
demuestra todas las combinaciones de tamaño pequeño, textura y superposición;
las condiciones de cada registro y los resultados desglosados delimitan la cobertura.

El corpus anterior conserva `cohort: previous`; las nuevas imágenes llevan
`cohort: expansion`. Se registran plataforma, piezas, fondo, combinación,
distribución y cliente por separado. Las métricas de evaluación distinguen los nombres de cada
plataforma: por ejemplo, Alpha de Lichess y Alpha de Chess.com no se mezclan.

El [informe del corpus](../../data/reports/digital-styles-v2.json) recoge 860
capturas y 3784 variantes controladas, añadidas a las 16560 imágenes anteriores:
**21204 tableros** en total (14616 de entrenamiento, 3132 de validación y 3456 de
evaluación). Las 324 variantes de parejas reservadas permanecen en evaluación.
Siguen siendo 20 grupos y 80 posiciones; esas imágenes no son partidas independientes.

## Entrenamiento, regresiones y compatibilidad

La [configuración fijada](../../tools/train-styles-v2.json) entrena desde cero
40 épocas en CPU. La validación prioriza los tableros completos correctos de todo
el corpus anterior, incluidas sus flechas; después considera el acierto total,
sensibilidad media por clase y pérdida. Se conserva la selección de casillas
afectadas y los pesos por clase solo en entrenamiento. Validación y evaluación
mantienen las 64 casillas. Las combinaciones reservadas no seleccionan el modelo.
No se borran marcas ni se reconstruye mediante supuestos de legalidad.

La ejecución completó las 40 épocas y seleccionó la **época 39** solo mediante
validación: 3131/3132 tableros exactos, con **2484/2484** controles del corpus
anterior y 647/648 tableros de estilos nuevos. Los pesos elegidos están en
`.cache/neural-styles-v2/best.pt`; los modelos anteriores siguen disponibles.
Los hashes identifican datos, índice, código de entrenamiento y pesos. También
se contrastaron los 21204 registros combinados con el plan congelado, incluidas
posiciones equivalentes y hashes de imágenes entre particiones.

La comparación separa clasificación con límites verificados y flujo con detección,
con resultados por imagen completa y clase. Desglosa plataforma, piezas, fondo,
combinación exacta, distribución, tamaño, vista, superposición y corpus de origen;
las parejas reservadas tienen un grupo propio. Los fallos permanecen en el total.
Hay que consultar las regresiones del corpus anterior además de la media global.
Un piloto medido no equivale a compatibilidad general de una versión publicada.

### Evaluación registrada y regresiones conocidas

La [comparación terminada](../../data/reports/neural-styles-v2-evaluation.json)
incluye hashes, historial de entrenamiento, métricas por clase, fallos de detección
y todos los desgloses. Los pesos se fijaron antes de ejecutarla y no se ajustaron
después de ver sus resultados. Ambos modelos recibieron las mismas 3456 imágenes,
derivadas de **12 posiciones de origen en tres grupos**, con orientación explícita.

| Corpus | Modelo anterior: verificados / detectados | Modelo nuevo: verificados / detectados |
| --- | --- | --- |
| Estilos anteriores | 2484/2484 · 2484/2484 | 2482/2484 · 2482/2484 |
| Estilos nuevos, todos sus fondos | 324/972 · 324/972 | 972/972 · 968/972 |
| Parejas reservadas, subconjunto de los nuevos | 162/324 · 162/324 | 324/324 · 321/324 |
| Total | 2808/3456 · 2808/3456 | 3454/3456 · 3450/3456 |

El modelo nuevo acertó **221182/221184 casillas** con límites verificados. Sus dos
errores son regresiones en variantes anteriores de Chess.com Neo con flechas:
`digital-037`, blancas abajo, azul, `arrow-piece`; y `digital-038`, negras abajo,
marrón, `arrow-crossed`. El modelo anterior acertaba ambas. La clasificación limpia
y con marcas sencillas mantuvo el acierto completo en este corpus. El indicador
global `cleanPerformanceMaintained` del informe **no** significa ausencia de
regresiones en todas las condiciones anteriores.

La detección encontró **3452/3456** tableros con un error máximo de dos píxeles.
Los cuatro fallos son recortes de solo tablero de 384 píxeles con Staunty y negras
abajo: wood4 `digital-038`, y azul `digital-001`, `digital-006`, `digital-038`.
Devuelven `BOARD_NOT_FOUND` y cuentan como fallos, sin excluirlos de la precisión.
Con límites verificados el clasificador acertó sus piezas. Ambos modelos utilizan
el mismo detector; estos fallos se distinguen de las regresiones del modelo.

La tabla resume las 24 parejas concretas medidas. Varios nombres en una fila
indican que se probaron todas las combinaciones de piezas y fondos indicadas.
Son **resultados de un piloto evaluado**, no una garantía general de compatibilidad.

| Plataforma | Piezas | Fondos | Tableros exactos, límites verificados | Tableros exactos, límites detectados |
| --- | --- | --- | ---: | ---: |
| Lichess | cburnett, Merida, Alpha | brown, blue, green | 1242/1242 | 1242/1242 |
| Chess.com | Classic, Bases | brown, blue, green | 828/828 | 828/828 |
| Chess.com | Neo | green | 138/138 | 138/138 |
| Chess.com | Neo | brown | 137/138 | 137/138 |
| Chess.com | Neo | blue | 137/138 | 137/138 |
| Lichess | Staunty | brown | 162/162 | 162/162 |
| Lichess | Staunty | wood4 | 162/162 | 161/162 |
| Lichess | Staunty | blue (reservada) | 162/162 | 159/162 |
| Chess.com | Alpha | green | 162/162 | 162/162 |
| Chess.com | Alpha | wood | 162/162 | 162/162 |
| Chess.com | Alpha | blue (reservada) | 162/162 | 162/162 |

Los pesos nuevos son un **candidato opcional con regresiones conocidas**, no un
sustituto incondicional de `.cache/neural-arrows-v1/best.pt`. Antes de la aceptación
hay que abordar las dos regresiones con flechas y los cuatro fallos de detección
con ejemplos de desarrollo; estos casos ya consultados pasan a servir como
regresión, no como nuevas pruebas ciegas. La comprobación del flujo real también
acertó 34 imágenes mediante `NeuralClassifier`; la API configurada y la CLI
devolvieron exactamente el contrato con solo `piecePlacement`.

Las posiciones consultadas en hitos anteriores sirven como regresión. El paso 10
sigue necesitando umbrales fijados y un corpus nuevo e independiente de aceptación.
Las capturas reales requieren posiciones revisadas; las apps nativas Android/iOS,
interfaces reales no probadas, cualquier tema y piezas completamente tapadas
quedan fuera de lo demostrado. Los diagramas quedan fuera de esta ampliación digital.

## Reproducir

Estas rutas contienen los artefactos locales tras la ejecución; para repetir la
construcción utiliza destinos nuevos. Imágenes y pesos quedan en `.cache/`, ignorada.

```bash
PLAYWRIGHT_BROWSERS_PATH="$PWD/.cache/ms-playwright" python -m tools.collect_styles --output-root .cache/digital-style-captures-v2 --report .cache/digital-style-captures-v2-report.json
python -m tools.build_style_dataset --capture-root .cache/digital-style-captures-v2 --derived .cache/digital-style-derived-v2 --new-squares .cache/digital-style-addition-v2 --parent .cache/digital-arrow-squares-v1 --output .cache/digital-style-squares-v2 --report data/reports/digital-styles-v2.json
python -m tools.train_neural --dataset .cache/digital-style-squares-v2 --run .cache/neural-styles-v2 --config tools/train-styles-v2.json --marked-cells-only --control-cohort previous
python -m tools.evaluate_marks --dataset .cache/digital-style-squares-v2 --baseline .cache/neural-arrows-v1/best.pt --candidate .cache/neural-styles-v2/best.pt --baseline-name arrowBaseline --candidate-name styleCandidate --split evaluation --output data/reports/neural-styles-v2-evaluation.json
python -m pytest tests/test_multistyle_runtime.py tests/test_style_expansion.py
```

`collect_styles --audit-only` comprueba una colección existente. Las mediciones de
desarrollo usan `--split validation`; las decisiones se fijan antes de consultar la
evaluación reservada. La distribución e instalación desde cero corresponden al paso 10.
