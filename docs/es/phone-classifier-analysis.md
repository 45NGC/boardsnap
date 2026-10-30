# Diagnóstico del clasificador fotográfico

[English](../en/phone-classifier-analysis.md) | **Español**

El paso de medición está completado reutilizando las predicciones existentes.
**Recomendación: mantener foto v1 como experimento y el candidato digital como
referencia.** Se puede avanzar con la localización fotográfica, pero todavía no
hay una versión fotográfica aceptada ni compatibilidad general por tema.

Se analizaron las mismas 30 fotos de validación con esquinas revisadas: 19 tableros
completos correctos frente a 18 anteriormente, y 1.871/1.920 casillas correctas
frente a 1.863/1.920. No se entrenó, no se ejecutó inferencia nueva y no se utilizó
la evaluación final. Pesos, etiquetas, esquinas y particiones permanecen intactos.

El [informe reproducible](../../data/reports/phone-classifier-analysis-v1.json)
contiene cada fallo, comparación por casilla, soporte de cada clase, colores de
casilla, grupos visuales y condiciones. La [revisión de apariencias](../../data/manifests/phone-validation-appearance-v1.json)
es un documento separado: no modifica los manifiestos fijados para entrenar.

## Piezas y casillas

`Precisión` significa qué proporción de las predicciones de una clase era correcta;
`recuperación` significa qué proporción de sus ejemplos reales se reconoció.
Las mayúsculas representan blancas y las minúsculas negras; `empty` es vacía.

| Clase | Ejemplos | Recuperación anterior | Recuperación foto v1 | Precisión foto v1 |
| --- | ---: | ---: | ---: | ---: |
| `empty` | 1188 | 100.0% | 99.7% | 97.9% |
| `P` | 178 | 94.4% | 93.8% | 99.4% |
| `N` | 36 | 88.9% | 94.4% | 85.0% |
| `B` | 40 | 97.5% | 97.5% | 90.7% |
| `R` | 52 | 90.4% | 94.2% | 90.7% |
| `Q` | 22 | 86.4% | 95.5% | 95.5% |
| `K` | 30 | 93.3% | 93.3% | 100.0% |
| `p` | 192 | 90.6% | 92.7% | 99.4% |
| `n` | 39 | 92.3% | 92.3% | 92.3% |
| `b` | 41 | 85.4% | 87.8% | 97.3% |
| `r` | 49 | 98.0% | 100.0% | 100.0% |
| `q` | 23 | 82.6% | 82.6% | 95.0% |
| `k` | 30 | 100.0% | 100.0% | 100.0% |

La cifra global está muy influida por las 1.188 casillas vacías. Se recuperan
13 casillas y empeoran cinco: dos vacías pasan a caballo negro, otra vacía a peón
blanco, un peón blanco a torre y un alfil negro a dama. Esto ocurre en fotos que
ya fallaban; por eso no se pierde ningún tablero fotográfico completo acertado.

Confusiones predominantes: peón negro → vacía (14), peón blanco → torre (5), peón
blanco → vacía (5) y alfil negro → alfil blanco (4). Los errores abarcan forma,
presencia y color, no una única pieza. Los peones negros fallan en ambos colores
de casilla (8 claras y 6 oscuras). Hay solo una dama negra sobre casilla clara y
cuatro reyes blancos sobre clara: un 100 % en esos grupos no es evidencia sólida.

## Apariencias comprobadas

Los identificadores siguientes son **grupos visuales locales**, no nombres
oficiales de temas. Se separan diseño de piezas y fondo. Los grupos similares de
plataformas distintas no se dan por idénticos. Los resultados son descriptivos,
revisados después de consultar validación; no constituyen una nueva aceptación.

| Grupo visual | Anterior | Foto v1 | Errores de casilla foto v1 |
| --- | ---: | ---: | ---: |
| `cc-classic` | 2/2 | 2/2 | 0 |
| `cc-flat` | 0/4 | 1/4 | 3 |
| `cc-shaded` | 0/2 | 0/2 | 10 |
| `cc-thin-stem` | 0/2 | 0/2 | 23 |
| `lc-classic-a` | 6/6 | 6/6 | 0 |
| `lc-classic-b` | 2/2 | 2/2 | 0 |
| `lc-rounded-king` | 0/2 | 0/2 | 5 |
| `video-chessbase` | 1/1 | 1/1 | 0 |
| `video-classic-a` | 2/2 | 2/2 | 0 |
| `video-classic-b` | 4/4 | 4/4 | 0 |
| `video-flat-brown` | 0/1 | 0/1 | 2 |
| `video-flat-green` | 0/1 | 0/1 | 6 |
| `video-flat-vibes` | 1/1 | 1/1 | 0 |

- `cc-classic`: piezas convencionales detalladas; marrón liso.
- `cc-flat`: siluetas planas; verde y azul lisos. El fallo de e5 en IMG_5395
  coincide visualmente con varias flechas sobre un peón; los otros dos son
  confusiones de color de alfil. Son hipótesis visuales, no causas demostradas.
- `cc-shaded`: piezas sombreadas y torres con ladrillos; madera. Suma diez fallos
  en IMG_5397–5398, incluidos falsos caballos sobre casillas vacías de madera.
- `cc-thin-stem`: peones de tallo fino y copa ancha; fondo morado. IMG_5401–5402
  concentran 23/49 errores (47 %): 12 peones negros omitidos y otras confusiones
  de peones/caballos. Hay errores claros incluso sin flechas.
- `lc-classic-a/b`: dos grupos convencionales; marrón, azul grisáceo y madera.
- `lc-rounded-king`: piezas sombreadas y rey blanco de corona redondeada; madera.
  IMG_5391–5392 suman cinco fallos de damas, caballo y reyes.
- `video-flat-brown/green`: IMG_5403–5404, con interferencias fuertes que deforman
  los trazos; ocho errores. El estilo y el muaré no pueden aislarse con estas fotos.
- Los otros grupos de vídeo acertaron todas sus posiciones observadas, incluidos
  ejemplos con flechas; no se extiende ese resultado a cualquier vídeo.

La correspondencia exacta entre grupos, fotos y fondos está en el informe.
**Alcance útil actual:** clasificación experimental de tableros ya rectificados,
con orientación explícita, en estas apariencias observadas. Los siete grupos con
acierto completo reúnen 18 fotos; `cc-flat` añade un acierto en cuatro. Los grupos
con fallos se mantienen como cobertura incompleta. No declaramos ningún tema
oficial compatible por completo basándonos en una o dos fotos.

## Procedencia y condiciones

| Subconjunto | Anterior | Foto v1 |
| --- | ---: | ---: |
| `chesscom` | 2/10 | 3/10 |
| `lichess` | 8/10 | 8/10 |
| `video` | 8/10 | 8/10 |
| `arrows` | 10/12 | 10/12 |
| `highlights` | 16/26 | 17/26 |
| `textured-board` | 6/10 | 6/10 |
| `strong-moire` | 1/3 | 1/3 |
| `circles` | 2/2 | 2/2 |
| `cursor` | 2/2 | 2/2 |

Los subconjuntos se solapan y no se deben sumar. «Vídeo» describe la procedencia,
no la plataforma del tablero: se identificaron cuatro escenas Lichess y una
ChessBase; en las otras cinco se conserva `unknown`. Las escenas con un tablero
físico adicional se valoran exclusivamente por su diagrama digital.

Las 30 fotos contienen perspectiva y muaré y proceden del mismo iPhone 8.
Los bordes cortos anotados miden entre 1.788 y 2.398 píxeles; dividir por ocho da
224–300 píxeles por casilla en ese borde, **no resolución óptica efectiva**.
La razón entre bordes opuestos va de 1,045 a 1,200; no equivale a grados de cámara.
No hay evidencia de dispositivos distintos ni controles que aíslen desenfoque,
reflejos, perspectiva fuerte o compresión. El muaré fuerte aparece en tres fotos:
una acierta. Por tanto, ni el muaré ni las flechas explican por sí solos los fallos.
Las fotos de la misma partida/vídeo están relacionadas: 30 fotos no son 30 fuentes
independientes. Se conserva el grupo de validación original completo.

## Datos que merece la pena reforzar

1. **Antes de recoger más fotos, inventariar los 160 ejemplos de entrenamiento**
   buscando los grupos problemáticos. No hemos demostrado que estén ausentes;
   puede faltar variedad o suficientes ejemplos de ciertas clases/colores.
2. Priorizar el diseño de peones finos de IMG_5401–5402, después el sombreado sobre
   madera de IMG_5397–5398 y los reyes/damas de IMG_5391–5392. Incluir piezas de
   ambos colores, claras/oscuras y casillas vacías; varios fondos para separar
   diseño y textura. Como piloto orientativo, 8–12 fotos nuevas por grupo desde
   varias partidas identificadas; no es una cantidad que garantice precisión.
3. Para el muaré, recoger pares de referencia directa/foto de una misma posición,
   variando distancia y ángulo sobre varias partidas. Reservar grupos distintos
   para validar. Así se podrá distinguir estilo de degradación óptica sin usar
   las fotos de validación como entrenamiento.
4. Si se vuelve a entrenar, revisar una mezcla con ejemplos digitales para
   conservar sus aciertos. Foto v1 mantiene las tres regresiones digitales ya
   conocidas (3.128/3.132 frente a 3.131/3.132). No cambiar el modelo predeterminado.

No es necesario añadir otro lote indiscriminado ni entrenar ahora. La medición
permite avanzar a la detección/corrección de perspectiva con límites claros de
lo que podrá aportar el clasificador. La mejora dirigida de estos estilos queda
identificada como trabajo posterior; la aceptación final sigue pendiente.

## Reproducir el análisis

Desde la raíz del repositorio, con el entorno activado:

```bash
python -m tools.analyze_phone_classifier
python -m pytest tests/test_phone_classifier_analysis.py tests/test_phone_inference.py -q
```

Se verifican hashes, pertenencia exacta de las fotos, etiquetas y orientación
antes de sumar las predicciones guardadas. No se cargan modelos ni se ejecuta
inferencia. Las 19 pruebas cubren emparejamiento, regresiones por casilla, colores
canónicos y rechazo de datos cambiados o ajenos a validación. Los mosaicos locales
revisados están en `.cache/phone-classifier-analysis-v1/`; no se versionan fotos.
