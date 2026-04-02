"""
Entrypoint: runs HTTP static server (port 8080) + WS game server (port 8765).
"""
import asyncio
import logging
from pathlib import Path

import websockets
from aiohttp import web

import config
from ws_handler import handler

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("quadra")

STATIC_DIR = Path(__file__).parent / "static"


async def _start_http() -> None:
    app = web.Application()

    async def index(request):
        return web.FileResponse(STATIC_DIR / "index.html")

    app.router.add_get("/", index)
    app.router.add_get("/index.html", index)
    app.router.add_static("/css/", STATIC_DIR / "css")
    app.router.add_static("/js/",  STATIC_DIR / "js")

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, config.HTTP_HOST, config.HTTP_PORT)
    await site.start()
    log.info(f"HTTP server on http://{config.HTTP_HOST}:{config.HTTP_PORT}")


async def main() -> None:
    await _start_http()

    log.info(f"WebSocket server on ws://{config.WS_HOST}:{config.WS_PORT}")
    async with websockets.serve(
        handler,
        config.WS_HOST,
        config.WS_PORT,
        ping_interval=config.WS_PING_INTERVAL,
        ping_timeout=config.WS_PING_TIMEOUT,
    ):
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
