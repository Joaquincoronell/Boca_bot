# Boca Bot

Proyecto para controlar un monitor de plateas desde un navegador.

## Componentes

- **Frontend Next.js (Vercel):** panel responsive, ID de partido, preferencias locales, conexión protegida, estado/logs y botones iniciar/detener.
- **Backend FastAPI + Playwright (Railway):** servidor contenedorizado con sesión cifrada, controles de acceso, verificación a intervalos y selección restringida a sectores mapeados.

## Puesta en marcha

1. [Configurar y desplegar el servidor en Railway](server/README.md).
2. Configurar en Vercel `BOCA_BACKEND_URL`, `BOCA_BACKEND_TOKEN` y `DASHBOARD_PASSWORD`.
3. Importar la sesión de Boca Socios de forma privada desde una computadora.
4. Mapear los selectores de los sectores reales de Boca Socios antes de iniciar el monitor.

**Estado:** El frontend se despliega mediante Vercel; el backend está listo como código fuente, **pero no se ha desplegado ni comprobado contra el sitio real**. El panel no garantiza disponibilidad, reserva ni compra; el servidor se detiene ante restricciones, CAPTCHA o bloqueos. Por ahora se diseñó para un solo socio.

No agregar sesiones, cookies, contraseñas o claves al repositorio.
