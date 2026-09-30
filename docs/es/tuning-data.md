# Ejemplos de ajuste

[English](../en/tuning-data.md) | **Español** · [Inicio](README.md)

Ubicación: [`data/tuning/`](../../data/tuning/).

Utiliza la [herramienta de captura](capture-data.md) para recoger el primer perfil
de lichess desde un manifiesto con las particiones asignadas de antemano.

El primer conjunto es `lichess-cburnett-brown-v1`: 16 PNG y sus anotaciones JSON
para ocho posiciones en ambas orientaciones. Las capturas revisadas del piloto
se incorporaron sin cambios el 30-09-2026. Servirán para plantillas, preprocesado
y primeros experimentos de clasificación; no constituyen un conjunto completo
de entrenamiento. Todavía no hay modelo ni resultados de reconocimiento.

El [manifiesto del conjunto](../../data/manifests/lichess-cburnett-brown-v1.json)
fija posiciones y particiones independientemente del ejemplo editable del script.
Las imágenes miden 1280 × 1000, con tablero de 584 × 584, piezas cburnett,
casillas brown, coordenadas internas y contexto del editor. Cada JSON conserva
fecha original, procedencia, colocación canónica, orientación, límites y hash.
Consulta las [atribuciones](../../data/THIRD_PARTY_NOTICES.md) de los recursos.

Se revisaron visualmente las 20 capturas, sus posiciones y orientaciones. Se
comprobó visualmente la extensión de la cuadrícula; se conservaron los límites
decimales del DOM sin medirlos independientemente con precisión subpíxel.
Las pruebas de integridad comprueban archivos y particiones, no la detección.
Para repetir la captura usa el manifiesto y una raíz de salida nueva; no
sobrescribas las imágenes versionadas cuando cambie el sitio web.

Al incorporar cada muestra, registrar identificador, procedencia, permiso de
uso, perfil visual, resolución, posición conocida, orientación y grupo de
origen. Todos sus recortes, aumentos y transformaciones pertenecerán a la misma
partición. Para modelos aprendidos se separará también validación de entrenamiento.

No copiar aquí imágenes de `tests/fixtures/evaluation/` conservándolas a la vez
como evaluación. Una muestra utilizada para ajustar ya no es una evaluación
independiente.
