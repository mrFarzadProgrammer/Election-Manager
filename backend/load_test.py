from __future__ import annotations

import argparse
import asyncio
import math
import statistics
import time
from dataclasses import dataclass

import httpx


@dataclass
class Result:
    status_code: int | None
    latency_s: float
    error: str | None = None


def _percentile(sorted_values: list[float], p: float) -> float:
    if not sorted_values:
        return float("nan")
    if p <= 0:
        return sorted_values[0]
    if p >= 100:
        return sorted_values[-1]

    k = (len(sorted_values) - 1) * (p / 100.0)
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return sorted_values[int(k)]
    d0 = sorted_values[f] * (c - k)
    d1 = sorted_values[c] * (k - f)
    return d0 + d1


async def _worker(
    client: httpx.AsyncClient,
    sem: asyncio.Semaphore,
    method: str,
    url: str,
    headers: dict[str, str],
    body_text: str | None,
    timeout_s: float,
) -> Result:
    async with sem:
        t0 = time.perf_counter()
        try:
            resp = await client.request(
                method,
                url,
                headers=headers,
                content=body_text.encode("utf-8") if body_text is not None else None,
                timeout=timeout_s,
            )
            dt = time.perf_counter() - t0
            return Result(status_code=int(resp.status_code), latency_s=dt)
        except Exception as e:
            dt = time.perf_counter() - t0
            return Result(status_code=None, latency_s=dt, error=f"{type(e).__name__}: {e}")


async def run(
    *,
    url: str,
    total: int,
    concurrency: int,
    method: str,
    headers: dict[str, str],
    body_text: str | None,
    timeout_s: float,
) -> list[Result]:
    limits = httpx.Limits(max_connections=max(concurrency, 1), max_keepalive_connections=max(concurrency, 1))
    async with httpx.AsyncClient(limits=limits, http2=False, trust_env=False) as client:
        sem = asyncio.Semaphore(concurrency)
        tasks = [
            asyncio.create_task(_worker(client, sem, method, url, headers, body_text, timeout_s))
            for _ in range(total)
        ]
        return await asyncio.gather(*tasks)


def main() -> int:
    parser = argparse.ArgumentParser(description="Simple async HTTP load test")
    parser.add_argument("--url", required=True)
    parser.add_argument("--total", type=int, default=2000)
    parser.add_argument("--concurrency", type=int, default=200)
    parser.add_argument("--method", default="GET")
    parser.add_argument("--header", action="append", default=[], help="Header like 'Name: value'")
    parser.add_argument("--body", default=None, help="Raw request body (utf-8)")
    parser.add_argument("--timeout", type=float, default=10.0)

    args = parser.parse_args()

    url: str = args.url
    total = max(1, int(args.total))
    concurrency = max(1, int(args.concurrency))
    method = str(args.method).upper().strip() or "GET"

    headers: dict[str, str] = {}
    for h in args.header:
        if not isinstance(h, str) or ":" not in h:
            continue
        k, v = h.split(":", 1)
        k = k.strip()
        v = v.strip()
        if k:
            headers[k] = v

    body_text = args.body
    timeout_s = float(args.timeout)

    print(f"URL: {url}")
    print(f"Method: {method}")
    print(f"Total: {total}  Concurrency: {concurrency}  Timeout: {timeout_s}s")

    t0 = time.perf_counter()
    results = asyncio.run(
        run(
            url=url,
            total=total,
            concurrency=concurrency,
            method=method,
            headers=headers,
            body_text=body_text,
            timeout_s=timeout_s,
        )
    )
    elapsed = time.perf_counter() - t0

    latencies = [r.latency_s for r in results]
    latencies_sorted = sorted(latencies)

    by_status: dict[str, int] = {}
    errors = 0
    for r in results:
        if r.error is not None:
            errors += 1
        key = str(r.status_code) if r.status_code is not None else "ERR"
        by_status[key] = by_status.get(key, 0) + 1

    ok = sum(v for k, v in by_status.items() if k.startswith("2"))
    rps = total / elapsed if elapsed > 0 else float("inf")

    print("\n--- Summary ---")
    print(f"Elapsed: {elapsed:.2f}s")
    print(f"RPS: {rps:.1f}")
    print(f"2xx: {ok}/{total} ({(ok/total*100.0):.2f}%)")
    print(f"Errors: {errors}")
    print(f"Status counts: {dict(sorted(by_status.items(), key=lambda kv: kv[0]))}")

    print("\n--- Latency (ms) ---")
    def ms(x: float) -> float:
        return x * 1000.0

    p50 = _percentile(latencies_sorted, 50)
    p90 = _percentile(latencies_sorted, 90)
    p95 = _percentile(latencies_sorted, 95)
    p99 = _percentile(latencies_sorted, 99)

    print(f"min: {ms(latencies_sorted[0]):.2f}")
    print(f"p50: {ms(p50):.2f}")
    print(f"p90: {ms(p90):.2f}")
    print(f"p95: {ms(p95):.2f}")
    print(f"p99: {ms(p99):.2f}")
    print(f"max: {ms(latencies_sorted[-1]):.2f}")
    print(f"mean: {ms(statistics.mean(latencies)):.2f}")

    if errors:
        sample = [r.error for r in results if r.error][:5]
        print("\n--- Error samples ---")
        for e in sample:
            print(e)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
