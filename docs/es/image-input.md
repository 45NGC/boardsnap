# Entrada de imágenes

[English](../en/image-input.md) | **Español** · [Inicio](README.md)

`boardsnap.image_input.read_image(path)` acepta una cadena o un `os.PathLike`
de texto (como `pathlib.Path`) y devuelve un objeto Pillow `Image.Image`
completamente decodificado, en modo RGB con ocho bits por canal. Pillow es una
dependencia del motor, instalada mediante `python -m pip install -e '.[dev]'`.

```python
from boardsnap.image_input import ImageInputError, read_image

try:
    with read_image("data/tuning/lichess-cburnett-brown-v1/pos-001-white.png") as image:
        print(image.mode, image.size)  # RGB (1280, 1000)
except ImageInputError as error:
    print(error.to_dict())
```

La imagen contiene sus propios píxeles y no mantiene abierto el archivo. La
función no modifica la entrada, imprime resultados, cambia el tamaño, recorta
ni construye posiciones. El origen está arriba a la izquierda: `(x, y)` indica
columna y fila.

## Formatos y normalización

- Se admiten PNG y JPEG estáticos, identificados por contenido y no extensión.
  Decodificar un formato no demuestra compatibilidad del reconocimiento.
- Los modos binario, gris, gris con alfa, paleta, RGB, RGBA y CMYK se convierten
  a RGB. Se rechazan expresamente los modos de gris de mayor profundidad.
- El alfa, la transparencia de paleta y los colores transparentes se componen
  sobre blanco. El resultado no tiene canal alfa.
- Se aplica la rotación o reflexión EXIF; las dimensiones pueden cambiar.
  Esto sigue los metadatos de visualización, no la orientación de blancas o
  negras. No se deducen coordenadas de casillas.
- Se descartan los metadatos después de normalizar. No se utilizan los perfiles
  ICC incrustados para gestionar el color.
- No se admiten PNG de varios fotogramas ni formatos identificados distintos
  de PNG/JPEG.
- Se respeta la protección activa de píxeles de descompresión de Pillow; sus
  avisos y errores producen `UNSUPPORTED_IMAGE` sin cambiar el límite global.

El archivo se lee una vez. Sus bytes se verifican y se reabren en memoria para
decodificarlos completamente. Así los fallos del decodificador no se confunden
con los de lectura del archivo.
[Pillow aplaza la decodificación al abrir](https://pillow.readthedocs.io/en/stable/reference/Image.html#PIL.Image.open),
por lo que una cabecera legible no basta. La orientación de los metadatos se
aplica con [ImageOps.exif_transpose](https://pillow.readthedocs.io/en/stable/reference/ImageOps.html#PIL.ImageOps.exif_transpose).

## Fallos

Los fallos previstos lanzan `ImageInputError` con `code`, `message` y `to_dict()`.
Los mensajes están en inglés; utiliza el código, no el texto exacto.

| Código | Casos |
| --- | --- |
| `INPUT_READ_ERROR` | Archivo inexistente, directorio, permisos u otro impedimento para leer bytes |
| `INVALID_IMAGE` | Contenido vacío o no identificado, checksum corrupto, píxeles truncados o fallo de decodificación |
| `UNSUPPORTED_IMAGE` | Formato identificado no admitido, animación, modo de píxel o límite del decodificador |

El contenido que Pillow no identifica produce `INVALID_IMAGE`, incluidos los
formatos desconocidos para su decodificador. Un formato identificado no admitido
se rechaza antes de verificar toda su integridad. Un argumento de tipo incorrecto
produce `TypeError`; los errores inesperados de programación no se ocultan como
fallos de entrada.

`error.to_dict()` genera el [contrato de errores](output-contract.md), por ejemplo:

```json
{"error": {"code": "INVALID_IMAGE", "message": "The image file is empty."}}
```

El futuro adaptador convertirá ese diccionario en JSON. Los fallos no devuelven
`piecePlacement`. La [detección](detection.md) utiliza esta representación;
la CLI y la integración Flutter siguen pendientes.

## Pruebas

```bash
python -m pytest tests/test_image_input.py
python -m pytest
```

Los 31 casos utilizan imágenes temporales, sin navegador, red ni conjunto de
evaluación. Comprueban formatos válidos, orden de canales y píxeles, independencia
del archivo, modos, transparencia, CMYK, EXIF, errores de acceso, cabeceras
legibles con datos truncados, checksums corruptos, formatos o condiciones no
admitidos y límites de píxeles.
