"""Headless screenshots of the Intelligence screen (for docs/ and the report).
    VASOOL_AUTH=off uvicorn api.main:app --port 8765 &
    python scripts/intelligence_shots.py http://localhost:8765
Writes docs/screenshots/intelligence_*.png and reports any JS errors."""
import asyncio, sys
from pathlib import Path
from playwright.async_api import async_playwright

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8765"
OUT = Path(__file__).resolve().parents[1] / "docs" / "screenshots"; OUT.mkdir(parents=True, exist_ok=True)


async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        pg = await b.new_page(viewport={"width": 1180, "height": 900}, device_scale_factor=1)
        errors = []
        pg.on("pageerror", lambda e: errors.append(str(e)))
        pg.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
        await pg.goto(BASE + "/#/intelligence")
        await pg.wait_for_selector(".intel-sample", timeout=20000)
        await pg.click("#lang-en"); await pg.wait_for_selector(".intel-sample")
        await pg.screenshot(path=OUT / "intelligence_empty.png", full_page=False)
        await pg.click(".intel-sample[data-f^='hdfc']")
        await pg.wait_for_selector("#intel-diff", timeout=30000)
        await pg.wait_for_timeout(500)
        await pg.screenshot(path=OUT / "intelligence_top.png", full_page=False)
        await pg.click(".intel-sample[data-f^='axis']")
        await pg.wait_for_timeout(300); await pg.wait_for_selector("#intel-diff", timeout=30000); await pg.wait_for_timeout(500)
        await pg.screenshot(path=OUT / "intelligence_full.png", full_page=True)
        # transactions table with disagreements only
        await pg.click("#intel-diff"); await pg.wait_for_timeout(600)
        el = await pg.query_selector("#intel-diff")
        await el.scroll_into_view_if_needed(); await pg.wait_for_timeout(300)
        await pg.screenshot(path=OUT / "intelligence_table.png", full_page=False)
        # model card
        await pg.click("details summary"); await pg.wait_for_selector(".fig-btn", timeout=15000)
        btn = await pg.query_selector(".fig-btn[data-f='fig5_classification.png']")
        if btn:
            await btn.click(); await pg.wait_for_timeout(800)
        card = await pg.query_selector("#model-card")
        await card.scroll_into_view_if_needed(); await pg.wait_for_timeout(300)
        await pg.screenshot(path=OUT / "intelligence_modelcard.png", full_page=False)
        # Tamil
        await pg.click("#lang-ta"); await pg.wait_for_timeout(600)
        await pg.screenshot(path=OUT / "intelligence_tamil.png", full_page=False)
        await b.close()
        print("errors:", errors if errors else "none")
        print("wrote", sorted(x.name for x in OUT.glob("intelligence_*.png")))


asyncio.run(main())
