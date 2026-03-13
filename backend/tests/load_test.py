import requests
import time
import concurrent.futures

API_URL = "http://localhost:8000/api/predict"
NUM_REQUESTS = 100
CONCURRENT_USERS = 10

def send_request(i):
    start = time.time()
    try:
        requests.post(API_URL, json={"url": f"http://test-{i}.com"})
        latency = (time.time() - start) * 1000
        return latency
    except Exception as e:
        print(f"Error: {e}")
        return None

def run_load_test():
    print(f"Starting Load Test: {NUM_REQUESTS} requests with {CONCURRENT_USERS} concurrent users...")
    
    latencies = []
    start_total = time.time()
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=CONCURRENT_USERS) as executor:
        futures = [executor.submit(send_request, i) for i in range(NUM_REQUESTS)]
        for future in concurrent.futures.as_completed(futures):
            res = future.result()
            if res:
                latencies.append(res)

    total_time = time.time() - start_total
    avg_latency = sum(latencies) / len(latencies)
    max_latency = max(latencies)
    min_latency = min(latencies)
    rps = NUM_REQUESTS / total_time

    print("\n--- Load Test Results ---")
    print(f"Total Requests: {NUM_REQUESTS}")
    print(f"Total Time: {total_time:.2f}s")
    print(f"Requests Per Second (RPS): {rps:.2f}")
    print(f"Average Latency: {avg_latency:.2f}ms")
    print(f"Min Latency: {min_latency:.2f}ms")
    print(f"Max Latency: {max_latency:.2f}ms")

if __name__ == "__main__":
    run_load_test()
