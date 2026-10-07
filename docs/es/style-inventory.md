# Inventario de estilos y condiciones digitales

[English](../en/style-inventory.md) | **Español** · [Inicio](README.md)

Inventario v1, revisado el **2026-10-07**. Esta es la lista delimitada de ampliación
para Lichess y Chess.com. Los diagramas de libros quedan aplazados. Añadir una fila
registra trabajo pendiente; no añade un perfil de reconocimiento ni demuestra
compatibilidad.

Las tres combinaciones digitales existentes son **pilotos evaluados**. Ninguna
se eleva aquí a compatibilidad general de una versión: cada una tiene cuatro
capturas reservadas de solo dos posiciones independientes, compartidas entre los
tres perfiles.

## Tres dimensiones independientes

| Dimensión | Registrar por separado | Responsabilidad del reconocimiento |
| --- | --- | --- |
| Fondo del tablero | Plataforma, ID local del estilo, nombre original, versión/hash del recurso, colores planos o textura | Detección y tratamiento del fondo |
| Diseño de piezas | Plataforma, ID local del estilo, nombre original, versión/hash del recurso, doce símbolos visibles | Clasificación de trece clases, incluida la casilla vacía |
| Distribución de interfaz | Pantalla/página, cliente, versión, tamaño de ventana, densidad de píxeles, modo claro/oscuro, coordenadas y límites del tablero | Encontrar el tablero entre elementos de interfaz y leer pistas de orientación |

El fondo de la página fuera de la cuadrícula pertenece a la **interfaz**, no al
fondo del tablero. Un «tema» de la plataforma puede combinar las tres dimensiones.
Que dos plataformas usen el mismo nombre no demuestra que sus dibujos sean iguales.

La unidad de compatibilidad es una combinación explícita de **fondo + piezas +
interfaz/cliente + condiciones**. Evaluar un componente no demuestra compatibilidad
con su producto cartesiano con los demás. Las tablas organizan la recogida de
datos; sus entradas E se refieren exclusivamente a C01–C03.

Los objetos `Profile` de `src/boardsnap/profiles.py` siguen agrupando la configuración
de ejecución. Este hito separa el inventario y los futuros campos de anotación;
no permite combinar estilos arbitrariamente mediante la API Python o la CLI.
`--profile` y el contrato de salida permanecen iguales.

## Estados y requisitos para avanzar

| Código | Estado | Evidencia necesaria |
| --- | --- | --- |
| P | Pendiente de capturar | Objetivo identificado; no hay corpus anotado que cubra ese alcance exacto. Comprobar disponibilidad y dibujos antes de recoger datos. |
| D | En desarrollo | Hay muestras versionadas y anotadas, con grupos de origen y particiones fijados; falta implementar o validar. |
| E | Evaluado | Implementación congelada probada con datos reservados e informe enlazado con fallos y resultados de posiciones completas. La evaluación puede fallar. |
| C | Compatible | E más los criterios de aceptación de la versión, definidos previamente, superados para las combinaciones, clientes y condiciones enumerados. |

Ninguna tabla declara C actualmente. «Pendiente» para Android/iOS significa que
BoardSnap no tiene capturas que lo demuestren; **no** afirma que el tema exista
en esa aplicación. Un script, un ejemplo dibujado o una prueba unitaria que pasa
no bastan para marcar E o C. Desarrollar solamente la herramienta de captura
tampoco basta para marcar D.

Antes de pasar una combinación evaluada a C, registrar un plan de aceptación con
el número de **posiciones independientes**, tamaños, condiciones, versiones de
cliente, objetivo de posiciones exactas, tolerancia de límites y objetivo para
imágenes negativas. Fijarlos antes de la evaluación final. No basta con superar
los pilotos actuales de cuatro imágenes. Contar los fallos de detección en el
denominador del flujo completo y publicar precisión por clase/fondo, coincidencias
exactas de `piecePlacement` y tiempo de procesamiento. Separar los resultados por
condición para que los tableros limpios no oculten fallos con flechas. La
compatibilidad describe el alcance medido, no una garantía de perfección.

## Fuentes y alcance delimitado

- Lichess: se consultaron los registros públicos de [fondos 2D](https://github.com/lichess-org/lila/blob/master/modules/pref/src/main/Theme.scala)
  y [piezas 2D](https://github.com/lichess-org/lila/blob/master/modules/pref/src/main/PieceSet.scala)
  en la fecha de revisión. La lista incluye 25 fondos y 41 diseños de piezas
  visibles; `disguised` se excluye al final. Esas ramas pueden cambiar; esta tabla
  solo cambia mediante una actualización explícita del inventario.
- Chess.com: los [ejemplos de fondos](https://www.chess.com/article/view/what-your-chess-board-theme-says-about-you)
  y [ejemplos de piezas](https://www.chess.com/article/view/what-your-chess-piece-style-says-about-you)
  publicados en 2022 aportan nombres para una **selección inicial de objetivos**,
  no un catálogo actual completo. El enlace público de ajustes redirigió al inicio
  de sesión durante la revisión; hay que comprobar selección y disponibilidad al
  capturar. Las anotaciones existentes identifican los recursos `9rdwe` y `ejgfv`,
  pero no una correspondencia verificada entre esas piezas y la etiqueta «Neo»
  del selector.
- La [guía de personalización de Chess.com](https://support.chess.com/en/articles/8594320-how-do-i-change-my-background-board-and-pieces)
  distingue los ajustes web/móvil y los temas especiales temporales. Los clientes
  móviles necesitan capturas independientes: compartir dibujos no verifica su
  interfaz, escalado ni representación de coordenadas.

G1 es el primer grupo de recogida: fondos planos y piezas 2D convencionales.
G2 es el grupo posterior: texturas, dibujos más diferentes y diseños restantes
cuya apariencia necesita revisión. Son **prioridades de planificación**, no una
medida de dificultad ni una afirmación de que todos los fondos G2 tengan textura.

Esta versión tiene **88 filas de componentes**: 25 fondos Lichess, 41 juegos de
piezas Lichess, 11 fondos Chess.com y 11 entradas de piezas Chess.com (incluido el
predeterminado fijado, cuyo alias falta por confirmar). No son 88 perfiles
compatibles. Si se confirma que Neo es el predeterminado capturado, unir el alias
con evidencia en vez de contarlo como nueva cobertura. Las entradas adicionales
del selector de Chess.com requerirán otra revisión del inventario; reconocer
«todos los temas actuales o futuros» no es el criterio de finalización de v1.

## Fondos del tablero

La columna Web se refiere únicamente a las interfaces limitadas de escritorio
C01–C03. El navegador móvil tiene su propio estado en la tabla de interfaces.

### Lichess

| Nombre original del fondo | Grupo | Web | App Android | App iOS |
| --- | --- | --- | --- | --- |
| `brown` | G1 | E (C01) | P | P |
| `wood` | G2 | P | P | P |
| `wood2` | G2 | P | P | P |
| `wood3` | G2 | P | P | P |
| `wood4` | G2 | P | P | P |
| `maple` | G2 | P | P | P |
| `maple2` | G2 | P | P | P |
| `horsey` | G2 | P | P | P |
| `leather` | G2 | P | P | P |
| `blue` | G1 | E (C02) | P | P |
| `blue2` | G2 | P | P | P |
| `blue3` | G2 | P | P | P |
| `canvas` | G2 | P | P | P |
| `blue-marble` | G2 | P | P | P |
| `ic` | G2 | P | P | P |
| `green` | G1 | P | P | P |
| `marble` | G2 | P | P | P |
| `green-plastic` | G2 | P | P | P |
| `olive` | G2 | P | P | P |
| `grey` | G2 | P | P | P |
| `metal` | G2 | P | P | P |
| `newspaper` | G2 | P | P | P |
| `purple` | G1 | P | P | P |
| `purple-diag` | G2 | P | P | P |
| `pink` | G2 | P | P | P |

### Chess.com

Los nombres son candidatos del catálogo salvo el recurso Green capturado.
Un cambio de dibujo bajo el mismo nombre necesita otra versión y evaluación.

| Nombre del fondo / recurso fijado | Grupo | Web | App Android | App iOS |
| --- | --- | --- | --- | --- |
| Green (`9rdwe`) | G1 | E (C03) | P | P |
| Brown | G1 | P | P | P |
| Blue | G1 | P | P | P |
| Dark Wood | G2 | P | P | P |
| Walnut | G2 | P | P | P |
| Icy Sea | G2 | P | P | P |
| Tournament | G2 | P | P | P |
| Bubblegum | G2 | P | P | P |
| Marble | G2 | P | P | P |
| Glass | G2 | P | P | P |
| Lolz | G2 | P | P | P |

## Diseños de piezas

Hay que recoger todas las clases sobre casillas claras y oscuras. Nombres como
Alpha o Wood en dos plataformas son objetivos diferentes hasta verificar que los
dibujos coinciden; incluso esa coincidencia no transfiere la compatibilidad del
flujo completo.

### Lichess

| Nombre original de piezas | Grupo | Web | App Android | App iOS |
| --- | --- | --- | --- | --- |
| `cburnett` | G1 | E (C01, C02) | P | P |
| `merida` | G1 | P | P | P |
| `alpha` | G1 | P | P | P |
| `pirouetti` | G2 | P | P | P |
| `chessnut` | G2 | P | P | P |
| `chess7` | G2 | P | P | P |
| `reillycraig` | G2 | P | P | P |
| `companion` | G2 | P | P | P |
| `riohacha` | G2 | P | P | P |
| `kosal` | G2 | P | P | P |
| `leipzig` | G2 | P | P | P |
| `fantasy` | G2 | P | P | P |
| `spatial` | G2 | P | P | P |
| `celtic` | G2 | P | P | P |
| `california` | G2 | P | P | P |
| `caliente` | G2 | P | P | P |
| `pixel` | G2 | P | P | P |
| `firi` | G2 | P | P | P |
| `rhosgfx` | G2 | P | P | P |
| `maestro` | G2 | P | P | P |
| `fresca` | G2 | P | P | P |
| `cardinal` | G2 | P | P | P |
| `gioco` | G2 | P | P | P |
| `tatiana` | G2 | P | P | P |
| `staunty` | G2 | P | P | P |
| `cooke` | G2 | P | P | P |
| `monarchy` | G2 | P | P | P |
| `papercut` | G2 | P | P | P |
| `minimal-warmth` | G2 | P | P | P |
| `governor` | G2 | P | P | P |
| `dubrovny` | G2 | P | P | P |
| `shahi-ivory-brown` | G2 | P | P | P |
| `icpieces` | G2 | P | P | P |
| `mpchess` | G2 | P | P | P |
| `kiwen-suwi` | G2 | P | P | P |
| `totoy` | G2 | P | P | P |
| `horsey` | G2 | P | P | P |
| `anarcandy` | G2 | P | P | P |
| `xkcd` | G2 | P | P | P |
| `shapes` | G2 | P | P | P |
| `letter` | G2 | P | P | P |

### Chess.com

| Nombre de piezas / recurso fijado | Grupo | Web | App Android | App iOS |
| --- | --- | --- | --- | --- |
| Predeterminado capturado (`ejgfv`) | G1 | E (C03) | P | P |
| Neo | G1 | P | P | P |
| Classic | G1 | P | P | P |
| Bases | G1 | P | P | P |
| Alpha | G1 | P | P | P |
| Icy Sea | G1 | P | P | P |
| Wood | G2 | P | P | P |
| Neo-Wood | G2 | P | P | P |
| Glass | G2 | P | P | P |
| Game Room | G2 | P | P | P |
| Marble | G2 | P | P | P |

## Interfaces y clientes objetivo

Los ID siguientes son identificadores del inventario, no opciones implementadas
en la CLI. «Web» sin matices no debe incluir todos los navegadores, tamaños o páginas.

| ID de interfaz | Plataforma / cliente / pantalla | Estado | Evidencia o trabajo pendiente |
| --- | --- | --- | --- |
| LC01 | Lichess, Chromium de escritorio, editor | E | C01, C02; ventana de 1280 × 1000, densidad 1, cuadrícula de 584 px; el script oculta campos FEN/URL y control de tamaño |
| LC02 | Lichess, navegador de escritorio, análisis/estudio | P | Capturar ambas pantallas por separado, con barra lateral y panel de evaluación |
| LC03 | Lichess, navegador de escritorio, partida | P | Capturar relojes, paneles de jugadores y lista de movimientos |
| LC04 | Lichess, navegador móvil | P | Chrome en Android y Safari en iOS; vertical y horizontal por separado |
| LC05 | Lichess, app nativa Android | P | Registrar app/versión, dispositivo y sistema; pantallas de partida y análisis |
| LC06 | Lichess, app nativa iOS | P | Registrar app/versión, dispositivo y sistema; pantallas de partida y análisis |
| CC01 | Chess.com, Chromium de escritorio, análisis | E | Combinación C03; ventana de 1280 × 1000, cuadrícula de 704 px; el script oculta flechas, resaltados, barra de evaluación y campos |
| CC02 | Chess.com, navegador de escritorio, partida | P | Capturar relojes, paneles de jugadores y lista de movimientos |
| CC03 | Chess.com, navegador de escritorio, revisión/problemas | P | Capturar ambas pantallas por separado, incluidas anotaciones de revisión |
| CC04 | Chess.com, navegador móvil | P | Chrome en Android y Safari en iOS; vertical y horizontal por separado |
| CC05 | Chess.com, app nativa Android | P | Registrar app/versión, dispositivo y sistema; pantallas de partida y análisis |
| CC06 | Chess.com, app nativa iOS | P | Registrar app/versión, dispositivo y sistema; pantallas de partida y análisis |

LC/CC identifican interfaces; C01–C03 identifican combinaciones de reconocimiento evaluadas.
El navegador de las anotaciones existentes es Chromium 153.0.8010.12.
Para cada interfaz de escritorio, verificar Firefox y Safari sigue en P. Emular
un tamaño de móvil en Chromium aporta datos de desarrollo, no evidencia de una
app nativa Android/iOS. Recortar un tablero de escritorio tampoco demuestra
compatibilidad móvil.

## Combinaciones evaluadas existentes

Solo estas tres combinaciones tienen evidencia de reconocimiento digital hoy.
«Limpio» significa piezas estáticas, cuadrícula completa y alineada, sin flechas,
resaltados ni obstrucciones. Hay ambas vistas; el perfil se selecciona explícitamente.

| ID | Fondo | Piezas | Interfaz | Perfil de ejecución | Estado | Resultado reservado |
| --- | --- | --- | --- | --- | --- | --- |
| C01 | Lichess brown | cburnett | LC01 | `lichess-cburnett-brown-v1` | E | 4/4 posiciones, 256/256 casillas |
| C02 | Lichess blue | cburnett | LC01 | `lichess-cburnett-blue-v1` | E | 4/4 posiciones, 256/256 casillas |
| C03 | Chess.com Green `9rdwe` | capturadas `ejgfv` | CC01 | `chesscom-default-green-v1` | E | 4/4 posiciones, 256/256 casillas |

Evidencia: [informe brown](../../data/reports/lichess-cburnett-brown-v1-classification-evaluation.json),
[informe blue](../../data/reports/lichess-cburnett-blue-v1-classification-evaluation.json),
[informe Chess.com](../../data/reports/chesscom-default-green-v1-classification-evaluation.json)
y [limitaciones de los perfiles](profiles.md).
Los tres reutilizan los mismos dos grupos de posiciones reservadas. El tablero
vacío de ajuste de Chess.com se obtuvo eliminando explícitamente piezas del DOM;
su procedencia no demuestra una interfaz nativa de tablero vacío.

## Condiciones que evaluar por separado

Los estados se refieren a las **combinaciones digitales anteriores**, no a todos
los estilos inventariados. «D» indica que existen casos limitados de regresión,
pero falta evidencia más amplia mediante capturas. Este documento no declara
compatible ninguna condición nueva.

| ID | Condición | Estado | Cobertura necesaria / evidencia existente |
| --- | --- | --- | --- |
| K01 | PNG limpio, completo y alineado | E | Informes existentes C01–C03, solo tamaños originales |
| K02 | Blancas/negras abajo, orientación explícita | D | Regresión con posición asimétrica en los tres perfiles; ampliar a nuevos estilos/interfaces |
| K03 | Coordenadas presentes / ausentes / contradictorias | D | Pruebas de prioridad automática/explícita, incluidas imágenes de ajuste editadas; capturar ejemplos naturales |
| K04 | Solo tablero / desplazado / márgenes con interfaz | D | Regresiones geométricas sintéticas existentes; faltan capturas independientes |
| K05 | Tamaño, zoom del navegador, densidad de píxeles | D | Hay escalados de ajuste al 75%/125%; recoger cuadrículas nativas de 256/384/512/768 px y densidades 1/2/3 cuando sea posible |
| K06 | JPEG / imagen compartida recomprimida | P | La decodificación RGB existe, pero falta evaluación representativa de compresión en el flujo completo; empezar con calidades 95/80/60 |
| K07 | Interfaz clara/oscura y paneles alrededor | P | Probar detección frente a colores similares de interfaz, ambos modos y variantes de pantalla |
| K08 | Casillas destacadas del último movimiento | P | Origen/destino, claras/oscuras, ocupadas y vacías |
| K09 | Casilla seleccionada e indicadores de movimientos legales | P | Puntos/anillos, destinos ocupados de captura, ambos colores de piezas |
| K10 | Resaltados de jaque y premovimiento | P | Colores/opacidades diferentes, rey destacado y otras casillas ocupadas |
| K11 | Flechas y círculos dibujados por el usuario | P | Colores, grosores, cruces, casillas vacías y piezas |
| K12 | Flechas del motor e insignias de calidad de jugada | P | Una/varias flechas, etiquetas que toquen piezas y bordes |
| K13 | Superposiciones combinadas | P | Casos explícitos: último movimiento + flecha; selección + indicadores; jaque + flecha; insignia de revisión + flecha del motor |
| K14 | Imágenes negativas y ambiguas | D | Hay regresiones sin tablero, con franjas, vacías y con varias cuadrículas; añadir interfaz real sin tablero, tablas parecidas y tableros parciales |

Los valores de K05/K06 son puntos de prueba previstos, no rangos compatibles.
Probar las superposiciones sobre capturas completas **antes** de extraer casillas,
manteniendo juntas las variantes limpias y anotadas de una posición en la misma
partición. Una flecha sobre casillas vacías no demuestra reconocimiento de una
flecha que tape una pieza. Si un símbolo queda completamente oculto o no se
distingue visualmente, puede faltar información para recuperarlo exactamente;
no corregirlo inventando legalidad, turno ni campos adicionales del FEN.

## Lotes de trabajo ordenados

1. **Ampliar evidencia de C01–C03.** Recoger posiciones independientes con las trece
   clases sobre ambos fondos, las dos vistas y geometría limpia; fijar el plan de
   aceptación antes de consultar las nuevas imágenes reservadas.
2. **Fondos G1 con piezas fijas.** Lichess green y purple con cburnett; Chess.com
   Brown y Blue con el dibujo predeterminado verificado. Mantener la interfaz de
   escritorio y PNG limpio mientras cambia el fondo.
3. **Piezas G1 con fondo fijo.** Lichess merida y después alpha sobre brown;
   Chess.com verificar el alias Neo y después Classic, Bases, Alpha e Icy Sea
   sobre Green. Capturar posiciones diagnósticas y posiciones reales independientes.
4. **Combinaciones G1 y clientes.** Probar combinaciones cruzadas antes de declararlas.
   Ampliar a pantallas de partida/análisis, navegador móvil, app Android y después
   app iOS. Registrar un resultado por cada combinación/cliente declarado.
5. **Condiciones K05–K13.** Primero tamaños/compresión/modos de interfaz, después
   casillas destacadas, indicadores/jaque/premovimiento, flechas/círculos,
   anotaciones de revisión y los cuatro casos mixtos enumerados. Fijar la cobertura
   exacta en lugar de «cualquier superposición».
6. **G2.** Recorrer los fondos y diseños restantes en el orden de las tablas,
   comprobando primero apariencia y disponibilidad. Empezar con un compañero de
   referencia para cada componente y evaluar después las combinaciones a publicar.

Variar un componente facilita la recogida; no demuestra que todas las parejas
funcionen. Un grupo se completa cuando el manifiesto de la versión enumera sus
combinaciones compatibles y cada combinación declarada supera su plan de
aceptación. Las entradas que no se puedan obtener o interpretar se retirarán o
aplazarán explícitamente con un motivo en otra revisión, sin contarlas como compatibles.

## Anotación y mantenimiento

Registrar estos campos por separado en el manifiesto versionado de cada nueva
recogida (son **metadatos propuestos**, no campos aceptados por las herramientas actuales):

- `platform`, `boardStyleId`, `pieceStyleId`, `layoutId` y hashes de los dibujos fijados.
- Tipo de cliente (`desktop-web`, `mobile-web`, `android-app`, `ios-app`), versión de
  navegador/app, sistema, dimensiones de ventana/imagen, densidad y modo de interfaz.
- ID de condiciones, colores/opacidad/geometría exactos de superposiciones, escalado
  y compresión.
- URL/fecha de origen, hash de imagen, grupo de origen, partición, `piecePlacement`
  esperado, orientación visual y límites del tablero comprobados independientemente.
- Disponibilidad/fuente de captura, atribución, ruta del informe, revisión del
  código/recursos evaluados, número de fallos y fecha de cada cambio de estado.

Mantener juntas cada posición y sus variantes de recorte, vista, superposiciones,
temas y compresión entre particiones. Los modelos aprendidos necesitarán además
una partición de validación distinta de la evaluación final. Documentar los nuevos
dibujos externos en los [avisos de procedencia](../../data/THIRD_PARTY_NOTICES.md).

Actualizar estados en este documento y su versión inglesa a la vez, enlazar la
evidencia, conservar informes de regresión anteriores y mantener los ID estables.
Este inventario no introduce integración HTTP/Flutter, reconocimiento de nuevos
temas, dependencia de PyTorch ni ampliaciones de la herramienta de captura.

## Fuera del inventario v1

Tableros físicos 3D, modos digitales en perspectiva/3D, animaciones de movimiento,
piezas ocultas/a ciegas (incluido `disguised` de Lichess), temas temporales de eventos,
CSS arbitrario del usuario/fondos de tablero subidos a medida y diagramas de libros.
Las futuras entradas del catálogo necesitan una revisión explícita del alcance.
Este límite no elimina el perfil experimental de libros; simplemente aplaza ese trabajo.

