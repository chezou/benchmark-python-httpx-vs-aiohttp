#!/usr/bin/env python3
"""Benchmark comparing httpx and aiohttp HTTP client performance."""

import argparse
import asyncio
import multiprocessing
import statistics
import sys
import time
from typing import Any

import aiohttp
import httpx
from aiohttp import web

# Configuration
PORT = 8888
URL = f"http://localhost:{PORT}/"
NUM_WORKERS = multiprocessing.cpu_count()
NUM_SERIAL_REQUESTS = 1000
NUM_PARALLEL_BATCHES = 10
BATCH_SIZE = 100
WARMUP_REQUESTS = 100


# ============================================================================
# Server Implementation
# ============================================================================

async def handle_request(request):
    """Simple test server handler."""
    return web.Response(text="Hello, world!\n")


def run_server_worker():
    """Run a single server worker process."""
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
    """Start multi-process async server."""
    processes = []
    for _ in range(NUM_WORKERS):
        p = multiprocessing.Process(target=run_server_worker)
        p.start()
        processes.append(p)
    return processes


def stop_server(processes):
    """Stop all server processes."""
    for p in processes:
        p.terminate()
    for p in processes:
        p.join(timeout=2)
        if p.is_alive():
            p.kill()
            p.join()


# ============================================================================
# Benchmark Functions
# ============================================================================

async def benchmark_httpx_serial(n: int, connection_pool: bool = False) -> list[float]:
    """Benchmark httpx with serial requests.

    Args:
        n: Number of requests to make
        connection_pool: Whether to use connection pooling

    Returns:
        List of latencies in seconds
    """
    latencies = []
    limits = (
        httpx.Limits()
        if connection_pool
        else httpx.Limits(max_keepalive_connections=0, keepalive_expiry=0)
    )

    async with httpx.AsyncClient(limits=limits) as client:
        for _ in range(n):
            start = time.perf_counter()
            response = await client.get(URL)
            assert response.status_code == 200
            latencies.append(time.perf_counter() - start)
    return latencies


async def benchmark_aiohttp_serial(n: int, connection_pool: bool = False) -> list[float]:
    """Benchmark aiohttp with serial requests.

    Args:
        n: Number of requests to make
        connection_pool: Whether to use connection pooling

    Returns:
        List of latencies in seconds
    """
    latencies = []
    connector = aiohttp.TCPConnector(force_close=not connection_pool)

    async with aiohttp.ClientSession(connector=connector) as session:
        for _ in range(n):
            start = time.perf_counter()
            async with session.get(URL) as response:
                assert response.status == 200
                await response.text()
            latencies.append(time.perf_counter() - start)
    return latencies


async def benchmark_httpx_parallel(batch_size: int, num_batches: int, connection_pool: bool = False) -> list[float]:
    """Benchmark httpx with parallel requests.

    Args:
        batch_size: Number of parallel requests per batch
        num_batches: Number of batches to run
        connection_pool: Whether to use connection pooling

    Returns:
        List of batch completion times in seconds
    """
    latencies = []
    limits = (
        httpx.Limits()
        if connection_pool
        else httpx.Limits(max_keepalive_connections=0, keepalive_expiry=0)
    )

    async with httpx.AsyncClient(limits=limits) as client:
        for _ in range(num_batches):
            batch_start = time.perf_counter()
            tasks = [client.get(URL) for _ in range(batch_size)]
            responses = await asyncio.gather(*tasks)

            for response in responses:
                assert response.status_code == 200

            latencies.append(time.perf_counter() - batch_start)
    return latencies


async def benchmark_aiohttp_parallel(batch_size: int, num_batches: int, connection_pool: bool = False) -> list[float]:
    """Benchmark aiohttp with parallel requests.

    Args:
        batch_size: Number of parallel requests per batch
        num_batches: Number of batches to run
        connection_pool: Whether to use connection pooling

    Returns:
        List of batch completion times in seconds
    """
    latencies = []
    connector = aiohttp.TCPConnector(force_close=not connection_pool)

    async with aiohttp.ClientSession(connector=connector) as session:
        for _ in range(num_batches):
            batch_start = time.perf_counter()

            async def make_request():
                async with session.get(URL) as response:
                    assert response.status == 200
                    return await response.text()

            tasks = [make_request() for _ in range(batch_size)]
            await asyncio.gather(*tasks)
            latencies.append(time.perf_counter() - batch_start)
    return latencies


# ============================================================================
# Utility Functions
# ============================================================================

def calculate_stats(latencies: list[float]) -> dict[str, float]:
    """Calculate statistics from latencies.

    Args:
        latencies: List of latencies in seconds

    Returns:
        Dictionary of statistics in milliseconds
    """
    sorted_latencies = sorted(latencies)
    return {
        "min": min(latencies) * 1000,
        "max": max(latencies) * 1000,
        "mean": statistics.mean(latencies) * 1000,
        "median": statistics.median(latencies) * 1000,
        "stdev": statistics.stdev(latencies) * 1000 if len(latencies) > 1 else 0,
        "p95": sorted_latencies[int(len(latencies) * 0.95)] * 1000,
        "p99": sorted_latencies[int(len(latencies) * 0.99)] * 1000,
    }


async def warmup(connection_pool: bool = False):
    """Warmup the server with initial requests."""
    print("Warming up server...")

    # Warmup with httpx
    limits = (
        httpx.Limits()
        if connection_pool
        else httpx.Limits(max_keepalive_connections=0, keepalive_expiry=0)
    )
    async with httpx.AsyncClient(limits=limits) as client:
        for _ in range(WARMUP_REQUESTS):
            await client.get(URL, timeout=1.0)

    # Warmup with aiohttp
    connector = aiohttp.TCPConnector(force_close=not connection_pool)
    async with aiohttp.ClientSession(connector=connector) as session:
        for _ in range(WARMUP_REQUESTS):
            await session.get(URL, timeout=1.0)


async def run_benchmarks(connection_pool: bool = False) -> dict[str, Any]:
    """Run all benchmarks and collect results."""
    results = {}

    await warmup(connection_pool)

    # Serial benchmarks
    print(f"\nRunning serial benchmarks ({NUM_SERIAL_REQUESTS} requests each)...")

    print("  Testing httpx (serial)...")
    httpx_serial = await benchmark_httpx_serial(NUM_SERIAL_REQUESTS, connection_pool)
    results["httpx_serial"] = calculate_stats(httpx_serial)

    print("  Testing aiohttp (serial)...")
    aiohttp_serial = await benchmark_aiohttp_serial(
        NUM_SERIAL_REQUESTS, connection_pool
    )
    results["aiohttp_serial"] = calculate_stats(aiohttp_serial)

    # Parallel benchmarks
    print(
        f"\nRunning parallel benchmarks ({BATCH_SIZE} requests x {NUM_PARALLEL_BATCHES} batches)..."
    )

    print("  Testing httpx (parallel)...")
    httpx_parallel = await benchmark_httpx_parallel(
        BATCH_SIZE, NUM_PARALLEL_BATCHES, connection_pool
    )
    results["httpx_parallel_batch"] = calculate_stats(httpx_parallel)

    print("  Testing aiohttp (parallel)...")
    aiohttp_parallel = await benchmark_aiohttp_parallel(
        BATCH_SIZE, NUM_PARALLEL_BATCHES, connection_pool
    )
    results["aiohttp_parallel_batch"] = calculate_stats(aiohttp_parallel)

    # Calculate per-request stats for parallel
    results["httpx_parallel_per_request"] = calculate_stats(
        [t / BATCH_SIZE for t in httpx_parallel]
    )
    results["aiohttp_parallel_per_request"] = calculate_stats(
        [t / BATCH_SIZE for t in aiohttp_parallel]
    )

    return results


# ============================================================================
# Report Generation
# ============================================================================


def generate_report(results_no_pool: dict[str, Any], results_with_pool: dict[str, Any], update_readme: bool = False):
    """Generate markdown report comparing both configurations."""
    report = f"""# HTTP Client Benchmark: httpx vs aiohttp

## Environment
- Python: {sys.version.split()[0]}
- httpx: {httpx.__version__}
- aiohttp: {aiohttp.__version__}
- Server: Multi-process async server ({NUM_WORKERS} workers)
- URL: {URL}

## Results

### Serial Requests ({NUM_SERIAL_REQUESTS} requests, one at a time)

#### Without Connection Pooling

| Metric | httpx | aiohttp |
|--------|-------|---------|
| Min (ms) | {results_no_pool['httpx_serial']['min']:.3f} | {results_no_pool['aiohttp_serial']['min']:.3f} |
| Max (ms) | {results_no_pool['httpx_serial']['max']:.3f} | {results_no_pool['aiohttp_serial']['max']:.3f} |
| Mean (ms) | {results_no_pool['httpx_serial']['mean']:.3f} | {results_no_pool['aiohttp_serial']['mean']:.3f} |
| Median (ms) | {results_no_pool['httpx_serial']['median']:.3f} | {results_no_pool['aiohttp_serial']['median']:.3f} |
| Stdev (ms) | {results_no_pool['httpx_serial']['stdev']:.3f} | {results_no_pool['aiohttp_serial']['stdev']:.3f} |
| P95 (ms) | {results_no_pool['httpx_serial']['p95']:.3f} | {results_no_pool['aiohttp_serial']['p95']:.3f} |
| P99 (ms) | {results_no_pool['httpx_serial']['p99']:.3f} | {results_no_pool['aiohttp_serial']['p99']:.3f} |

#### With Connection Pooling

| Metric | httpx | aiohttp |
|--------|-------|---------|
| Min (ms) | {results_with_pool['httpx_serial']['min']:.3f} | {results_with_pool['aiohttp_serial']['min']:.3f} |
| Max (ms) | {results_with_pool['httpx_serial']['max']:.3f} | {results_with_pool['aiohttp_serial']['max']:.3f} |
| Mean (ms) | {results_with_pool['httpx_serial']['mean']:.3f} | {results_with_pool['aiohttp_serial']['mean']:.3f} |
| Median (ms) | {results_with_pool['httpx_serial']['median']:.3f} | {results_with_pool['aiohttp_serial']['median']:.3f} |
| Stdev (ms) | {results_with_pool['httpx_serial']['stdev']:.3f} | {results_with_pool['aiohttp_serial']['stdev']:.3f} |
| P95 (ms) | {results_with_pool['httpx_serial']['p95']:.3f} | {results_with_pool['aiohttp_serial']['p95']:.3f} |
| P99 (ms) | {results_with_pool['httpx_serial']['p99']:.3f} | {results_with_pool['aiohttp_serial']['p99']:.3f} |

### Parallel Requests ({BATCH_SIZE} requests x {NUM_PARALLEL_BATCHES} batches)

#### Without Connection Pooling - Batch Timing

| Metric | httpx | aiohttp |
|--------|-------|---------|
| Min (ms) | {results_no_pool['httpx_parallel_batch']['min']:.3f} | {results_no_pool['aiohttp_parallel_batch']['min']:.3f} |
| Max (ms) | {results_no_pool['httpx_parallel_batch']['max']:.3f} | {results_no_pool['aiohttp_parallel_batch']['max']:.3f} |
| Mean (ms) | {results_no_pool['httpx_parallel_batch']['mean']:.3f} | {results_no_pool['aiohttp_parallel_batch']['mean']:.3f} |
| Median (ms) | {results_no_pool['httpx_parallel_batch']['median']:.3f} | {results_no_pool['aiohttp_parallel_batch']['median']:.3f} |

#### With Connection Pooling - Batch Timing

| Metric | httpx | aiohttp |
|--------|-------|---------|
| Min (ms) | {results_with_pool['httpx_parallel_batch']['min']:.3f} | {results_with_pool['aiohttp_parallel_batch']['min']:.3f} |
| Max (ms) | {results_with_pool['httpx_parallel_batch']['max']:.3f} | {results_with_pool['aiohttp_parallel_batch']['max']:.3f} |
| Mean (ms) | {results_with_pool['httpx_parallel_batch']['mean']:.3f} | {results_with_pool['aiohttp_parallel_batch']['mean']:.3f} |
| Median (ms) | {results_with_pool['httpx_parallel_batch']['median']:.3f} | {results_with_pool['aiohttp_parallel_batch']['median']:.3f} |

## Summary

### Impact of Connection Pooling

**httpx:**
- Serial: {((results_no_pool['httpx_serial']['mean'] - results_with_pool['httpx_serial']['mean']) / results_no_pool['httpx_serial']['mean'] * 100):.1f}% {"faster" if results_with_pool['httpx_serial']['mean'] < results_no_pool['httpx_serial']['mean'] else "slower"} with pooling
- Parallel: {((results_no_pool['httpx_parallel_batch']['mean'] - results_with_pool['httpx_parallel_batch']['mean']) / results_no_pool['httpx_parallel_batch']['mean'] * 100):.1f}% {"faster" if results_with_pool['httpx_parallel_batch']['mean'] < results_no_pool['httpx_parallel_batch']['mean'] else "slower"} with pooling

**aiohttp:**
- Serial: {((results_no_pool['aiohttp_serial']['mean'] - results_with_pool['aiohttp_serial']['mean']) / results_no_pool['aiohttp_serial']['mean'] * 100):.1f}% {"faster" if results_with_pool['aiohttp_serial']['mean'] < results_no_pool['aiohttp_serial']['mean'] else "slower"} with pooling
- Parallel: {((results_no_pool['aiohttp_parallel_batch']['mean'] - results_with_pool['aiohttp_parallel_batch']['mean']) / results_no_pool['aiohttp_parallel_batch']['mean'] * 100):.1f}% {"faster" if results_with_pool['aiohttp_parallel_batch']['mean'] < results_no_pool['aiohttp_parallel_batch']['mean'] else "slower"} with pooling

### Library Comparison

**Without Connection Pooling:**
- Serial: {"aiohttp" if results_no_pool['aiohttp_serial']['mean'] < results_no_pool['httpx_serial']['mean'] else "httpx"} is {abs(results_no_pool['httpx_serial']['mean'] - results_no_pool['aiohttp_serial']['mean']) / min(results_no_pool['httpx_serial']['mean'], results_no_pool['aiohttp_serial']['mean']) * 100:.1f}% faster
- Parallel: {"aiohttp" if results_no_pool['aiohttp_parallel_batch']['mean'] < results_no_pool['httpx_parallel_batch']['mean'] else "httpx"} is {abs(results_no_pool['httpx_parallel_batch']['mean'] - results_no_pool['aiohttp_parallel_batch']['mean']) / min(results_no_pool['httpx_parallel_batch']['mean'], results_no_pool['aiohttp_parallel_batch']['mean']) * 100:.1f}% faster

**With Connection Pooling:**
- Serial: {"aiohttp" if results_with_pool['aiohttp_serial']['mean'] < results_with_pool['httpx_serial']['mean'] else "httpx"} is {abs(results_with_pool['httpx_serial']['mean'] - results_with_pool['aiohttp_serial']['mean']) / min(results_with_pool['httpx_serial']['mean'], results_with_pool['aiohttp_serial']['mean']) * 100:.1f}% faster
- Parallel: {"aiohttp" if results_with_pool['aiohttp_parallel_batch']['mean'] < results_with_pool['httpx_parallel_batch']['mean'] else "httpx"} is {abs(results_with_pool['httpx_parallel_batch']['mean'] - results_with_pool['aiohttp_parallel_batch']['mean']) / min(results_with_pool['httpx_parallel_batch']['mean'], results_with_pool['aiohttp_parallel_batch']['mean']) * 100:.1f}% faster
"""

    if update_readme:
        with open('README.md', 'w') as f:
            f.write(report)
        print("\nREADME.md has been updated with the benchmark results.")

    print("\n" + "="*60)
    print("BENCHMARK COMPLETE")
    print("="*60)
    print(report)


# ============================================================================
# Main Entry Point
# ============================================================================

def main():
    """Main entry point."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Benchmark httpx vs aiohttp HTTP clients')
    parser.add_argument('--update-readme', action='store_true',
                        help='Run benchmark and update README.md with results')
    args = parser.parse_args()

    print(f"Starting benchmark server on {URL} with {NUM_WORKERS} workers...")

    # Start server
    server_processes = start_server()

    # Wait for server to be ready
    print("Waiting for server to be ready...")
    max_retries = 30
    for i in range(max_retries):
        try:
            import urllib.request

            with urllib.request.urlopen(URL, timeout=1) as response:
                if response.status == 200:
                    print("Server is ready!")
                    break
        except Exception:
            if i == max_retries - 1:
                print("Server failed to start")
                stop_server(server_processes)
                sys.exit(1)
            time.sleep(0.1)

    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        print("\nRunning benchmarks with both configurations...")

        print("\n" + "=" * 60)
        print("ROUND 1: WITHOUT CONNECTION POOLING")
        print("=" * 60)
        results_no_pool = loop.run_until_complete(run_benchmarks(False))

        print("\n" + "=" * 60)
        print("ROUND 2: WITH CONNECTION POOLING")
        print("=" * 60)
        results_with_pool = loop.run_until_complete(run_benchmarks(True))

        # Generate comparison report
        generate_report(results_no_pool, results_with_pool, update_readme=args.update_readme)

    finally:
        # Stop server
        print("\nStopping server...")
        stop_server(server_processes)


if __name__ == "__main__":
    main()
