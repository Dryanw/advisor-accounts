**What I don't trust**

1. idempotency_cache.py: would need to verify if the lock would induce any performance issue, and potentially if there
   is a better implementation with fastapi-idempotency + Redis

**AI use**
I have used Claude Code to review the code that I wrote and provide comments