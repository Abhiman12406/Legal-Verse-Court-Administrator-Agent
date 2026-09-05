from __future__ import annotations

import asyncio
import logging
import os
import sys
from typing import Optional

from temporalio.client import Client
from temporalio.worker import Worker

from lexis_ops.orchestration.temporal_workflow import (
    LexisOpsFilingWorkflow,
    activity_constraint_scheduling,
    activity_notice_and_audit,
    activity_ocr_ingress,
    activity_security_and_precheck,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [LexisOps-TemporalWorker] %(message)s",
)
logger = logging.getLogger("lexis_ops.worker")


async def run_temporal_worker(
    temporal_host: Optional[str] = None,
    task_queue: Optional[str] = None,
    namespace: Optional[str] = None,
) -> None:
    """
    Connects to the Temporal cluster and starts the LexisOps durable workflow worker.
    """
    host = temporal_host or os.environ.get("TEMPORAL_HOST", "localhost:7233")
    queue = task_queue or os.environ.get("TEMPORAL_TASK_QUEUE", "lexis-ops-filing-queue")
    ns = namespace or os.environ.get("TEMPORAL_NAMESPACE", "default")

    logger.info(f"Connecting to Temporal cluster at {host} (namespace={ns})...")
    client = await Client.connect(host, namespace=ns)
    logger.info(f"Connected to Temporal. Initializing worker on task queue '{queue}'...")

    worker = Worker(
        client,
        task_queue=queue,
        workflows=[LexisOpsFilingWorkflow],
        activities=[
            activity_ocr_ingress,
            activity_security_and_precheck,
            activity_constraint_scheduling,
            activity_notice_and_audit,
        ],
    )

    logger.info("LexisOps Temporal Worker initialized successfully. Listening for tasks...")
    await worker.run()


def main() -> None:
    try:
        asyncio.run(run_temporal_worker())
    except KeyboardInterrupt:
        logger.info("Temporal Worker interrupted by user. Shutting down gracefully.")
        sys.exit(0)
    except Exception as exc:
        logger.error(f"Fatal error in Temporal Worker: {exc}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
