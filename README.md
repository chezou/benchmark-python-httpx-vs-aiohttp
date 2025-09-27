# HTTP Client Benchmark: httpx vs aiohttp

## Environment
- Python: 3.13.7
- httpx: 0.28.1
- aiohttp: 3.12.15
- Server: Multi-process async server (12 workers)
- URL: http://localhost:8888/

## Results

### Serial Requests (1000 requests, one at a time)

#### Without Connection Pooling

| Metric | httpx | aiohttp | httpx + aiohttp |
|--------|-------|---------|---------|
| Min (ms) | 0.860 | 0.360 | 0.481 |
| Max (ms) | 4.151 | 0.850 | 1.817 |
| Mean (ms) | 0.979 | 0.397 | 0.546 |
| Median (ms) | 0.942 | 0.380 | 0.526 |
| Stdev (ms) | 0.166 | 0.046 | | 0.077 |
| P95 (ms) | 1.150 | 0.486 | 0.623 |
| P99 (ms) | 1.644 | 0.560 | | 0.945 |

#### With Connection Pooling

| Metric | httpx | aiohttp | httpx + aiohttp |
|--------|-------|---------|---------|
| Min (ms) | 0.404 | 0.173 | 0.310 |
| Max (ms) | 1.708 | 0.882 | 29.239 |
| Mean (ms) | 0.461 | 0.192 | 0.400 |
| Median (ms) | 0.447 | 0.182 | 0.355 |
| Stdev (ms) | 0.067 | 0.030 | 0.917 |
| P95 (ms) | 0.531 | 0.236 | 0.454 |
| P99 (ms) | 0.794 | 0.271 | 0.950 |

### Parallel Requests (100 requests x 10 batches)

#### Without Connection Pooling - Batch Timing

| Metric | httpx | aiohttp | httpx + aiohttp |
|--------|-------|---------|---------|
| Min (ms) | 61.127 | 20.429 | 32.960 |
| Max (ms) | 134.535 | 24.059 | 36.623 |
| Mean (ms) | 76.340 | 21.235 | 35.669 |
| Median (ms) | 68.537 | 20.929 | 35.757 |

#### With Connection Pooling - Batch Timing

| Metric | httpx | aiohttp | httpx + aiohttp |
|--------|-------|---------|---------|
| Min (ms) | 77.580 | 7.453 | 19.463 |
| Max (ms) | 737.140 | 21.923 | 30.590 |
| Mean (ms) | 525.791 | 9.145 | 21.840 |
| Median (ms) | 686.779 | 7.713 | 20.723 |

## Summary

### Impact of Connection Pooling

**httpx:**
- Serial: 52.9% faster with pooling
- Parallel: -588.8% slower with pooling

**aiohttp:**
- Serial: 51.8% faster with pooling
- Parallel: 56.9% faster with pooling

**httpx + aiohttp:**
- Serial: 26.7% faster with pooling
- Parallel: 38.8% faster with pooling

### Library Comparison

#### aiohttp vs httpx

**Without Connection Pooling:**
- Serial: aiohttp is 146.5% faster
- Parallel: aiohttp is 259.5% faster

**With Connection Pooling:**
- Serial: aiohttp is 140.6% faster
- Parallel: aiohttp is 5649.4% faster

#### aiohttp vs httpx + aiohttp transport

**Without Connection Pooling:**
- Serial: aiohttp is 37.5% faster
- Parallel: aiohttp is 68.0% faster

**With Connection Pooling:**
- Serial: aiohttp is 109.0% faster
- Parallel: aiohttp is 138.8% faster
