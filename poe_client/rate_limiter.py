"""
Rate limiter for POE API with exponential backoff and request queuing.

This module implements Phase 2 rate limiting features:
- Exponential backoff starting at 250ms
- Respect for Retry-After headers
- Request queuing with priority system
- Automatic retry with jitter
"""
import asyncio
import random
import time
import heapq
from collections import deque, defaultdict
from typing import Dict, Any, Optional, Callable, TypeVar, Coroutine
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from loguru import logger

T = TypeVar('T')


@dataclass(order=True)
class PriorityRequest:
    """Priority request for queuing system."""
    priority: int
    timestamp: float = field(compare=False)
    request_id: str = field(compare=False)
    func: Callable = field(compare=False)
    args: tuple = field(compare=False)
    kwargs: dict = field(compare=False)
    future: asyncio.Future = field(compare=False)


class RequestQueue:
    """
    Priority queue for managing requests.
    
    Lower priority numbers are processed first (1 = highest priority).
    """
    
    def __init__(self):
        self.queue: list = []
        self.lock = asyncio.Lock()
        self.request_count = 0
        
    async def put(self, request: PriorityRequest) -> None:
        """Add a request to the priority queue."""
        async with self.lock:
            heapq.heappush(self.queue, request)
            self.request_count += 1
            logger.debug(f"Added request {request.request_id} with priority {request.priority}")
    
    async def get(self) -> Optional[PriorityRequest]:
        """Get the highest priority request from the queue."""
        async with self.lock:
            if self.queue:
                request = heapq.heappop(self.queue)
                logger.debug(f"Processing request {request.request_id}")
                return request
            return None
    
    async def size(self) -> int:
        """Get current queue size."""
        async with self.lock:
            return len(self.queue)
    
    async def clear_expired(self, max_age_seconds: int = 300) -> int:
        """Remove requests older than max_age_seconds."""
        async with self.lock:
            current_time = time.time()
            expired = []
            new_queue = []
            
            for req in self.queue:
                if current_time - req.timestamp > max_age_seconds:
                    expired.append(req)
                    req.future.set_exception(TimeoutError(f"Request {req.request_id} expired"))
                else:
                    new_queue.append(req)
            
            self.queue = new_queue
            heapq.heapify(self.queue)
            
            if expired:
                logger.warning(f"Cleared {len(expired)} expired requests")
            
            return len(expired)


class ExponentialBackoffRateLimiter:
    """
    Rate limiter with exponential backoff for POE API.
    
    Features:
    - 500 RPM limit enforcement
    - Exponential backoff starting at 250ms
    - Retry-After header support
    - Request queuing with priorities
    - Automatic retry with jitter
    """
    
    def __init__(
        self,
        rpm_limit: int = 500,
        base_wait_ms: int = 250,
        max_backoff_s: int = 30,
        max_retries: int = 5
    ):
        """
        Initialize rate limiter.
        
        Args:
            rpm_limit: Requests per minute limit
            base_wait_ms: Base wait time in milliseconds
            max_backoff_s: Maximum backoff in seconds
            max_retries: Maximum retry attempts
        """
        self.rpm_limit = rpm_limit
        self.base_wait = base_wait_ms / 1000.0
        self.max_backoff = max_backoff_s
        self.max_retries = max_retries
        
        # Request tracking
        self.request_times = deque()
        self.request_queue = RequestQueue()
        self.lock = asyncio.Lock()
        
        # Error tracking
        self.error_counts = defaultdict(int)
        self.retry_after_until = None
        
        # Metrics
        self.metrics = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'rate_limited': 0,
            'retries': 0,
            'queue_size_max': 0,
            'total_wait_time': 0.0,
        }
        
        # Start queue processor
        self.queue_processor_task = None
        self.running = True
    
    def _cleanup_window(self) -> None:
        """Remove old requests outside the 60-second window."""
        current_time = time.time()
        while self.request_times and self.request_times[0] < current_time - 60:
            self.request_times.popleft()
    
    async def _wait_for_slot(self) -> None:
        """Wait until a request slot is available."""
        async with self.lock:
            while True:
                self._cleanup_window()
                
                # Check if we're under retry-after restriction
                if self.retry_after_until and time.time() < self.retry_after_until:
                    wait_time = self.retry_after_until - time.time()
                    logger.info(f"Waiting {wait_time:.2f}s for retry-after period")
                    await asyncio.sleep(wait_time)
                    self.retry_after_until = None
                
                # Check if we can make a request
                if len(self.request_times) < self.rpm_limit:
                    self.request_times.append(time.time())
                    return
                
                # Calculate wait time with exponential backoff
                backoff_multiplier = min(2 ** self.error_counts['rate_limit'], 64)
                backoff = min(self.base_wait * backoff_multiplier, self.max_backoff)
                jitter = random.uniform(0, backoff * 0.5)
                total_wait = backoff + jitter
                
                self.metrics['total_wait_time'] += total_wait
                self.metrics['rate_limited'] += 1
                
                logger.debug(f"Rate limit reached, waiting {total_wait:.3f}s")
                await asyncio.sleep(total_wait)
    
    async def execute(
        self,
        func: Callable[..., Coroutine[Any, Any, T]],
        *args,
        priority: int = 5,
        request_id: Optional[str] = None,
        **kwargs
    ) -> T:
        """
        Execute a function with rate limiting.
        
        Args:
            func: Async function to execute
            priority: Request priority (1-10, 1 = highest)
            request_id: Optional request identifier
            *args, **kwargs: Arguments for the function
            
        Returns:
            Function result
            
        Raises:
            Exception: If max retries exceeded or function fails
        """
        if request_id is None:
            request_id = f"req_{int(time.time() * 1000)}"
        
        self.metrics['total_requests'] += 1
        
        # Add to queue if processor is running
        if self.queue_processor_task and not self.queue_processor_task.done():
            future = asyncio.Future()
            request = PriorityRequest(
                priority=priority,
                timestamp=time.time(),
                request_id=request_id,
                func=func,
                args=args,
                kwargs=kwargs,
                future=future
            )
            await self.request_queue.put(request)
            
            # Update max queue size metric
            queue_size = await self.request_queue.size()
            self.metrics['queue_size_max'] = max(self.metrics['queue_size_max'], queue_size)
            
            return await future
        
        # Direct execution with rate limiting
        retries = 0
        last_error = None
        
        while retries <= self.max_retries:
            try:
                # Wait for available slot
                await self._wait_for_slot()
                
                # Execute the function
                logger.debug(f"Executing request {request_id} (attempt {retries + 1})")
                result = await func(*args, **kwargs)
                
                # Handle retry-after header if present
                if hasattr(result, 'headers') and 'Retry-After' in result.headers:
                    retry_after = float(result.headers['Retry-After'])
                    self.retry_after_until = time.time() + retry_after
                    logger.warning(f"Got Retry-After header: {retry_after}s")
                
                # Reset error counts on success
                self.error_counts['rate_limit'] = 0
                self.error_counts[request_id] = 0
                self.metrics['successful_requests'] += 1
                
                return result
                
            except Exception as e:
                last_error = e
                retries += 1
                self.metrics['retries'] += 1
                self.error_counts[request_id] += 1
                
                if retries > self.max_retries:
                    logger.error(f"Request {request_id} failed after {retries} attempts: {e}")
                    self.metrics['failed_requests'] += 1
                    raise
                
                # Calculate backoff for retry
                backoff = min(self.base_wait * (2 ** (retries - 1)), self.max_backoff)
                jitter = random.uniform(0, backoff * 0.5)
                wait_time = backoff + jitter
                
                logger.warning(f"Request {request_id} failed, retrying in {wait_time:.3f}s: {e}")
                await asyncio.sleep(wait_time)
        
        raise last_error or Exception(f"Request {request_id} failed")
    
    async def start_queue_processor(self) -> None:
        """Start the background queue processor."""
        if not self.queue_processor_task or self.queue_processor_task.done():
            self.queue_processor_task = asyncio.create_task(self._process_queue())
            logger.info("Started queue processor")
    
    async def stop_queue_processor(self) -> None:
        """Stop the background queue processor."""
        self.running = False
        if self.queue_processor_task:
            await self.queue_processor_task
            logger.info("Stopped queue processor")
    
    async def _process_queue(self) -> None:
        """Process requests from the queue."""
        while self.running:
            try:
                # Clear expired requests
                await self.request_queue.clear_expired()
                
                # Get next request
                request = await self.request_queue.get()
                if not request:
                    await asyncio.sleep(0.1)
                    continue
                
                # Execute the request
                try:
                    result = await self.execute(
                        request.func,
                        *request.args,
                        priority=request.priority,
                        request_id=request.request_id,
                        **request.kwargs
                    )
                    request.future.set_result(result)
                except Exception as e:
                    request.future.set_exception(e)
                    
            except Exception as e:
                logger.error(f"Queue processor error: {e}")
                await asyncio.sleep(1)
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics."""
        return {
            **self.metrics,
            'current_rpm': len(self.request_times),
            'queue_size': len(self.request_queue.queue),
            'success_rate': (
                self.metrics['successful_requests'] / self.metrics['total_requests'] * 100
                if self.metrics['total_requests'] > 0 else 0
            ),
        }
    
    def reset_metrics(self) -> None:
        """Reset metrics counters."""
        self.metrics = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'rate_limited': 0,
            'retries': 0,
            'queue_size_max': 0,
            'total_wait_time': 0.0,
        }


# Global rate limiter instance
rate_limiter = ExponentialBackoffRateLimiter()


async def with_rate_limit(
    func: Callable[..., Coroutine[Any, Any, T]],
    *args,
    priority: int = 5,
    **kwargs
) -> T:
    """
    Convenience function to execute with rate limiting.
    
    Args:
        func: Async function to execute
        priority: Request priority (1-10)
        *args, **kwargs: Function arguments
        
    Returns:
        Function result
    """
    return await rate_limiter.execute(func, *args, priority=priority, **kwargs)