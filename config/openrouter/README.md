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
El primer usuario registrado será administrador y actuará como superadmin. Las altas siguientes quedarán pendientes hasta que un administrador las active. El administrador puede cerrar nuevas altas en su panel una vez creadas las cuentas necesarias.
En Administración > Ajustes > Conexiones, comprobar la conexión OpenAI compatible con URL `https://openrouter.ai/api/v1`. Cuando haya clave, verificar la conexión y conceder acceso a los modelos/conexión al grupo de usuarios previsto; no asumir que ver los modelos como administrador implica que todos los usuarios los ven.
## Persistencia y permisos
El volumen `openrouter-data` conserva la BDD SQLite, archivos, auditoría operativa y el secreto de sesión generado por el script de inicio de upstream. No eliminar el volumen para reiniciar la aplicación. Para detener los contenedores conservando los datos:
```powershell
docker compose -p open-webui-openrouter -f docker-compose.openrouter.yaml down
```
Se mantiene `ENABLE_PERSISTENT_CONFIG=true` para conservar los cambios de administración. Después del primer arranque, los valores ya guardados en BDD prevalecen sobre los valores iniciales del archivo; si se incorpora la clave más tarde, actualizar también la conexión desde el panel. Reiniciar el contenedor no sustituye por sí solo una clave ya guardada. No usar `RESET_CONFIG_ON_START` para esto, porque afectaría a otros ajustes.
La clave puede quedar almacenada en la configuración de BDD por el funcionamiento estándar de upstream. Proteger el archivo local, el volumen y sus copias de seguridad. El secreto de sesión vacío se genera automáticamente dentro del volumen; no es la clave de OpenRouter.
Se preparan las opciones existentes de aislamiento: autenticación, acceso administrativo a chats y recursos, compartición y canales desactivados, y chats temporales desactivados. También se deshabilita inicialmente el borrado de chats/mensajes y la edición de parámetros por usuarios. Los permisos concedidos por grupos son aditivos: revisar sus excepciones al habilitarlos.
Estas opciones iniciales no implementan un archivo inmutable de auditoría ni una política por cada parámetro de OpenRouter. La autorización debe probarse mediante API con usuarios distintos antes de publicar una instancia; véase el [análisis técnico](../../docs/openrouter-analysis.es.md).
## Estado de validación de esta entrega
Se validaron estáticamente el YAML, las variables contra el código de upstream, la clave vacía y las exclusiones del archivo local. No se ha arrancado la aplicación ni construido la imagen: Docker no está instalado en el entorno actual. No se ha enviado ninguna petición autenticada a OpenRouter.
