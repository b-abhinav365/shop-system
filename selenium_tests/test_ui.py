"""Selenium UI tests. Start the app first, then:
    BASE_URL=http://localhost:5000 pytest selenium_tests -v
Assumes the seeded catalogue (product id 1 = Laptop) and the default admin (admin / admin123).
"""
import os
import time
import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait

BASE = os.environ.get("BASE_URL", "http://localhost:5000")
USER = "customer%d" % int(time.time())


@pytest.fixture(scope="module")
def driver():
    o = Options()
    if os.environ.get("HEADLESS", "1") == "1":
        o.add_argument("--headless=new")
    o.add_argument("--no-sandbox")
    o.add_argument("--disable-dev-shm-usage")
    o.add_argument("--window-size=1200,900")
    d = webdriver.Chrome(options=o)
    d.get(BASE)
    yield d
    d.quit()


def fill(d, field_id, value):
    e = d.find_element(By.ID, field_id)
    e.clear()
    e.send_keys(value)


def click_and_expect(d, label, text):
    d.find_element(By.XPATH, "//button[normalize-space()='%s']" % label).click()
    WebDriverWait(d, 10).until(lambda x: text in x.find_element(By.ID, "o").text)


def output(d):
    return d.find_element(By.ID, "o").text


def test_TC00_page_loads(driver):
    assert "Online Shopping" in driver.title


def test_TC01_customer_login(driver):
    fill(driver, "user", USER)
    fill(driver, "pass", "secret123")
    click_and_expect(driver, "Register", "Customer registered")
    click_and_expect(driver, "Login", "Login successful")


def test_TC02_search_product(driver):
    fill(driver, "query", "Laptop")
    click_and_expect(driver, "Search", "Product displayed")
    assert "Laptop" in output(driver)


def test_TC03_add_to_cart(driver):
    fill(driver, "pid", "1")
    fill(driver, "qty", "1")
    click_and_expect(driver, "Add to Cart", "Product added")


def test_TC04_update_quantity(driver):
    fill(driver, "qty", "3")
    click_and_expect(driver, "Update Qty", "Cart updated")
    click_and_expect(driver, "View Cart", "165000")


def test_TC05_remove_product(driver):
    click_and_expect(driver, "Remove", "Product removed")


def test_TC06_checkout(driver):
    fill(driver, "qty", "2")
    click_and_expect(driver, "Add to Cart", "Product added")
    click_and_expect(driver, "Checkout", "Order placed")


def test_TC07_view_order_history(driver):
    click_and_expect(driver, "Order History", "Order details displayed")
    assert "Laptop" in output(driver)


def test_TC08_admin_adds_product(driver):
    click_and_expect(driver, "Logout", "Logged out")
    fill(driver, "user", "admin")
    fill(driver, "pass", "admin123")
    click_and_expect(driver, "Login", "Login successful")
    fill(driver, "pn", "Mouse")
    fill(driver, "pp", "499")
    fill(driver, "ps", "20")
    fill(driver, "pc", "Electronics")
    click_and_expect(driver, "Add Product", "Product created")
