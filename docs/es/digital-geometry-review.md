# Robustez geométrica de las 30 capturas de uso real

[English](../en/digital-geometry-review.md) · [Inicio](README.md)

Esta revisión usa únicamente desarrollo/regresión. No incorpora fotografías de
móvil, homografías, entrenamiento, distribución ni evaluación final independiente.
Los pesos v8 y `neural-tolerance-v1-conservative` permanecen intactos.

## Resultado y alcance

| Medida | Antes | Después |
| --- | ---: | ---: |
| Tableros localizados / límites dentro de tolerancia | 27/30 | 30/30 |
| Posiciones exactas con geometría revisada, cada modelo | 29/30 | 29/30 |
| Casillas correctas con geometría revisada, cada modelo | 1918/1920 | 1918/1920 |
| Posiciones exactas mediante CLI, cada modelo | 26/30 | 29/30 |
| Controles sintéticos positivos con error ≤2 px | 0/36 | 36/36 |
| Controles sintéticos negativos o fuera de alcance rechazados | 12/12 | 12/12 |

Los 27 rectángulos aceptados anteriormente conservan exactamente sus límites;
ninguna posición antes correcta pasa a ser incorrecta en este lote. Ambos modelos
producen los mismos resultados de acierto/error. La mejora recupera `real-use-25`,
`real-use-26` y `real-use-29` en el recorrido automático, incluida la CLI real.
**No significa que todas las capturas se reconozcan perfectamente:** queda un
fallo de clasificación en `real-use-4`.

## Inventario y anotaciones

El [manifiesto](../../data/manifests/real-use-development-v1.json) registra las 30
imágenes con nombre actual, hash, tamaño, posición, orientación, perímetro visible,
cuadrícula, condiciones, procedencia conocida y estado de revisión. Las imágenes
permanecen en `.cache/real-use-tests`; no se han añadido sus bytes a Git. Para
reproducir los resultados se necesita ese corpus local o una copia idéntica.

Quince referencias se heredan por hash del corpus anterior. Se conservan posición,
grupo y partición; `real-use-11`, `12` y `13` son tres variantes de una posición.
Las nuevas quince colocaciones se transcribieron visualmente antes de comparar
predicciones. Se revisaron las treinta imágenes; las nuevas anotaciones identifican
al asistente como revisor, **no afirman confirmación del usuario**. La geometría
nueva se contrastó con píxeles y líneas interiores, con incertidumbre de rasterizado;
no procede de una medida externa subpíxel. La tolerancia del lote es tres píxeles,
la misma escala de tolerancia usada para revisar los casos anteriores.

El usuario no conoce las partidas/vídeos exactos. La mayoría de originales son
capturas de vídeos y algunos de páginas; no se han inventado URL, momentos, temas
o partidas. Los nuevos originales quedan en un grupo conservador de procedencia
sin resolver. Las posiciones diferentes no demuestran independencia. El corpus
entero permanece en desarrollo: no se puede repartir después entre entrenamiento,
selección y aceptación sin revisar sus relaciones. Hay 28 colocaciones distintas,
no 30 ejemplos independientes.

Los comandos activos de documentación usan `real-use-N`. Los identificadores,
rutas de copias versionadas y `originalPath` de informes/manifiestos históricos
se preservan como procedencia: no son rutas de ejecución nuevas ni se reescriben
rompiendo sus hashes. `rename-map.json` permite relacionar los nombres antiguos;
su hash queda registrado en el manifiesto nuevo.

| Imagen | Vista | Cuadrícula revisada | CLI antes → después |
| --- | --- | --- | --- |
| real-use-1 | white-bottom | (19, 11, 578, 571) | OK → OK |
| real-use-2 | white-bottom | (51, 26, 1024, 992) | OK → OK |
| real-use-3 | black-bottom | (45, 25, 1013, 993) | OK → OK |
| real-use-4 | white-bottom | (18, 30, 1008, 1019) | FAIL → FAIL |
| real-use-5 | white-bottom | (44, 15, 1016, 986) | OK → OK |
| real-use-6 | white-bottom | (48, 44, 984, 981) | OK → OK |
| real-use-7 | white-bottom | (29, 28, 788, 788) | OK → OK |
| real-use-8 | white-bottom | (37, 28, 963, 953) | OK → OK |
| real-use-9 | white-bottom | (23, 10, 799, 787) | OK → OK |
| real-use-10 | white-bottom | (9, 10, 257, 258) | OK → OK |
| real-use-11 | black-bottom | (35, 17, 435, 417) | OK → OK |
| real-use-12 | black-bottom | (0, 1, 399, 401) | OK → OK |
| real-use-13 | black-bottom | (2, 2, 299, 299) | OK → OK |
| real-use-14 | black-bottom | (35, 14, 435, 414) | OK → OK |
| real-use-15 | black-bottom | (28, 8, 428, 408) | OK → OK |
| real-use-16 | white-bottom | (41, 11, 417, 387) | OK → OK |
| real-use-17 | black-bottom | (15, 13, 573, 570) | OK → OK |
| real-use-18 | black-bottom | (22, 16, 580, 573) | OK → OK |
| real-use-19 | white-bottom | (10, 24, 466, 480) | OK → OK |
| real-use-20 | white-bottom | (9, 3, 465, 459) | OK → OK |
| real-use-21 | white-bottom | (55, 23, 1143, 1111) | OK → OK |
| real-use-22 | white-bottom | (15, 11, 903, 899) | OK → OK |
| real-use-23 | white-bottom | (14, 8, 594, 586) | OK → OK |
| real-use-24 | white-bottom | (28, 14, 608, 592) | OK → OK |
| real-use-25 | white-bottom | (6, 13, 1016, 994) | FAIL → OK |
| real-use-26 | white-bottom | (3, 8, 1013, 988) | FAIL → OK |
| real-use-27 | black-bottom | (22, 22, 727, 728) | OK → OK |
| real-use-28 | black-bottom | (25, 18, 730, 724) | OK → OK |
| real-use-29 | black-bottom | (4, 11, 1015, 991) | FAIL → OK |
| real-use-30 | white-bottom | (35, 53, 859, 878) | OK → OK |

La tabla resume ambos modelos; los informes JSON contienen resultados y errores
por imagen/modelo, clases, grupos y condiciones. Las categorías se solapan y sus
denominadores no se deben sumar como si fueran conjuntos independientes.

## Diagnóstico antes de modificar producción

Se completó la evaluación inicial de las 30 imágenes y sus 60 procesos CLI antes
de editar `detection.py`. Se comunicaron las métricas y se conservaron los informes
[real antes](../../data/reports/real-use-geometry-before.json) y
[sintético antes](../../data/reports/digital-geometry-synthetic-before.json).

**Diferencia entre escalas y borde estrecho: 25, 26 y 29.** Sus pasos horizontal y
vertical difieren aproximadamente un 3 %. Las propuestas por líneas ya encontraban
la región, pero el filtro casi cuadrado la rechazaba. Además, el perímetro izquierdo
visible se encuentra seis píxeles hacia dentro respecto a la cuadrícula extrapolada.
Las siete divisiones de cada eje y los otros bordes dan evidencia para separar
ambas geometrías. Con límites revisados, ambos modelos ya reconocían las tres.

| Imagen | Cuadrícula para dividir | Perímetro visible |
| --- | --- | --- |
| real-use-25 | (6,13,1016,994) | (12,14,1017,994) |
| real-use-26 | (3,8,1013,988) | (9,8,1014,988) |
| real-use-29 | (4,11,1015,991) | (10,11,1015,991) |

Coordenadas `(izquierda, arriba, derecha, abajo)`, con extremos finales exclusivos.
No se puede asegurar si esa franja procede de máscara, marco o recorte del vídeo.
Se registra como origen pendiente; no se afirma haber recuperado información
oculta. No salen de la imagen ni se reconstruyen casillas.

**Clasificación sobre textura: real-use-4.** Los dos modelos predicen un caballo
negro en `a5` y en `h4`, aunque ambas casillas están vacías. El fallo persiste con
geometría revisada y con la automática, cuyos límites coinciden. Es compatible
con confusión de la textura de madera y el remuestreo del vídeo; el experimento
no permite atribuirlo a un efecto visual único ni al nombre de un tema. Cambiar
el detector para eliminar esas predicciones no está justificado.

**Resto: 26 imágenes.** Detección y reconocimiento completos correctos antes y
después, dentro de la tolerancia geométrica indicada. Incluyen cursores, resaltados,
flechas, texturas, márgenes y fondos de vídeo. No demuestran cobertura universal.

## Cambio implementado

Se conserva la prioridad de todas las rutas existentes. Solo cuando ninguna
localiza un tablero se llama a `_rectangular_grid_candidates`:

1. Propone extensiones a partir de líneas interiores en ambos ejes.
2. Ajusta inicio y paso horizontal/vertical separadamente, sin redimensionar la
   entrada para forzar una propuesta cuadrada.
3. Limita la relación entre lado mayor y menor a **1,05**. Es un alcance digital
   deliberadamente pequeño, no una estimación de perspectiva. No reabre candidatos
   casi cuadrados rechazados por las rutas anteriores.
4. Exige alternancia y evidencia fuerte en **las siete divisiones de cada eje**.
5. Verifica el perímetro completo. Si no coincide con la cuadrícula en un píxel,
   solo admite la recuperación estrecha existente: un borde afectado, como máximo
   `min(6, floor(lado_menor_de_casilla × 0.08))` píxeles y los demás bordes alineados.
6. Rechaza continuación que indique una cuadrícula mayor y mantiene el error por
   múltiples candidatos. Devuelve la cuadrícula validada, sin ajustarla después
   otra vez al borde visible.

El 5 % limita el alcance, **no prueba por sí solo que un tablero esté completo**.
Es menor que la pérdida de una fila/columna entera (12,5 %), pero recortes mucho
menores también deben rechazarse mediante evidencia interior/exterior. No se
amplió el presupuesto de franja para hacer pasar estas imágenes. No hay reglas
por nombre, plataforma, posición o resolución. La normalización existente ya
convierte un rectángulo válido en 512×512; no se cambian clasificador ni extracción.

## Validación y regresiones

La matriz controlada tiene 36 imágenes: tamaños base 160, 257 y 512; diferencias
de escala del 2 % y 4 % en ambos ejes; escenas limpias, con resaltados/flechas y
con textura/JPEG de calidad 82. Usa márgenes asimétricos, remuestreo bilineal o
bicúbico y dibujos artificiales independientes de estas capturas. Mide geometría,
no clasificación de esas figuras. Los doce controles incluyen ocultación de
14 píxeles, recorte de 14 píxeles, una columna ausente, cuadrículas 7×7/9×9 y
deformaciones del 8/15 % fuera del alcance de la nueva ruta.

Ocho comprobaciones adicionales usan tamaños/relaciones distintos: 193 al 3 %,
401 al 4,5 %, y 800 con lados de 839 y 841 píxeles, en ambos ejes. Comprueban
alineación por debajo del 5 % y rechazo por encima. No son evaluación final ni
demuestran independencia fotográfica. Los controles reales de 25/26/29 con 14
píxeles ocultos de la primera columna también se rechazan.

Se reutilizan los negativos de superficies, líneas, otras cuadrículas y los
casos geométricos anteriores de `tests/test_detection*.py`. Los seis fallos
originales pasan otra vez con [v8](../../data/reports/digital-regressions-anisotropic-v8.json)
y [candidato](../../data/reports/digital-regressions-anisotropic-candidate.json).
La CLI se ejecutó en procesos reales para cada imagen y modelo, antes/después:
120 invocaciones. Se comprobó JSON único, código de salida, stderr vacío y
correspondencia con el recorrido Python, también para los errores iniciales.

Los [resultados posteriores](../../data/reports/real-use-geometry-after.json),
[controles sintéticos](../../data/reports/digital-geometry-synthetic-after.json) y
[resumen de comprobaciones](../../data/reports/digital-geometry-summary.json)
registran hashes y resultados. La batería amplia y sus pruebas adicionales se
detallan en el resumen; no se suman ejecuciones solapadas como pruebas distintas.

La batería amplia terminó con **845 pruebas correctas**, sin fallos ni omisiones.
Las ocho comprobaciones adicionales, incorporadas después de recoger esa batería,
también pasaron. Las 54 pruebas iniciales están incluidas en las 845.

## Reproducción

Desde la raíz, con el entorno y ambos modelos existentes. Cada informe debe usar
un nombre nuevo: las herramientas se niegan a sobrescribir informes anteriores.

```bash
source .venv/bin/activate
python -m tools.evaluate_real_use --cli --output .cache/geometry-recheck.json
python -m tools.digital_geometry_scenarios --output .cache/geometry-controls.json
BOARDSNAP_TEST_MODEL=.cache/neural-tolerance-v1-conservative/best.pt \
  python -m pytest tests/test_detection*.py tests/test_video_development.py \
  tests/test_cli.py tests/test_cli_process.py tests/test_normalization.py \
  tests/test_segmentation.py tests/test_output.py tests/test_image_input.py -q
boardsnap .cache/real-use-tests/real-use-25.png \
  --model .cache/neural-tolerance-v1-conservative/best.pt --orientation white-bottom
boardsnap .cache/real-use-tests/real-use-29.png \
  --model .cache/neural-tolerance-v1-conservative/best.pt --orientation black-bottom
```

`--image-root RUTA` admite una copia del corpus con los mismos nombres y hashes.
No interpreta los nombres para reconocer: solo sirven al evaluador para cargar
las etiquetas. La línea base usa el detector de `e38df0ed8e3058afe5e98a3108a7469933cd6145`;
para repetirla, usar una copia aislada de ese código junto a las herramientas de
evaluación nuevas y los mismos datos, sin revertir el directorio de trabajo actual.
Normalmente basta reutilizar su informe y comprobar los hashes: no se recomienda
repetirla sin cambios de entradas. Para los seis casos, reutilizar
`python -m tools.recheck_digital_regressions --model RUTA --output INFORME` con cada modelo.

## Limitaciones y siguiente paso

Se puede cerrar **esta ampliación geométrica digital acotada**, conservando sus
regresiones, y continuar el piloto fotográfico. No se acepta todavía una versión
general del producto. Quedan:

- La confusión de textura de `real-use-4`, claramente separada del detector.
- El recorrido neuronal completo pendiente sobre las 3456 imágenes ya consultadas.
  Su evaluación previa con límites verificados no se presenta como flujo automático.
- Procedencia exacta de las nuevas capturas y confirmación externa de las nuevas
  transcripciones. No deben alimentar particiones nuevas sin revisar sus relaciones.
- Giro, perspectiva, papel y degradaciones fotográficas: fuera de esta corrección.
- No se puede distinguir universalmente una franja de fondo tapada de un recorte
  mínimo. La excepción está acotada; nunca promete recuperar piezas ocultas.

Los conjuntos antiguos llamados `evaluation` que usan las regresiones ya habían
sido consultados. No se ha abierto ni ejecutado el conjunto final independiente.
