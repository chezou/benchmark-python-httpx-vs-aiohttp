#!/usr/bin/env python3

import asyncio
import time
import statistics
import multiprocessing
import sys
import argparse
from typing import Any

import httpx
import aiohttp
from aiohttp import web
import uvloop

PORT = 8888
URL = f"http://localhost:{PORT}/"
NUM_WORKERS = multiprocessing.cpu_count()


async def handle_request(request):
    """Simple handler that returns Hello, world!"""
    return web.Response(text="Hello, world!\n!")


def run_server_worker():
    """Run a single server worker process"""
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
    app = web.Application()
    app.router.add_get('/', handle_request)

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    runner = web.AppRunner(app)
    loop.run_until_complete(runner.setup())
    site = web.TCPSite(runner, 'localhost', PORT, reuse_address=True, reuse_port=True)
    loop.run_until_complete(site.start())

    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass
    finally:
        loop.run_until_complete(runner.cleanup())


def start_server():
    """Start multi-process async server"""
    processes = []
    for _ in range(NUM_WORKERS):
        p = multiprocessing.Process(target=run_server_worker)
        p.start()
        processes.append(p)
    return processes


def stop_server(processes):
    """Stop all server processes"""
    for p in processes:
        p.terminate()
    for p in processes:
        p.join(timeout=2)
        if p.is_alive():
            p.kill()
            p.join()


async def benchmark_httpx_serial(n: int, connection_pool: bool = False) -> list[float]:
    """Benchmark httpx with serial requests"""
    latencies = []
    if connection_pool:
        limits = httpx.Limits()
    else:
        limits = httpx.Limits(max_keepalive_connections=0, keepalive_expiry=0)

    async with httpx.AsyncClient(limits=limits) as client:
        for _ in range(n):
            start = time.perf_counter()
            response = await client.get(URL)
            assert response.status_code == 200
            latencies.append(time.perf_counter() - start)
    return latencies


async def benchmark_aiohttp_serial(n: int, connection_pool: bool = False) -> list[float]:
    """Benchmark aiohttp with serial requests"""
    latencies = []
    if connection_pool:
        tcp_connector = aiohttp.TCPConnector(force_close=False)
    else:
        tcp_connector = aiohttp.TCPConnector(force_close=True)
    async with aiohttp.ClientSession(connector=tcp_connector) as session:
        for _ in range(n):
            start = time.perf_counter()
            async with session.get(URL) as response:
                assert response.status == 200
                await response.text()
            latencies.append(time.perf_counter() - start)
    return latencies


async def benchmark_httpx_parallel(batch_size: int, num_batches: int, connection_pool: bool = False) -> list[float]:
    """Benchmark httpx with parallel requests"""
    latencies = []
    if connection_pool:
        limits = httpx.Limits()
    else:
        limits = httpx.Limits(max_keepalive_connections=0, keepalive_expiry=0)

    async with httpx.AsyncClient(limits=limits) as client:
        for _ in range(num_batches):
            batch_start = time.perf_counter()
            tasks = []
            for _ in range(batch_size):
                tasks.append(client.get(URL))

            responses = await asyncio.gather(*tasks)
            for response in responses:
                assert response.status_code == 200

            batch_time = time.perf_counter() - batch_start
            latencies.append(batch_time)
    return latencies


async def benchmark_aiohttp_parallel(batch_size: int, num_batches: int, connection_pool: bool = False) -> list[float]:
    """Benchmark aiohttp with parallel requests"""
    latencies = []
    if connection_pool:
        tcp_connector = aiohttp.TCPConnector(force_close=False)
    else:
        tcp_connector = aiohttp.TCPConnector(force_close=True)
    async with aiohttp.ClientSession(connector=tcp_connector) as session:
        for _ in range(num_batches):
            batch_start = time.perf_counter()
            tasks = []

            async def make_request():
                async with session.get(URL) as response:
                    assert response.status == 200
                    return await response.text()

            for _ in range(batch_size):
                tasks.append(make_request())

            await asyncio.gather(*tasks)
            batch_time = time.perf_counter() - batch_start
            latencies.append(batch_time)
    return latencies


def calculate_stats(latencies: list[float]) -> dict[str, float]:
    """Calculate statistics from latencies"""
    return {
        'min': min(latencies) * 1000,  # Convert to ms
        'max': max(latencies) * 1000,
        'mean': statistics.mean(latencies) * 1000,
        'median': statistics.median(latencies) * 1000,
        'stdev': statistics.stdev(latencies) * 1000 if len(latencies) > 1 else 0,
        'p95': sorted(latencies)[int(len(latencies) * 0.95)] * 1000,
        'p99': sorted(latencies)[int(len(latencies) * 0.99)] * 1000,
    }


async def warmup(connection_pool: bool = False):
    """Warmup the server and clients with a few requests"""
    print("Warming up server...")

    # with httpx
    if connection_pool:
        limits = httpx.Limits()
    else:
        limits = httpx.Limits(max_keepalive_connections=0, keepalive_expiry=0)

    async with httpx.AsyncClient(limits=limits) as client:
        for _ in range(100):
            try:
                await client.get(URL, timeout=1.0)
            except Exception:
                pass

    # with aiohttp
    if connection_pool:
        aiohttp_connector = aiohttp.TCPConnector(force_close=False)
    else:
        aiohttp_connector = aiohttp.TCPConnector(force_close=True)
    async with aiohttp.ClientSession(connector=aiohttp_connector) as session:
        for _ in range(100):
            try:
                await session.get(URL, timeout=1.0)
            except Exception:
                pass

    await asyncio.sleep(0.1)


async def run_benchmarks(connection_pool: bool = False):
    """Run all benchmarks and collect results"""
    results = {}

    # Warmup
    await warmup(connection_pool)

    # Serial benchmarks
    print("\nRunning serial benchmarks (1000 requests each)...")

    print("  Testing httpx (serial)...")
    httpx_serial_latencies = await benchmark_httpx_serial(1000, connection_pool)
    results['httpx_serial'] = calculate_stats(httpx_serial_latencies)

    print("  Testing aiohttp (serial)...")
    aiohttp_serial_latencies = await benchmark_aiohttp_serial(1000, connection_pool)
    results['aiohttp_serial'] = calculate_stats(aiohttp_serial_latencies)

    # Parallel benchmarks
    print("\nRunning parallel benchmarks (100 requests x 10 batches)...")

    print("  Testing httpx (parallel)...")
    httpx_parallel_latencies = await benchmark_httpx_parallel(100, 10, connection_pool)
    results['httpx_parallel_batch'] = calculate_stats(httpx_parallel_latencies)

    print("  Testing aiohttp (parallel)...")
    aiohttp_parallel_latencies = await benchmark_aiohttp_parallel(100, 10, connection_pool)
    results['aiohttp_parallel_batch'] = calculate_stats(aiohttp_parallel_latencies)

    # Calculate per-request stats for parallel
    httpx_parallel_per_req = [t/100 for t in httpx_parallel_latencies]
    aiohttp_parallel_per_req = [t/100 for t in aiohttp_parallel_latencies]

    results['httpx_parallel_per_request'] = calculate_stats(httpx_parallel_per_req)
    results['aiohttp_parallel_per_request'] = calculate_stats(aiohttp_parallel_per_req)

    return results


def generate_report(results: dict[str, Any], connection_pool: bool = False):
    """Generate markdown report"""
    report = f"""# HTTP Client Benchmark: httpx vs aiohttp

## Environment
- Python: {sys.version.split()[0]}
- httpx: {httpx.__version__}
- aiohttp: {aiohttp.__version__}
- Server: Multi-process async server ({NUM_WORKERS} workers)
- URL: {URL}
- Connection Pool: {'Enabled' if connection_pool else 'Disabled'}

## Results

### Serial Requests (1000 requests, one at a time)

| Metric | httpx | aiohttp |
|--------|-------|---------|
| Min (ms) | {results['httpx_serial']['min']:.3f} | {results['aiohttp_serial']['min']:.3f} |
| Max (ms) | {results['httpx_serial']['max']:.3f} | {results['aiohttp_serial']['max']:.3f} |
| Mean (ms) | {results['httpx_serial']['mean']:.3f} | {results['aiohttp_serial']['mean']:.3f} |
| Median (ms) | {results['httpx_serial']['median']:.3f} | {results['aiohttp_serial']['median']:.3f} |
| Stdev (ms) | {results['httpx_serial']['stdev']:.3f} | {results['aiohttp_serial']['stdev']:.3f} |
| P95 (ms) | {results['httpx_serial']['p95']:.3f} | {results['aiohttp_serial']['p95']:.3f} |
| P99 (ms) | {results['httpx_serial']['p99']:.3f} | {results['aiohttp_serial']['p99']:.3f} |

### Parallel Requests (100 requests x 10 batches)

#### Batch Timing (time to complete 100 parallel requests)

| Metric | httpx | aiohttp |
|--------|-------|---------|
| Min (ms) | {results['httpx_parallel_batch']['min']:.3f} | {results['aiohttp_parallel_batch']['min']:.3f} |
| Max (ms) | {results['httpx_parallel_batch']['max']:.3f} | {results['aiohttp_parallel_batch']['max']:.3f} |
| Mean (ms) | {results['httpx_parallel_batch']['mean']:.3f} | {results['aiohttp_parallel_batch']['mean']:.3f} |
| Median (ms) | {results['httpx_parallel_batch']['median']:.3f} | {results['aiohttp_parallel_batch']['median']:.3f} |

#### Per-Request Average (batch time / 100)

| Metric | httpx | aiohttp |
|--------|-------|---------|
| Mean (ms) | {results['httpx_parallel_per_request']['mean']:.3f} | {results['aiohttp_parallel_per_request']['mean']:.3f} |
| Median (ms) | {results['httpx_parallel_per_request']['median']:.3f} | {results['aiohttp_parallel_per_request']['median']:.3f} |

## Summary

**Serial Performance:**
- {"aiohttp" if results['aiohttp_serial']['mean'] < results['httpx_serial']['mean'] else "httpx"} is {abs(results['httpx_serial']['mean'] - results['aiohttp_serial']['mean']) / min(results['httpx_serial']['mean'], results['aiohttp_serial']['mean']) * 100:.1f}% faster on average for serial requests

**Parallel Performance:**
- {"aiohttp" if results['aiohttp_parallel_batch']['mean'] < results['httpx_parallel_batch']['mean'] else "httpx"} is {abs(results['httpx_parallel_batch']['mean'] - results['aiohttp_parallel_batch']['mean']) / min(results['httpx_parallel_batch']['mean'], results['aiohttp_parallel_batch']['mean']) * 100:.1f}% faster on average for parallel batch requests
"""

    with open('README.md', 'w') as f:
        f.write(report)

    print("\n" + "="*60)
    print("BENCHMARK COMPLETE")
    print("="*60)
    print(report)


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Benchmark httpx vs aiohttp HTTP clients')
    parser.add_argument('--connection-pooling', action='store_true',
                        help='Enable connection pooling (default: disabled)')
    parser.add_argument('--no-connection-pooling', action='store_true',
                        help='Disable connection pooling (default behavior)')
    args = parser.parse_args()

    # Determine connection pool setting
    if args.connection_pooling and args.no_connection_pooling:
        parser.error("Cannot specify both --connection-pooling and --no-connection-pooling")

    connection_pool = args.connection_pooling

    print(f"Starting benchmark server on {URL} with {NUM_WORKERS} workers...")
    print(f"Connection Pool: {'Enabled' if connection_pool else 'Disabled'}")

    # Start server
    server_processes = start_server()

    # Wait for server to be ready
    time.sleep(2)

    try:
        # Use uvloop for better performance
        asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

        # Run benchmarks
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        results = loop.run_until_complete(run_benchmarks(connection_pool))

        # Generate report
        generate_report(results, connection_pool)

    finally:
        # Stop server
        print("\nStopping server...")
        stop_server(server_processes)


if __name__ == "__main__":
    main()
