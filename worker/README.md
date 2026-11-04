# Worker de Boca Bot

Este monitor es **local y experimental**, separado del dashboard Next.js. Se basa en el archivo Python aportado por el usuario. No hay sincronización entre ambos todavía.

## Ejecutar

```bash
python -m pip install -r worker/requirements.txt
python -m playwright install chromium
BOCA_MATCH_ID=882 python worker/boca_solidario.py
```

En Windows PowerShell: `$env:BOCA_MATCH_ID='882'; python worker/boca_solidario.py`.

Requiere iniciar sesión manualmente. No saltea CAPTCHA, colas ni bloqueos. El intervalo mínimo es 30 segundos. No está validado con el DOM real y **no reconoce ni selecciona sectores automáticamente** hasta que se mapeen sus identificadores. Tampoco envía notificaciones; no hay proveedor configurado. El clic en «Agregar platea» no garantiza reserva ni compra.

No subir sesiones, cookies, credenciales ni perfiles del navegador al repositorio.
