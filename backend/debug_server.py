import asyncio
import sys
import uvicorn

if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())


def main():
    config = uvicorn.Config(
        "backend.main:app",
        host="127.0.0.1",
        port=8001,
        log_level="debug",
        access_log=True,
        reload=False,
    )
    server = uvicorn.Server(config)
    asyncio.run(server.serve())


if __name__ == "__main__":
    main()