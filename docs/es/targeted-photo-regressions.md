# Regresiones del entrenamiento fotográfico dirigido

**Español** | [English](../en/targeted-photo-regressions.md)

Análisis del 14 de noviembre de 2026. **Conviene conservar `neural-phone-v1`.**
El candidato `neural-phone-targeted-v1` pierde principalmente la capacidad de
ignorar marcas y texturas en casillas vacías. No es un fallo nuevo de detección:
los informes comparan ambos clasificadores sobre exactamente los mismos recortes
verificados y las mismas etiquetas.

Se reutilizaron las predicciones guardadas y se inspeccionaron visualmente los
recortes afectados. No se ejecutaron modelos, nuevos entrenamientos ni la
evaluación final. No se modificaron pesos, detección, preprocesado ni particiones.

- [Informe reproducible por casilla](../../data/reports/targeted-photo-regressions-v1.json).
- [Galería local de los 11 casos y controles sin marcas](../../.cache/phone-targeted-regressions-v1/index.html).
- [Resultado del entrenamiento](targeted-photo-training.md).

## Qué ocurre en los 11 tableros que dejaron de ser correctos

Cada tablero pierde **una sola casilla**. Diez errores inventan una pieza sobre
una casilla vacía; uno cambia un peón negro por un alfil negro. Siete casillas son
claras y cuatro oscuras. No hay una inversión general de orientación o de color.

| Caso de la galería | Imagen / combinación | Casilla | Esperado → candidato | Evidencia visible |
| --- | --- | --- | --- | --- |
| phone-01 | lichess-img_5388; apariencia `lc-classic-a` | d8, oscura | vacía → dama negra | Vetas de madera y patrón fotográfico; ninguna flecha atraviesa d8 |
| phone-02 | lichess-img_5390; apariencia `lc-classic-b` | d8, oscura | vacía → dama negra | Vetas de madera; esa casilla no contiene marcas ni piezas |
| digital-01 | digital-014; Lichess, cburnett, verde | g6, clara | vacía → peón blanco | Punta triangular de flecha roja |
| digital-02 | digital-034; Chess.com, neo, verde | b5, clara | vacía → rey blanco | Punta verde dentro de círculo y resaltado |
| digital-03 | digital-034; Lichess, alpha, verde | g4, clara | vacía → peón blanco | Punta triangular de flecha roja |
| digital-04 | digital-036; Chess.com, classic, azul | f1, clara | vacía → alfil blanco | Punta de flecha verde junto a la coordenada |
| digital-05 | digital-036; Chess.com, neo, azul | c2, clara | vacía → caballo blanco | Inicio redondeado de flecha roja diagonal |
| digital-06 | digital-070; Lichess, merida, azul | d4, oscura | peón negro → alfil negro | Cruce de flecha naranja gruesa y azul fina sobre el peón |
| digital-07 | digital-033; Lichess, staunty, wood4 | h7, clara | vacía → caballo blanco | Inicio de flecha roja diagonal sobre madera |
| digital-08 | digital-035; Lichess, staunty, wood4 | d8, oscura | vacía → rey negro | Inicio vertical de flecha naranja sobre madera |
| digital-09 | digital-014; Chess.com, alpha, verde | f3, clara | vacía → rey blanco | Flecha verde, círculo y resaltado |

Los nombres cortos digitales se repiten entre configuraciones; el informe conserva
la ruta completa. Las apariencias fotográficas son etiquetas visuales del corpus,
no nombres oficiales de selectores.

**Los nueve controles digitales de la misma posición, estilo y orientación sin
marcas siguen siendo completamente correctos con ambos modelos.** En particular,
las ocho casillas vacías vuelven a clasificarse como vacías y d4 como peón negro.
Esto vincula esas pérdidas a la tolerancia a superposiciones, no a una pérdida
general de reconocimiento de esos juegos de piezas.

Las puntas rojas de digital-01 y digital-03 tienen **píxeles idénticos** en los
recortes de 64×64, aunque las posiciones y los juegos de piezas sean distintos.
Son dos tableros perdidos, pero no dos patrones visuales independientes. Los 11
recortes fallidos contienen diez patrones distintos; los dos recortes fotográficos
son similares, pero no idénticos.

## Lo que oculta contar solo tableros completos

| Validación | Casillas antes correctas que empeoran | Casillas antes erróneas que mejoran | Nuevas piezas falsas |
| --- | ---: | ---: | ---: |
| Fotográfica, 30 fotos | 10 | 12 | 9 |
| Digital, 3.132 capturas | 10 | 0 | 9 |

En fotos también hay dos cambios de una clase errónea a otra errónea; no cuentan
como mejoras ni como nuevas regresiones. Las ocho regresiones fotográficas que
no aparecen en los dos tableros perdidos están en fotos que ya tenían otros errores:
`chesscom-img_5397` (f4/e3), `5398` (e3), `lichess-img_5392` (a7/c5/e1) y
`video-img_5404` (e4/e3). En digital existe además una casilla a4 vacía convertida
en caballo blanco en `digital-071`, Chess.com bases/marrón, que ya fallaba antes.
El informe conserva todos estos cambios, no solo los once tableros destacados.

Por tanto, el pequeño aumento neto del acierto fotográfico no demuestra estabilidad:
se recuperan 12 casillas, pero se rompen otras 10. Las casillas vacías fotográficas
correctas bajan de 1.185 a 1.176 sobre 1.188.

## Explicación: hechos e hipótesis

**Hechos del entrenamiento:** se usaron 160 fotos anteriores y 24 nuevas, estas
últimas de ocho posiciones, sin capturas digitales de entrenamiento. La destilación
solo conservaba predicciones del modelo anterior sobre las fotos antiguas; no
incluía los ejemplos digitales con flechas que ahora empeoran.

Las casillas vacías siguen siendo abundantes: 6.270/10.240 en las fotos antiguas y
867/1.536 en las nuevas. No es correcto concluir que «faltaban casillas vacías»
en general. Falta comprobar si los ejemplos de entrenamiento contienen suficiente
variedad de **vacías con texturas, puntas, trazos y círculos** como la problemática.

El peso de pérdida de la clase vacía pasa de 0,1256 a 0,1269; el de dama negra se
mantiene en 5,6264. El ponderado favorece aprender clases poco frecuentes y podría
influir en el equilibrio entre detectar piezas finas e inventarlas, pero **no se
ha demostrado que cause estas regresiones**. No debe atribuirse el problema a un
cambio brusco de esos pesos: apenas cambiaron.

**Hipótesis principal:** al adaptarse a las fotografías, el clasificador desplazó
sus criterios de separación entre pieza y fondo y perdió parte de su tolerancia
a marcas digitales. Es coherente con los controles sin marcas y la ausencia de
repaso digital, pero no se ha probado causalmente mediante otro entrenamiento.
En las fotos de madera, la evidencia visible apunta a textura/muaré interpretados
como dama; este análisis no separa experimentalmente el efecto de cada factor.

## Qué preparar después

1. Mantener el candidato descartado como referencia y continuar usando phone-v1.
2. Inventariar **solo en entrenamiento** ejemplos digitales con puntas, inicios,
   círculos y cruces, y fotos de vacías sobre madera. Incluir controles sin marcas,
   casillas ocupadas y piezas finas para no resolver falsos positivos borrando piezas.
3. Preparar un entrenamiento mixto que repase esos grupos junto a fotos antiguas y
   nuevas; controlar las proporciones por procedencia/condición y evitar multiplicar
   indiscriminadamente variantes de las ocho posiciones nuevas.
4. Fijar una comparación que conserve los aciertos anteriores y mida errores en
   vacías y piezas por separado. No trasladar estos ejemplos de validación al
   entrenamiento ni convertir sus recortes en reglas especiales.

No recomiendo cambiar ahora el detector, borrar flechas o imponer «vacía» mediante
un umbral arbitrario. Tampoco hace falta pedir más fotos antes de inventariar los
ejemplos de entrenamiento que ya existen. Este paso termina con un diagnóstico;
no se ha iniciado el entrenamiento mixto.

Reproducir sin inferencia:

```bash
python -m tools.analyze_targeted_regressions
python -m pytest tests/test_targeted_regression_analysis.py -q
```

El [inventario de entrenamiento](training-coverage.md) identifica marcas digitales y fotos de madera/piezas finas reutilizables. No se inicia otro entrenamiento; el siguiente paso es preparar un corpus mixto equilibrado.
