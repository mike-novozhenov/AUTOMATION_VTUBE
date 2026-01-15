import requests
import time
import pytest

# Import pages list and time limit from settings.py
from config.settings import ENDPOINTS, MAX_WAIT_TIME

@pytest.mark.parametrize("url", ENDPOINTS)
def test_check_all_pages_health(url):
    """
    Term: Parametrization — running one test with different input data
    """
    start_time = time.time()
    
    response = requests.get(url, timeout=10)
    
    duration = time.time() - start_time
    
    # Availability check
    assert response.status_code == 200, f"Page {url} is down! Got {response.status_code}"
    
    # Perfomance check
    print(f"\n[INFO] URL: {url} | Latency: {duration:.2f}s")
    assert duration < MAX_WAIT_TIME, f"Slow response on {url}: {duration:.2f}s"