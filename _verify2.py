
import asyncio
async def main():
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        b = await p.chromium.launch(headless=True)
        pg = await b.new_page(viewport={"width":1440,"height":900})
        await pg.goto("http://127.0.0.1:9120/", wait_until="networkidle", timeout=60000)
        await pg.wait_for_timeout(5000)
        await pg.screenshot(path="/tmp/tsp_scrape_tab.png", full_page=False)
        # klik tab Dashboard
        tabs = await pg.query_selector_all('[data-baseweb="tab"]')
        print("tab count:", len(tabs))
        if len(tabs) > 1:
            await tabs[1].click()
            await pg.wait_for_timeout(4000)
        txt = await pg.evaluate("document.body.innerText")
        print("DASH TEXT:", [l for l in txt.split("\n") if l.strip()][:14])
        await pg.screenshot(path="/tmp/tsp_dash_tab.png", full_page=False)
        await b.close()
asyncio.run(main())
