# Boca Bot — worker local (Playwright)
# Este archivo conserva la lógica del bot recibido, con selección de URL por ID.
# No está conectado al dashboard web ni probado contra el DOM actual.
import asyncio
import os
import re
from pathlib import Path
from playwright.async_api import async_playwright

MATCH_ID = os.getenv("BOCA_MATCH_ID", "882")
if not MATCH_ID.isdecimal():
    raise ValueError("BOCA_MATCH_ID debe ser numérico")
URL = f"https://bocasocios.bocajuniors.com.ar/matches/{MATCH_ID}/plateas"
INTERVAL = max(30, int(os.getenv("INTERVAL", "45")))
PROFILE = str(Path.home() / ".boca_solidario_browser")

async def find_button(page, name):
    button = page.get_by_role("button", name=re.compile(name, re.I))
    return button.first if await button.count() and await button.first.is_visible() else None

async def blocked(page):
    text = (await page.locator("body").inner_text(timeout=10000)).lower()
    return any(x in text for x in ("sala de espera", "fila virtual", "demasiadas solicitudes", "acceso denegado", "access denied", "verifica que eres humano"))

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch_persistent_context(PROFILE, headless=False)
        page = browser.pages[0] if browser.pages else await browser.new_page()
        await page.goto(URL, wait_until="domcontentloaded", timeout=30000)
        print(f"Partido {MATCH_ID}: {URL}")
        print("Iniciá sesión manualmente. El bot no evade colas ni controles de acceso.")
        try:
            while True:
                if await blocked(page):
                    print("Control de acceso detectado. Se detiene.")
                    break
                if "/plateas" not in page.url:
                    print("Esperando página de plateas...")
                else:
                    add = await find_button(page, r"^agregar platea$")
                    if add:
                        await add.click(timeout=4000)
                        print("Se pulsó Agregar platea. Verificá manualmente el carrito.")
                        break
                    search = await find_button(page, r"^buscar asiento disponible$")
                    if search:
                        await search.click(timeout=4000)
                        await page.wait_for_timeout(1500)
                        add = await find_button(page, r"^agregar platea$")
                        if add:
                            await add.click(timeout=4000)
                            print("Se pulsó Agregar platea. Verificá manualmente el carrito.")
                        else:
                            print("No apareció Agregar platea. Revisá la pantalla.")
                        break
                    print("Sin sector seleccionado. Se necesita mapear los sectores reales.")
                await asyncio.sleep(INTERVAL)
                if "/plateas" in page.url:
                    await page.reload(wait_until="domcontentloaded", timeout=30000)
        except KeyboardInterrupt:
            print("Detenido por usuario")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
