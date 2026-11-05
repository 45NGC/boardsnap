# Evaluación final: requisitos pendientes

[English](../en/final-evaluation-readiness.md) | **Español**

**El paso 7 no está terminado.** La revisión del 3 de noviembre de 2026 no ha
realizado inferencia final, consumido un conjunto reservado ni declarado aceptada
la versión. El candidato `screen-preview-v1`, sus modelos y su distribución
permanecen intactos.

El [informe reproducible](../../data/reports/screen-final-readiness-v1.json)
verifica los hashes de la política, código, recursos, modelos, distribuible y
mediciones reutilizadas. Distingue instalación/rendimiento de calidad e
independencia. No es un evaluador final ni concede aceptación.

## Lo que falta

1. **Calidad fotográfica.** El resultado consultado es 20/30 (66,7 %), frente al
   90 % fijado. Por procedencia: Lichess 8/10, Chess.com 5/10 y vídeo 7/10; tampoco
   alcanzan el 85 % exigido por grupo. Esto diagnostica falta de preparación;
   no es un resultado de evaluación final. Cambiar el nombre del conjunto o
   seleccionar únicamente los aciertos no resuelve esa diferencia.
2. **Evidencia digital actualizada.** El informe de regresiones fijado en la
   política pasó con el mismo modelo, pero sus hashes de código son anteriores a
   la integración fotográfica. No se afirma una regresión nueva: faltan resultados
   de regresión vinculados al código actual. Los 40 aciertos del benchmark no
   sustituyen esta comprobación ni el conjunto final.
3. **Corpus independiente revisado.** No se ha aportado uno para esta auditoría.
   En la carpeta fotográfica habitual hay 191 archivos y todos sus nombres ya
   figuran en manifiestos o informes. No constituyen un lote nuevo independiente.
   No se ha abierto ninguna imagen para esta revisión de inventario.
4. **Protocolo adecuado.** El evaluador digital antiguo no acepta directamente
   el esquema de dos modelos del candidato actual. Hay que vincular el protocolo
   final a este candidato, sus estratos y sus evidencias antes de ejecutarlo.

La política fotográfica exige al menos 120 positivas de 20 procedencias
independientes identificadas y 100 negativas, además de los mínimos por categoría,
clase y condición. Estos mínimos no son una instrucción de tomar fotos al azar
ahora: primero conviene resolver la preparación del candidato y fijar las series
para no consumir la evaluación en ajustes.

## Decisión de alcance

- **Digital primero, fotos experimentales:** actualizar regresiones digitales,
  preparar un protocolo digital vinculado al candidato y reunir/capturar su lote
  reservado conforme al catálogo de 24 combinaciones. La aceptación solo podría
  declarar ese alcance digital; las fotos seguirían explícitamente experimentales.
- **Ambos modos aceptados:** continuar con los fallos fotográficos usando material
  de desarrollo, congelar un nuevo candidato si cambia el reconocimiento y,
  entonces, preparar conjuntos independientes para ambos modos. No rebajar los
  umbrales del candidato congelado para aprobar los resultados existentes.

Las capturas controladas pueden automatizarse. Fotografías nuevas de pantallas
requieren tomas reales; las variantes sintéticas no demuestran esa condición.
Registrar partida/vídeo, posición esperada, orientación y geometría revisada.
Todas las variantes y posiciones relacionadas deben conservar el mismo grupo.
La anotación visual previa sirve para verificar etiquetas; no se utilizará la
predicción del candidato para ajustar imágenes o etiquetas a su resultado.

## Repetir la auditoría sin consumir imágenes

```bash
python -m tools.check_final_readiness --output .cache/final-readiness-recheck.json
python -m pytest tests/test_final_readiness.py -q
```

La auditoría devuelve código **1** para dejar explícito que no concede aceptación;
una excepción indica evidencia inválida o modificada. Nunca llama al clasificador,
abre píxeles finales ni crea marcadores de intento. Pasan seis pruebas: calidad
insuficiente, evidencia antigua, categorías ausentes, pesos incompatibles y la
imposibilidad de convertir incluso resultados consultados perfectos en aceptación.

Cuando se ejecute la evaluación real, resultados por posición, clase, detección,
condición y rendimiento deberán conservarse, incluso si falla. Si se usan para
corregir el sistema, pasan a desarrollo/regresión y hará falta nueva evidencia
independiente. Hasta entonces, sigue disponible únicamente la
[versión preliminar para pruebas externas](screen-preview.md).
