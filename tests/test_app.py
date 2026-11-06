import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pytest
from app import create_app


@pytest.fixture
def app(tmp_path):
    return create_app(str(tmp_path / "t.db"))


def login_as(app, user, pw, register=True):
    c = app.test_client()
    if register:
        c.post("/api/register", json={"username": user, "password": pw})
    c.post("/api/login", json={"username": user, "password": pw})
    return c


@pytest.fixture
def cust(app):
    return login_as(app, "cust", "pw1234")


@pytest.fixture
def admin(app):
    return login_as(app, "admin", "admin123", register=False)


def test_TC01_customer_login(app):
    c = app.test_client()
    assert c.post("/api/register", json={"username": "a", "password": "pw1234"}).status_code == 201
    r = c.post("/api/login", json={"username": "a", "password": "pw1234"})
    assert r.status_code == 200 and r.json["message"] == "Login successful"


def test_TC01b_bad_login_and_duplicate(app):
    c = app.test_client()
    c.post("/api/register", json={"username": "a", "password": "pw1234"})
    assert c.post("/api/register", json={"username": "a", "password": "pw1234"}).status_code == 409
    assert c.post("/api/login", json={"username": "a", "password": "wrong"}).status_code == 401


def test_catalogue_is_public(app):
    r = app.test_client().get("/api/products")
    assert r.status_code == 200 and len(r.json) == 4


def test_TC02_search_product(app):
    r = app.test_client().get("/api/products/search?q=laptop")
    assert r.json["message"] == "Product displayed" and r.json["results"][0]["name"] == "Laptop"


def test_TC02b_search_no_match(app):
    assert app.test_client().get("/api/products/search?q=zzz").json["message"] == "No products found"


def test_TC03_add_to_cart(cust):
    r = cust.post("/api/cart", json={"product_id": 1, "qty": 1})
    assert r.json["message"] == "Product added"
    assert len(cust.get("/api/cart").json["items"]) == 1


def test_TC03b_add_more_than_stock(cust):
    assert cust.post("/api/cart", json={"product_id": 1, "qty": 9999}).status_code == 400


def test_TC04_update_quantity(cust):
    cust.post("/api/cart", json={"product_id": 1, "qty": 1})
    assert cust.put("/api/cart/1", json={"qty": 3}).json["message"] == "Cart updated"
    cart = cust.get("/api/cart").json
    assert cart["items"][0]["qty"] == 3 and cart["total"] == 165000.0


def test_TC05_remove_product(cust):
    cust.post("/api/cart", json={"product_id": 1, "qty": 1})
    assert cust.delete("/api/cart/1").json["message"] == "Product removed"
    assert cust.get("/api/cart").json["items"] == []


def test_TC06_checkout(cust):
    cust.post("/api/cart", json={"product_id": 1, "qty": 2})
    r = cust.post("/api/checkout")
    assert r.status_code == 201 and r.json["message"] == "Order placed" and r.json["total"] == 110000.0
    assert cust.get("/api/cart").json["items"] == []
    stock = [p for p in cust.get("/api/products").json if p["id"] == 1][0]["stock"]
    assert stock == 98


def test_TC06b_checkout_empty_cart(cust):
    assert cust.post("/api/checkout").status_code == 400


def test_TC07_order_history(cust):
    cust.post("/api/cart", json={"product_id": 2, "qty": 1})
    cust.post("/api/checkout")
    r = cust.get("/api/orders")
    assert r.json["message"] == "Order details displayed"
    assert r.json["orders"][0]["items"][0]["name"] == "Headphones"


def test_TC08_admin_product_management(admin):
    pid = admin.post("/api/admin/products", json={"name": "Mouse", "price": 499, "stock": 20, "category": "Electronics"}).json["id"]
    assert admin.put("/api/admin/products/%d" % pid, json={"price": 599}).json["message"] == "Product updated"
    assert admin.delete("/api/admin/products/%d" % pid).json["message"] == "Product deleted"


def test_customer_cannot_use_admin(cust):
    assert cust.post("/api/admin/products", json={"name": "X", "price": 1, "stock": 1}).status_code == 403


def test_cart_requires_login(app):
    assert app.test_client().get("/api/cart").status_code == 401
