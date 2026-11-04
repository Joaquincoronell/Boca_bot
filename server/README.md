# Servidor Boca Bot (Railway + Vercel)

Este backend ejecuta un navegador Chromium con Playwright en un **contenedor persistente**. El dashboard Next.js queda en Vercel y se conecta a la API mediante un proxy protegido. Este código no está desplegado automáticamente; se requiere una cuenta de hosting y configuración.

## 1. Publicar el backend en Railway

1. Crear un servicio desde el repositorio GitHub \`Joaquincoronell/Boca_bot\`.
2. Railway leerá \`railway.json\` y construirá \`server/Dockerfile\`.
3. Configurar **una sola réplica** (el monitor es un proceso único). No habilitar autoscaling horizontal.
4. Agregar un **volumen persistente** montado en \`/data\` para conservar la configuración y la sesión cifrada al reiniciar.
5. Variables de entorno secretas en Railway:
   - \`BOCA_API_TOKEN\`: cadena aleatoria fuerte de al menos 24 caracteres.
   - \`BOCA_SESSION_KEY\`: clave Fernet generada con \`python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"\`.
   - \`BOCA_DATA_DIR=/data\`
   - \`BOCA_SECTOR_MAP_JSON\`: mapa JSON de nombres de sectores reales a **selectores CSS validados** en Boca Socios. Ejemplo ilustrativo: \`{"PLATEA_1":"[data-sector-id='SECTOR_REAL_1']"}\`. No usar el ejemplo sin inspeccionar el DOM.
   - Opcionales: \`TELEGRAM_BOT_TOKEN\`, \`TELEGRAM_CHAT_ID\`.
6. Generar un dominio público HTTPS para la API. No publicar las claves ni la sesión en el repositorio.
7. Verificar \`GET https://TU-SERVIDOR/health\`: debería devolver \`{"ok":true,...}\`.

El monitor **no inicia solo** después de un reinicio. Se inicia desde el dashboard tras verificar sesión y mapa.

## 2. Conectar el dashboard Vercel

En el proyecto Vercel \`bocabot\` configurar las variables de entorno del lado del servidor:

- \`BOCA_BACKEND_URL=https://TU-SERVIDOR.up.railway.app\` (sin ruta final).
- \`BOCA_BACKEND_TOKEN\`: el **mismo valor** de \`BOCA_API_TOKEN\`.
- \`DASHBOARD_PASSWORD\`: una contraseña fuerte para autorizar los comandos del dashboard.

Volver a desplegar Vercel tras guardar las variables. Nunca usar \`NEXT_PUBLIC_\` para estas variables. Desde el dashboard introducí la contraseña y pulsá "Conectar / actualizar".

## 3. Importar la sesión de Boca Socios de forma privada

Se realiza **en tu computadora**, donde podés iniciar sesión manualmente:

\`\`\`bash
python -m pip install playwright==1.56.0
python -m playwright install chromium
python server/export_session.py
\`\`\`

Luego subí el archivo generado al backend **solo mediante HTTPS**, autenticándote con el token de Railway. En macOS/Linux:

\`\`\`bash
export BOCA_API_TOKEN="TOKEN_CONFIGURADO_EN_RAILWAY"
curl --fail-with-body -X POST \
  -H "Authorization: Bearer $BOCA_API_TOKEN" \
  -H "Content-Type: application/json" \
  --data-binary @boca_session.json \
  https://TU-SERVIDOR.up.railway.app/api/session
\`\`\`

En PowerShell:

\`\`\`powershell
$env:BOCA_API_TOKEN = "TOKEN_CONFIGURADO_EN_RAILWAY"
Invoke-RestMethod -Uri "https://TU-SERVIDOR.up.railway.app/api/session" -Method Post -ContentType "application/json" -Headers @{ Authorization = "Bearer $env:BOCA_API_TOKEN" } -InFile "boca_session.json"
\`\`\`

No uses correo, chat ni GitHub para enviar esta sesión. Borrá el archivo local cuando ya no lo necesites. La sesión puede caducar y requerir una nueva importación.

## 4. Selección de sectores y funcionamiento

El monitor **solo hace clic en sectores que estén tanto permitidos por el dashboard como mapeados explícitamente** mediante \`BOCA_SECTOR_MAP_JSON\`. Si falta el mapeo, el servidor rechaza el inicio para evitar que elija un sector excluido.

Los nombres de plateas de la interfaz siguen siendo ilustrativos: hay que inspeccionar el DOM del mapa de Boca Socios y usar los identificadores reales. Ningún selector del ejemplo está confirmado. El bot utiliza un intervalo mínimo de 30 segundos, detiene la ejecución si detecta controles de acceso y no evade CAPTCHA ni filas. La selección de "Agregar platea" **no implica que la entrada esté reservada**. Verificá el carrito y completá la operación manualmente.

El backend está diseñado para **un solo socio**. Para varios socios hace falta aislamiento adicional de sesiones, cuentas, permisos y workers.

## Endpoints API (privados)

- \`GET /api/state\` — estado, eventos y configuración.
- \`PUT /api/config\` — actualizar partido, intervalo y sectores deseados.
- \`POST /api/session\` — importar el JSON de estado autenticado de Playwright y cifrarlo en el volumen.
- \`POST /api/start\` / \`POST /api/stop\` — iniciar y detener.
- Todos requieren \`Authorization: Bearer <BOCA_API_TOKEN>\`.

El endpoint público \`GET /health\` solo devuelve disponibilidad del proceso.

**Costos:** Railway cobra según el plan/uso; mantener Chromium en ejecución consume memoria y CPU. Revisar la tarifa antes de desplegar.
