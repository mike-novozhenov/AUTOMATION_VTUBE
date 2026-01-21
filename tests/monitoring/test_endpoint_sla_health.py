import requests
import pytest
import allure
from config.settings import ENDPOINTS, MAX_WAIT_TIME

@allure.suite("Health Check")
@allure.feature("Monitoring Services")
@allure.story("Web Availability")

@pytest.mark.cron_15min
@pytest.mark.parametrize("url", ENDPOINTS)
def test_check_pages_health(url):
    allure.dynamic.title(f"Health Check: {url}")
    
    check_url_logic(url)

@allure.step("Request and verification {url}")
def check_url_logic(url):
    try:
        # 1) Using .elapsed to measure pure server response time (Latency)
        response = requests.get(url, timeout=10)
        duration = response.elapsed.total_seconds()
        
        # 2) Store metrics in Allure
        allure.attach(f"Duration: {duration:.2f}s", name="Latency", attachment_type=allure.attachment_type.TEXT)
        
        # 3) Assertions
        assert response.status_code == 200, f"Page {url} is down! Got {response.status_code}"
        assert duration < MAX_WAIT_TIME, f"Slow response on {url}: {duration:.2f}s"
        
        print(f"\n[INFO] URL: {url} | Latency: {duration:.2f}s")
        
    except requests.exceptions.RequestException as e:
        # Handle transport-level errors (DNS, Timeout, etc.)
        pytest.fail(f"Network error on {url}: {e}")