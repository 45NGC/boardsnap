# Diseño de integración con Flutter

[English](../en/flutter-integration.md) · [Resumen](README.md)

Plataformas objetivo: **Android, iOS y web**, según lo indicado para chess-scanner.
El mecanismo propuesto es **una API HTTPS que envuelva el núcleo Python**. Así,
los tres clientes comparten el mismo reconocimiento. Este documento especifica
ese adaptador; **aquí no se implementan servidor, despliegue ni cliente Flutter**.
La CLI sigue siendo una herramienta local de desarrollo. Un cliente móvil o web
no puede integrar el motor ejecutando el comando Python instalado en tu ordenador.

## Responsabilidades y petición propuesta

Un backend independiente llamaría a
`recognize_image(temporary_path, profile=profile_id)`. Gestionaría los archivos
temporales, límites, concurrencia y serialización. El núcleo no conocería su
framework web. Flutter se encarga de seleccionar la imagen, enviarla, mostrar el
editor y gestionar el resto del estado de la partida.

Endpoint propuesto: `POST /v1/recognize`, formulario multipart:

- `image`: un archivo PNG/JPEG enviado como bytes, no una ruta local del dispositivo.
- `profile`: uno de los [perfiles evaluados](profiles.md). Si se omite se utiliza
  `lichess-cburnett-brown-v1`, igual que en la CLI. Un ID desconocido es un error.

Éxito, HTTP 200, `Content-Type: application/json`:

```json
{"piecePlacement":"rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR"}
```

Se mantiene el [contrato actual](output-contract.md). Los errores contienen solo
`{"error":{"code":"...","message":"..."}}`, sin una posición de éxito.
Correspondencias sugeridas para el adaptador futuro:

| Estado HTTP | Código | Significado |
| --- | --- | --- |
| 400 | `INVALID_REQUEST` | Falta el archivo, llegan varios o el perfil es desconocido; validación del adaptador. |
| 413 | `PAYLOAD_TOO_LARGE` | Se supera el límite de bytes configurado; validación del adaptador. |
| 422 | `INVALID_IMAGE`, `UNSUPPORTED_IMAGE`, `BOARD_NOT_FOUND` | El núcleo no puede procesar la imagen enviada. |
| 500 | `INPUT_READ_ERROR`, `PROCESSING_FAILED` | El servidor no puede leer su archivo temporal o procesar la imagen. |

Los dos códigos de validación de petición son **propuestas exclusivas de HTTP**,
no errores nuevos de la CLI o del núcleo. Los detalles de excepciones quedan en
los registros del servidor. No se añaden confianza, confirmaciones, turno,
enroques, captura al paso ni FEN completo. Sin coordenadas legibles se mantiene
la convención de blancas abajo.

## Trabajo en chess-scanner y en el backend futuro

1. Implementar y desplegar el pequeño adaptador HTTP Python antes de conectar
   Flutter. Fijar límites de bytes, dimensiones y tiempo, y borrar temporales tanto
   al acertar como al fallar. No conservar imágenes enviadas por defecto.
2. Configurar la URL del servicio en Flutter y enviar bytes mediante multipart.
   El [paquete `http` de Dart](https://pub.dev/documentation/http/latest/http/MultipartRequest-class.html)
   ofrece `MultipartRequest`; `MultipartFile.fromBytes` sirve para compartir el
   camino entre móvil y web. La [guía de Flutter](https://docs.flutter.dev/cookbook/networking/send-data)
   explica el manejo de peticiones. No incluir Python, OpenCV ni subprocesos de la CLI en Flutter.
3. Decodificar el JSON y pasar `piecePlacement` al editor. Las decisiones sobre
   el estado de la partida siguen en la app. Mostrar errores claros ante JSON
   inválido, fallo de red, tiempo agotado o error estructurado. Permitir cancelar
   o reintentar sin importar el tablero dos veces.
4. En web, configurar CORS para los orígenes y métodos/cabeceras de la aplicación.
   Usar HTTPS en despliegue y configurar la red en las compilaciones móviles.
   Autenticación, límites de uso y alojamiento se concretan al desplegar.
5. Probar Android, iOS y un navegador real: posiciones conocidas, archivos
   inválidos, ausencia de tablero, desconexión, timeout, fallo de servidor y CORS.
   Un fallo no debe modificar el editor. La posición debe coincidir exactamente
   con la CLI para la misma imagen y perfil.

Esta opción necesita conexión, envía imágenes a un servidor y tiene costes de
alojamiento y latencia. Si se requiere funcionamiento sin conexión, habrá que
revisar expresamente la arquitectura: exportar modelos o usar un motor nativo
sería otro trabajo; este diseño HTTP no proporciona reconocimiento local.
