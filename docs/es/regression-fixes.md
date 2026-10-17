# Corrección de regresiones digitales

[English](../en/regression-fixes.md) | **Español** · [Inicio](README.md)

Los [seis fallos originales](../../data/reports/digital-regressions-v8.json) pasan
con `.cache/neural-styles-v8/best.pt` y el detector actualizado. Los tres casos de
Staunty que empeoraron durante el desarrollo también [pasan](../../data/reports/digital-staunty-regressions-v8.json).
Es evidencia de regresión, **no la aceptación digital final**. El plan de fuentes
reservado para aceptación no se ha capturado, entrenado ni evaluado aquí.

Capturas posteriores del usuario mostraron dos imágenes adicionales que fallan,
registradas como [casos de desarrollo de vídeos](video-development.md). Los resultados
de esta página describen la corrección original, no compatibilidad con esas nuevas
condiciones de vídeo.

La alternativa de usar la imagen completa descrita más abajo es histórica. El
[ajuste posterior de bordes visibles](video-development.md#paso-3-ajuste-de-bordes-visibles)
exige comprobar líneas interiores y perímetro antes de aceptar una propuesta
basada en el marco de la imagen. Corrige la 002 y conserva los seis casos originales.

El [informe completo de regresión](../../data/reports/neural-styles-v8-regression.json)
mide **3456/3456 imágenes correctas**, tanto con límites verificados como detectados:
221184/221184 casillas, ningún fallo nuevo de reconocimiento y todos los límites
detectados con un error máximo de dos píxeles respecto a sus anotaciones. Son variantes
de **12 posiciones de origen**, no 3456 posiciones independientes. Pasan las 2484
variantes de estilos anteriores y las 972 de ampliación, incluidas 324 de
combinaciones reservadas. La [comprobación de la CLI](../../data/reports/digital-cli-v8-regression.json)
también supera los seis casos originales con JSON exacto, código de salida 0 y
`stderr` vacío.

Tests automáticos: **1373 pasan, 36 omitidos y 2 fallos esperados**. Los omitidos son
pruebas opcionales de navegador; los fallos esperados pertenecen a la referencia
experimental de diagramas de libros.

## Detección

Los cuatro fallos eran tableros Staunty completos de 384 píxeles, recortados hasta
el borde de la imagen y vistos desde negras: wood4/digital-038 y blue/digital-001,
006 y 038. Las bases repetidas de las piezas desplazaban el ajuste de líneas fuera
de la imagen y se descartaban los límites, aunque la cuadrícula fuera válida.

Ahora, cuando ningún ajuste de cuadrícula pasa, una imagen completa casi cuadrada
se considera otra propuesta. Debe superar las comprobaciones de alternancia de
casillas y continuidad de líneas. Los límites ajustados conservan prioridad para
que un margen pequeño no produzca un segundo tablero ficticio. Los cuatro casos
tienen ahora **error de límites cero**. Los tests conservan controles sin tablero,
cuadrículas de otras dimensiones, tableros incompletos y detecciones múltiples.

La [regresión separada de detección](../../data/reports/digital-detection-v2-regression.json)
conserva los 28 rectángulos revisados de imágenes reales/sintéticas y rechaza sus
28 negativos con el tablero eliminado. No demuestra clasificación de capturas reales.

## Reconocimiento y datos de entrenamiento

Los fallos de Neo confundían un peón blanco con uno negro bajo una cabeza de flecha
azul y un rey blanco con un caballo blanco bajo flechas cruzadas. Ambos devuelven
ahora la colocación exacta esperada. Se sigue cargando un único modelo pequeño de
13 clases, sin borrar flechas ni aplicar correcciones específicas por posición.

Los ajustes de pesos por sí solos no conservaban todos los estilos. La corrección
final añade [1144 variantes exclusivas de entrenamiento](../../data/reports/arrowhead-training-v1.json):
un ejemplo de cabeza de flecha azul por clase, color de casilla, orientación y
combinación de estilo vista (13 × 2 × 2 × 22). Proceden únicamente de los 14 grupos
originales de entrenamiento. Las flechas se dibujan sobre tableros completos antes
de normalizar y recortar. Su dirección varía de forma determinista, con anchura de
0,22 casillas y RGBA `[45, 110, 220, 192]`. No se ha copiado al entrenamiento ninguna
imagen de regresión.

El conjunto adicional aporta 6437 casillas afectadas, para **320783** en total.
Deben coincidir los hashes de fuente, posición, grupo, colocación, orientación y
estilo con los registros originales de entrenamiento. Se rechazan imágenes de
fuentes reservadas aunque se cambie su etiqueta. Validación y regresión mantienen
sus distribuciones; las dos combinaciones de piezas/fondo reservadas permanecen
fuera del entrenamiento y la validación.

El [registro de entrenamiento](../../data/reports/neural-styles-v8-training.json)
selecciona la época 12 de 12 solo mediante validación: **3131/3132** posiciones
completas, incluidos los **2484/2484** controles de estilos anteriores. Queda un
fallo de validación. Los fallos conocidos guiaron el desarrollo entre ejecuciones;
el corpus de regresión ya consultado no es una prueba final independiente.

| Ejecución | Método | Resultado en los casos conocidos |
| --- | --- | --- |
| v3 | Ajuste supervisado de styles-v2 | Persistían los dos fallos originales con flechas |
| v4 | Conservar predicciones de entrenamiento de arrows-v1, temperatura 2 | Persistía el fallo del rey |
| v5 | Continuar v4, temperatura de referencia 4 | Pasaban los seis casos originales, pero aparecían tres fallos de Staunty |
| v6 | Promedio de parámetros v2/v5 seleccionado mediante validación | Staunty se recuperaba; fallaba el peón original |
| v7 | Referencias de entrenamiento para estilos anteriores y nuevos | Seguía fallando el peón original |
| v8 | Ajuste supervisado de v7 con variantes equilibradas de cabezas de flecha azules | Pasan los seis originales y los tres casos de Staunty |

Los artefactos registran hashes de modelos de origen, datos, configuración y código.
Los tests comprueban la reanudación determinista, rechazan cambios de inicialización,
referencias o máscaras, e impiden que las variantes adicionales crucen particiones.
Las referencias y el promedio de parámetros son herramientas de entrenamiento;
para reconocer imágenes solo se necesitan los pesos v8.

## Utilizar y reproducir

Los pesos son locales y Git los ignora. Los modelos anteriores y el paquete
provisional v1 se conservan. Selecciona expresamente el modelo corregido:

```bash
export BOARDSNAP_MODEL="$PWD/.cache/neural-styles-v8/best.pt"
boardsnap image.png --orientation white-bottom
```

SHA-256 del modelo: `9546c6cfc34517f631cd58bf3eae0cdb3aa7790765b6f4ad1c0bf307ca4ad704`.
La salida correcta sigue conteniendo únicamente `piecePlacement`; el JSON de
error y los códigos de salida no cambian.

Desde la raíz, con el entorno, corpus y modelos anteriores disponibles:

```bash
python -m tools.build_arrowhead_training --parent .cache/digital-style-squares-v2 --captures .cache/arrowhead-training-captures-v1 --output .cache/arrowhead-training-squares-v1 --report data/reports/arrowhead-training-v1.json
python -m tools.train_neural --dataset .cache/digital-style-squares-v2 --extra-training-dataset .cache/arrowhead-training-squares-v1 --run .cache/neural-styles-v8 --config tools/train-styles-v8.json --marked-cells-only --control-cohort previous --initialize-from .cache/neural-styles-v7/best.pt
python -m tools.check_known_regressions --dataset .cache/digital-style-squares-v2 --model .cache/neural-styles-v8/best.pt --previous-report data/reports/neural-styles-v2-evaluation.json --output data/reports/digital-regressions-v8.json
python -m tools.evaluate_marks --dataset .cache/digital-style-squares-v2 --baseline .cache/neural-arrows-v1/best.pt --candidate .cache/neural-styles-v8/best.pt --baseline-name arrowBaseline --candidate-name styleCandidate --split evaluation --regression --output data/reports/neural-styles-v8-regression.json
python -m pytest
```

Los comandos de creación requieren carpetas de destino nuevas. Para reanudar
un entrenamiento interrumpido, añade `--resume` con las mismas entradas. Volver a
comprobar modelos existentes no requiere regenerar datos ni entrenar. La cadena
de modelos de origen es:

```bash
python -m tools.train_neural --dataset .cache/digital-style-squares-v2 --run .cache/neural-styles-v4 --config tools/train-styles-v4.json --marked-cells-only --control-cohort previous --initialize-from .cache/neural-styles-v2/best.pt --teacher .cache/neural-arrows-v1/best.pt
python -m tools.train_neural --dataset .cache/digital-style-squares-v2 --run .cache/neural-styles-v5 --config tools/train-styles-v5.json --marked-cells-only --control-cohort previous --initialize-from .cache/neural-styles-v4/best.pt --teacher .cache/neural-arrows-v1/best.pt
python -m tools.average_neural --dataset .cache/digital-style-squares-v2 --left .cache/neural-styles-v2/best.pt --right .cache/neural-styles-v5/best.pt --run .cache/neural-styles-v6
python -m tools.train_neural --dataset .cache/digital-style-squares-v2 --run .cache/neural-styles-v7 --config tools/train-styles-v7.json --marked-cells-only --control-cohort previous --initialize-from .cache/neural-styles-v6/best.pt --teacher .cache/neural-arrows-v1/best.pt --expansion-teacher .cache/neural-styles-v2/best.pt
```

La [política de aceptación v1](digital-release.md) fija el código y modelo anteriores;
se conserva como evidencia histórica. Para cerrar el paso 10 faltan las nuevas
comprobaciones de candidato, CPU, distribución y política congelada antes de
la evaluación final protegida.
