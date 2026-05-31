import time
import asyncio

class TokenBucket:
    
    def __init__(self, max_capacity:int, refil_rate:float):
        self.tokens = float(max_capacity)
        self.capacity = float(max_capacity)
        self.refill_rate = float(refil_rate)
        self.last_refill = time.monotonic()
        self._lock = asyncio.Lock()
        
    
    def _refill(self):
        current_time = time.monotonic()
        
        time_elapsed = current_time-self.last_refill
        
        new_tokens = self.refill_rate * time_elapsed
        
        if new_tokens > 0 :
            self.tokens = min(self.capacity, self.tokens + new_tokens)
            self.last_refill = current_time
    
    
    async def acquire(self):
        while True:
            async with self._lock:
                self._refill()
                
                if self.tokens >= 1:
                    self.tokens -= 1
                    return

                deficit = 1 - self.tokens
                
                refill_time = deficit / self.refill_rate

            await asyncio.sleep(refill_time)
             
        