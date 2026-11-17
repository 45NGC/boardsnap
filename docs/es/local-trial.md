# Configuración local de prueba y rendimiento en CPU

**Español** | [English](../en/local-trial.md)

**La configuración de prueba está lista y pasa los límites de rendimiento.**
El reconocimiento fotográfico sigue siendo experimental; esto no es aceptación de
calidad ni distribución de una versión. No se entrenó ningún modelo ni se consultó
la evaluación final independiente.

- [Configuración y checksums](../../data/manifests/local-trial-v1.json).
- [Mediciones completas](../../data/reports/local-trial-cpu-v1.json).
- [Calidad de la CLI con el candidato fotográfico](mixed-sqrt-cli.md).
- [Diseño de la integración futura](flutter-integration.md).

## Modelos explícitos

| Modo | Modelo | Estado |
| --- | --- | --- |
| `digital` | `.cache/neural-tolerance-v1-conservative/best.pt` | Referencia digital existente, fijada en screen-preview-v1 |
| `photo` | `.cache/neural-mixed-sqrt-v1/last.pt` | Candidato fotográfico experimental; no promocionado |
| Referencia de comparación fotográfica | `.cache/neural-phone-v1/best.pt` | Se conserva intacta |

El digital seleccionado es el modelo conservador de la configuración anterior;
no es phone-v1, que se utilizó como control en la última comparación de la CLI.
Esta medición digital verifica 40 capturas representativas de validación y no
repite el lote de 36 capturas reales con el modelo conservador.

`local-trial-v1.json` fija rutas y SHA-256. `tools.try_model` requiere modo y
orientación, comprueba el modelo y llama a la CLI habitual con `--model` explícito.
No depende de `BOARDSNAP_MODEL`, no infiere el modo, ni cambia el comportamiento
predeterminado de `boardsnap`. Solo devuelve la salida habitual del proceso.
Un error de configuración local produce JSON `CONFIGURATION_ERROR`, código 1,
antes de ejecutar reconocimiento. Ese código pertenece a la herramienta de prueba,
no al núcleo ni al contrato HTTP.

Estos comandos se ejecutan desde la raíz del repositorio con `.venv` activado:

```bash
python -m tools.try_model "/ruta/captura.png" --input-type digital --orientation white-bottom
python -m tools.try_model "/ruta/foto.jpg" --input-type photo --orientation black-bottom
```

Equivalentes con la CLI directa (sin la comprobación adicional de checksum):

```bash
boardsnap "/ruta/captura.png" --input-type digital --model .cache/neural-tolerance-v1-conservative/best.pt --orientation white-bottom
boardsnap "/ruta/foto.jpg" --input-type photo --model .cache/neural-mixed-sqrt-v1/last.pt --orientation black-bottom
```

El usuario debe elegir la orientación real. No indica el turno. El JSON de éxito
sigue conteniendo exclusivamente `piecePlacement`. Los pesos en `.cache` son
locales: clonar el repositorio no los descarga. Esta configuración no sustituye
un paquete de distribución con pesos, dependencias y comprobación de instalación.

## Recorrido completo con un modelo residente

Medido el 16 de noviembre de 2026 en Intel Core i5-10400, Linux x86_64,
Python 3.12.3, PyTorch 2.14.1+cpu, cuatro hilos PyTorch y uno OpenCV.
Cada modo usa un proceso nuevo con un único modelo. No se midieron simultáneamente.

| Medida | Capturas, modelo conservador | Fotos, candidato raíz cuadrada |
| --- | ---: | ---: |
| Imágenes de validación consultada | 40 | 30 |
| Mediana con modelo cargado | 448 ms | 1.040 ms |
| p95 con modelo cargado | 519 ms | 2.782 ms |
| Inicio frío: imports, carga y primera imagen | 1.406 ms | 2.041 ms |
| Máximo RSS del proceso | 317 MiB | 427 MiB |
| Posiciones completas correctas | 40/40 | 22/30 |

Se incluyeron fallos en el tiempo y el denominador fotográfico. El p95 describe
una pasada por imágenes distintas, no una estimación de variación repetida de cada
foto. El máximo RSS incluye imports, decodificación, buffers y memoria retenida por
el asignador; no es el tamaño del archivo de pesos ni la memoria aislada de la red.

Se conservaron los límites de rendimiento de la prueba anterior: p95 ≤1 s digital
y ≤5 s foto; frío ≤5/10 s; RSS ≤1.024 MiB; al menos 40/30 imágenes.
**Ambos modos pasan.** Estos límites son de escritorio/servidor local, no una
promesa sobre Android, iOS, HTTP, múltiples peticiones o capacidad concurrente.

## Comparación aislada del clasificador fotográfico

Se utilizaron los 64 recortes verificados del primer tablero de validación
fotográfica del plan mixto. Para cada modelo se ejecutaron tres procesos nuevos,
cada uno con 20 calentamientos y 100 mediciones. No se carga el corpus completo
ni un segundo modelo en esos procesos. Incluye conversión RGB a tensor y red;
excluye lectura de foto, detección y rectificación.

| Medida agregada | phone-v1 | Candidato |
| --- | ---: | ---: |
| Mediana de las medianas | 1,284 ms | 1,291 ms |
| Mediana de p95 | 2,015 ms | 2,008 ms |
| Mediana de RSS máximo | ≈257 MiB | ≈256 MiB |

Las razones candidato/referencia son 1,005 en mediana, 0,996 en p95 y 0,998 en
RSS. Todas están por debajo del límite relativo 1,25 establecido en el plan.
La diferencia de tiempos es pequeña y no debe interpretarse como una aceleración
robusta. La mayor parte del tiempo del recorrido fotográfico queda fuera de la
clasificación de las 64 casillas; no hace falta una red más rápida para explicar
la latencia actual.

## Verificación y reproducibilidad

Pasan cinco pruebas: selección explícita, fallo de checksum, rechazo de rutas fuera
del repositorio, transmisión de modo/orientación y código de salida a la CLI,
error de configuración estructurado y agregación por mediana de procesos nuevos.
Se probó además el lanzador real con una foto y una captura conocidas, comprobando
el resultado esperado, stdout JSON y stderr vacío. Los modelos y el código de
producción conservan sus hashes.

```bash
python -m tools.benchmark_local_trial
python -m pytest tests/test_local_trial.py -q
```

El benchmark guarda cada medición completa en `.cache/local-trial-cpu-v1/`; si se
interrumpe, reutiliza los procesos terminados con la misma firma y receta. Los
resultados originales permanecen guardados. El informe registra hashes de código,
modelos, configuración, imágenes y procedencia de las muestras.

## Decisión y siguiente paso

Se puede usar esta configuración para probar el recorrido que consumirá Flutter,
manteniendo visible el carácter experimental del modo fotográfico. Pasar velocidad
y memoria no corrige las regresiones de calidad con esquinas anotadas ni convierte
estos datos consultados en evaluación final.

El siguiente trabajo recomendado es fijar el contrato de integración por modo y
preparar un adaptador HTTP mínimo en su capa separada, con pruebas que comparen su
JSON con la CLI. La app enviaría imagen, orientación e `inputType`; el servidor
seleccionaría el modelo fijado para el modo. No se implementó ese servidor aquí.

Respecto a mejorar en una semana: los últimos datos muestran una mejora útil
(20→22 fotos completas con detección automática), pero no permiten garantizar otra
mejora considerable ni extrapolarla a fotos nuevas. Este paso de rendimiento y
configuración no cambia la precisión. Una mejora posterior necesitaría una
intervención concreta sobre los fallos restantes y una comprobación independiente.
