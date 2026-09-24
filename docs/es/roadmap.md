# Hoja de ruta incremental

[English](../en/roadmap.md) | **Español** · [Inicio](README.md)

## 0. Base del proyecto (esta iteración)

Paquete instalable `boardsnap` con un único `__init__.py`, arquitectura propuesta
en documentación, configuración de pytest y espacios separados para ajuste y
evaluación. Los módulos se añadirán al implementar cada etapa. No incluye
algoritmos, funciones de reconocimiento, plantillas, modelos, imágenes, CLI
ejecutable ni pruebas de reconocimiento simuladas.

## 1. Contrato comprobable y primer perfil de datos

Implementar y probar la serialización de matrices conocidas y los errores del
contrato. Fijar un primer perfil con capturas propias de **un solo tema de
lichess**, anotando explícitamente juego de piezas, fondo y tamaños; su identidad
exacta se decidirá con las muestras disponibles. No se declara compatible antes
de medirlo.

Empezar con PNG, tablero completo y alineado, piezas estáticas sin superposiciones
y una única cuadrícula por imagen. Reservar desde el principio imágenes de
evaluación con posiciones anotadas. Incluir todas las piezas, casillas vacías,
ambas orientaciones y posiciones asimétricas. Conservar las coordenadas del borde
cuando existan.

La división se hará por imagen original, posición y familia de variantes:
recortes, escalados y compresiones derivados de una misma muestra permanecerán
en la misma partición. Ninguna plantilla se extraerá del conjunto de evaluación.

## 2. Primera cadena completa y CLI

Implementar lectura, detección de cuadrícula mediante geometría y regularidad,
recorte, tamaño normalizado, 64 casillas y un clasificador de plantillas del
perfil elegido. Contemplar por separado el fondo de casilla y las piezas.
Resolver la orientación con las coordenadas admitidas por el perfil o aplicar
la convención documentada.

Conectar la CLI al mismo núcleo y comprobar JSON, errores y códigos de salida.
Cada etapa tendrá pruebas aisladas; el recorrido completo se evaluará con
imágenes reservadas. El hito exige publicar los fallos observados y acertar
exactamente las posiciones de una suite de aceptación fijada antes del ajuste;
no supone reconocimiento universal.

## 3. Ampliación digital medida

Añadir un perfil concreto de chess.com y después nuevos temas, resoluciones y
formatos, uno a uno. Probar compresión, márgenes de interfaz y colores distintos
con muestras separadas. Registrar por perfil qué se ha medido y qué queda fuera.
Mantener regresiones de los perfiles anteriores al incorporar uno nuevo.

## 4. Diagramas de libros

Comenzar con una familia concreta de símbolos impresos, diagramas completos y
escaneos limpios. Evaluar binarización, líneas y contornos para rejillas sin
alternancia de colores, y después inclinación moderada, ruido y fondos de papel.
No extrapolar resultados de capturas digitales a símbolos tipográficos de libros.

## 5. Clasificación aprendida e integración

Si las plantillas requieren demasiadas variantes o fallan en la evaluación,
comparar descriptores visuales con un clasificador pequeño y, si se justifica,
una red convolucional de 13 clases, con PyTorch como framework candidato.
Separar entrenamiento, validación y evaluación final antes de ajustar modelos.
Versionar los datos y los artefactos.

Elegir expresamente el mecanismo de integración con chess-scanner cuando se
conozcan plataformas, latencia y condiciones de ejecución. Implementarlo en un
adaptador separado, manteniendo el contrato y el núcleo existentes.

## Comparación inicial de enfoques

Son hipótesis de diseño para contrastar con el corpus; todavía no hay medidas
de precisión. La detección geométrica y la clasificación de piezas son tareas
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
