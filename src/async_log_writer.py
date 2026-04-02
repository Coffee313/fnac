"""
Async log writer for high-throughput logging.

Implements a queue-based async writer that batches logs before writing to database.
This allows non-blocking log writes and significantly improves throughput.
"""

import asyncio
import logging
from typing import List, Optional
from src.models import AuthenticationLog
from src.database import Database

logger = logging.getLogger(__name__)


class AsyncLogWriter:
    """
    Async log writer with batching for high-throughput scenarios.
    
    Features:
    - Non-blocking log writes via asyncio queue
    - Automatic batching (configurable batch size)
    - Periodic flush (configurable interval)
    - Graceful shutdown
    """
    
    def __init__(self, batch_size: int = 100, flush_interval: float = 1.0):
        """
        Initialize async log writer.
        
        Args:
            batch_size: Number of logs to batch before writing
            flush_interval: Seconds to wait before flushing partial batch
        """
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self.queue: asyncio.Queue = None
        self.writer_task: Optional[asyncio.Task] = None
        self.running = False
    
    async def start(self) -> None:
        """Start the async log writer."""
        if self.running:
            return
        
        self.running = True
        self.queue = asyncio.Queue()
        self.writer_task = asyncio.create_task(self._batch_writer())
        logger.info("Async log writer started")
    
    async def stop(self) -> None:
        """Stop the async log writer and flush remaining logs."""
        if not self.running:
            return
        
        self.running = False
        
        # Wait for queue to empty
        await self.queue.join()
        
        # Cancel writer task
        if self.writer_task:
            self.writer_task.cancel()
            try:
                await self.writer_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Async log writer stopped")
    
    async def log_async(self, log_entry: AuthenticationLog) -> None:
        """
        Queue a log entry for async writing.
        
        This is non-blocking and returns immediately.
        
        Args:
            log_entry: AuthenticationLog to write
        """
        if not self.running:
            logger.warning("Log writer not running, dropping log")
            return
        
        await self.queue.put(log_entry)
    
    async def _batch_writer(self) -> None:
        """
        Batch writer coroutine that processes logs from queue.
        
        Writes logs in batches or on timeout, whichever comes first.
        """
        batch: List[AuthenticationLog] = []
        
        while self.running:
            try:
                # Wait for next log or timeout
                try:
                    log_entry = await asyncio.wait_for(
                        self.queue.get(),
                        timeout=self.flush_interval
                    )
                    batch.append(log_entry)
                    self.queue.task_done()
                except asyncio.TimeoutError:
                    # Timeout - flush partial batch if any
                    if batch:
                        await self._flush_batch(batch)
                        batch = []
                    continue
                
                # Check if batch is full
                if len(batch) >= self.batch_size:
                    await self._flush_batch(batch)
                    batch = []
            
            except Exception as e:
                logger.error(f"Error in batch writer: {e}")
                # Continue processing despite errors
                continue
        
        # Final flush on shutdown
        if batch:
            await self._flush_batch(batch)
    
    async def _flush_batch(self, batch: List[AuthenticationLog]) -> None:
        """
        Write a batch of logs to database.
        
        Args:
            batch: List of AuthenticationLog entries to write
        """
        if not batch:
            return
        
        try:
            db = Database()
            conn = db.get_connection()
            cursor = conn.cursor()
            
            # Batch insert in single transaction
            cursor.executemany("""
                INSERT INTO auth_logs 
                (id, timestamp, client_mac, device_id, outcome, vlan_id, policy_name, policy_decision, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, [
                (
                    log.id,
                    log.timestamp.isoformat(),
                    log.client_mac,
                    log.device_id,
                    log.outcome.value,
                    log.vlan_id,
                    log.policy_name,
                    log.policy_decision,
                    log.created_at.isoformat()
                )
                for log in batch
            ])
            
            conn.commit()
            conn.close()
            
            logger.debug(f"Flushed batch of {len(batch)} logs")
        
        except Exception as e:
            logger.error(f"Error flushing batch: {e}")
            # Don't raise - continue processing other batches


# Global async log writer instance
_async_writer: Optional[AsyncLogWriter] = None


def get_async_writer() -> AsyncLogWriter:
    """Get or create the global async log writer."""
    global _async_writer
    if _async_writer is None:
        _async_writer = AsyncLogWriter(batch_size=100, flush_interval=1.0)
    return _async_writer


async def init_async_logging() -> None:
    """Initialize async logging."""
    writer = get_async_writer()
    await writer.start()


async def shutdown_async_logging() -> None:
    """Shutdown async logging and flush remaining logs."""
    global _async_writer
    if _async_writer:
        await _async_writer.stop()
        _async_writer = None
