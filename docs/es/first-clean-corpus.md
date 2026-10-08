# Primer corpus limpio de clasificación

[English](../en/first-clean-corpus.md) | **Español** · [Inicio](README.md)

Los pasos 6.1 y 6.2 definen y recogen el primer corpus limpio para un clasificador
aprendido de casillas. La integridad de las capturas se comprueba por separado
de la precisión del reconocimiento. Recoger datos no añade modelos, dependencias
ni perfiles de reconocimiento.

La recogida local completada contiene **3600 pares PNG/JSON verificados** en 720
lotes. El [informe de integridad](../../data/reports/digital-clean-corpus-v1.json)
recoge todas las imágenes y sus particiones heredadas. Solo verifica las capturas;
no se ha entrenado ni evaluado ningún modelo.

## Combinaciones seleccionadas

Cada juego se captura sobre **los tres fondos** indicados. Fondo y piezas siguen
siendo parámetros independientes.

| Plataforma | Piezas (`pieceSet`) | Fondos (`boardTheme`) | Función |
| --- | --- | --- | --- |
| Lichess | `cburnett` | `brown`, `blue`, `green` | Conservar referencias marrón/azul y añadir otro fondo |
| Lichess | `merida` | `brown`, `blue`, `green` | Ampliar la captura verde/Merida comprobada |
| Lichess | `alpha` | `brown`, `blue`, `green` | Reutilizar las piezas del piloto morado/Alpha sobre fondos compartidos |
| Chess.com | `neo` | `green`, `brown`, `blue` | Conservar la referencia verde predeterminada y añadir otros fondos |
| Chess.com | `classic` | `green`, `brown`, `blue` | Ampliar la captura azul/Classic comprobada |
| Chess.com | `bases` | `green`, `brown`, `blue` | Ampliar la captura marrón/Bases comprobada |

Son **seis juegos de piezas (tres por plataforma) y 18 combinaciones**. Neo se
identificó en el catálogo público por las mismas URL de recursos `ejgfv` del
perfil verde predeterminado. Cada captura verifica los recursos renderizados.
Capturar estilos nuevos no los convierte en perfiles de reconocimiento evaluados
ni compatibles.

Los fondos siguen afectando al contraste y la apariencia. Compartir varios entre
diseños reduce la posibilidad de asociar un fondo a unas piezas concretas. Este
es un alcance inicial, no todo el catálogo. Texturas, marcas, flechas y aplicaciones
móviles nativas quedan para etapas posteriores.

## Posiciones, tamaños y particiones

La [receta base](../../tools/capture-digital-clean-v1.json) utiliza las 80 posiciones
del [plan fijado](position-plan.md), las 18 combinaciones, ambas orientaciones y
una ventana de 1280 × 1000 píxeles CSS. La densidad de píxeles es 1.

La [herramienta de recogida](../../tools/collect_clean_corpus.py) la amplía de forma
determinista:

- `standard`: las 80 posiciones a 1280 × 1000; **2880 PNG**.
- `compact`: una posición por grupo de origen a 1024 × 900; **720 PNG**.
  Se ordenan los grupos por identificador y se elige la posición `índice_grupo % 4`
  de sus cuatro posiciones en el manifiesto. Los mismos 20 ejemplos se utilizan
  con todos los estilos.
- Ambos tamaños usan `white-bottom`, `black-bottom` y `conditions: ["clean"]`.
  El tablero se adapta a la página; sus límites medidos se guardan en cada imagen.

| Partición | Posiciones distintas | PNG estándar | PNG compactos | Total PNG |
| --- | ---: | ---: | ---: | ---: |
| Entrenamiento | 56 | 2016 | 504 | 2520 |
| Validación | 12 | 432 | 108 | 540 |
| Evaluación | 12 | 432 | 108 | 540 |
| Total | 80 | 2880 | 720 | 3600 |

Siguen siendo **20 grupos de origen independientes**, repartidos 14/3/3. Cada
variante hereda posición/grupo/partición del manifiesto fijado. No se vuelven a
repartir durante las capturas ni al recortar casillas. Más capturas no equivalen
a más posiciones independientes; muchas casillas vacías serán parecidas.

Todas las combinaciones aparecen en cada partición. Esto prueba **posiciones**
no vistas, no combinaciones desconocidas de diseño y fondo. Reservar combinaciones
requiere un experimento posterior sin mover posiciones de partición. Se pueden
comprobar las etiquetas de evaluación final para verificar las capturas; no usar
sus resultados de reconocimiento para elegir modelo, preprocesado o entrenamiento.

## Capturar y reanudar

Desde la raíz del repositorio con el extra de captura y Chromium instalados
(véase [instalación y adaptadores](configurable-capture.md)):

```bash
export PLAYWRIGHT_BROWSERS_PATH="$PWD/.cache/ms-playwright"
# Validación local opcional: sin navegador ni descargas
python -m tools.capture_batch capture tools/capture-digital-clean-v1.json --output-root .cache/digital-clean-corpus --validate-only
# Capturar; repetir exactamente este comando para reanudar
python -m tools.collect_clean_corpus --output-root .cache/digital-clean-corpus --report data/reports/digital-clean-corpus-v1.json
# Revisar los pares PNG/JSON guardados sin abrir el navegador
python -m tools.collect_clean_corpus --output-root .cache/digital-clean-corpus --report data/reports/digital-clean-corpus-v1.json --audit-only
```

La [comprobación de 36 imágenes](../../tools/capture-digital-clean-style-check-v1.json)
utiliza exclusivamente la posición de entrenamiento `digital-009`. Su ejecución
local completada está en `.cache/digital-clean-checks/`. Se excluye del corpus del
modelo: verifica la herramienta, no añade 36 posiciones independientes.

La herramienta genera **720 lotes atómicos**, uno por estilo/tamaño/grupo de origen.
Cada uno contiene ocho imágenes estándar o dos compactas. La salida queda así:

```text
.cache/digital-clean-corpus/digital-positions-v1/
  clean-<platform>-<background>-<pieces>-<standard|compact>-sequence-NNN/
    batch.json
    <training|validation|evaluation>/<configurationId>/
      digital-NNN-<white-bottom|black-bottom>.png
      digital-NNN-<white-bottom|black-bottom>.json
```

Se reutiliza una página por estilo y tamaño. En Lichess se cambia la posición
mediante el campo FEN del editor y el control de giro; en Chess.com, mediante
`game.load` y su control de giro. Cada imagen conserva las verificaciones del DOM
antes y después de capturar. La reutilización y las modificaciones se registran
en la procedencia: son páginas automatizadas modificadas, no pantallas intactas
de partidas reales.

Antes de guardar se comprueban las piezas, sus colores y casillas, la orientación,
las URL de recursos efectivamente aplicados frente al estilo elegido, su carga,
el tablero completo y visible, la ausencia de marcas y la estabilidad durante
la captura. Se decodifica el PNG y se verifican sus dimensiones y límites. Un
estilo no disponible o una actualización fallida interrumpe el grupo sin sustituir
datos silenciosamente.

Un grupo fallido se descarta y reintenta con un contexto nuevo del navegador,
hasta tres veces. Se conservan los grupos completados. Al reanudar se revisan los
lotes existentes sin sobrescribirlos: manifiesto/receta, variantes previstas,
partición, filas/orientación renderizadas, hash del PNG, igualdad de anotaciones,
dimensiones y límites deben coincidir. Archivos ausentes, adicionales o alterados
hacen fallar la ejecución. Usa una raíz exclusiva, sin otros lotes.

Una interrupción brusca puede dejar `.capture.lock` y carpetas temporales
`.capture-*`. Solo tras comprobar que no sigue ejecutándose la herramienta,
elimina esas entradas temporales, conserva los lotes `clean-*` terminados y
reanuda. No cambies etiquetas para saltarte una verificación. Un lote terminado
corrupto requiere investigar y eliminar expresamente ese lote antes de recapturarlo.

El informe de finalización se escribe **solo cuando todos los lotes pasan**.
Recoge rutas/hashes, identidades, configuraciones, dimensiones y límites de cada
PNG; la configuración completa y procedencia están en las anotaciones locales.
La herramienta devuelve 0 si funciona y 1 si falla. Sus mensajes de progreso no
forman parte del contrato JSON de la CLI de reconocimiento.

Las imágenes permanecen en `.cache/`, ignorada por Git: subir recetas, código e
informe no guarda las imágenes. Conserva una copia del corpus antes de limpiar
la caché o vuelve a capturarlo y genera un informe nuevo. Las plataformas pueden
cambiar; otra ejecución no garantiza PNG idénticos byte a byte.

## Capturas manuales y siguiente paso

**No necesitas capturas manuales para este lote limpio.** Las 20 capturas reales
aportadas contienen resaltados del último movimiento y siguen separadas como
datos de detección. Antes de clasificarlas hay que revisar posiciones/procedencia
y ampliar la importación de partidas reales. Sus grupos reservados de evaluación
deben seguir reservados. Otras interfaces, partidas reales y apps nativas
necesitarán ejemplos adicionales más adelante.

Lo siguiente es generar casillas etiquetadas conservando las particiones,
comprobar cobertura por clase/fondo/estilo y después entrenar un modelo pequeño
y compararlo con las plantillas. Recoger datos no demuestra precisión de
reconocimiento.

Conserva [atribuciones y condiciones de los recursos](../../data/THIRD_PARTY_NOTICES.md).
Alpha tiene condiciones de uso personal/no comercial; esta recogida experimental
no establece derechos de distribución del arte ni de un modelo futuro.
