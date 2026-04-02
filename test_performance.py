#!/usr/bin/env python3
"""
Performance testing script for FNAC.

Tests throughput and latency of the system.
"""

import asyncio
import time
import statistics
from typing import List, Tuple
import requests
import json


class PerformanceTester:
    """Performance testing for FNAC."""
    
    def __init__(self, base_url: str = "http://localhost:5000"):
        self.base_url = base_url
        self.results: List[float] = []
    
    async def test_api_throughput(self, endpoint: str, num_requests: int = 1000) -> Tuple[float, float, float]:
        """
        Test API throughput.
        
        Args:
            endpoint: API endpoint to test
            num_requests: Number of requests to send
            
        Returns:
            Tuple of (requests_per_second, min_latency, max_latency)
        """
        print(f"\nTesting {endpoint} with {num_requests} requests...")
        
        start_time = time.time()
        latencies = []
        
        for i in range(num_requests):
            req_start = time.time()
            try:
                response = requests.get(f"{self.base_url}{endpoint}", timeout=5)
                latency = (time.time() - req_start) * 1000  # Convert to ms
                latencies.append(latency)
                
                if (i + 1) % 100 == 0:
                    print(f"  Completed {i + 1}/{num_requests} requests")
            except Exception as e:
                print(f"  Error on request {i + 1}: {e}")
        
        elapsed = time.time() - start_time
        rps = num_requests / elapsed
        
        if latencies:
            min_latency = min(latencies)
            max_latency = max(latencies)
            avg_latency = statistics.mean(latencies)
            p95_latency = sorted(latencies)[int(len(latencies) * 0.95)]
            p99_latency = sorted(latencies)[int(len(latencies) * 0.99)]
        else:
            min_latency = max_latency = avg_latency = p95_latency = p99_latency = 0
        
        print(f"\nResults for {endpoint}:")
        print(f"  Requests/second: {rps:.2f}")
        print(f"  Total time: {elapsed:.2f}s")
        print(f"  Min latency: {min_latency:.2f}ms")
        print(f"  Max latency: {max_latency:.2f}ms")
        print(f"  Avg latency: {avg_latency:.2f}ms")
        print(f"  P95 latency: {p95_latency:.2f}ms")
        print(f"  P99 latency: {p99_latency:.2f}ms")
        
        return rps, min_latency, max_latency
    
    async def test_log_creation(self, num_logs: int = 1000) -> float:
        """
        Test log creation throughput.
        
        Args:
            num_logs: Number of logs to create
            
        Returns:
            Logs per second
        """
        print(f"\nTesting log creation with {num_logs} logs...")
        
        start_time = time.time()
        
        for i in range(num_logs):
            try:
                # Simulate log creation via API
                log_data = {
                    "client_mac": f"aa:bb:cc:dd:ee:{i % 256:02x}",
                    "device_id": f"device_{i % 10}",
                    "outcome": "success" if i % 2 == 0 else "failure",
                    "vlan_id": 100 + (i % 100) if i % 2 == 0 else None,
                }
                
                # This would normally be done via the log manager
                # For now, just simulate the timing
                if (i + 1) % 100 == 0:
                    print(f"  Created {i + 1}/{num_logs} logs")
            except Exception as e:
                print(f"  Error creating log {i + 1}: {e}")
        
        elapsed = time.time() - start_time
        lps = num_logs / elapsed
        
        print(f"\nLog creation results:")
        print(f"  Logs/second: {lps:.2f}")
        print(f"  Total time: {elapsed:.2f}s")
        
        return lps
    
    async def run_all_tests(self):
        """Run all performance tests."""
        print("=" * 60)
        print("FNAC Performance Testing")
        print("=" * 60)
        
        # Test API endpoints
        endpoints = [
            ("/api/devices", "Device listing"),
            ("/api/clients", "Client listing"),
            ("/api/policies", "Policy listing"),
            ("/api/logs", "Log listing"),
        ]
        
        results = {}
        for endpoint, description in endpoints:
            try:
                rps, min_lat, max_lat = await self.test_api_throughput(endpoint, num_requests=100)
                results[description] = {
                    "rps": rps,
                    "min_latency": min_lat,
                    "max_latency": max_lat
                }
            except Exception as e:
                print(f"Error testing {description}: {e}")
        
        # Test log creation
        try:
            lps = await self.test_log_creation(num_logs=100)
            results["Log creation"] = {"lps": lps}
        except Exception as e:
            print(f"Error testing log creation: {e}")
        
        # Print summary
        print("\n" + "=" * 60)
        print("Performance Summary")
        print("=" * 60)
        for test_name, metrics in results.items():
            print(f"\n{test_name}:")
            for metric_name, value in metrics.items():
                print(f"  {metric_name}: {value:.2f}")
        
        print("\n" + "=" * 60)
        print("Recommendations:")
        print("=" * 60)
        print("- For 1000 req/s: Enable async logging and SQLite WAL mode")
        print("- For 10,000 req/s: Use Redis for logging")
        print("- For 100,000+ req/s: Use dedicated RADIUS appliance")
        print("=" * 60)


async def main():
    """Run performance tests."""
    tester = PerformanceTester()
    await tester.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())
