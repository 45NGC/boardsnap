# Contrato de salida

[English](../en/output-contract.md) | **Español** · [Inicio](README.md)

Este documento define el contrato de salida. La API Python descrita más abajo
permite construir resultados correctos a partir de matrices ya clasificadas.
La lectura de imágenes y sus tres códigos de error están implementados en
[image_input](image-input.md). La [detección](detection.md) implementa
`BOARD_NOT_FOUND` y rechaza varias cuadrículas con `UNSUPPORTED_IMAGE`.
El reconocimiento de piezas, los errores posteriores y la CLI siguen pendientes.

## Éxito

Un único objeto JSON con exactamente un campo, `piecePlacement`, de tipo cadena:

```json
{
  "piecePlacement": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR"
}
```

Es únicamente el primer campo del FEN, sin espacios ni campos adicionales:

- Ocho filas separadas por `/`, desde la octava hasta la primera.
- En cada fila, columnas de `a` a `h`.
- Blancas: `P`, `N`, `B`, `R`, `Q`, `K`; negras: `p`, `n`, `b`, `r`, `q`, `k`.
- Cada secuencia de casillas vacías se comprime en un único dígito de `1` a `8`.
- Cada fila representa exactamente ocho casillas.

No se añaden turno, enroque, captura al paso, contadores, confianza, casillas
dudosas, alternativas ni metadatos de orientación. La app decidirá cómo editar
la posición y completar los demás datos de una partida. Una clasificación
incorrecta podrá corregirse allí; no se solicitará confirmación desde el motor.

## API Python de salida

`boardsnap.output.build_result(board)` devuelve un diccionario con exactamente
`{"piecePlacement": "..."}`; la
codificación JSON pertenece al adaptador externo.
Por ejemplo, un tablero explícitamente vacío se puede serializar así:

```python
from boardsnap.output import build_result

board = [[None] * 8 for _ in range(8)]
result = build_result(board)
assert result == {"piecePlacement": "8/8/8/8/8/8/8/8"}
```

La entrada es una matriz de 8 × 8 casillas ya clasificadas, ordenada desde `a8`
hasta `h1`. El tablero y sus filas admiten listas y tuplas. Cada casilla es
`None` si está vacía o un carácter de `PNBRQKpnbrqk`. Las cadenas de texto, los
bytes y los diccionarios no son contenedores válidos para el tablero o sus filas.
Los puntos de los datos de prueba se convierten a `None` antes de llamar a esta
API; no son valores válidos para las casillas.

- Los tipos incorrectos de tablero, fila o casilla provocan `TypeError`.
- Las dimensiones incorrectas o las cadenas con símbolos inválidos provocan `ValueError`.
- La matriz de entrada no se modifica.
- Una matriz explícita de 64 casillas vacías es válida, igual que las
  distribuciones que serían ilegales en una partida; la función solo serializa
  la colocación.

Estos son errores de validación de la matriz interna, distintos de los errores
estructurados del procesamiento de imágenes descritos más abajo. Esta función
no reconoce piezas ni deduce la orientación; esas etapas deben proporcionar
la matriz en el orden canónico.

## Orientación

Implementada para las etiquetas interiores del primer perfil en
[orientation.py](orientation.md). Otras distribuciones de coordenadas siguen
sin admitirse y pueden activar la misma convención. Es un dato interno del motor.

Las coordenadas legibles del borde tendrán prioridad para identificar filas y
columnas. Resolver orientación implica asignar coordenadas a las casillas;
no implica girar los dibujos de las piezas para clasificarlas.

| Vista de la imagen | Correspondencia con la salida |
| --- | --- |
| Blancas abajo | Arriba a la izquierda = `a8`; abajo a la derecha = `h1`. |
| Negras abajo | Arriba a la izquierda = `h1`; abajo a la derecha = `a8`; se invierten filas y columnas de la matriz. |

Cuando no haya pistas suficientes o las etiquetas no permitan una lectura
coherente, se asumirá **blancas abajo**: arriba a la izquierda será `a8` y abajo
a la derecha `h1`. Esta regla es determinista y no genera un campo adicional
ni una solicitud de confirmación. Puede producir una orientación incorrecta si
el tablero real estaba visto desde negras.

La distribución de piezas, su color y el color de las casillas no bastan por sí
solos para demostrar la orientación. No se supondrá que los peones o los reyes
están en sus filas iniciales. La normalización de metadatos de una imagen es
distinta de la orientación ajedrecística; los giros de 90 grados, reflejos y
perspectivas arbitrarias quedan fuera del primer perfil.

## Fallo

Si un fallo impide obtener una posición, se devolverá exclusivamente `error`,
con un código estable para máquinas y un mensaje legible:

```json
{
  "error": {
    "code": "BOARD_NOT_FOUND",
    "message": "No se ha detectado un tablero de ajedrez en la imagen."
  }
}
```

| Código | Significado |
| --- | --- |
| `INPUT_READ_ERROR` | No se pueden leer los bytes de la entrada, por ejemplo porque el archivo no existe. |
| `INVALID_IMAGE` | Contenido vacío, corrupto o imposible de decodificar como imagen. |
| `UNSUPPORTED_IMAGE` | Formato o condición de entrada explícitamente no admitidos por el perfil implementado. |
| `BOARD_NOT_FOUND` | No se localiza un tablero utilizable. |
| `PROCESSING_FAILED` | Un fallo de procesamiento impide completar las 64 casillas y generar la colocación. |

El consumidor dependerá de `code`, no del texto exacto de `message`. No se
devolverá `piecePlacement` junto a un error, una posición parcial ni un tablero
vacío como sustituto del fallo. Un diseño desconocido puede no distinguirse
automáticamente de un fallo de detección o de una clasificación incorrecta;
la cobertura de estilos se documentará con ejemplos evaluados.

## Transporte por CLI (pendiente)

La interfaz prevista es `boardsnap imagen.png`. Para una petición válida,
`stdout` contendrá exactamente un objeto JSON terminado en salto de línea:
éxito con código de proceso `0`, o fallo de imagen/procesamiento con código `1`.
Los diagnósticos irán a `stderr`. Ayuda y errores de invocación, como omitir la
ruta, seguirán la interfaz de argumentos de la CLI; no representan una imagen
procesada y los errores de invocación usarán código `2`.

El formato de resultado no presupone HTTP ni códigos de estado de un servidor.
