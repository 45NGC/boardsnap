# BoardSnap

[English](../en/README.md) | **Español**

`boardsnap` será un motor Python que recibe una imagen de un tablero de ajedrez
digital o un diagrama de libro y devuelve una única colocación de piezas para
la aplicación Flutter **chess-scanner**.

**Estado: estructura inicial, sin reconocimiento implementado.** El paquete se
puede instalar e importar; solo contiene `__init__.py`. Los módulos de cada etapa
se crearán cuando se implemente su funcionalidad.
Todavía no hay CLI ejecutable, estilos compatibles, imágenes de evaluación ni
pruebas funcionales. Los ejemplos JSON de la documentación describen el contrato;
no son resultados generados por el programa.

## Alcance

El motor localizará un tablero, lo recortará y normalizará, lo dividirá en
64 casillas, identificará piezas y resolverá la orientación antes de serializar
la posición. La salida contendrá exclusivamente el primer campo del FEN:

```json
{
  "piecePlacement": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR"
}
```

No habrá interfaz, editor, análisis de partidas, turno, enroque ni captura al
paso. Tampoco se devolverán puntuaciones de confianza, casillas dudosas,
alternativas ni solicitudes de confirmación. Las correcciones de piezas
corresponderán al editor de chess-scanner.

El [contrato de salida](output-contract.md) define el orden de las casillas,
la orientación por defecto y los errores estructurados. El mecanismo de
integración con Flutter está pendiente de una decisión expresa; el núcleo será
independiente de Flutter y de cualquier framework web.

## Instalación para desarrollo

Requiere Python **3.11 o posterior**, `pip` y soporte de `venv`. Desde la raíz
del repositorio, en una shell POSIX:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
python -c "import boardsnap; print(boardsnap.__file__)"
```

Si la distribución de Python no incluye `ensurepip`, instala el soporte de
entornos virtuales de tu sistema antes de crear `.venv`.

No hay dependencias de ejecución en esta iteración. `setuptools` construye el
paquete y el extra `dev` instala `pytest`. Las bibliotecas de imágenes y visión
se añadirán cuando se implemente y evalúe la etapa que las necesite.

## Estructura

```text
src/boardsnap/
    __init__.py          # Paquete Python mínimo
docs/
    en/                 # Documentación en inglés
    es/                 # Documentación en español
data/tuning/             # Futuros ejemplos de ajuste y entrenamiento
tests/
    README.md
    fixtures/evaluation/ # Futuras imágenes reservadas de evaluación
```

La [arquitectura](architecture.md) describe el flujo y la futura separación
de responsabilidades, todavía sin archivos de implementación. La
[hoja de ruta](roadmap.md) compara enfoques y fija las siguientes iteraciones.
Las guías de [datos de ajuste](tuning-data.md) e
[imágenes de evaluación](evaluation-data.md) describen las particiones previstas.
Ambos idiomas contienen los mismos documentos; al cambiar el contrato o el
alcance, se actualizarán las dos versiones.

El código, los comentarios, la configuración y los archivos generales del
proyecto se escriben en inglés. El contenido en español se limita a la
documentación de `docs/es/`.

## Pruebas

Después de instalar el extra `dev`:

```bash
python -m pytest
python -m pytest --collect-only
```

Por ahora ambos comandos descubren **cero pruebas** y terminan con código `5`,
el comportamiento de pytest cuando no hay pruebas. No indica pruebas superadas.
Véanse los [códigos de salida de pytest](https://docs.pytest.org/en/stable/reference/exit-codes.html).
La configuración está en `pyproject.toml`; no se añaden pruebas vacías ni
resultados simulados para hacer que el comando termine con éxito.

El [plan de pruebas](testing.md) incluye detección, orientación, piezas,
serialización y errores con posiciones conocidas. Las imágenes de evaluación
estarán separadas de las utilizadas para ajustar el reconocimiento.

## CLI prevista

En una iteración posterior se habilitará esta interfaz:

```bash
boardsnap imagen.png
```

**Este comando aún no está registrado ni implementado.** Producirá un objeto
JSON por imagen según el contrato, sin depender de la integración con Flutter.

## Estilos y limitaciones

Actualmente **ningún estilo está soportado**. El primer objetivo será un perfil
concreto de captura digital, fijando piezas, fondo y resoluciones con ejemplos.
Lichess y chess.com son fuentes objetivo, no una promesa de compatibilidad con
todos sus temas. Los diagramas impresos se incorporarán como perfiles separados.

Quedan fuera las fotografías de tableros físicos con piezas tridimensionales.
No se presupone compatibilidad con cualquier diseño, color o resolución. Los
primeros perfiles tampoco cubrirán tableros parciales, animaciones, piezas
ocultas, flechas, múltiples tableros o imágenes muy inclinadas o degradadas.
Sin pistas de orientación se asumirá la vista con blancas abajo (`a8` arriba a
la izquierda); una imagen con negras abajo sin coordenadas puede quedar
invertida respecto a la posición real.

## Licencia

El repositorio incluye la [GNU Affero General Public License v3](../../LICENSE).
