"""Headless walkthrough of the web app: scan → found → get it back → guardian → approve → case.
Saves screenshots to /tmp/vr-shots. Used for QA and for the demo video."""
import asyncio, sys
from pathlib import Path
from playwright.async_api import async_playwright

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8765"
OUT = Path("/tmp/vr-shots"); OUT.mkdir(exist_ok=True)


async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        pg = await b.new_page(viewport={"width": 1180, "height": 820}, device_scale_factor=1)
        errors = []
        pg.on("pageerror", lambda e: errors.append(str(e)))
        pg.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
        await pg.goto(BASE + "/#/")
        await pg.wait_for_selector("#scanform")
        await pg.click("#lang-en")
        await pg.screenshot(path=OUT / "01-home.png", full_page=True)
        await pg.click(".sample[data-name^='canara']")
        await pg.click("#scanbtn")
        await pg.wait_for_selector(".hero-amount", timeout=20000)
        await pg.screenshot(path=OUT / "02-found.png", full_page=True)
        # answer the min-balance question: No
        btns = await pg.query_selector_all(".qbtns[data-q='notice_received'] .ans[data-val='no']")
        if btns:
            await btns[0].click(); await pg.wait_for_timeout(800)
        # open a why panel
        await pg.click(".why-toggle")
        await pg.wait_for_selector(".why .kv", timeout=5000)
        await pg.screenshot(path=OUT / "03-why.png", full_page=True)
        # settings → guardian
        await pg.goto(BASE + "/#/settings"); await pg.wait_for_selector("#gform")
        await pg.fill("#gform [name=name]", "Kumar"); await pg.fill("#gform [name=phone]", "+91 98765 43210")
        await pg.fill("#gform [name=consent]", "En account-la edhavadhu thappa nadandha, en payyan Kumar-ku solunga.")
        await pg.click("#gform button[type=submit]"); await pg.wait_for_timeout(600)
        await pg.screenshot(path=OUT / "04-settings.png", full_page=True)
        # findings → get it back
        await pg.goto(BASE + "/#/findings"); await pg.wait_for_selector("#getback")
        await pg.click("#getback")
        await pg.wait_for_selector("#askg", timeout=10000)
        await pg.screenshot(path=OUT / "05-case-prepared.png", full_page=True)
        await pg.click("#preview"); await pg.wait_for_timeout(500)
        await pg.click("#askg")
        await pg.wait_for_selector("#approve", timeout=10000)
        await pg.screenshot(path=OUT / "06-guardian.png", full_page=True)
        await pg.click("#approve")
        await pg.wait_for_selector(".track .on", timeout=10000)
        await pg.wait_for_timeout(500)
        await pg.screenshot(path=OUT / "07-sent.png", full_page=True)
        # ask
        await pg.goto(BASE + "/#/ask"); await pg.wait_for_selector("#askform")
        await pg.fill("#q", "why did the bank charge me 295?"); await pg.click("#askform button[type=submit]")
        await pg.wait_for_timeout(900)
        await pg.fill("#q", "what should I do?"); await pg.click("#askform button[type=submit]")
        await pg.wait_for_timeout(900)
        await pg.screenshot(path=OUT / "08-ask.png", full_page=True)
        await pg.goto(BASE + "/#/rules"); await pg.wait_for_selector(".rule")
        await pg.screenshot(path=OUT / "09-rules.png", full_page=False)
        await pg.goto(BASE + "/#/cases"); await pg.wait_for_selector(".track")
        await pg.screenshot(path=OUT / "10-cases.png", full_page=True)
        # phone width check
        await pg.set_viewport_size({"width": 400, "height": 820})
        await pg.goto(BASE + "/#/findings"); await pg.wait_for_selector(".hero-amount")
        await pg.screenshot(path=OUT / "11-mobile-found.png", full_page=True)
        await b.close()
        print("errors:", errors)
        print("shots:", sorted(p.name for p in OUT.iterdir()))


asyncio.run(main())
