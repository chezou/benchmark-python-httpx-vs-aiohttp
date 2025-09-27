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
| Min (ms) | 0.590 | 0.224 |
| Max (ms) | 4.060 | 0.735 |
| Mean (ms) | 0.764 | 0.246 |
| Median (ms) | 0.745 | 0.242 |
| Stdev (ms) | 0.151 | 0.023 |
| P95 (ms) | 0.944 | 0.274 |
| P99 (ms) | 1.196 | 0.320 |

#### With Connection Pooling

| Metric | httpx | aiohttp |
|--------|-------|---------|
| Min (ms) | 0.276 | 0.073 |
| Max (ms) | 0.986 | 0.899 |
| Mean (ms) | 0.319 | 0.088 |
| Median (ms) | 0.312 | 0.086 |
| Stdev (ms) | 0.047 | 0.028 |
| P95 (ms) | 0.348 | 0.109 |
| P99 (ms) | 0.602 | 0.125 |

### Parallel Requests (100 requests x 10 batches)

#### Without Connection Pooling - Batch Timing

| Metric | httpx | aiohttp |
|--------|-------|---------|
| Min (ms) | 33.594 | 8.270 |
| Max (ms) | 35.893 | 19.605 |
| Mean (ms) | 34.434 | 9.899 |
| Median (ms) | 34.117 | 8.567 |

#### With Connection Pooling - Batch Timing

| Metric | httpx | aiohttp |
|--------|-------|---------|
| Min (ms) | 58.868 | 3.682 |
| Max (ms) | 961.111 | 9.972 |
| Mean (ms) | 531.088 | 5.117 |
| Median (ms) | 679.352 | 4.226 |

## Summary

### Impact of Connection Pooling

**httpx:**
- Serial: 58.2% faster with pooling
- Parallel: -1442.3% slower with pooling

**aiohttp:**
- Serial: 64.1% faster with pooling
- Parallel: 48.3% faster with pooling

### Library Comparison

**Without Connection Pooling:**
- Serial: aiohttp is 210.3% faster
- Parallel: aiohttp is 247.8% faster

**With Connection Pooling:**
- Serial: aiohttp is 261.3% faster
- Parallel: aiohttp is 10278.9% faster
