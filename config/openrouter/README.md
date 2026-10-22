# Open WebUI con OpenRouter
Configuración inicial del fork, basada en Open WebUI v0.12.3. La clave de OpenRouter queda vacía deliberadamente. La conexión no estará operativa hasta introducir una clave válida.
## Preparación
Desde la raíz del repositorio, crear el archivo local solo si todavía no existe:
```powershell
if (-not (Test-Path -LiteralPath 'config/openrouter/.env')) {
    Copy-Item -LiteralPath 'config/openrouter/.env.example' -Destination 'config/openrouter/.env'
}
```
Editar `config/openrouter/.env` y completar `OPENAI_API_KEY=` cuando se disponga de la credencial. El archivo local está excluido de Git y del contexto de construcción de Docker; la plantilla sí se versiona. No se necesitan workflows ni acceso a n8n.
## Arranque
Instalar Docker Engine con Compose o Docker Desktop antes de ejecutar:
```powershell
docker compose -p open-webui-openrouter -f docker-compose.openrouter.yaml config --quiet
docker compose -p open-webui-openrouter -f docker-compose.openrouter.yaml up --build -d
```
Abrir `http://localhost:3000`. El puerto se publica en la interfaz local. La imagen se construye desde este checkout del fork, por lo que incorporará sus modificaciones futuras. La primera compilación puede tardar por las dependencias de upstream.
El primer usuario registrado será administrador y actuará como superadmin. Upstream cierra automáticamente el registro tras esa primera cuenta. Desde Administración > Usuarios se pueden crear las demás cuentas; si se reabre el registro, las altas quedan pendientes hasta su activación. Se reutilizan los roles existentes `pending`, `user` y `admin`.
En Administración > Ajustes > Conexiones, comprobar la conexión OpenAI compatible con URL `https://openrouter.ai/api/v1`. Cuando haya clave, verificar la conexión y conceder acceso a los modelos/conexión al grupo de usuarios previsto; no asumir que ver los modelos como administrador implica que todos los usuarios los ven.
## Persistencia y permisos
El volumen `openrouter-data` conserva la BDD SQLite, archivos, auditoría operativa y el secreto de sesión generado por el script de inicio de upstream. No eliminar el volumen para reiniciar la aplicación. Para detener los contenedores conservando los datos:
```powershell
docker compose -p open-webui-openrouter -f docker-compose.openrouter.yaml down
```
Se mantiene `ENABLE_PERSISTENT_CONFIG=true` para conservar los cambios de administración. Después del primer arranque, los valores ya guardados en BDD prevalecen sobre los valores iniciales del archivo; si se incorpora la clave más tarde, actualizar también la conexión desde el panel. Reiniciar el contenedor no sustituye por sí solo una clave ya guardada. No usar `RESET_CONFIG_ON_START` para esto, porque afectaría a otros ajustes.
La clave puede quedar almacenada en la configuración de BDD por el funcionamiento estándar de upstream. Proteger el archivo local, el volumen y sus copias de seguridad. El secreto de sesión vacío se genera automáticamente dentro del volumen; no es la clave de OpenRouter.
`OPENROUTER_STRICT_USER_ISOLATION=true` impone en backend la propiedad privada de conversaciones, archivos y carpetas; desactiva compartir y los canales para usuarios normales, incluso con permisos de grupo. El administrador conserva el acceso global. Los archivos servidos desde `/cache` requieren propietario registrado en BDD para un usuario normal. Se deshabilitan inicialmente los chats temporales y el borrado de chats/mensajes; el registro del proveedor se conserva aunque se elimine un chat.
## Páginas de escritorio y políticas
La interfaz principal está diseñada para ordenador: lista e inspector en dos columnas, tablas de parámetros y edición de políticas con espacio de trabajo completo.
- Administración > OpenRouter (`/admin/openrouter`): todos los intercambios, catálogo, permisos y versiones de políticas.
- OpenRouter (`/openrouter`): intercambios propios, entrada efectiva visible, respuesta y descarga de salida original.
- Controles de conversación: parámetros autorizados del modelo OpenRouter seleccionado y enlace al inspector del chat.
Por defecto, los parámetros están en solo lectura salvo el transporte de streaming. El administrador habilita cada campo como editable, solo lectura, oculto o exclusivo del servidor, con tipo, límites, valores permitidos y valor fijado/predeterminado opcional. Puede aplicar restricciones globales, por modelo, grupo o usuario; las restricciones de ámbitos distintos se acumulan y no amplían las globales. La API rechaza modificaciones no autorizadas antes de contactar con OpenRouter, incluso desde un cliente fabricado. Los controles de OpenRouter son independientes del permiso genérico de parámetros avanzados de upstream.
Se guarda la entrada original, el cuerpo efectivo enviado, la política aplicada, los fragmentos originales de respuesta, hashes, estado, uso y razonamiento entregado por el proveedor. No se guardan cabeceras de autorización ni cookies. El razonamiento privado que el proveedor no devuelve no se puede obtener; los bloques cifrados se conservan como tales. El registro es acumulativo por API y no constituye almacenamiento WORM: un operador con acceso directo a BDD puede modificarlo. Véase el [detalle de implementación](../../docs/openrouter-implementation.es.md).
## Estado de validación de esta entrega
Se han ejecutado la aplicación completa con SQLite y cuentas reales, migraciones, pruebas de autorización y captura con proveedor simulado, pruebas de frontend y compilación de producción. La interfaz se ha revisado en navegador de escritorio a 1600 × 1000. Docker no está instalado en este entorno, por lo que queda sin verificar la construcción del contenedor. La clave sigue vacía y no se ha enviado ninguna petición autenticada al servicio real de OpenRouter. El chequeo de tipos general de upstream ya presenta miles de errores anteriores; los componentes nuevos se comprueban y compilan por separado.
