
import asyncio
async def main():
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        b = await p.chromium.launch(headless=True)
        pg = await b.new_page(viewport={"width":1440,"height":900})
        await pg.goto("http://127.0.0.1:9120/", wait_until="networkidle", timeout=60000)
        await pg.wait_for_timeout(6000)
        txt = await pg.evaluate("document.body.innerText")
        lines = [l for l in txt.split("\n") if l.strip()]
        print("PAGE1 LINES:", lines[:16])
        # sidebar visible?
        sb = await pg.query_selector("[data-testid=stSidebar]")
        print("sidebar present:", sb is not None)
        # topbar?
        tb = await pg.query_selector(".tsp-topbar")
        print("topbar present:", tb is not None)
        if tb:
            print("topbar text:", (await tb.inner_text()).replace("\n"," | "))
        # klik nav Dashboard
        nav = await pg.query_selector_all("[data-testid=stSidebar] a, [data-testid=stNavLink]")
        print("nav items:", len(nav))
        clicked = False
        for n in nav:
            t = (await n.inner_text() or "").strip()
            if "Dashboard" in t:
                await n.click(); clicked = True; break
        print("clicked dashboard:", clicked)
        await pg.wait_for_timeout(5000)
        txt2 = await pg.evaluate("document.body.innerText")
        l2 = [l for l in txt2.split("\n") if l.strip()]
        print("PAGE2 LINES:", l2[:14])
        # klik AI Insight
        for n in await pg.query_selector_all("[data-testid=stSidebar] a, [data-testid=stNavLink]"):
            t = (await n.inner_text() or "").strip()
            if "AI Insight" in t:
                await n.click(); break
        await pg.wait_for_timeout(5000)
        txt3 = await pg.evaluate("document.body.innerText")
        l3 = [l for l in txt3.split("\n") if l.strip()]
        print("PAGE3 LINES:", l3[:14])
        # default streamlit header hidden?
        hdr = await pg.evaluate("(() => {const h=document.querySelector('[data-testid=stHeader]'); return h? getComputedStyle(h).display : 'gone';})()")
        print("stHeader display:", hdr)
        await b.close()
asyncio.run(main())
