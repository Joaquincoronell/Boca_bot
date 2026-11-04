"""Boca Bot API: single-worker Playwright service; deployment requires a persistent container."""
import asyncio
import json
import os
import re
import secrets
from collections import deque
from datetime import datetime, timezone
from pathlib import Path

import httpx
from cryptography.fernet import Fernet, InvalidToken
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from playwright.async_api import async_playwright

app = FastAPI(title="Boca Bot Server", docs_url=None, redoc_url=None)
DATA = Path(os.getenv("BOCA_DATA_DIR", str(Path.home() / ".boca_bot_data")))
DATA.mkdir(parents=True, exist_ok=True)
CONFIG_FILE = DATA / "config.json"
SESSION_FILE = DATA / "session.enc"
API_TOKEN = os.getenv("BOCA_API_TOKEN", "")
SESSION_KEY = os.getenv("BOCA_SESSION_KEY", "")
EVENTS = deque(maxlen=80)
task = None
state = {"status": "detenido", "running": False, "last_check": None, "last_message": "Servidor listo."}


def timestamp():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def log(message, status=None):
    EVENTS.appendleft({"at": timestamp(), "message": message})
    state["last_message"] = message
    if status is not None:
        state["status"] = status
    print(f"[{timestamp()}] {message}", flush=True)


class Configuration(BaseModel):
    match_id: str = Field(default="882", pattern=r"^[0-9]{1,12}$")
    interval_seconds: int = Field(default=45, ge=30, le=3600)
    all_sectors: bool = False
    allowed_sectors: list[str] = Field(default_factory=list)


def load_config():
    try:
        return Configuration.model_validate_json(CONFIG_FILE.read_text())
    except FileNotFoundError:
        return Configuration()
    except Exception as exc:
        log(f"Configuración inválida: {type(exc).__name__}", "error")
        return Configuration()


def save_config(config):
    tmp = CONFIG_FILE.with_suffix(".tmp")
    tmp.write_text(config.model_dump_json())
    os.replace(tmp, CONFIG_FILE)


def mapped_sectors():
    # Selectores explícitos, comprobados manualmente. Nunca adivinar por color.
    try:
        obj = json.loads(os.getenv("BOCA_SECTOR_MAP_JSON", "{}"))
        if not isinstance(obj, dict):
            raise ValueError("Map debe ser objeto")
        return {k: v for k, v in obj.items()
                if isinstance(k, str) and isinstance(v, str) and k.strip() and v.strip()}
    except (ValueError, TypeError):
        return {}


def cipher():
    if not SESSION_KEY:
        raise HTTPException(503, "Falta BOCA_SESSION_KEY en el servidor.")
    try:
        return Fernet(SESSION_KEY.encode("ascii"))
    except (ValueError, TypeError):
        raise HTTPException(503, "BOCA_SESSION_KEY no es una clave Fernet válida.")


def read_session():
    try:
        return json.loads(cipher().decrypt(SESSION_FILE.read_bytes()))
    except FileNotFoundError:
        raise HTTPException(409, "Falta sesión. Importá una sesión autenticada desde tu computadora.")
    except (InvalidToken, ValueError):
        raise HTTPException(409, "No se puede descifrar la sesión. Revisá BOCA_SESSION_KEY.")


def save_session(obj):
    token = cipher().encrypt(json.dumps(obj, separators=(",", ":")).encode())
    tmp = SESSION_FILE.with_suffix(".tmp")
    tmp.write_bytes(token)
    os.chmod(tmp, 0o600)
    os.replace(tmp, SESSION_FILE)


def allowed_map(config):
    mapping = mapped_sectors()
    if config.all_sectors:
        return mapping
    return {k: v for k, v in mapping.items() if k in config.allowed_sectors}


async def authorize(request: Request):
    header = request.headers.get("authorization", "")
    if len(API_TOKEN) < 24 or not header.startswith("Bearer "):
        raise HTTPException(401, "No autorizado")
    if not secrets.compare_digest(header[7:], API_TOKEN):
        raise HTTPException(401, "No autorizado")


@app.get("/", response_class=HTMLResponse)
async def home():
    # Landing pública sin detalles de sesión ni credenciales.
    return """<!doctype html>
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Boca Bot | Servidor</title>
<style>
*{box-sizing:border-box}body{margin:0;min-height:100vh;display:grid;place-items:center;background:#f5f7fb;color:#13284c;font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;padding:24px}
main{width:100%;max-width:520px;background:#fff;border:1px solid #e5eaf3;border-radius:20px;padding:35px;box-shadow:0 14px 45px #0c214014}
h1{font-size:30px;margin:8px 0 14px}.eyebrow{font-weight:800;letter-spacing:.1em;color:#286de5;font-size:13px}.status{display:inline-flex;align-items:center;gap:8px;border-radius:24px;padding:8px 12px;background:#ecf8f0;color:#176537;font-weight:700;font-size:14px}.dot{width:9px;height:9px;border-radius:50%;background:#1aaf57}p{line-height:1.6;color:#53627a}.note{border-left:3px solid #286de5;background:#f4f7ff;padding:12px 14px;border-radius:6px;margin:24px 0}.button{display:block;text-align:center;text-decoration:none;border-radius:11px;padding:14px;background:#266de0;color:#fff;font-weight:750;margin-top:18px}.small{font-size:13px;color:#64748b;margin:16px 0 0}
</style></head><body><main>
<div class="eyebrow">BOCA BOT · SERVIDOR</div><h1>Servidor conectado</h1>
<div class="status"><span class="dot"></span>API disponible en Render</div>
<p>Esta es la parte técnica que ejecuta Playwright. El panel para elegir partido y sectores está en otra dirección.</p>
<div class="note"><strong>Importante:</strong> servidor disponible no significa que el monitor esté buscando entradas. Faltan la sesión autenticada de Boca Socios, el mapeo de sectores y la integración con el panel.</div>
<a class="button" href="https://bocabot.vercel.app">Abrir panel de Boca Bot</a>
<p class="small">Prueba técnica: <a href="/health">ver respuesta de salud del servidor</a> (JSON).</p>
</main></body></html>"""


@app.get("/health")
async def health():
    return {"ok": True, "service": "boca-bot-server"}


@app.get("/api/state", dependencies=[Depends(authorize)])
async def get_state():
    cfg = load_config()
    return {
        **state, "events": list(EVENTS), "config": cfg.model_dump(),
        "session_configured": SESSION_FILE.exists(),
        "mapped_sector_names": sorted(mapped_sectors().keys()),
        "allowed_mapped_sectors": sorted(allowed_map(cfg).keys()),
    }


@app.put("/api/config", dependencies=[Depends(authorize)])
async def put_config(config: Configuration):
    if task and not task.done():
        raise HTTPException(409, "Detené el monitor antes de cambiar su configuración.")
    config.allowed_sectors = list(dict.fromkeys(config.allowed_sectors))[:100]
    save_config(config)
    log(f"Configuración guardada para partido {config.match_id}.")
    return {"ok": True, "config": config.model_dump()}


@app.post("/api/session", dependencies=[Depends(authorize)])
async def upload_session(request: Request):
    if task and not task.done():
        raise HTTPException(409, "Detené el monitor antes de actualizar la sesión.")
    raw = await request.body()
    if len(raw) > 300_000:
        raise HTTPException(413, "Sesión demasiado grande.")
    try:
        session = json.loads(raw)
        if not isinstance(session, dict) or not isinstance(session.get("cookies"), list) or not isinstance(session.get("origins"), list):
            raise ValueError("Formato inválido")
    except (ValueError, TypeError):
        raise HTTPException(400, "Enviá JSON de Playwright storage_state().")
    save_session(session)
    log("Sesión cifrada importada. No se muestran cookies ni credenciales.")
    return {"ok": True}


async def alert(message):
    token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    chat = os.getenv("TELEGRAM_CHAT_ID", "")
    if not token or not chat:
        return
    try:
        async with httpx.AsyncClient(timeout=12) as client:
            response = await client.post(f"https://api.telegram.org/bot{token}/sendMessage",
                                         json={"chat_id": chat, "text": message})
            response.raise_for_status()
    except Exception as exc:
        log(f"Error al enviar alerta: {type(exc).__name__}")


async def visible_button(page, text):
    loc = page.get_by_role("button", name=re.compile(text, re.IGNORECASE))
    return loc.first if await loc.count() and await loc.first.is_visible() and await loc.first.is_enabled() else None


async def is_blocked(page, response=None):
    if response and response.status in (403, 429):
        return True
    try:
        body = (await page.locator("body").inner_text(timeout=8000)).lower()
    except Exception:
        return False
    return any(word in body for word in (
        "sala de espera", "fila virtual", "demasiadas solicitudes",
        "acceso denegado", "access denied", "verifica que eres humano",
        "captcha", "verify you are human", "rate limit"
    ))


async def monitor(config: Configuration):
    state["running"] = True
    log("Monitor iniciado.", "iniciando")
    page = None
    browser = None
    try:
        session = read_session()
        sectors = allowed_map(config)
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=True, args=["--no-sandbox"])
            context = await browser.new_context(storage_state=session)
            page = await context.new_page()
            url = f"https://bocasocios.bocajuniors.com.ar/matches/{config.match_id}/plateas"
            failures = 0
            while True:
                try:
                    response = await page.goto(url, wait_until="domcontentloaded", timeout=35000)
                    state["last_check"] = timestamp()
                    if await is_blocked(page, response):
                        log("Control de acceso o límite detectado. Monitor detenido.", "bloqueado")
                        await alert("Boca Bot: control de acceso. Monitor detenido. Revisá manualmente.")
                        break
                    if "/plateas" not in page.url:
                        log("No se llegó al mapa de plateas. La sesión puede haber vencido.", "sesion_vencida")
                        await alert("Boca Bot: sesión vencida o redirección. Requiere nueva autenticación.")
                        break

                    log(f"Revisando partido {config.match_id}.", "buscando")
                    selected_name = None
                    for name, selector in sectors.items():
                        loc = page.locator(selector).first
                        if await loc.count() and await loc.is_visible() and await loc.is_enabled():
                            await loc.click(timeout=3000)
                            selected_name = name
                            log(f"Sector permitido seleccionado: {name}")
                            break

                    if selected_name is not None:
                        await page.wait_for_timeout(1000)
                        search = await visible_button(page, r"^buscar asiento disponible$")
                        if search:
                            await search.click(timeout=4000)
                            log("Se pulsó Buscar asiento disponible.")
                            await page.wait_for_timeout(1500)
                        add = await visible_button(page, r"^agregar platea$")
                        if add:
                            await add.click(timeout=4000)
                            log("Se pulsó Agregar platea. Carrito NO verificado.", "agregado_sin_verificar")
                            await alert(f"Boca Bot: se pulsó Agregar platea en {selected_name}. Verificá el carrito y completá la compra: {url}")
                            break
                        log(f"No se encontró botón para agregar platea en {selected_name}.")
                    else:
                        log("No se encontró sector permitido disponible.")
                    # Si el sitio renueva cookies durante la navegación, persistimos la sesión cifrada.
                    save_session(await context.storage_state())
                    failures = 0
                    await asyncio.sleep(config.interval_seconds)
                except asyncio.CancelledError:
                    raise
                except Exception as exc:
                    failures += 1
                    log(f"Error de revisión ({failures}/3): {type(exc).__name__}", "error")
                    if failures >= 3:
                        await alert("Boca Bot: monitor detenido por errores repetidos.")
                        break
                    await asyncio.sleep(config.interval_seconds)
    except asyncio.CancelledError:
        log("Monitor detenido por el usuario.", "detenido")
        raise
    except Exception as exc:
        log(f"No se pudo ejecutar el monitor: {type(exc).__name__}", "error")
    finally:
        if browser:
            try:
                await browser.close()
            except Exception:
                pass
        state["running"] = False
        if state["status"] in ("iniciando", "buscando"):
            state["status"] = "detenido"


@app.post("/api/start", dependencies=[Depends(authorize)])
async def start():
    global task
    if task and not task.done():
        raise HTTPException(409, "El monitor ya está activo.")
    cfg = load_config()
    if not SESSION_FILE.exists():
        raise HTTPException(409, "Falta importar la sesión autenticada.")
    if not allowed_map(cfg):
        raise HTTPException(409, "Falta mapear selectores reales de sectores permitidos; no se inicia para evitar sectores equivocados.")
    # Validación de cifrado antes de iniciar.
    read_session()
    task = asyncio.create_task(monitor(cfg))
    return {"ok": True, "status": "iniciando"}


@app.post("/api/stop", dependencies=[Depends(authorize)])
async def stop():
    global task
    if task and not task.done():
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)
    else:
        log("Monitor detenido.", "detenido")
    return {"ok": True, "status": state["status"]}
