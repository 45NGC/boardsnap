# Candidato congelado para tableros en pantalla

[English](../en/screen-preview.md) | **Español**

`screen-preview-v1`, paquete **0.1.0.dev1**, es una versión preliminar portable
para probar en CPU Linux fuera del repositorio. **No es una aceptación final.**
Los modelos digital y fotográfico permanecen separados y sin cambios. No se han
capturado ni consultado imágenes finales independientes.

## Candidato y catálogo fijados

La [política](../../data/manifests/screen-preview-v1.json) fija mediante SHA-256
cada archivo del núcleo, los recursos instalados, la configuración del paquete,
ambos modelos y sus metadatos: arquitectura, clases, tamaño de entrada,
preprocesado, configuración de entrenamiento y versiones de datos. El distribuible
incluye también un inventario de código, dependencias, documentación y mediciones.
Cualquier cambio exige otro candidato; se conservan los registros anteriores.

| Modo | Catálogo objetivo | Estado |
| --- | --- | --- |
| Digital Lichess | cburnett, Merida y Alpha sobre brown/blue/green; Staunty sobre brown/blue/wood4 | 12 combinaciones medidas; aceptación independiente pendiente |
| Digital Chess.com | Neo, Classic y Bases sobre green/brown/blue; Alpha sobre green/blue/wood | 12 combinaciones medidas; aceptación independiente pendiente |
| Fotografías | Tableros completos en pantallas de Lichess, Chess.com y vídeos, perspectiva moderada y orientación explícita | Experimental; ningún tema fotográfico oficial declarado compatible |

El catálogo digital fija capturas de editor/análisis de navegador, recortes limpios
y márgenes artificiales, última jugada, selección, jaque, círculos, puntos y cuatro
condiciones de flechas controladas. Esto no demuestra compatibilidad con cualquier
vídeo, marcas reales o aplicaciones nativas Android/iOS.

El inventario fotográfico finito conserva los 13 **grupos visuales observados** del
[diagnóstico](phone-classifier-analysis.md): `cc-classic`, `cc-flat`, `cc-shaded`,
`cc-thin-stem`, `lc-classic-a`, `lc-classic-b`, `lc-rounded-king`, `video-chessbase`,
`video-classic-a`, `video-classic-b`, `video-flat-brown`, `video-flat-green` y
`video-flat-vibes`. No son nombres oficiales de temas. La evidencia fotográfica
procede de un iPhone 8 y 30 fotos de validación consultada; unos pocos aciertos no
demuestran compatibilidad con otros dispositivos o con todos estos grupos.
Quedan excluidos libros, piezas físicas 3D, oclusiones graves y estilos no medidos.

## Umbrales anteriores a la evaluación independiente

Estar listo para instalarse es distinto de haber alcanzado la calidad de
reconocimiento. El paquete puede probarse fuera; la calidad fotográfica aún
bloquea una versión con compatibilidad fotográfica general.

| Criterio | Digital | Objetivo fotográfico |
| --- | ---: | ---: |
| Posiciones completas, contando las no detectadas como fallos | ≥99 % | ≥90 % |
| Posiciones completas en cada condición declarada | ≥98 % | ≥85 % |
| Precisión y exhaustividad de cada una de las 13 clases | ≥99,5 % | ≥98 % |
| Tableros no detectados | ≤0,5 % | ≤5 % |
| Detecciones falsas | ≤0,5 %, al menos 200 negativos | ≤1 %, al menos 100 negativos |
| Transformación de orientación explícita | 100 % | 100 % |
| Geometría correcta sobre todas las entradas positivas | ≥99,5 % a dos píxeles | ≥95 % dentro del criterio fotográfico |
| p95 del recorrido con modelo cargado | ≤1 s | ≤5 s |
| Arranque, carga y primera imagen | ≤5 s | ≤10 s |
| Pico de memoria del proceso | ≤1024 MiB | ≤1024 MiB |

Digital conserva los mínimos de la política anterior, incluidas 4.560 imágenes
positivas. El objetivo fotográfico exige al menos 120 positivas de 20 grupos de
procedencia independientes identificados, 30 por categoría, diez por condición
declarada y 50 casillas esperadas por clase. Los requisitos se aplican a la vez;
algunos catálogos necesitarán más de 120 fotos. Se desglosará por procedencia,
diseño observado, fondo, perspectiva, resolución, superposición y orientación.
La falta de datos impide superar el criterio; el promedio no compensa un grupo
que falla. La geometría mantiene IoU ≥0,95, error de esquina ≤1 % del lado y
desplazamiento máximo de cuadrícula ≤8 % de casilla.

Son objetivos de utilidad para la primera versión, **no se han rebajado para
aprobar con 20/30**. Estos tamaños no prueban una tasa de error poblacional.
Antes de inferir, hay que revisar anotaciones y fijar grupos: todas las variantes
y posiciones relacionadas de una partida/vídeo permanecen juntas. Esta preparación
no inicia la evaluación final. Su corpus fotográfico y procedimiento de medición
se prepararán aparte. Los conjuntos consultados siguen siendo regresiones; usar
los resultados finales para corregir consume su independencia. El evaluador
digital existente tiene su propio esquema: esta política de dos modelos no se
puede pasar directamente a ese evaluador como si fuera equivalente.

## Mediciones e instalación

Se ha usado un **wheel instalado en un entorno nuevo**, sin instalación editable
ni paquetes del sistema: CPython 3.12.3, Linux x86-64, Intel Core i5-10400,
Torch 2.14.1+cpu, cuatro hilos Torch y uno OpenCV. Las mediciones se ejecutaron
secuencialmente después de terminar las pruebas.

| Validación de rendimiento | Digital | Foto |
| --- | ---: | ---: |
| Imágenes distintas, incluidos fallos | 40 | 30 |
| Posiciones completas correctas | 40/40 | 20/30 |
| p95 con modelo cargado | 546 ms | 2.839 ms |
| Arranque, carga y primera imagen | 1.499 ms | 2.130 ms |
| Pico de memoria RSS | 437 MiB | 549 MiB |

El tiempo con modelo cargado incluye lectura, detección, normalización o corrección
de perspectiva, clasificación y construcción de la respuesta. El tiempo de
arranque incluye importaciones, pesos y primera imagen; no es el p95 de muchos
arranques independientes. RSS incluye las bibliotecas importadas. No son medidas
de un móvil, concurrencia de servidor o HTTPS. Las 40 capturas sirven para medir
rendimiento, no constituyen una nueva evaluación de calidad.

Pasan `pip check`, nueve comprobaciones de instalación digital y once fotográficas:
ambas orientaciones, ambos puntos de entrada, JSON exacto, errores estructurados,
ausencia de tablero y argumentos inválidos. Se ejecuta desde `/tmp`, sin el
repositorio en `PYTHONPATH`. Los archivos instalados se comparan byte a byte con
el wheel. Las fotos de comprobación proceden únicamente de validación consultada.

La suite general supera 1.665 pruebas; se omiten 80 por navegador/modelo opcional
o archivos locales ausentes y se excluyen 161 marcadas como evaluación. Las
herramientas de distribución tienen una comprobación adicional de 33 pruebas,
incluidas 16 nuevas. Las omitidas no se cuentan como aprobadas. No se ha entrenado
ni sustituido ningún modelo.

## Distribuible portable

Archivo local: **`.cache/releases/screen-preview-v1.tar.gz`**. Incluye wheel,
dependencias, `requirements.lock` con versiones y hashes exactos, ambos modelos,
código fuente, políticas, informes, avisos, `INSTALL.md` y un verificador que solo
usa la biblioteca estándar. No incluye fotos privadas ni corpus. No se publica
nada automáticamente y `.cache` sigue fuera de Git.

El [informe de distribución](../../data/reports/screen-preview-v1.json) registra
por separado los SHA-256 del archivo y de su manifiesto. Comprueba el hash antes
de extraerlo. Se puede copiar a otro equipo **Linux x86-64 con Python 3.12**;
los wheels requieren glibc 2.28 o posterior. Otros sistemas necesitan sus propias
dependencias y comprobaciones. Se incluye PyTorch CPU: no hace falta GPU, acceso
a Internet, repositorio editable ni corpus de entrenamiento para reconocer imágenes.

Desde el directorio extraído `screen-preview-v1`:

```bash
python3.12 verify_preview.py . --sha256 HASH_DEL_MANIFIESTO_EN_EL_INFORME
python3.12 -m venv /tmp/boardsnap-preview-env
/tmp/boardsnap-preview-env/bin/python -m pip install --no-index --find-links dependencies --require-hashes -r requirements.lock
/tmp/boardsnap-preview-env/bin/python -m pip check
/tmp/boardsnap-preview-env/bin/boardsnap /ruta/captura.png --model "$PWD/models/digital/model.pt" --orientation white-bottom
/tmp/boardsnap-preview-env/bin/boardsnap /ruta/foto.jpg --input-type photo --model "$PWD/models/photo/model.pt" --orientation black-bottom
```

Crea el entorno **fuera** del directorio extraído: el verificador rechaza archivos
no inventariados. Si tu Python no incluye `ensurepip`, usa `venv --without-pip` y
un pip existente con `--python RUTA_ENTORNO/bin/python` y los mismos argumentos de
instalación sin conexión. Las entradas son PNG/JPEG; convierte HEIC previamente.
Indica modelo y tipo de entrada. El éxito sigue devolviendo solo `piecePlacement`;
se conservan errores estructurados y códigos de salida.

## Qué sigue pendiente

Foto v1 aún no detecta `video-img_5403`, inventa un caballo en h8 en `5406` y tiene
confusiones de estilos/muaré documentadas en la [revisión](photo-recovery.md).
El resultado digital de rendimiento tampoco constituye aceptación independiente.
Quedan la aceptación final del reconocimiento, publicación, alojamiento de pesos
e integración Flutter/HTTPS. Su [contrato](flutter-integration.md) no cambia.
