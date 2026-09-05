from __future__ import annotations

import asyncio
import logging
import os
import uvicorn

from lexis_ops.orchestration.worker import run_temporal_worker
from lexis_ops.server import app

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [LexisOps-Entrypoint] %(message)s",
)
logger = logging.getLogger("lexis_ops.entrypoint")


async def resilient_worker_loop():
    """Starts the Temporal worker with automatic backoff retry until connected."""
    host = os.environ.get("TEMPORAL_HOST", "localhost:7233")
    delay = 2
    while True:
        try:
            logger.info(f"Attempting to launch Temporal Worker connecting to {host}...")
            await run_temporal_worker(temporal_host=host)
            break
        except Exception as exc:
            logger.warning(f"Temporal cluster at {host} not ready yet ({exc}). Retrying in {delay}s...")
            await asyncio.sleep(delay)
            delay = min(delay * 1.5, 30)


async def main_async():
    port = int(os.environ.get("PORT", "8000"))
    host = os.environ.get("HOST", "0.0.0.0")

    config = uvicorn.Config(app=app, host=host, port=port, log_level="info")
    server = uvicorn.Server(config)

    # Launch worker loop and web server concurrently
    worker_task = asyncio.create_task(resilient_worker_loop())
    server_task = asyncio.create_task(server.serve())

    await asyncio.gather(server_task, worker_task)


def main():
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
