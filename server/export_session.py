"""Exporta una sesión local de Playwright para enviarla cifrada al servidor."""
import asyncio
import os
from pathlib import Path

from playwright.async_api import async_playwright

MATCH_ID = os.getenv("BOCA_MATCH_ID", "882")
if not MATCH_ID.isdecimal():
    raise SystemExit("BOCA_MATCH_ID debe ser numérico")
PROFILE = os.getenv("BOCA_LOCAL_PROFILE", str(Path.home() / ".boca_solidario_browser"))
OUT = Path("boca_session.json").resolve()


async def main():
    print("IMPORTANTE: el archivo de sesión contiene credenciales privadas.")
    print("No lo subas a GitHub ni lo compartas por chat.")
    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(PROFILE, headless=False)
        page = context.pages[0] if context.pages else await context.new_page()
        await page.goto(f"https://bocasocios.bocajuniors.com.ar/matches/{MATCH_ID}/plateas",
                        wait_until="domcontentloaded", timeout=30000)
        await asyncio.to_thread(input, "Comprobá que iniciaste sesión. Luego pulsá ENTER acá para exportar: ")
        await context.storage_state(path=str(OUT))
        await context.close()
        try:
            OUT.chmod(0o600)
        except OSError:
            pass
    print(f"Sesión exportada a {OUT}. Tratala como contraseña.")


if __name__ == "__main__":
    asyncio.run(main())
