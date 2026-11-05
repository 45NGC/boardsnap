# Inventario de errores fotográficos actuales

[English](../en/photo-error-inventory.md) | **Español**

**Paso 1 terminado:** comparación reproducible de las 30 fotos de validación
consultada, usando foto v1 y el detector recuperado v2. No se ha ejecutado
inferencia, entrenamiento ni experimentos de preprocesado. El candidato congelado,
los modelos, las etiquetas y las particiones permanecen intactos.

- [Tabla CSV de errores y controles](../../data/reports/photo-error-inventory-v1.csv).
- [Informe JSON completo, incluidas las 30 fotos](../../data/reports/photo-error-inventory-v1.json).
- [Anexo de fallos geométricos de desarrollo](../../data/reports/photo-error-inventory-v1-development.csv).

## Resumen comparable

| Medida | Resultado |
| --- | ---: |
| Fotos detectadas | 29/30 |
| Posiciones correctas con esquinas anotadas | 19/30 |
| Posiciones correctas por CLI automática | 20/30 |
| Correctas por ambos caminos | 18/30 |
| Fallos actuales del recorrido automático | 10 |
| Tabla: falla al menos uno de los dos caminos | 12 |
| Errores de casilla con esquinas anotadas, **mismas 29 fotos detectadas** | 47/1.856 |
| Errores de casilla con recorte automático, **mismas 29 fotos** | 32/1.856 |

En las 30 fotos, las esquinas anotadas producen 49 errores: dos pertenecen a la
foto que no se detecta automáticamente. No se compara ese total con 32 como si
ambos caminos hubieran clasificado las mismas imágenes. La foto no detectada no
tiene predicciones automáticas; su número de errores de casilla es **desconocido**,
no cero, y su posición completa cuenta como fallo.

## Tabla por foto

`casilla esperado→predicho`; mayúsculas = blancas, minúsculas = negras,
`P/N/B/R/Q/K` = peón/caballo/alfil/torre/dama/rey y `∅` = vacía. Las casillas están
siempre en coordenadas canónicas, también para las fotos con negras abajo.
**Todas** tienen perspectiva y muaré anotados; la columna de condiciones muestra
los factores adicionales. Los identificadores de apariencia son grupos visuales
locales, no nombres oficiales de temas. «Anotadas» describe la clasificación
usando las esquinas revisadas, no una transcripción errónea de las piezas.

| Foto / vista | Apariencia / fondo | Condiciones adicionales | Errores con esquinas anotadas | Errores automáticos | Interpretación |
| --- | --- | --- | --- | --- | --- |
| `chesscom-img_5395` / negras abajo | `cc-flat` / `plain-green` | flechas, resaltados | `e5 p→∅` | `e5 p→∅` | Falla con ambas geometrías |
| `chesscom-img_5396` / negras abajo | `cc-flat` / `plain-green` | resaltados | `e5 b→B` | **OK** | Control: automático recupera |
| `chesscom-img_5397` / blancas abajo | `cc-shaded` / `wood-texture` | flechas, textura, resaltados | `d8 q→p`; `f8 b→B`; `a5 ∅→n`; `f5 b→B`; `f3 N→∅`; `a1 R→∅`; `b1 N→∅` | `d8 q→p`; `f8 b→B`; `a1 R→B`; `b1 N→∅` | Falla con ambas geometrías |
| `chesscom-img_5398` / blancas abajo | `cc-shaded` / `wood-texture` | textura, resaltados | `e6 p→∅`; `b2 ∅→n`; `a1 R→∅` | `a1 R→B` | Falla con ambas geometrías |
| `chesscom-img_5399` / blancas abajo | `cc-flat` / `plain-blue` | resaltados | `f8 b→B` | **OK** | Control: automático recupera |
| `chesscom-img_5401` / blancas abajo | `cc-thin-stem` / `plain-purple` | — | `a7 p→∅`; `b7 p→∅`; `c7 p→∅`; `f7 p→∅`; `g7 p→∅`; `h7 p→∅`; `e6 p→∅`; `f6 n→N`; `e5 n→N`; `g3 P→R`; `a2 P→∅`; `b2 P→R`; `c2 P→∅`; `f2 P→R`; `h2 P→R` | `a7 p→∅`; `b7 p→∅`; `c7 p→∅`; `f7 p→∅`; `g7 p→∅`; `h7 p→∅`; `e6 p→∅`; `f6 n→N`; `e5 n→N`; `a2 P→∅`; `c2 P→∅` | Falla con ambas geometrías |
| `chesscom-img_5402` / blancas abajo | `cc-thin-stem` / `plain-purple` | — | `c7 p→∅`; `a6 p→∅`; `g6 p→∅`; `h6 p→∅`; `g4 p→∅`; `g3 P→R`; `a2 P→∅`; `c2 P→∅` | `c7 p→∅`; `a6 p→∅`; `g6 p→∅`; `h6 p→∅`; `g4 p→∅`; `a2 P→∅`; `c2 P→∅` | Falla con ambas geometrías |
| `lichess-img_5391` / negras abajo | `lc-rounded-king` / `wood-texture` | textura, resaltados | `d8 q→b`; `f6 n→N`; `e1 K→N` | `d8 q→b`; `f6 n→N`; `e1 K→N` | Falla con ambas geometrías |
| `lichess-img_5392` / negras abajo | `lc-rounded-king` / `wood-texture` | textura, resaltados | `d4 q→Q`; `d2 K→N` | `d4 q→Q`; `d2 K→N` | Falla con ambas geometrías |
| `video-img_5403` / negras abajo | `video-flat-brown` / `plain-brown` | muaré fuerte, resaltados | `d8 q→n`; `d1 R→∅` | **No detectado** | Detección + clasificación pendiente |
| `video-img_5404` / blancas abajo | `video-flat-green` / `plain-green` | muaré fuerte, tablero físico en el fondo, resaltados | `f8 b→q`; `c4 B→∅`; `d4 P→N`; `c2 P→∅`; `e2 ∅→P`; `d1 Q→∅` | `c5 ∅→R`; `e1 ∅→B` | Falla con ambas geometrías |
| `video-img_5406` / blancas abajo | `video-classic-a` / `plain-blue` | flechas, miniaturas adicionales, resaltados | **OK** | `h8 ∅→n` | Sensible al recorte |


## Qué podemos atribuir y qué no

- **Detector:** `5403` es el único rechazo de validación. Además, con geometría
  anotada confunde la dama de d8 y omite la torre de d1. Recuperar su tablero no
  garantiza por sí solo recuperar la posición completa.
- **Clasificación con geometría revisada:** ocho fotos fallan con ambos recortes.
  Hay evidencia de un problema que persiste sin depender exclusivamente de la
  detección automática. El diseño, fondo, óptica y preprocesado pueden interactuar;
  estos informes no permiten asignar una causa única a cada confusión.
- **Sensibilidad al recorte:** `5406` pasa de posición correcta a un caballo negro
  falso en h8. El error máximo de esquina es 8,69 píxeles en la foto original y el
  desplazamiento máximo de cuadrícula equivale a 0,0293 casillas, dentro del criterio.
  Los 29 tableros detectados cumplen el criterio geométrico. Por tanto, no se puede
  llamar «detección incorrecta» a cualquier diferencia respecto a las anotaciones.
- **Cambios mixtos:** en `5404` el recorte automático corrige seis casillas, pero
  introduce piezas falsas en c5 y e1. En `5397–5398`, a1 sigue siendo incorrecta,
  aunque cambia de torre omitida a torre confundida con alfil. La tabla conserva
  esos cambios de clase y no los cuenta como recuperaciones.
- **Controles positivos necesarios:** `5396` y `5399` ahora aciertan gracias al
  recorte automático. No se deben perder al intentar corregir la sensibilidad.

En total, sobre las mismas 29 fotos, el recorte automático **corrige 18 casillas e
introduce tres errores nuevos**: c5 y e1 en `5404`, h8 en `5406`. Esto justifica
medir ambas geometrías; no justifica sustituir indiscriminadamente una por otra.
Las anotaciones manuales también tienen precisión limitada.

## Prioridades para fijar el catálogo y los próximos datos

1. **`cc-thin-stem`, `5401–5402`: 18/32 errores automáticos**, dos posiciones
   incorrectas. Se pierden doce peones negros y cuatro blancos; dos caballos negros
   se confunden con blancos. No tienen flechas ni resaltados anotados. La auditoría
   anterior no encontró ese mismo diseño de peón entre los ejemplos representativos
   del entrenamiento: es una carencia concreta que merece prioridad.
2. **`cc-shaded`, `5397–5398`: cinco errores**, dos posiciones. Revisar piezas
   sombreadas sobre madera, torres, caballos y distinción de color. Hay ejemplos
   similares en entrenamiento; no se afirma que falte toda esa familia.
3. **`lc-rounded-king`, `5391–5392`: cinco errores**, dos posiciones. Reyes/damas
   y caballos requieren ejemplos dirigidos. Estos tres grupos concentran **28/32
   errores**, aunque son observaciones relacionadas, no 28 casos independientes.
4. **Recorte y muaré:** conservar `5404` y `5406`, además de los controles `5396`
   y `5399`, para medir robustez geométrica sin perder los aciertos actuales.
5. **Marcas:** en `5395` se omite el peón e5 donde coinciden flechas. Es una hipótesis
   visual previa; la coincidencia no prueba causalidad ni exige eliminar las flechas.
6. **Geometría restante:** `5403` y el anexo de desarrollo, sin mezclarlos con
   ejemplos medidos únicamente para clasificación.

Las condiciones se solapan: 9/12 posiciones con flechas, 18/26 con resaltados,
6/10 con texturas y 1/3 con muaré fuerte son correctas automáticamente. Estos
porcentajes no aíslan el efecto de cada condición. No hay evidencia controlada
para atribuir errores concretos a desenfoque o reflejos. No se ha hecho una nueva
revisión visual de los píxeles ni de las transcripciones en este paso.

## Desarrollo y experimentos anteriores

El lote de desarrollo tiene 134/161 detecciones dentro de tolerancia y 27 rechazos.
El anexo conserva sus identificadores, nombres originales, condiciones y grupos.
No hay en estos informes una comparación de clasificación con ambas geometrías
para ese lote: no se inventan casillas fallidas ni estilos y no se suma al
resultado de las 30 fotos. Los 161 ejemplos tampoco son fuentes independientes.

Se conserva el rechazo de los tres experimentos de remuestreo y del entrenamiento
`neural-phone-robustness-v2`: perdían aciertos anteriores. El JSON enlaza los
informes y recoge sus decisiones históricas. Sus métricas usaban geometría v1;
no se presentan como una nueva medición del detector v2. No se ha repetido ninguno.

## Reproducir

```bash
python -m tools.consolidate_photo_errors --output-prefix .cache/photo-error-review
python -m pytest tests/test_photo_error_inventory.py -q
```

El comando genera JSON, CSV pareado y CSV geométrico de desarrollo. Rechaza salidas
existentes, identidades duplicadas, cambios de etiquetas/orientación/partición,
evidencia geométrica incoherente e informes de otro modelo o código. Solo abre
JSON y código para verificar hashes: no necesita abrir fotos ni pesos. Las 18
pruebas incluyen esa restricción, coordenadas canónicas, errores ausentes frente
a cero errores y los totales actuales.

El siguiente paso es **fijar el catálogo fotográfico inicial** usando estas
prioridades; aún no es necesario repetir el entrenamiento ni tomar un lote
indiscriminado de fotografías. La evaluación final permanece reservada.
