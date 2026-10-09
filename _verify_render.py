
import asyncio
async def main():
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        b = await p.chromium.launch(headless=True)
        pg = await b.new_page()
        await pg.goto("http://127.0.0.1:9120/", wait_until="networkidle", timeout=60000)
        await pg.wait_for_timeout(6000)
        title = await pg.title()
        header = await pg.query_selector(".tsp-header")
        hdr_txt = await header.inner_text() if header else "NOT FOUND"
        primary = await pg.evaluate("getComputedStyle(document.documentElement).getPropertyValue('--ss-primary')")
        body_len = len(await pg.evaluate("document.body.innerText"))
        logo_img = await pg.evaluate("(() => {const i=document.querySelector('.tsp-header img'); return i? (i.complete && i.naturalWidth>0 ? 'LOADED' : 'BROKEN') : 'NO IMG';})()")
        print("TITLE:", title)
        print("HEADER:", hdr_txt)
        print("--ss-primary:", primary)
        print("body innerText len:", body_len)
        print("LOGO:", logo_img)
        await b.close()
asyncio.run(main())
