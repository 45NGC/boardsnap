# Localización de tableros fotografiados

[English](../en/photo-detection.md) | **Español**

Hay un primer detector geométrico de fotografías en
`boardsnap.photo_detection.detect_photo_board`. Recibe una imagen RGB y devuelve
las cuatro esquinas de una cuadrícula completa de 8×8. No utiliza redes neuronales,
posiciones esperadas, anotaciones, nombres de archivo ni colores de temas conocidos.

El detector digital, los modelos de piezas y el comportamiento de `boardsnap`
permanecen intactos. Esta etapa mide **localización**, no reconocimiento completo:
la conexión automática con el clasificador fotográfico corresponde al siguiente paso.

## Cómo funciona

1. Reduce la imagen de trabajo a un máximo de 1.200 píxeles por lado, conservando
   la transformación a las coordenadas originales. No cambia la imagen recibida.
2. Propone cuadriláteros a partir de bordes y contornos. Si ninguno se valida,
   busca dos familias de líneas con separación compatible con una cuadrícula
   proyectada. La separación de las líneas puede variar con la perspectiva.
3. Rectifica provisionalmente cada propuesta y utiliza las siete líneas interiores
   de cada dirección para ajustar la geometría. El ajuste tiene un límite de
   desplazamiento y exige consenso de las intersecciones.
4. Comprueba alternancia en las 64 casillas, continuidad de las 14 líneas interiores
   y presencia de los cuatro bordes completos. Estima los fondos por fila para
   admitir cambios de iluminación de la pantalla sin confundirlos con casillas.
5. Rechaza extrapolaciones fuera de la imagen y subregiones 8×8 de cuadrículas
   mayores cuando la alternancia continúa en el exterior. Si valida varios
   tableros distintos, devuelve un error de ambigüedad.

Las esquinas se devuelven como números decimales en píxeles de la imagen RGB
normalizada, en orden **superior izquierda, superior derecha, inferior derecha,
inferior izquierda**. Ese orden describe la foto; no determina si las blancas o
las negras están abajo. Se usan `BOARD_NOT_FOUND` y `UNSUPPORTED_IMAGE` como errores
estructurados existentes. No se incluyen puntuaciones de confianza.

## Resultados y criterios

Se fijaron tres condiciones de acuerdo con las anotaciones antes de medir la
validación: IoU del cuadrilátero ≥ 0,95, error máximo de esquina ≤ 1 % del lado
medio anotado y desplazamiento máximo de las 81 intersecciones ≤ 8 % de una
casilla. Son criterios geométricos de este piloto, no aceptación del producto.
Las propias anotaciones manuales tienen precisión limitada.

| Conjunto | Chess.com | Lichess | Vídeos | Total dentro del criterio |
| --- | ---: | ---: | ---: | ---: |
| Desarrollo | 52/55 | 52/53 | 28/53 | 132/161 |
| Validación | 10/10 | 10/10 | 7/10 | 27/30 |

Todos los tableros devueltos cumplen el criterio; el resto se rechaza. En desarrollo
se incluye la foto de clasificación ambigua, porque sus esquinas sí están revisadas.
Las 161 fotos no se presentan como 161 fuentes independientes.

En validación fallan `video-img_5403`, `video-img_5406` y `video-img_5407`.
No se ha ajustado el detector para recuperar esos tres casos después de medirlos.
Los vídeos son la limitación principal; las cifras de las páginas directas no
demuestran compatibilidad con cualquier interfaz, vídeo o aplicación móvil nativa.

Informes con esquinas esperadas/detectadas, métricas, hashes y fallos:

- [Desarrollo](../../data/reports/photo-detection-development-v1.json).
- [Validación](../../data/reports/photo-detection-validation-v1.json).
- [Controles negativos](../../data/reports/photo-detection-controls-v1.json):
  18/18 rechazos correctos. Se conservó la interfaz de seis fotos de desarrollo y
  se eliminó el tablero, se ocultaron 14 de los 64 píxeles normalizados de la
  primera columna o se ocultó la columna completa. Son controles construidos;
  no sustituyen un conjunto independiente de negativos naturales.

No se ha consultado la evaluación final reservada ni se ha reentrenado ningún modelo.
Los tiempos de los informes corresponden a ejecuciones locales y no son un
benchmark aislado de rendimiento móvil.

## Ver la detección de una foto

Desde la raíz del repositorio y con `.venv` activado:

```bash
python -m tools.detect_photo ".cache/real-use-tests/mi-foto.jpg" --output .cache/photo-detection/mi-foto
```

Usa una carpeta de salida nueva o vacía. Se guardan:

- `outline.jpg`: foto reducida con el contorno rojo y las cuatro esquinas numeradas.
- `rectified.png`: vista del tablero corregida a 512×512 para inspección.
- `detection.json`: coordenadas en la imagen original y descripción del diagnóstico.

Este JSON es de una **herramienta de diagnóstico**, no cambia el contrato público
de reconocimiento, que sigue devolviendo únicamente `piecePlacement`. En un fallo
de lectura o detección, el comando devuelve un error JSON y código de salida 1;
los argumentos inválidos producen código 2. No se reemplazan archivos de pruebas
anteriores ni se modifica la foto original. Admite PNG/JPEG, con orientación EXIF
normalizada por la entrada existente; convierte HEIC previamente.

Ya hay un ejemplo comprobado en
`.cache/photo-detection-v1/chesscom-5393/outline.jpg` y su `rectified.png`.
Para probar además las piezas de una nueva detección puedes usar, como recorrido
manual de desarrollo, el clasificador existente sobre el recorte:

```bash
python -m tools.recognize_photo .cache/photo-detection/mi-foto/rectified.png --model .cache/neural-phone-v1/best.pt --orientation white-bottom --rectified
```

Usa `black-bottom` si corresponde. Tener esquinas correctas no garantiza reconocer
todas las piezas; se mantienen las limitaciones del [clasificador fotográfico](phone-classifier-analysis.md).

## Pruebas y límites

Pasan 17 pruebas fotográficas específicas: perspectiva, inclinación, iluminación,
marcas, recuperación sin contorno exterior, varias cuadrículas, falsos tableros,
cuadrículas de otras dimensiones, recortes parciales, controles de 14 píxeles,
entrada estrecha y salidas de diagnóstico. La comprobación conjunta con las
regresiones digitales pasa 281 pruebas y omite tres por capturas locales ausentes;
las 17 fotográficas se volvieron a comprobar tras proteger la entrada estrecha.

```bash
python -m pytest tests/test_photo_detection.py tests/test_detection.py tests/test_detection_structure.py tests/test_detection_bounds.py tests/test_detection_border_grid.py tests/test_detection_clutter.py tests/test_detection_anisotropic.py -m "not evaluation" -q
python -m tools.evaluate_photo_detection --manifest data/manifests/phone-validation-v1.json --output .cache/photo-detection-validation-recheck.json
```

Alcance: cuadrículas completas, aproximadamente frontales o con perspectiva e
inclinación moderadas, con alternancia visible y suficiente tamaño/contraste.
Los lados de una propuesta deben medir al menos 80 píxeles en la imagen de trabajo
y su razón máxima/mínima debe ser menor que 2. No se garantizan inclinaciones
extremas, reflejos intensos, oclusión importante, muaré severo, casillas de bajo
contraste o distorsión de lente. Un patrón ajedrezado decorativo de 8×8 puede ser
geométricamente indistinguible de un tablero vacío.

El siguiente paso es integrar explícitamente este detector y la rectificación
en el recorrido fotográfico, comprobando posiciones completas y preservando el
recorrido digital. No se declara todavía aceptada la versión fotográfica.
