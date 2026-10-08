# Hoja de ruta incremental

[English](../en/roadmap.md) | **Español** · [Inicio](README.md)

Hito actual de la hoja de ruta digital completado: orientación explícita en el
flujo Python y la CLI (`white-bottom`, `black-bottom`, `auto` predeterminado).
Las pruebas cubren ambas vistas, coordenadas ausentes/contrarias, compatibilidad
e inválidos; el JSON no cambia. Consulta [orientación](orientation.md).
Más temas y superposiciones quedan para después; el experimento de libros se aplaza.

También queda completado el siguiente hito de planificación: el [inventario
bilingüe de estilos y condiciones](style-inventory.md) separa fondos, piezas e
interfaces, define cuatro estados según evidencia y distingue navegadores y apps
nativas. Sus lotes ordenados son la lista actual de ampliación.

La preparación de posiciones ya está implementada: [80 posiciones en 20 grupos](position-plan.md),
particiones fijas de entrenamiento/validación/evaluación (56/12/12), secuencias
legales reproducibles, separación del corpus anterior y comprobación por clase y
color de casilla. Hay ocho combinaciones escasas documentadas; aún no hay capturas
del lote. Lo siguiente es adaptar las capturas al plan de tres particiones por
grupo, primero con los perfiles limpios actuales y después con fondos G1 y piezas
fijas. Este trabajo de preparación no declara nuevos temas compatibles.

## 0. Base del proyecto (completada)

Paquete instalable `boardsnap` con un único `__init__.py`, arquitectura propuesta
en documentación, configuración de pytest y espacios separados para ajuste y
evaluación. Los módulos se añadirán al implementar cada etapa. No incluye
algoritmos, funciones de reconocimiento, plantillas, modelos, imágenes, CLI
ejecutable ni pruebas de reconocimiento simuladas.

## 1. Contrato comprobable y primer perfil de datos

La serialización de matrices y la validación interna están implementadas y
cubiertas por 53 casos de prueba superados. La lectura admite PNG/JPEG,
normalización RGB y tres códigos de error de entrada, con 31 pruebas unitarias.
Los fallos de recursos de plantillas ya usan `PROCESSING_FAILED`.
El primer perfil ya es `lichess-cburnett-brown-v1`: 20 PNG anotados con piezas
cburnett, tablero brown, capturas de 1280 × 1000 y cuadrícula de 584 × 584.
Hay ocho posiciones de ajuste y dos reservadas de evaluación, ambas con las
dos orientaciones. El [manifiesto](../../data/manifests/lichess-cburnett-brown-v1.json)
fija este conjunto inicial. La recogida no demuestra compatibilidad del
reconocimiento. La [detección del primer perfil](detection.md) está implementada
y probada con recortes, escalados, desplazamientos e imágenes sin tablero;
se documentan por separado los resultados reservados. Las capturas originales
comparten distribución: siguen haciendo falta capturas independientes y negativos
más variados antes de afirmar generalización. La [normalización y división en
64 casillas](normalization.md) ya están implementadas y conservan el origen
completo para orientar. La [orientación](orientation.md) ya lee las coordenadas
interiores del perfil y aplica la convención documentada. El [clasificador de
plantillas y el flujo Python](classification.md) ya tienen una referencia medida.
La [CLI de JSON](cli.md) también está implementada. Lo siguiente es ampliar las
pruebas independientes; la [ampliación de perfiles](profiles.md) y el [diseño Flutter](flutter-integration.md) ya están documentados.

Empezar con PNG, tablero completo y alineado, piezas estáticas sin superposiciones
y una única cuadrícula por imagen. Reservar desde el principio imágenes de
evaluación con posiciones anotadas. Incluir todas las piezas, casillas vacías,
ambas orientaciones y posiciones asimétricas. Conservar las coordenadas del borde
cuando existan.

La división se hará por imagen original, posición y familia de variantes:
recortes, escalados y compresiones derivados de una misma muestra permanecerán
en la misma partición. Ninguna plantilla se extraerá del conjunto de evaluación.

## 2. Primera cadena completa y CLI (implementadas para el primer perfil)

El flujo Python conecta entrada, detección, normalización, 64 casillas,
clasificación por plantillas, orientación y salida. La [CLI](cli.md) utiliza ese
mismo núcleo y proporciona JSON, errores estructurados, códigos de salida y
diagnósticos separados. Se prueban tanto el comando instalado como la ejecución
como módulo con capturas de ajuste y reservadas, además de las pruebas aisladas.
La [referencia medida](classification.md) documenta los límites de la aceptación
inicial; este hito no supone reconocimiento universal.

## 3. Ampliación digital medida (primeros perfiles implementados)

Lichess blue/cburnett y el estilo verde predeterminado capturado de Chess.com
ya tienen perfiles explícitos, plantillas de ajuste, herramienta de captura y
regresión. Cada uno reconoce 4/4 imágenes reservadas (dos posiciones en ambas
vistas). La [guía de perfiles](profiles.md) detalla los límites: estos pilotos
pequeños con posiciones compartidas no demuestran compatibilidad universal.

Lo siguiente es reunir posiciones seleccionadas independientemente, otras
distribuciones del navegador y compresiones, conservando las regresiones.
Incorporar estilos evaluados uno a uno.

## 4. Diagramas de libros (referencia experimental implementada)

La edición ilustrada concreta de *Chess Strategy* tiene cinco diagramas de ajuste
y dos reservados. El detector de marco/brillo y sus 80 recortes de ajuste logran
126/128 casillas reservadas, pero **0/2 posiciones exactas**. La aceptación completa
sigue pendiente y ambos fallos quedan registrados como fallos esperados estrictos.

Después hay que reunir más ejemplos de esa familia y mejorar la robustez con
un conjunto de desarrollo separado. Si se utilizan los fallos reservados para
ajustar, pasan a desarrollo y se preparan otros diagramas independientes de
aceptación. Otros libros, fuentes, páginas completas y perspectiva quedan fuera
del alcance medido.

## 5. Clasificación aprendida e integración

La [referencia de plantillas congelada](classification.md) puede compararse con
un modelo PyTorch pequeño de trece clases sobre el perfil actual, sin cubrir todos
los temas primero. Separar grupos completos en entrenamiento, validación y
evaluación antes de ajustar modelos; comprobar clases/fondos y añadir muestras
independientes cuando falten. Mantener juntos todos los recortes, vistas y aumentos.
Versionar datos y recursos; el corpus actual no demuestra ventajas robustas de una red.

Para Android, iOS y web queda la [propuesta HTTPS documentada](flutter-integration.md).
El backend adaptador y el cliente Flutter se implementarán en otra tarea; esta
iteración aporta solo el diseño y conserva el contrato del núcleo.

## Comparación inicial de enfoques

Las alternativas siguen siendo hipótesis; ya hay [medidas de la referencia de
plantillas](classification.md), limitadas al corpus inicial. Detección y clasificación son tareas
distintas y podrán usar técnicas diferentes.

| Enfoque | Precisión esperada y límites | Complejidad | Mantenimiento |
| --- | --- | --- | --- |
| Plantillas sobre casillas normalizadas | Buen punto de partida para símbolos y escalas delimitados; sensibles a nuevos dibujos, resaltados y recortes. | Baja; permite inspeccionar cada ejemplo. | Crece con temas, fondos y variantes. |
| Visión clásica: líneas, contornos, umbrales y descriptores | Útil para localizar rejillas y separar figura/fondo; las reglas de forma pueden confundir piezas similares. | Media; exige ajustar preprocesado por familia de imágenes. | Las reglas pueden volverse frágiles al ampliar estilos. |
| Descriptores + clasificador supervisado pequeño | Puede absorber variaciones cubiertas por los datos; depende de etiquetas y del dominio evaluado. | Media; añade entrenamiento y validación. | Requiere datos y artefactos reproducibles. |
| Red convolucional de 13 clases | Potencial para más diversidad visual con suficientes ejemplos; no garantiza generalización a estilos inéditos. | Alta frente a la base de plantillas. | Añade costes de etiquetado, entrenamiento, distribución y seguimiento de regresiones. |

La comparación de plantillas de OpenCV proporciona una referencia técnica para
el primer experimento ([documentación oficial](https://docs.opencv.org/4.x/de/da9/tutorial_template_matching.html)).
Los contornos y su jerarquía son otra herramienta candidata para diagramas
([OpenCV](https://docs.opencv.org/4.x/d9/d8b/tutorial_py_contours_hierarchy.html)).
Para el clasificador pequeño se podrá estudiar un SVM multiclase
([scikit-learn](https://scikit-learn.org/stable/modules/svm.html)); citar estas
opciones no implica añadirlas como dependencias ahora.

## Cómo medir el avance

Registrar detección correcta del tablero, orientación correcta, acierto por
clase de casilla y coincidencia exacta de `piecePlacement` por imagen y estilo.
La precisión por casilla no sustituirá la coincidencia de la posición completa;
los errores de detección también contarán en la evaluación de extremo a extremo.
Medir además tiempo de proceso y coste de mantener cada perfil.

Estas métricas serán informes de desarrollo, nunca campos de la respuesta a la
app. La evaluación reservada no servirá para elegir plantillas, umbrales o
hiperparámetros. Si una muestra se incorpora al ajuste tras analizar un fallo,
dejará de pertenecer a la evaluación y se preparará una nueva muestra reservada.
