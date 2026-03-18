"""
Nexus Monitor Job Runner

Polls registered jobs on their configured intervals.
Jobs run sequentially — no overlap possible.
Includes per-job timeout (5 minutes default).
"""

import time
import signal
import logging
import concurrent.futures
from datetime import datetime, timezone, timedelta
from typing import Dict, Any

logger = logging.getLogger('NexusMonitor.runner')

DEFAULT_JOB_TIMEOUT = 300  # 5 minutes


class JobContext:
    """Context passed to each job's run() method"""

    def __init__(self, graph_client, keyvault, state, config: Dict[str, Any]):
        self.graph_client = graph_client
        self.keyvault = keyvault
        self.state = state
        self.config = config


class JobRunner:
    """Runs registered jobs on their polling intervals"""

    def __init__(self, jobs: list, context: JobContext, default_interval: int = 5):
        self.jobs = jobs
        self.context = context
        self.default_interval = default_interval
        self._running = True

        signal.signal(signal.SIGINT, self._handle_shutdown)
        signal.signal(signal.SIGTERM, self._handle_shutdown)

    def _handle_shutdown(self, signum, frame):
        logger.info(f"Shutdown signal received ({signum}), stopping...")
        self._running = False

    def run_once(self):
        """Run all jobs once (ignoring intervals). Used for testing."""
        logger.info(f"Running all {len(self.jobs)} job(s) once...")
        for job_cls in self.jobs:
            self._execute_job(job_cls)
        logger.info("Single run complete")

    def run_forever(self):
        """Main polling loop — runs jobs on their intervals until shutdown"""
        logger.info(f"Starting job runner with {len(self.jobs)} job(s)")
        for job_cls in self.jobs:
            logger.info(f"  - {job_cls.JOB_NAME} (every {job_cls.INTERVAL_MINUTES}m)")

        while self._running:
            for job_cls in self.jobs:
                if not self._running:
                    break

                last_run = self.context.state.get_last_run(job_cls.JOB_NAME)
                if last_run:
                    last_run_dt = datetime.fromisoformat(last_run.replace('Z', '+00:00'))
                    interval = timedelta(minutes=job_cls.INTERVAL_MINUTES)
                    if datetime.now(timezone.utc) - last_run_dt < interval:
                        continue

                self._execute_job(job_cls)

            # Sleep between poll cycles (check every 5 seconds for shutdown signal)
            for _ in range(6):  # 6 x 5s = 30s
                if not self._running:
                    break
                time.sleep(5)

        logger.info("Job runner stopped")

    def _execute_job(self, job_cls):
        """Execute a single job with error handling and timeout"""
        job_name = job_cls.JOB_NAME
        logger.info(f"Running job: {job_name}")
        start = time.time()

        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(job_cls.run, self.context)
                future.result(timeout=DEFAULT_JOB_TIMEOUT)
            elapsed = time.time() - start
            logger.info(f"Job {job_name} completed in {elapsed:.1f}s")
        except concurrent.futures.TimeoutError:
            elapsed = time.time() - start
            logger.error(f"Job {job_name} timed out after {elapsed:.1f}s (limit: {DEFAULT_JOB_TIMEOUT}s)")
        except Exception as e:
            elapsed = time.time() - start
            logger.error(f"Job {job_name} failed after {elapsed:.1f}s: {e}")

        # Update last_run regardless of success/failure
        self.context.state.set_last_run(job_name)
