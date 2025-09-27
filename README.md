# HTTP Client Benchmark: httpx vs aiohttp

## Environment
- Python: 3.13.7
- httpx: 0.28.1
- aiohttp: 3.12.15
- Server: Multi-process async server (11 workers)
- URL: http://localhost:8888/
- Connection Pool: Disabled

## Results

### Serial Requests (1000 requests, one at a time)

| Metric | httpx | aiohttp |
|--------|-------|---------|
| Min (ms) | 0.567 | 0.217 |
| Max (ms) | 4.399 | 5.713 |
| Mean (ms) | 0.743 | 0.280 |
| Median (ms) | 0.720 | 0.242 |
| Stdev (ms) | 0.156 | 0.222 |
| P95 (ms) | 0.917 | 0.444 |
| P99 (ms) | 1.125 | 0.920 |

### Parallel Requests (100 requests x 10 batches)

#### Batch Timing (time to complete 100 parallel requests)

| Metric | httpx | aiohttp |
|--------|-------|---------|
| Min (ms) | 33.173 | 8.316 |
| Max (ms) | 34.914 | 18.253 |
| Mean (ms) | 34.002 | 9.938 |
| Median (ms) | 33.975 | 8.783 |

#### Per-Request Average (batch time / 100)

| Metric | httpx | aiohttp |
|--------|-------|---------|
| Mean (ms) | 0.340 | 0.099 |
| Median (ms) | 0.340 | 0.088 |

## Summary

**Serial Performance:**
- aiohttp is 165.4% faster on average for serial requests

**Parallel Performance:**
- aiohttp is 242.1% faster on average for parallel batch requests
