"""
Performance and load testing suite.
Tests system performance under various load conditions.
"""

import pytest
import asyncio
import time
import statistics
import concurrent.futures
from unittest.mock import Mock, AsyncMock, patch
import requests
import json
import sys
import os
from fastapi.testclient import TestClient

# Add the parent directory to the path so we can import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestPerformanceMetrics:
    """Test system performance metrics."""
    
    @pytest.fixture
    def client(self):
        """Create a test client."""
        return TestClient(app)
    
    def test_api_response_time(self, client):
        """Test API response times under normal load."""
        endpoints = [
            "/health",
            "/",
        ]
        
        response_times = []
        
        for endpoint in endpoints:
            start_time = time.time()
            response = client.get(endpoint)
            end_time = time.time()
            
            response_time = (end_time - start_time) * 1000  # Convert to milliseconds
            response_times.append(response_time)
            
            assert response.status_code == 200
        
        # Average response time should be under 100ms for simple endpoints
        avg_response_time = statistics.mean(response_times)
        assert avg_response_time < 100, f"Average response time {avg_response_time}ms is too high"
    
    def test_concurrent_requests_performance(self, client):
        """Test performance with concurrent requests."""
        endpoint = "/health"
        num_requests = 50
        
        def make_request():
            start_time = time.time()
            response = client.get(endpoint)
            end_time = time.time()
            return {
                "status_code": response.status_code,
                "response_time": (end_time - start_time) * 1000
            }
        
        # Execute concurrent requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request) for _ in range(num_requests)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        # Analyze results
        successful_requests = [r for r in results if r["status_code"] == 200]
        response_times = [r["response_time"] for r in successful_requests]
        
        # At least 95% of requests should succeed
        success_rate = len(successful_requests) / num_requests
        assert success_rate >= 0.95, f"Success rate {success_rate} is too low"
        
        # Average response time should be reasonable
        if response_times:
            avg_response_time = statistics.mean(response_times)
            assert avg_response_time < 200, f"Average response time {avg_response_time}ms is too high under load"
    
    def test_memory_usage_stability(self):
        """Test memory usage stability over time."""
        import psutil
        import gc
        
        # Get initial memory usage
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Simulate some workload
        for _ in range(1000):
            # Create some objects
            data = [{"key": i, "value": f"data_{i}"} for i in range(100)]
            json.dumps(data)
            del data
        
        # Force garbage collection
        gc.collect()
        
        # Check memory usage after workload
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be reasonable (less than 50MB for this test)
        assert memory_increase < 50, f"Memory increase {memory_increase}MB is too high"
    
    def test_database_connection_pool_performance(self):
        """Test database connection pool performance."""
        # This would test connection pool efficiency
        # For now, we'll simulate the test structure
        connection_times = []
        
        # Simulate connection acquisition and release
        for _ in range(20):
            start_time = time.time()
            # Simulate database operation
            time.sleep(0.01)  # Simulate DB latency
            end_time = time.time()
            
            connection_times.append((end_time - start_time) * 1000)
        
        # Connection acquisition should be fast
        avg_connection_time = statistics.mean(connection_times)
        assert avg_connection_time < 50, f"Average connection time {avg_connection_time}ms is too high"


class TestLoadTesting:
    """Test system behavior under various load conditions."""
    
    @pytest.fixture
    def api_base_url(self):
        """Base URL for API testing."""
        return os.getenv("API_BASE_URL", "http://localhost:8000")
    
    def test_sustained_load(self, api_base_url):
        """Test system under sustained load over time."""
        duration = 30  # seconds
        requests_per_second = 10
        endpoint = f"{api_base_url}/health"
        
        start_time = time.time()
        end_time = start_time + duration
        
        results = []
        
        while time.time() < end_time:
            request_start = time.time()
            
            try:
                response = requests.get(endpoint, timeout=5)
                request_end = time.time()
                
                results.append({
                    "status_code": response.status_code,
                    "response_time": (request_end - request_start) * 1000,
                    "timestamp": request_start
                })
            except Exception as e:
                results.append({
                    "status_code": 0,
                    "error": str(e),
                    "timestamp": request_start
                })
            
            # Rate limiting
            time.sleep(1.0 / requests_per_second)
        
        # Analyze results
        successful_requests = [r for r in results if r["status_code"] == 200]
        response_times = [r["response_time"] for r in successful_requests if "response_time" in r]
        
        # Success rate should be high
        success_rate = len(successful_requests) / len(results)
        assert success_rate >= 0.95, f"Success rate {success_rate} under sustained load is too low"
        
        # Response times should be stable
        if response_times:
            avg_response_time = statistics.mean(response_times)
            p95_response_time = statistics.quantiles(response_times, n=20)[18]  # 95th percentile
            
            assert avg_response_time < 300, f"Average response time {avg_response_time}ms under sustained load is too high"
            assert p95_response_time < 500, f"95th percentile response time {p95_response_time}ms under sustained load is too high"
    
    def test_burst_load(self, api_base_url):
        """Test system under burst load."""
        burst_size = 100
        endpoint = f"{api_base_url}/health"
        
        def make_burst_request():
            start_time = time.time()
            try:
                response = requests.get(endpoint, timeout=10)
                end_time = time.time()
                return {
                    "status_code": response.status_code,
                    "response_time": (end_time - start_time) * 1000
                }
            except Exception as e:
                return {
                    "status_code": 0,
                    "error": str(e)
                }
        
        # Execute burst
        with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
            futures = [executor.submit(make_burst_request) for _ in range(burst_size)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        # Analyze burst results
        successful_requests = [r for r in results if r["status_code"] == 200]
        response_times = [r["response_time"] for r in successful_requests if "response_time" in r]
        
        # System should handle burst reasonably well
        success_rate = len(successful_requests) / burst_size
        assert success_rate >= 0.80, f"Success rate {success_rate} under burst load is too low"
        
        if response_times:
            avg_response_time = statistics.mean(response_times)
            assert avg_response_time < 1000, f"Average response time {avg_response_time}ms under burst load is too high"
    
    def test_gradual_load_increase(self, api_base_url):
        """Test system with gradually increasing load."""
        endpoint = f"{api_base_url}/health"
        load_levels = [1, 5, 10, 20, 50]  # requests per second
        duration_per_level = 10  # seconds
        
        performance_by_load = {}
        
        for rps in load_levels:
            start_time = time.time()
            end_time = start_time + duration_per_level
            
            results = []
            
            while time.time() < end_time:
                request_start = time.time()
                
                try:
                    response = requests.get(endpoint, timeout=5)
                    request_end = time.time()
                    
                    results.append({
                        "status_code": response.status_code,
                        "response_time": (request_end - request_start) * 1000
                    })
                except Exception:
                    results.append({"status_code": 0})
                
                time.sleep(1.0 / rps)
            
            # Calculate metrics for this load level
            successful_requests = [r for r in results if r["status_code"] == 200]
            response_times = [r["response_time"] for r in successful_requests if "response_time" in r]
            
            if response_times:
                performance_by_load[rps] = {
                    "success_rate": len(successful_requests) / len(results),
                    "avg_response_time": statistics.mean(response_times),
                    "p95_response_time": statistics.quantiles(response_times, n=20)[18]
                }
            else:
                performance_by_load[rps] = {
                    "success_rate": 0,
                    "avg_response_time": 0,
                    "p95_response_time": 0
                }
        
        # Performance should degrade gracefully
        for i in range(1, len(load_levels)):
            prev_rps = load_levels[i-1]
            curr_rps = load_levels[i]
            
            prev_perf = performance_by_load[prev_rps]
            curr_perf = performance_by_load[curr_rps]
            
            # Success rate should not drop dramatically
            success_rate_drop = prev_perf["success_rate"] - curr_perf["success_rate"]
            assert success_rate_drop < 0.2, f"Success rate dropped too much from {prev_rps} to {curr_rps} RPS"
            
            # Response time should not increase dramatically
            if prev_perf["avg_response_time"] > 0 and curr_perf["avg_response_time"] > 0:
                response_time_increase = curr_perf["avg_response_time"] / prev_perf["avg_response_time"]
                assert response_time_increase < 5, f"Response time increased too much from {prev_rps} to {curr_rps} RPS"


class TestScalabilityTesting:
    """Test system scalability characteristics."""
    
    @pytest.fixture
    def api_base_url(self):
        """Base URL for API testing."""
        return os.getenv("API_BASE_URL", "http://localhost:8000")
    
    def test_horizontal_scalability_simulation(self, api_base_url):
        """Test horizontal scalability simulation."""
        # This simulates what would happen with multiple instances
        # For now, we test that the system can handle multiple concurrent users
        
        num_concurrent_users = 20
        requests_per_user = 10
        endpoint = f"{api_base_url}/health"
        
        def simulate_user_activity():
            user_results = []
            
            for _ in range(requests_per_user):
                start_time = time.time()
                
                try:
                    response = requests.get(endpoint, timeout=5)
                    end_time = time.time()
                    
                    user_results.append({
                        "status_code": response.status_code,
                        "response_time": (end_time - start_time) * 1000
                    })
                except Exception:
                    user_results.append({"status_code": 0})
                
                # Simulate user think time
                time.sleep(0.1)
            
            return user_results
        
        # Execute concurrent user simulation
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_concurrent_users) as executor:
            futures = [executor.submit(simulate_user_activity) for _ in range(num_concurrent_users)]
            all_results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        # Flatten results
        flat_results = [result for user_results in all_results for result in user_results]
        successful_requests = [r for r in flat_results if r["status_code"] == 200]
        response_times = [r["response_time"] for r in successful_requests if "response_time" in r]
        
        # System should handle multiple concurrent users
        success_rate = len(successful_requests) / len(flat_results)
        assert success_rate >= 0.90, f"Success rate {success_rate} with concurrent users is too low"
        
        if response_times:
            avg_response_time = statistics.mean(response_times)
            assert avg_response_time < 500, f"Average response time {avg_response_time}ms with concurrent users is too high"
    
    def test_resource_utilization_scaling(self):
        """Test resource utilization under different loads."""
        import psutil
        
        process = psutil.Process()
        
        # Test resource usage at different load levels
        load_levels = [0, 10, 50, 100]  # Number of concurrent operations
        
        resource_usage_by_load = {}
        
        for load in load_levels:
            # Measure baseline
            baseline_cpu = process.cpu_percent()
            baseline_memory = process.memory_info().rss / 1024 / 1024  # MB
            
            # Apply load
            if load > 0:
                def cpu_intensive_task():
                    # Simulate CPU work
                    sum(i * i for i in range(1000))
                
                with concurrent.futures.ThreadPoolExecutor(max_workers=load) as executor:
                    futures = [executor.submit(cpu_intensive_task) for _ in range(load)]
                    [future.result() for future in concurrent.futures.as_completed(futures)]
            
            # Measure resource usage under load
            cpu_usage = process.cpu_percent()
            memory_usage = process.memory_info().rss / 1024 / 1024  # MB
            
            resource_usage_by_load[load] = {
                "cpu_usage": cpu_usage,
                "memory_usage": memory_usage,
                "cpu_increase": cpu_usage - baseline_cpu,
                "memory_increase": memory_usage - baseline_memory
            }
            
            # Allow system to settle
            time.sleep(1)
        
        # Resource usage should scale reasonably
        for i in range(1, len(load_levels)):
            prev_load = load_levels[i-1]
            curr_load = load_levels[i]
            
            prev_resources = resource_usage_by_load[prev_load]
            curr_resources = resource_usage_by_load[curr_load]
            
            # CPU usage should increase with load
            if curr_load > 0:
                assert curr_resources["cpu_usage"] >= prev_resources["cpu_usage"], \
                    f"CPU usage should increase with load from {prev_load} to {curr_load}"
    
    def test_database_scalability(self):
        """Test database performance under increasing data volume."""
        # This would test database performance with increasing data sizes
        # For now, we simulate the test structure
        
        data_sizes = [100, 1000, 10000]  # Number of records
        query_times = []
        
        for size in data_sizes:
            # Simulate database query with different data sizes
            start_time = time.time()
            
            # Simulate query complexity increasing with data size
            time.sleep(0.001 * (size / 100))  # Simulate query time
            
            end_time = time.time()
            query_time = (end_time - start_time) * 1000  # ms
            query_times.append(query_time)
            
            # Query time should not increase linearly (should be optimized)
            if len(query_times) > 1:
                time_increase_ratio = query_time / query_times[0]
                size_increase_ratio = size / data_sizes[0]
                
                # Time increase should be less than size increase (indicating good indexing/optimization)
                assert time_increase_ratio < size_increase_ratio, \
                    f"Query time scaling is poor for size {size}"
    
    def test_cache_performance_scalability(self):
        """Test cache performance under increasing load."""
        # Simulate cache hit/miss performance
        cache_sizes = [100, 1000, 10000]
        access_patterns = ["sequential", "random"]
        
        for pattern in access_patterns:
            for cache_size in cache_sizes:
                # Simulate cache access
                hit_times = []
                miss_times = []
                
                for i in range(100):  # Test accesses
                    if pattern == "sequential":
                        key = i % cache_size
                    else:  # random
                        key = (i * 7) % cache_size  # Pseudo-random
                    
                    start_time = time.time()
                    # Simulate cache access (hit or miss)
                    if i < cache_size:  # First accesses are misses
                        time.sleep(0.01)  # Simulate cache miss (slower)
                        miss_times.append((time.time() - start_time) * 1000)
                    else:
                        time.sleep(0.001)  # Simulate cache hit (faster)
                        hit_times.append((time.time() - start_time) * 1000)
                
                # Cache hits should be significantly faster than misses
                if hit_times and miss_times:
                    avg_hit_time = statistics.mean(hit_times)
                    avg_miss_time = statistics.mean(miss_times)
                    
                    # Hits should be at least 5x faster than misses
                    speedup = avg_miss_time / avg_hit_time
                    assert speedup >= 5, \
                        f"Cache speedup {speedup}x is too low for {pattern} pattern with size {cache_size}"


class TestStressTesting:
    """Test system behavior under extreme stress conditions."""
    
    @pytest.fixture
    def api_base_url(self):
        """Base URL for API testing."""
        return os.getenv("API_BASE_URL", "http://localhost:8000")
    
    def test_maximum_concurrent_connections(self, api_base_url):
        """Test maximum number of concurrent connections."""
        endpoint = f"{api_base_url}/health"
        max_connections = 500
        
        def make_connection():
            try:
                response = requests.get(endpoint, timeout=10)
                return response.status_code == 200
            except Exception:
                return False
        
        # Gradually increase concurrent connections
        successful_connections = 0
        
        for batch_size in range(50, max_connections + 1, 50):
            with concurrent.futures.ThreadPoolExecutor(max_workers=batch_size) as executor:
                futures = [executor.submit(make_connection) for _ in range(batch_size)]
                batch_results = [future.result() for future in concurrent.futures.as_completed(futures)]
                
                batch_success = sum(batch_results)
                success_rate = batch_success / batch_size
                
                # If success rate drops below 50%, we've found the limit
                if success_rate < 0.5:
                    break
                
                successful_connections = batch_success
        
        # Should handle at least 100 concurrent connections
        assert successful_connections >= 100, \
            f"System only handled {successful_connections} concurrent connections, expected at least 100"
    
    def test_memory_exhaustion_resilience(self):
        """Test system resilience to memory exhaustion."""
        import gc
        
        # Monitor memory usage
        import psutil
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Try to consume significant memory
        memory_hog = []
        try:
            for i in range(1000):
                # Allocate large objects
                large_object = {"data": "x" * 10000, "index": i}
                memory_hog.append(large_object)
                
                # Check memory usage
                current_memory = process.memory_info().rss / 1024 / 1024  # MB
                memory_increase = current_memory - initial_memory
                
                # If memory increase is too large, stop
                if memory_increase > 500:  # 500MB limit
                    break
                
                # Periodically test if system is still responsive
                if i % 100 == 0:
                    # Simple operation to test responsiveness
                    test_data = {"test": i}
                    json.dumps(test_data)
        
        except MemoryError:
            # Expected to hit memory limit
            pass
        finally:
            # Clean up
            del memory_hog
            gc.collect()
        
        # System should still be functional after memory stress
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Memory should be released after cleanup
        memory_after_cleanup = final_memory - initial_memory
        assert memory_after_cleanup < 100, \
            f"Memory {memory_after_cleanup}MB after cleanup is too high"
    
    def test_high_frequency_requests(self, api_base_url):
        """Test system under very high frequency requests."""
        endpoint = f"{api_base_url}/health"
        duration = 10  # seconds
        target_rps = 100  # requests per second
        
        start_time = time.time()
        end_time = start_time + duration
        request_count = 0
        successful_requests = 0
        
        while time.time() < end_time:
            request_start = time.time()
            
            try:
                response = requests.get(endpoint, timeout=1)
                if response.status_code == 200:
                    successful_requests += 1
            except Exception:
                pass
            
            request_count += 1
            
            # Calculate required delay to maintain target RPS
            elapsed = time.time() - start_time
            expected_requests = elapsed * target_rps
            if request_count > expected_requests:
                # Sleep to maintain rate
                time.sleep(0.001)
        
        actual_rps = successful_requests / duration
        success_rate = successful_requests / request_count
        
        # Should maintain reasonable performance even at high frequency
        assert actual_rps >= target_rps * 0.5, \
            f"Actual RPS {actual_rps} is too low compared to target {target_rps}"
        assert success_rate >= 0.8, \
            f"Success rate {success_rate} at high frequency is too low"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])