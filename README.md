# HTTP Client Benchmark: httpx vs aiohttp

## Environment
- Python: 3.13.7
- httpx: 0.28.1
- aiohttp: 3.12.15
- Server: Multi-process async server (11 workers)
- URL: http://localhost:8888/

## Results

### Serial Requests (1000 requests, one at a time)

#### Without Connection Pooling

| Metric | httpx | aiohttp |
|--------|-------|---------|
| Min (ms) | 0.580 | 0.221 |
| Max (ms) | 3.598 | 0.996 |
| Mean (ms) | 0.755 | 0.265 |
| Median (ms) | 0.733 | 0.248 |
| Stdev (ms) | 0.138 | 0.065 |
| P95 (ms) | 0.910 | 0.340 |
| P99 (ms) | 1.170 | 0.622 |

#### With Connection Pooling

| Metric | httpx | aiohttp |
|--------|-------|---------|
| Min (ms) | 0.273 | 0.073 |
| Max (ms) | 6.405 | 0.889 |
| Mean (ms) | 0.332 | 0.090 |
| Median (ms) | 0.311 | 0.087 |
| Stdev (ms) | 0.216 | 0.027 |
| P95 (ms) | 0.382 | 0.109 |
| P99 (ms) | 0.655 | 0.121 |

### Parallel Requests (100 requests x 10 batches)

#### Without Connection Pooling - Batch Timing

| Metric | httpx | aiohttp |
|--------|-------|---------|
| Min (ms) | 33.390 | 8.355 |
| Max (ms) | 37.750 | 19.332 |
| Mean (ms) | 34.798 | 10.069 |
| Median (ms) | 33.893 | 8.922 |

#### With Connection Pooling - Batch Timing

| Metric | httpx | aiohttp |
|--------|-------|---------|
| Min (ms) | 53.329 | 3.521 |
| Max (ms) | 938.367 | 11.529 |
| Mean (ms) | 528.108 | 4.721 |
| Median (ms) | 708.868 | 4.044 |

## Summary

### Impact of Connection Pooling

**httpx:**
- Serial: 56.0% faster with pooling
- Parallel: -1417.6% slower with pooling

**aiohttp:**
- Serial: 66.1% faster with pooling
- Parallel: 53.1% faster with pooling

### Library Comparison

**Without Connection Pooling:**
- Serial: aiohttp is 185.0% faster
- Parallel: aiohttp is 245.6% faster

**With Connection Pooling:**
- Serial: aiohttp is 270.1% faster
- Parallel: aiohttp is 11086.2% faster
