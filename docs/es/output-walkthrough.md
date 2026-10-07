# Cómo funciona output.py

[English](../en/output-walkthrough.md) | **Español** · [Inicio](README.md)

[output.py](../../src/boardsnap/output.py) recibe un tablero cuyas piezas ya
están identificadas y ordenadas, valida su estructura y devuelve un diccionario
con únicamente `piecePlacement`, el primer campo del FEN.

Esta guía explica la implementación paso a paso. El
[contrato de salida](output-contract.md) define el comportamiento esperado y
[test_output.py](../../tests/test_output.py) contiene sus pruebas.

## 1. Los símbolos permitidos

```python
_PIECE_SYMBOLS = frozenset("PNBRQKpnbrqk")
```

Esta constante contiene los doce caracteres válidos para representar piezas:

| Pieza | Blancas | Negras |
| --- | --- | --- |
| Peón | `P` | `p` |
| Caballo | `N` | `n` |
| Alfil | `B` | `b` |
| Torre | `R` | `r` |
| Dama | `Q` | `q` |
| Rey | `K` | `k` |

`frozenset` crea un conjunto inmutable. Permite comprobar si un símbolo pertenece
al conjunto de piezas válidas: `"P" in _PIECE_SYMBOLS` es verdadero y
`"x" in _PIECE_SYMBOLS` es falso.

El guion bajo inicial indica, por convención, que es un detalle interno del
módulo. Python no impide acceder a él.

## 2. El tipo de una fila

```python
_Row = list[str | None] | tuple[str | None, ...]
```

`_Row` es un alias de tipos: un nombre corto para describir cómo puede
representarse una fila. No crea una clase nueva.

El símbolo `|` significa «o». Una fila puede ser una lista o una tupla cuyos
elementos sean cadenas de texto o `None`. Por ejemplo:

```python
["r", None, None, None, None, None, None, "k"]
```

`None` representa una casilla vacía. En `tuple[str | None, ...]`, los puntos
suspensivos indican una cantidad variable de elementos de esos tipos. La
exigencia de ocho casillas se comprueba dentro de la función.

## 3. La definición de la función

La firma de la función es la siguiente; los puntos suspensivos de este fragmento
representan el cuerpo omitido:

```python
def build_result(board: list[_Row] | tuple[_Row, ...]) -> dict[str, str]:
    ...
```

`board` puede ser una lista o una tupla de filas. La función devuelve un
diccionario con claves y valores de tipo cadena.

Estas anotaciones ayudan al editor y a las herramientas de análisis, pero
Python no valida automáticamente los argumentos por tener anotaciones. Por eso
la implementación añade comprobaciones explícitas.

El bloque entre triples comillas que sigue a la firma en el archivo es el
*docstring*. Documenta qué hace la función, qué entrada espera y qué excepciones
puede producir. La primera línea del archivo también es un docstring, pero
describe el módulo completo.

La matriz debe llegar ordenada así:

| Posición en la matriz | Casilla |
| --- | --- |
| `board[0][0]` | `a8` |
| `board[0][7]` | `h8` |
| `board[7][0]` | `a1` |
| `board[7][7]` | `h1` |

Los índices empiezan en cero. La función conserva ese orden; no deduce desde
qué lado se veía el tablero en la imagen.

## 4. La validación del tablero completo

```python
if not isinstance(board, (list, tuple)):
    raise TypeError("Board must be a list or tuple of rows.")
if len(board) != 8:
    raise ValueError("Board must contain exactly 8 rows.")
```

Primero se comprueba que `board` sea una lista o una tupla. Después se comprueba
que tenga ocho filas.

| Excepción | Cuándo se utiliza | Ejemplo |
| --- | --- | --- |
| `TypeError` | El tipo recibido es incorrecto. | `None`, un número o una cadena como tablero. |
| `ValueError` | El tipo es válido, pero su valor no cumple el contrato. | Una lista con siete filas. |

`raise` interrumpe la ejecución y comunica el error al código que llamó a la
función. No se devuelve una posición parcial. Comprobar el tipo antes de llamar
a `len()` también permite dar un mensaje claro cuando se recibe algo como `None`.

Estas excepciones validan una matriz interna. Los errores estructurados de
procesamiento corresponden a entrada, detección y clasificación; consulta el
[contrato de salida](output-contract.md).

## 5. El recorrido de las filas

```python
ranks: list[str] = []
for row_index, row in enumerate(board):
    if not isinstance(row, (list, tuple)):
        raise TypeError(f"board[{row_index}] must be a list or tuple.")
    if len(row) != 8:
        raise ValueError(f"board[{row_index}] must contain exactly 8 squares.")
```

`ranks` almacenará las ocho filas ya convertidas a texto FEN. El término inglés
*rank* se refiere a una fila del tablero.

`enumerate(board)` proporciona en cada vuelta el índice de la fila y la propia
fila. En la posición inicial, la primera vuelta tiene `row_index = 0` y
`row = ["r", "n", "b", "q", "k", "b", "n", "r"]`.

Se comprueba que cada fila sea una lista o una tupla de ocho elementos. Tener
64 elementos en total no basta: una matriz con una fila de siete y otra de nueve
también se rechaza.

Los mensajes usan cadenas con prefijo `f`, que permiten insertar valores. Por
ejemplo, si falla la cuarta fila, `{row_index}` se sustituye por `3` y el mensaje
señala `board[3]`.

## 6. El recorrido de las casillas

```python
rank: list[str] = []
empty_count = 0
```

Estas variables se crean dentro del bucle de filas. `rank`, en singular, guarda
los fragmentos de la fila actual. `ranks`, en plural, guarda las filas terminadas.
`empty_count` cuenta las casillas vacías consecutivas y empieza en cero para
cada fila.

Al recorrer las casillas se aplica esta comprobación:

```python
for column_index, piece in enumerate(row):
    if piece is None:
        empty_count += 1
        continue
```

Si la casilla está vacía, se incrementa el contador. `continue` pasa directamente
a la siguiente casilla, saltándose el resto del cuerpo del bucle.

Se utiliza `piece is None` para reconocer exclusivamente el valor acordado para
una casilla vacía. `0`, `False` y `""` deben producir un error, aunque Python
también los considere falsos en una condición.

## 7. La validación de una pieza

Si la casilla no contiene `None`, se comprueba su contenido:

```python
if not isinstance(piece, str):
    raise TypeError(
        f"board[{row_index}][{column_index}] must be a piece symbol or None."
    )
if piece not in _PIECE_SYMBOLS:
    raise ValueError(
        f"Invalid piece symbol at board[{row_index}][{column_index}]: {piece!r}."
    )
```

Primero debe ser una cadena. Después debe coincidir con uno de los doce símbolos
permitidos. `"P"` es válido; `"PP"`, `"."`, `"1"` y `"♙"` no lo son.

`{piece!r}` utiliza la representación de Python del valor. Esto permite distinguir
caracteres difíciles de ver: una cadena con un salto de línea aparece como
`'P\n'` en el mensaje.

## 8. La compresión de las casillas vacías

Al encontrar una pieza válida, primero se guardan los huecos anteriores:

```python
if empty_count:
    rank.append(str(empty_count))
    empty_count = 0
rank.append(piece)
```

`if empty_count` se cumple cuando el contador es distinto de cero. `str()`
convierte el número en texto y `append()` añade ese fragmento a la lista.
Después se reinicia el contador y se añade la pieza.

Considera esta fila:

```python
[None, "P", None, None, "n", None, None, None]
```

| Al procesar… | Contador de vacías | Fragmentos guardados |
| --- | --- | --- |
| Primera casilla vacía | 1 | `[]` |
| `"P"` | 0 | `["1", "P"]` |
| Dos casillas vacías | 2 | `["1", "P"]` |
| `"n"` | 0 | `["1", "P", "2", "n"]` |
| Tres casillas vacías finales | 3 | `["1", "P", "2", "n"]` |

Los últimos tres huecos todavía no se han escrito, porque después no aparece
otra pieza. Por eso se realiza esta comprobación al terminar el bucle:

```python
if empty_count:
    rank.append(str(empty_count))
```

Ahora los fragmentos son `["1", "P", "2", "n", "3"]`. El mismo mecanismo
convierte una fila completamente vacía en `"8"`.

## 9. La construcción del resultado

Al terminar cada fila:

```python
ranks.append("".join(rank))
```

`"".join(rank)` une los fragmentos sin separador. En el ejemplo produce `"1P2n3"`.
Cuando ya están procesadas las ocho filas, la función devuelve:

```python
return {"piecePlacement": "/".join(ranks)}
```

`"/".join(ranks)` coloca `/` entre las ocho filas. El resultado es un diccionario
Python; un adaptador futuro lo codificará como JSON para la CLI o la aplicación.

## Ejemplo completo

Este ejemplo puede ejecutarse con el paquete instalado:

```python
from boardsnap.output import build_result

board = [[None] * 8 for _ in range(8)]
board[0] = [None, "P", None, None, "n", None, None, None]

result = build_result(board)
assert result == {"piecePlacement": "1P2n3/8/8/8/8/8/8/8"}
```

Se crea una lista nueva para cada fila, de modo que las filas pueden modificarse
independientemente al preparar la entrada.

## Alcance y conservación de la entrada

La función no modifica `board`: lo recorre y construye nuevas listas y cadenas.
Tampoco comprueba legalidad ajedrecística; puede serializar un tablero vacío o
una distribución con varios reyes. Su responsabilidad es validar la
representación de las 64 casillas y convertirla en colocación de piezas.

La lectura de imágenes, el reconocimiento y la resolución de orientación
pertenecen a otras etapas. No se añaden turno, enroque, captura al paso,
contadores ni puntuaciones de confianza al resultado.
