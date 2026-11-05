# Catálogo fotográfico inicial

[English](../en/photo-catalogue.md) | **Español**

El paso 2 fija **siete entradas objetivo y catorce combinaciones con fondos**
para mejorar las fotografías de pantallas. Es una selección de lo que queremos
admitir, no una declaración de compatibilidad ni una evaluación nueva.
La fuente estructurada es [photo-catalogue-v1.json](../../data/manifests/photo-catalogue-v1.json),
con referencias y hashes de los informes reutilizados.

## Diseños y fondos elegidos

| Plataforma | Diseño o apariencia objetivo | Fondo 1 | Fondo 2 | Evidencia y trabajo pendiente |
| --- | --- | --- | --- | --- |
| Lichess | `cburnett` | `brown` | `blue` | Ambas configuraciones capturadas; verificar pares fotográficos identificados |
| Lichess | `merida` | `brown` | `blue` | Ambas configuraciones capturadas; verificar pares fotográficos identificados |
| Chess.com | `neo` | `green` | `brown` | Ambas configuraciones capturadas; verificar pares fotográficos identificados |
| Chess.com | `classic` | `green` | `brown` | Ambas configuraciones capturadas; verificar pares fotográficos identificados |
| Chess.com | `cc-thin-stem`: peones de tallo fino | Morado liso de referencia | `brown` | Identificar selector; referencias `chesscom-img_5401` y `5402` |
| Chess.com | `cc-shaded`: piezas sombreadas | Madera de referencia | `brown` | Identificar selector; referencias `chesscom-img_5397` y `5398` |
| Lichess | `lc-rounded-king`: rey de corona redondeada | Madera de referencia | `brown` | Identificar selector; referencias `lichess-img_5391` y `5392` |

Los primeros cuatro nombres proceden de la [receta de capturas existente](../../tools/capture-digital-clean-v1.json).
Las ocho combinaciones seleccionadas tienen 200 capturas digitales verificadas
cada una: 140 de entrenamiento, 30 de validación y 30 de evaluación histórica.
Es evidencia de integridad de captura, **no de precisión fotográfica**. Las fotos
actuales con nombres visuales como `cc-classic` o `lc-classic-a` no se asignan a
estos temas por semejanza del nombre. Tampoco se afirma cuáles son los ajustes
predeterminados actuales de las plataformas.

Las tres últimas entradas son identificadores visuales locales. El nombre
oficial del juego y el selector del fondo original siguen pendientes: «madera»
no significa necesariamente `wood` o `wood4`. Antes de automatizar sus capturas,
hay que confirmar la configuración y comparar las doce piezas renderizadas con
las referencias. Si una apariencia resulta ser uno de los cuatro diseños
conocidos, se fusionará conservando los identificadores y las referencias.
Por eso siete entradas no equivalen a siete diseños distintos demostrados.

## Por qué este grupo

Los cuatro diseños identificados ofrecen referencias convencionales cuya captura
ya funciona. Repetir dos fondos por diseño permite estudiar las piezas sin
asociarlas siempre al mismo color. Las texturas se introducen de forma acotada,
conservando los fondos de los fallos que queremos corregir.

El [inventario de errores](photo-error-inventory.md) registra:

| Apariencia | Posiciones automáticas correctas | Casillas incorrectas |
| --- | ---: | ---: |
| `cc-thin-stem` | 0/2 | 18 |
| `cc-shaded` | 0/2 | 5 |
| `lc-rounded-king` | 0/2 | 5 |

Estas seis fotos reúnen **28/32 errores automáticos de casilla** entre las 29
fotos detectadas. No son 28 observaciones independientes, ni este recuento incluye
la foto rechazada por el detector. El objetivo es reducir carencias observadas;
no demuestra que el diseño sea la única causa de los errores.

## Qué queda pendiente

- Nuevos lotes fotográficos de Lichess `alpha` y `staunty`, y Chess.com `bases` y
  `alpha`. Sus regresiones digitales existentes se conservan.
- Un tercer fondo por diseño, más texturas y todas las combinaciones posibles.
- Identificar y ampliar los otros diez grupos visuales locales enumerados en el
  manifiesto. Todas sus fotos siguen siendo controles, incluidos los fallos.
- Compatibilidad con aplicaciones nativas Android/iOS, ChessBase y distribuciones
  arbitrarias de vídeo. Fotografiar una pantalla con un móvil no demuestra
  compatibilidad con la interfaz de una aplicación móvil.
- Ampliar flechas cruzadas, reflejos fuertes, desenfoque o perspectiva severos y
  oclusiones opacas. Se mantienen las regresiones existentes con marcas y flechas.
- Diagramas de libros y tableros físicos tridimensionales.

Una foto de un vídeo puede aportar ejemplos de un diseño objetivo identificado;
su interfaz y procedencia se registrarán aparte. No valida automáticamente otros
diseños o vídeos. Esta selección tampoco retira compatibilidad digital previa.

## Siguiente recogida y comprobaciones

1. Identificar los selectores de las tres apariencias problemáticas antes de
   producir sus variantes. Se puede empezar por los cuatro diseños ya conocidos.
2. Revisar primero **15–20 fotos dirigidas**, antes de ampliar el lote. Es un
   piloto, no una cantidad que garantice precisión ni cobertura de los catorce pares.
3. Conservar por foto una captura directa de la misma posición, configuración,
   colocación esperada, orientación y partida o vídeo. El script puede generar
   referencias digitales; las fotografías de pantalla se toman con el teléfono.
4. Incluir ambas orientaciones, tableros completos, perspectiva moderada y ejemplos
   limpios y con último movimiento. Cubrir las trece clases sobre casillas claras
   y oscuras por diseño, registrando las carencias. No se necesitan todas las
   combinaciones de condiciones en el primer lote.
5. Agrupar antes de recortar: misma partida, vídeo, posición y todas sus variantes
   de fondo, vista, captura y fotografía permanecen en la misma partición.
   Las referencias antiguas conservan su grupo y partición; la validación ya
   consultada no se traslada a entrenamiento.
6. Medir por diseño y fondo con esquinas revisadas y detección automática, además
   de conservar los controles actuales. La compatibilidad dependerá de esos
   resultados y de la aceptación del siguiente candidato.

En este paso solo se selecciona el catálogo y se comprueba su coherencia con
los informes existentes. Las nuevas fotografías y su validación siguen pendientes.
No se modifica el candidato congelado `screen-preview-v1`, sus modelos ni sus
umbrales; tampoco se consulta la evaluación final independiente.
