# Aceptación y distribución digital

[English](../en/digital-release.md) | **Español** · [Inicio](README.md)

**Esta página documenta el paquete provisional v1 fijado.** La [corrección posterior](regression-fixes.md)
resuelve sus seis fallos conocidos con otro modelo y código. Los artefactos v1
se conservan; el nuevo candidato necesita su propia política y comprobación de distribución.

**Estado del paquete provisional v1: candidato, no versión digital aceptada.** El
[informe de preparación](../../data/reports/digital-readiness-v1.json) bloquea la
evaluación final por las dos regresiones con flechas y los cuatro fallos de
detección en recortes. Las [mediciones del paso 9](style-expansion.md) siguen siendo
pruebas de regresión; no se presentan como una evaluación final independiente.

Están implementados los criterios, el plan nuevo, el evaluador, el empaquetado del
modelo y las comprobaciones de instalación. En esta iteración **no se han capturado
ni reconocido las imágenes finales**: el plan continúa reservado. El paquete
conserva `0.1.0.dev0` y no se ha publicado una versión.

## Catálogo y umbrales fijados

La [política verificable por código](../../data/manifests/digital-acceptance-v1.json)
se escribió antes de la evaluación final. Fija el hash del modelo, el código del
motor, el catálogo, el plan de posiciones y los umbrales. Cambiar el candidato o
los criterios exige otra versión de la política; no se sobrescribe una ya fijada.

| Plataforma | Piezas | Fondos | Evidencia actual y límites |
| --- | --- | --- | --- |
| Lichess | cburnett, Merida, Alpha | brown, blue, green | Piloto evaluado; aceptación pendiente |
| Lichess | Staunty | brown, blue, wood4 | Piloto evaluado; cuatro recortes no detectados en blue/wood4 |
| Chess.com | Neo | green, brown, blue | Piloto evaluado; dos regresiones con flechas en brown/blue |
| Chess.com | Classic, Bases | green, brown, blue | Piloto evaluado; aceptación pendiente |
| Chess.com | Alpha | green, blue, wood | Piloto evaluado; aceptación pendiente |
| Apps nativas Android/iOS y otras pantallas reales | — | — | Las capturas de navegador no las demuestran |
| Otros temas, superposiciones nativas no evaluadas y oclusión completa | — | — | Fuera de esta aceptación |
| Diagramas de libros | — | — | Fuera de la versión digital |

Las 24 parejas corresponden al editor de Lichess y al análisis de Chess.com en
navegador de escritorio. Marcas y flechas utilizan el generador controlado existente.
Los recortes de 384 píxeles y tableros de 256 con márgenes artificiales son pruebas
limpias de distribución, no pruebas de apps móviles ni de todas las combinaciones
entre tableros pequeños y superposiciones.

| Criterio | Exigencia |
| --- | --- |
| Colocaciones completas exactas, flujo completo | Al menos 99 % global |
| Cada pareja, condición, distribución, plataforma y vista explícita | Al menos 98 % de colocaciones completas exactas |
| Cada una de las 13 clases | Precisión y sensibilidad de al menos 99,5 %; mínimo 100 casillas esperadas |
| Tableros no detectados | Como máximo 0,5 % |
| Límites con error máximo de dos píxeles | Al menos 99,5 % de las imágenes positivas, contando también los fallos |
| Detecciones falsas | Como máximo 0,5 %, sobre al menos 200 imágenes negativas |
| Correspondencia de orientación explícita | 100 % del orden canónico; ambas vistas también participan en las métricas completas |
| Procesamiento en CPU con modelo cargado | Percentil 95 de como máximo 1000 ms |
| Importaciones, carga del modelo y primera imagen | Como máximo 5000 ms en un proceso nuevo |
| Memoria máxima del proceso | Como máximo 1024 MiB de RSS |
| Requisitos previos | Ninguna imagen nueva fallada por regresión, ningún fallo de detección conocido sin resolver e instalación limpia correcta |

Faltan métricas, clases o grupos: se rechaza. Lo mismo ocurre con valores no finitos.
Un resultado mejor en un grupo no compensa otro que incumpla. Orientación significa
vista elegida, no turno. La lectura automática de coordenadas sigue disponible,
pero **queda fuera de la aceptación**; sus límites están documentados.

El presupuesto de tiempo corresponde a Linux en CPU, cuatro hilos de Torch y uno
de OpenCV, sin HTTP. No mide inferencia en Android/iOS. El umbral de negativos y
el pequeño número de partidas son criterios de un piloto, no una garantía
estadística de que esa tasa se mantenga en cualquier imagen real.

## Datos finales independientes

El [plan nuevo](../../data/manifests/digital-acceptance-positions-v1.json) contiene
40 posiciones de diez partidas legales generadas nuevas: aperturas, medio juego,
finales y promociones. Se comprueban partidas y posiciones equivalentes contra los
corpus consultados. Se reproducen los movimientos para verificar las etiquetas y
aparecen las 13 clases sobre ambos colores de casilla. No representa juego humano.

La receta prevé 1920 imágenes limpias: 40 posiciones × 24 parejas × dos vistas,
con tamaño estándar o compacto asignado por grupo. Una posición/vista de cada
partida y pareja recibe nueve casos de marcas/flechas y dos variantes limpias de
distribución. El total previsto es **4560 imágenes positivas** y 240 negativas
generadas: cuadrículas 6×6, 7×7, 9×9, 10×10, tableros incompletos 7×8 y bloques de
interfaz. Los negativos son sintéticos; otras capturas reales sin tablero necesitan
un corpus propio revisado.

Cada variante conserva su partida y posición. La partición es `acceptance`, que
el cargador de entrenamiento rechaza. La captura comprueba recursos renderizados,
posición, vista, límites completos y correspondencia PNG/anotación mediante el
adaptador existente. El motor solo recibe píxeles y vista; las etiquetas lo evalúan.

`evaluate_acceptance` vuelve a comprobar la preparación a partir de informes
identificados por hash. Con el candidato actual se detiene **antes de abrir el
corpus**. Cuando pase los requisitos, crea `acceptance-attempt.json` antes de
inferir. Incluso una ejecución fallida o interrumpida marca el conjunto como
consultado; no permite repetirlo silenciosamente como una prueba final nueva.
Después de ajustar usando casos consultados, estos sirven como regresión y hace
falta otro conjunto final independiente. Un candidato corregido puede reutilizar
este plan todavía intacto, pero con una política nueva que fije sus pesos y código.

En ese caso utiliza `prepare_acceptance --reuse-plan` con las rutas de la nueva
política y modelo. Cada evaluación iniciada registra también las partidas y
posiciones en `data/reports/acceptance-attempts/`. Conserva esos informes: cambiar
el nombre o copiar una carpeta de caché no crea un conjunto independiente. La
generación de planes excluye esas fuentes consultadas. Los tests utilizan
historiales temporales, sin consumir el conjunto reservado.

## Mediciones e instalación realizadas

El [informe de CPU](../../data/reports/digital-candidate-cpu-v1.json) utiliza 40
imágenes de validación, no datos finales: percentil 95 **168 ms**, arranque en frío
**1380 ms** y máximo **309 MiB** en un Intel Core i5-10400. Acertó las 40 posiciones.
Se registran versiones y equipo; los tiempos dependen del hardware y su carga.

La [instalación limpia](../../data/reports/digital-clean-install-v1.json) se comprobó
en un entorno Python 3.12 aislado, sin paquetes del sistema, instalando un wheel
sin modo editable y ejecutando desde `/tmp`. Incluye ambas plataformas y vistas,
JSON exacto, ausencia de tablero, imagen vacía, orientación inválida, recursos de
plantillas instalados y entrada como módulo. `pip check` no encontró dependencias
rotas. Esta prueba es de Linux; no demuestra instalación en otros sistemas o
versiones de Python.

## Artefactos locales de distribución

En `.cache/releases/digital-preview-v1/` están el wheel, las dependencias descargadas
y `model/`. La carpeta del modelo incluye pesos, metadatos, hashes, licencia y
avisos. El [informe del paquete del modelo](../../data/reports/digital-model-bundle-v1.json)
guarda por separado el hash de su manifiesto. Se conservan arquitectura, orden de
clases, preprocesado, tamaño de entrada, configuración y versión de los datos.

```bash
python -m tools.model_bundle verify .cache/releases/digital-preview-v1/model --manifest-sha256 HASH_DEL_INFORME
```

Se rechazan pesos, metadatos y avisos alterados. Es un paquete local: no se publica
ni se añade un servicio de descarga. Hay que copiar la carpeta completa del modelo
junto con el wheel correspondiente. `build --acceptance-report RUTA` solo podrá
marcar un paquete futuro como aceptado si el informe final cumple los criterios y
coincide con los pesos y la política exactos. Sin esa opción siempre es candidato.

Instala el wheel y sus dependencias de CPU y configura la ruta absoluta del modelo:

```bash
python -m pip install --no-index --find-links .cache/releases/digital-preview-v1/dependencies '.cache/releases/digital-preview-v1/wheels/boardsnap-0.1.0.dev0-py3-none-any.whl[ml]'
export BOARDSNAP_MODEL="$PWD/.cache/releases/digital-preview-v1/model/model.pt"
boardsnap imagen.png --orientation white-bottom
```

La instalación debe hacerse en un entorno nuevo. Si falta `ensurepip`, se puede
usar `python3 -m venv --without-pip NUEVO_ENTORNO` y el pip de otro entorno mediante
`python -m pip --python NUEVO_ENTORNO/bin/python install ...`, sin modificar Python
del sistema. Las dependencias descargadas aquí son para Linux x86-64/Python 3.12;
otros destinos necesitan sus propios wheels y otra comprobación limpia.

La respuesta pública sigue siendo exactamente `{"piecePlacement": "..."}` o el
error estructurado existente. No incorpora confianza, alternativas ni los demás
campos FEN. HTTPS y Flutter siguen [documentados](flutter-integration.md), sin
servidor ni cliente implementados en este repositorio.

## Comandos y siguiente decisión

```bash
python -m tools.digital_acceptance --policy data/manifests/digital-acceptance-v1.json --model .cache/neural-styles-v2/best.pt --regression data/reports/neural-styles-v2-evaluation.json --benchmark data/reports/digital-candidate-cpu-v1.json --installation data/reports/digital-clean-install-v1.json --output data/reports/digital-readiness-v1.json
python -m pytest
```

La preparación devuelve ahora **salida 1**, con dos requisitos incumplidos. Primero
hay que corregir esos casos con desarrollo/validación y repetir regresiones, CPU e
instalación limpia. Después se fija una política nueva para el candidato corregido:

```bash
PLAYWRIGHT_BROWSERS_PATH="$PWD/.cache/ms-playwright" python -m tools.acceptance_corpus --policy NUEVA_POLITICA.json --plan data/manifests/digital-acceptance-positions-v1.json --capture-root .cache/final-captures --output .cache/final-corpus
python -m tools.evaluate_acceptance --policy NUEVA_POLITICA.json --plan data/manifests/digital-acceptance-positions-v1.json --model NUEVO_MODELO.pt --readiness NUEVO_INFORME.json --corpus .cache/final-corpus --output data/reports/digital-final-acceptance.json
```

El evaluador devuelve 0 si acepta, 1 si rechaza por resultados medidos y 2 si el
intento está bloqueado o es inválido. Hoy no existe un informe final de aceptación.
Los informes actuales de preparación, CPU e instalación no deben presentarse como
ese resultado final.


Verificación: la suite completa pasó 1333 pruebas (36 casos opcionales de
navegador omitidos y dos fallos esperados de libros experimentales). La ejecución
separada del navegador pasó sus 71 casos, incluidos los 36 opcionales. Utilizan
páginas locales simuladas; no son un corpus de aceptación de las plataformas reales.
