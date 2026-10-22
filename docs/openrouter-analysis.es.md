# Análisis de Open WebUI, OpenRouter y auditoría de conversaciones
## Alcance y estado real
Revisión del 22 de octubre de 2026 sobre Open WebUI `v0.12.3`, commit `91ea4e3421d1d8069f13d4a463fcb5986d94ea60`. Fork: [rawborkchop/open-webui](https://github.com/rawborkchop/open-webui). Rama de trabajo: `feature/openrouter-governance`.
En esta entrega se ha clonado y creado el fork, preparado un despliegue desde su código y creado un archivo local con la credencial de OpenRouter vacía, según la indicación posterior del usuario. No se han consultado credenciales ni workflows de n8n. Los archivos de configuración se describen en [config/openrouter](../config/openrouter/README.md).
No se han implementado todavía el inspector adicional de OpenRouter, la política granular por parámetro ni el registro íntegro del tráfico del proveedor en BDD. Este documento define su implementación posterior y distingue esas funciones de las capacidades existentes. No se ha ejecutado la aplicación: Docker no está instalado en este entorno y la credencial permanece vacía.
## Conclusión de la revisión
Open WebUI es una base adecuada. Ya ofrece autenticación, usuarios persistidos, administradores, grupos, conversaciones en BDD, controles de modelos y tratamiento de razonamiento. No hace falta desarrollar otro sistema de cuentas ni otra aplicación de chat.
El trabajo nuevo se concentra en dos módulos: gobierno de parámetros de OpenRouter y registro de intercambios con el proveedor. La interfaz debe integrarse en la aplicación Svelte existente y el backend FastAPI debe ser la autoridad de permisos. Ocultar controles en el navegador no basta para restringir peticiones fabricadas por un cliente.
El rol existente `admin` puede representar al superadmin solicitado. No existe un rol de sistema separado llamado `superadmin`. Si en el futuro se necesitan simultáneamente administradores limitados y superadministradores, habrá que diseñar esa distinción y revisar los chequeos `role == 'admin'` de toda la aplicación; añadir una cadena nueva al campo del usuario no resuelve esa jerarquía.
## Qué existe y qué falta
| Requisito | Evidencia en el repositorio | Resultado |
| --- | --- | --- |
| Usuarios y roles en BDD | `backend/open_webui/models/users.py`, `routers/auths.py`, `routers/users.py` | Existente: `pending`, `user`, `admin`. Reutilizar. |
| Conversaciones persistentes | `models/chats.py`: `Chat.user_id`, `Chat.chat` y operaciones de mensajes | Existente para chats guardados; no equivale a registrar cada intercambio real con el proveedor. |
| Lectura administrativa de chats | `routers/chats.py`, `Chats.get_chat_by_id_with_permission` | Existente con `ENABLE_ADMIN_CHAT_ACCESS=true`; hay APIs administrativas para listar chats de un usuario. |
| Aislamiento entre usuarios | Comprobaciones de propietario, permisos de carpetas y `SharedChats` | Existente con excepciones de compartición. Para el caso solicitado se deben cerrar y probar esas excepciones. |
| Conexión OpenRouter | `routers/openai.py` y variables `OPENAI_API_BASE_URL`, `OPENAI_API_KEY` | Existente por API compatible. Preparada la configuración; falta la clave para operar. |
| Razonamiento devuelto | `utils/misc.py:get_reasoning_details`, `utils/middleware.py` | Se procesan contenido y detalles de razonamiento, tanto normales como en streaming. No es un archivo exacto de la respuesta original. |
| Controles administrativos de modelo | `models/models.py:ModelControl`, `utils/payload.py:apply_model_controls`, `routers/models.py` | Ya admite opciones aprobadas, menús y sliders que expanden parámetros. Se debe aprovechar. |
| Permiso de parámetros | `chat.params`, `chat.controls` y comprobaciones en `main.py` | Permisos de función y opciones aprobadas; falta una política general por campo y ruta de OpenRouter. |
| Auditoría operacional | `utils/audit.py`, `utils/logger.py`, variables `AUDIT_*` | Existente en archivos; el cuerpo se limita mediante `MAX_BODY_LOG_SIZE`, cuyo valor inicial es 2048 bytes. |
| Auditoría íntegra de OpenRouter en BDD | Salida real de `routers/openai.py` y `utils/session_pool.py` | Falta. El middleware HTTP de auditoría observa la API de WebUI, no todos los payloads finales de su proveedor. |
| Página dedicada de parámetros e intercambios | Rutas administrativas en `src/routes/(app)/admin` | Falta una página específica con el catálogo, políticas y el inspector de peticiones efectivas. |
## Datos que se pueden conservar
El requisito verificable debe ser: conservar todo el contenido de entrada que Open WebUI envíe a OpenRouter y todo el contenido de salida que reciba, junto con su contexto de ejecución. Incluye system/developer prompts, historial enviado, contexto RAG, mensajes de herramientas, respuestas, uso, errores y los campos de razonamiento que el proveedor entregue.
El razonamiento privado que el proveedor no expone no se puede recuperar. Algunas respuestas contienen resúmenes y otras bloques cifrados o redactados. Deben guardarse con su tipo original, sin presentarlos como razonamiento completo legible. `reasoning.exclude=false` permite solicitar lo disponible, pero no obliga a un modelo a revelar razonamiento interno. Documentación: [Reasoning Tokens](https://openrouter.ai/docs/guides/best-practices/reasoning-tokens).
El chat visible y un registro íntegro del proveedor tienen propósitos distintos. El chat puede editarse, bifurcarse, regenerarse o compactarse. Un turno puede generar varias llamadas: respuesta inicial, llamadas de herramientas, reintentos de la aplicación, generación de título o resumen. Cada llamada debe tener identidad propia y enlazarse con el chat, mensaje, usuario, ejecución y llamada padre que correspondan. Los reintentos internos de OpenRouter solo son observables hasta lo que exponga su API.
Hay que guardar, como mínimo:
- Entrada original del cliente y payload final autorizado, diferenciados: el segundo incorpora valores por defecto, políticas, prompts y transformaciones del servidor.
- Respuesta original del proveedor y versión normalizada para la conversación, sin sobrescribir una con la otra.
- Para streaming, bytes recibidos en orden, incluidos eventos de uso, comentarios y finalización; además, la respuesta reconstruida para consultar cómodamente.
- Identificadores local y de OpenRouter, propietario, modelo solicitado y devuelto, propósito, timestamps, latencia, estado HTTP, finalización, uso y coste cuando estén presentes.
- Llamadas de herramientas y resultados, versiones de políticas, valores aplicados por el servidor y motivo de cualquier restricción.
- Manifiesto de archivos y entradas multimodales; si solo se conservan URLs temporales, la entrada histórica no podrá reconstruirse. Cuando el archivo esté disponible en la aplicación, conservar una referencia estable y su hash, con el mismo control de acceso.
No registrar cabeceras Authorization, cookies, contraseñas ni claves del proveedor en los intercambios. La captura completa se refiere al contenido de inferencia y metadatos permitidos. Las credenciales siguen siendo configuración protegida del servidor.
En una cancelación o fallo de red, registrar el contenido realmente recibido y marcar el intercambio como incompleto. No afirmar que se guardó contenido que nunca llegó al servidor. Una respuesta completa requiere un marcador terminal y persistencia confirmada.
## Política de acceso propuesta
| Operación | Usuario | Superadmin (`admin` existente) |
| --- | --- | --- |
| Ver su historial y razonamiento disponible | Sí | Sí |
| Ver conversaciones, archivos o intercambios ajenos | No | Sí, mediante rutas administrativas |
| Inspeccionar payloads efectivos | Solo los de su propiedad y campos autorizados | Todos los intercambios |
| Editar parámetros | Solo campos y valores expresamente permitidos | Configuración global, por modelo y excepciones |
| Modificar políticas o permisos | No | Sí, con registro de cambios |
| Modificar claves de conexión | No | Sí, en configuración protegida |
| Exportar datos | Solo los propios si se habilita esa función | Todos, con autorización y registro |
La configuración inicial desactiva compartición de chats, compartición pública/abierta, canales y chats temporales para usuarios. Mantiene la lectura administrativa y el acceso administrativo a recursos del workspace. Las concesiones de grupos son aditivas; una futura concesión puede reabrir capacidades desactivadas en los permisos por defecto.
La revisión de aislamiento tiene que cubrir acceso directo por UUID, listados, búsqueda, exportación, archivos, carpetas compartidas, enlaces públicos, eventos WebSocket y todas las APIs de inferencia habilitadas. `user_id`, rol y pertenencia al chat se deben resolver desde la sesión verificada, nunca desde campos declarados por el cliente.
El acceso global de un administrador no implica que pueda editar cualquier conversación ajena mediante los mismos endpoints de un propietario: hay comprobaciones específicas por operación. Para revisar basta con acceso administrativo de lectura y exportación. Si se requiere además editar o borrar cualquier recurso, especificar y probar cada operación administrativa expresamente.
## Gobierno de parámetros de OpenRouter
Se propone una política por ruta JSON con estados `editable`, `read_only`, `hidden` y `server_only`, tipo, límites, enumeraciones, valor por defecto y valor obligatorio opcional. Una política necesita identidad y versión; cada intercambio guarda la versión y los valores efectivos usados.
La política global define el mínimo permitido. Una política por modelo o usuario puede restringirlo; los permisos de grupo no deben ampliar accidentalmente un límite obligatorio global. Resolver esa precedencia en una única función de dominio y probarla antes de construir la interfaz.
Ejemplos de rutas: `temperature`, `top_p`, `max_tokens`, `reasoning.effort`, `reasoning.max_tokens`, `reasoning.exclude`, `provider.order` y `provider.allow_fallbacks`. Las reglas deben contemplar objetos y arrays completos: permitir `reasoning.effort` no debe permitir cambiar todo `reasoning` con otros campos arbitrarios.
La validación debe reconocer entradas equivalentes y fuentes distintas: parámetros superiores, `params`, `custom_params`, opciones de modelo, cuerpos de `/responses` y proxy compatible, si se habilitan. Deshabilitar una ruta que no pueda aplicar las mismas garantías. No permitir que una petición directa evite la política que cumple la interfaz de chat.
Aplicar la política al normalizar las opciones del usuario y volver a verificar las invariantes sobre el payload final antes de enviarlo. Conservar la procedencia de cada valor para distinguir cambios permitidos del usuario, valores administrativos e inserciones internas de herramientas. Un rechazo de política devuelve un error explícito; no convierte silenciosamente un valor prohibido en uno permitido.
El catálogo debe incluir parámetros de muestreo y penalizaciones, límites de tokens, formato de respuesta y esquemas, herramientas, reasoning, selección de proveedor, fallbacks, plugins, transforms, modalidades y cualquier campo adicional soportado. Usar la documentación oficial y los metadatos de modelos de OpenRouter para indicar compatibilidad por modelo. Un catálogo estático necesita versión y actualización; los campos desconocidos pueden inspeccionarse como JSON, pero su edición por usuarios se deniega por defecto.
La página debe distinguir entre ausencia y valor explícito: omitir un parámetro permite que el proveedor use sus valores por defecto; enviar un valor supuestamente equivalente puede tener efectos distintos. Tampoco debe afirmar que el JSON enviado a OpenRouter es el payload interno exacto que ese servicio envía a cada proveedor. Documentación: [API Parameters](https://openrouter.ai/docs/api/reference/parameters).
## Interfaz propuesta
Integrar una sección OpenRouter en Administración y un inspector de ejecución dentro del chat, reutilizando tablas, navegación y controles de Svelte existentes.
| Vista | Contenido |
| --- | --- |
| Catálogo | Nombre, ruta, descripción, tipo, compatibilidad, estado editable/solo lectura y límites. |
| Políticas | Alcance global/modelo/usuario/grupo, opciones aprobadas, valores obligatorios, versión y vista previa como usuario. |
| Intercambios | Filtros por propietario, chat, modelo, fecha, propósito, error e identificador de generación. Paginación en servidor. |
| Detalle | Entrada original, entrada efectiva, respuesta original, salida normalizada, reasoning disponible, herramientas, uso y diferencias de parámetros. |
| Inspector del usuario | Sus ejecuciones y campos permitidos; sin credenciales, políticas internas ocultas ni datos de otros usuarios. |
Los Model Controls existentes sirven para ofrecer elecciones sencillas, por ejemplo niveles de reasoning. La nueva política decide qué puede viajar realmente al proveedor, incluso si se modifica la petición desde fuera de la interfaz.
Las vistas administrativas deben mostrar datos como contenido inerte. Los prompts y respuestas almacenados no deben ejecutar HTML o scripts al revisarlos. La autorización del servidor debe proteger también los endpoints de descarga y exportación del inspector.
## Arquitectura y almacenamiento propuestos
Mantener SvelteKit/Svelte, FastAPI, SQLAlchemy y las migraciones Alembic existentes. Evitar una reescritura general del upstream para facilitar futuras actualizaciones del fork. Los módulos nuevos seguirán responsabilidad única, dependencias hacia interfaces y una clase por archivo.
Separar los contextos de identidad/permisos, política de inferencia, conversación y auditoría. La identidad y conversación siguen siendo los módulos de upstream; política y auditoría añaden servicios propios con adaptadores de persistencia.
Objetos propuestos, cada uno en su archivo: `ParameterPolicy`, `ParameterPolicyEvaluator`, `ProviderExchange`, `ExchangeRecorder`, `ExchangeRepository` y sus adaptadores SQLAlchemy. Los endpoints orquestan autorización y casos de uso; el evaluador no depende de FastAPI, Svelte ni una conexión de BDD.
Esquema conceptual para revisar antes de una migración:
| Entidad | Responsabilidad |
| --- | --- |
| `parameter_policy` | Alcance, versión, reglas y actor del cambio. Versiones anteriores conservadas. |
| `provider_exchange` | Propietario y contexto, relación con chat/mensaje y padre, payload original/efectivo, estado y resultado. |
| `provider_exchange_chunk` | Fragmentos originales con secuencia única por intercambio, para streaming y reconstrucción. |
| `parameter_policy_change` | Quién cambió una política, cuándo y versiones anterior/nueva. |
SQLite en volumen sirve para validar el prototipo y ya viene preparado. Para carga multiusuario y un registro de intercambios creciente, evaluar PostgreSQL antes del despliegue estable. En PostgreSQL, conservar bytes originales en `bytea` o texto cuando su codificación esté garantizada y mantener una proyección `jsonb` para consultas. `jsonb` por sí solo no preserva el cuerpo original byte a byte. Usar los tipos de identificador compatibles con las entidades actuales; no convertir los IDs existentes sin una migración específica.
Prever índices por `(user_id, created_at, id)`, chat/mensaje e identificador externo y una restricción única por `(exchange_id, sequence)`. Paginar metadatos sin cargar cuerpos grandes; consultar el detalle bajo demanda. Definir qué sucede con los intercambios al borrar una cuenta o un chat: un borrado en cascada eliminaría la auditoría que se quiere conservar.
La autorización en backend es obligatoria. Si se incorpora RLS en PostgreSQL, usar un rol de aplicación sin bypass y contexto de usuario por transacción; el pool no debe reutilizar contexto de otra sesión. No basta con activar RLS si la aplicación se conecta con el propietario de las tablas. Su incorporación exige pruebas de compatibilidad con los trabajos internos y APIs administrativas de upstream.
## Punto de captura y garantías de integridad
En `routers/openai.py`, `generate_chat_completion` modifica el cuerpo, aplica opciones del modelo, resuelve conexión y serializa el payload antes de `session.request`. Capturar la entrada efectiva después de esas transformaciones y antes de la salida de red. Capturar la respuesta antes de `convert_responses_result` y otras normalizaciones.
Para streaming, envolver la lectura del proveedor conservando todos los bytes y el orden antes de que `utils/middleware.py` los convierta en mensajes. El wrapper actual de `utils/session_pool.py` es un punto de integración a revisar. No acumular toda una conversación en RAM ni esperar al final del stream para crear el registro.
El contrato de auditoría debe acordar cuándo una llamada se considera persistida. Para una garantía estricta, no enviar al proveedor si no puede persistirse la entrada, y no marcar la respuesta como completa hasta confirmar la escritura final. Si falla la BDD durante el stream, registrar el fallo y finalizar como incompleto; no continuar fingiendo captura íntegra. Agrupar escrituras de chunks puede mejorar rendimiento, siempre que se documenten los límites y la recuperación.
Guardar secuencias, tamaño y hash del contenido ayuda a detectar pérdidas o cambios. Los hashes almacenados en la misma BDD no demuestran por sí solos que un administrador de infraestructura no haya manipulado todo el registro. Un requisito de inmutabilidad resistente a ese administrador requeriría almacenamiento con protección adicional y gestión separada de claves o evidencias.
No activar simplemente `AUDIT_LOG_LEVEL=REQUEST_RESPONSE` como sustituto: sus cuerpos tienen un límite, se redactan ciertos datos y el punto observado es la API HTTP de WebUI. Tampoco guarda por sí mismo una entidad consultable por intercambio en la BDD. En esta entrega se activa únicamente auditoría de metadatos operacionales.
## Pruebas y criterios de aceptación
Aplicar TDD a los nuevos módulos: primero casos de dominio y de autorización que fallen, después implementación mínima y refactor. Separar Arrange, Act y Assert, sin assertions durante preparación o ejecución. Usar proveedores simulados, iteradores de eventos y señales explícitas; no sleeps ni esperas basadas en tiempo para hacer pasar pruebas.
| Grupo | Casos mínimos |
| --- | --- |
| Roles | Usuario pendiente bloqueado; usuario ordinario sin acceso administrativo; admin con lectura global; cambio de rol efectivo. |
| Aislamiento | Usuario A no puede listar, leer, buscar, exportar o suscribirse a datos de B, aunque conozca sus IDs; admin sí puede revisar ambos. |
| Compartición | Rutas de enlaces y carpetas no abren acceso entre usuarios bajo la configuración elegida. Probar también archivos y eventos. |
| Políticas | Campos permitidos, bloqueados, desconocidos, nulos, tipos incorrectos, rangos, objetos anidados, arrays, precedencia y actualización de versión. |
| Vías alternativas | Mismas restricciones por chat, API compatible, Responses, `custom_params`, modelos alias, herramientas y llamadas internas. |
| Captura | Igualdad de bytes de entrada/salida originales, JSON normal, SSE partido en fragmentos arbitrarios, UTF-8 dividido, uso final y eventos desconocidos. |
| Reasoning | Texto, resumen, bloques cifrados, campos de proveedor, ausencia de reasoning y cambio de modelo entre turnos. |
| Fallos | Error HTTP con JSON o SSE, cancelación, desconexión y fallo de persistencia. Registro incompleto identificable y sin falsa finalización. |
| Persistencia | Historial tras reinicio; reintentos registrados como intentos distintos; migración en BDD temporal y restauración de copia. |
| Interfaz | Vista de admin y de usuario, edición según política, inspección de entradas efectivas y salida segura de contenido no confiable. |
| Secretos | Claves/cookies excluidas de payloads auditados, exportaciones, respuestas de APIs ordinarias y contexto de construcción. |
La prueba de aislamiento debe usar cuentas y conversaciones reales de una instancia de prueba. Una prueba del evaluador de políticas por sí sola no acredita aislamiento de la aplicación completa.
## Entregas propuestas
| Orden | Entrega | Criterio para cerrarla |
| --- | --- | --- |
| 1 | Fork, checkout, archivo local vacío y Compose | Completada con validación estática. Queda pendiente el arranque en un host con Docker. |
| 2 | Línea base de autorización | Pruebas con A/B/admin y compartición cerrada; corregir cualquier vía de acceso encontrada. |
| 3 | Dominio de políticas y API administrativa | Restricciones por ruta verificadas en todos los caminos de inferencia habilitados. |
| 4 | Captura íntegra y persistencia | Entrada/salida originales y SSE verificables, estados incompletos y migraciones probadas. |
| 5 | Catálogo e inspector | Admin revisa todos los intercambios y configura permisos; usuario solo ve los suyos y edita lo permitido. |
| 6 | Operación estable | Prueba con clave real, reinicios, copias/restauración y capacidad de almacenamiento según tráfico esperado. |
Cada implementación llevará un commit independiente con la identidad Git del usuario, sin coautores. Los cambios funcionales posteriores deben conservar la separación entre auditoría original y contenido editable de chat.
## Decisiones pendientes antes de producción
Usar `admin` como superadmin es la opción de menor cambio para el alcance descrito. Solo diseñar un tercer nivel si se necesitan operadores administrativos que no deban leer conversaciones ajenas.
Definir modelos y proveedores permitidos, reglas iniciales editables, volumen de usuarios y tráfico, retención y facultades de borrado. Esos datos determinan almacenamiento, índices y política de archivos; no deben impedir implementar el prototipo local.
Una instancia con archivo vacío no puede acreditar conectividad autenticada, compatibilidad real de parámetros ni qué reasoning devolverá un modelo concreto. Validar esos puntos cuando se incorpore una clave; hasta entonces usar fixtures fieles y dejar claramente separados los resultados simulados y reales.
## Fuentes
- [Repositorio y código upstream revisado](https://github.com/open-webui/open-webui/tree/91ea4e3421d1d8069f13d4a463fcb5986d94ea60).
- [Roles de Open WebUI](https://docs.openwebui.com/features/authentication-access/rbac/roles/): rol admin, permisos y acceso administrativo a conversaciones.
- [Permisos de Open WebUI](https://docs.openwebui.com/features/authentication-access/rbac/permissions/): permisos por defecto y grupos.
- [Parámetros de OpenRouter](https://openrouter.ai/docs/api/reference/parameters): parámetros y diferencias entre omitir y enviar valores.
- [Reasoning de OpenRouter](https://openrouter.ai/docs/guides/best-practices/reasoning-tokens): disponibilidad, exclusión y estructura de detalles.
