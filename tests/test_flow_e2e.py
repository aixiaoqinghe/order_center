"""
E2E 端到端测试

前置条件:
  1. FastAPI 服务已启动 (uvicorn app.main:app --reload --port 8000)
  2. MQ 消费者已启动 (python scripts/consumer.py)

运行:
  pip install pytest
  pytest tests/ -v -s
"""
import time
import uuid

import httpx
import pytest

BASE_URL = "http://localhost:8000"


def _unique_name():
    """生成唯一用户名，避免测试之间冲突"""
    return f"e2e_{uuid.uuid4().hex[:8]}"


@pytest.fixture(scope="module", autouse=True)
def _check_service():
    """模块级前置检查: FastAPI 没启动就 skip 整个测试文件"""
    try:
        httpx.get(f"{BASE_URL}/docs", timeout=3)
    except httpx.ConnectError:
        pytest.skip(
            "FastAPI 服务未启动。请先跑: uvicorn app.main:app --reload --port 8000"
        )


@pytest.fixture
def client():
    """每个测试函数一个独立的 httpx client"""
    c = httpx.Client(timeout=10)
    yield c
    c.close()


@pytest.fixture
def user_and_order(client):
    """helper fixture: 注册用户 + 创建订单，返回 (user_id, order_id)"""
    name = _unique_name()

    # 注册
    r = client.post(
        f"{BASE_URL}/api/user/register",
        json={"user_name": name, "user_password": "123456"},
    )
    if r.json()["code"] != 200:
        r = client.post(
            f"{BASE_URL}/api/user/login",
            json={"user_name": name, "user_password": "123456"},
        )
    user_id = r.json()["data"]["user_id"]

    # 找一个有库存的商品
    products = client.get(f"{BASE_URL}/api/product/list").json()["data"]["list"]
    product_id = None
    for p in products:
        d = client.get(f"{BASE_URL}/api/product/{p['product_id']}").json().get("data")
        if d and d.get("available_stock", 0) > 0:
            product_id = p["product_id"]
            break
    if product_id is None:
        pytest.skip("所有商品库存都是 0，无法下单")

    # 创建订单
    r = client.post(
        f"{BASE_URL}/api/order/create",
        json={
            "user_id": user_id,
            "items": [{"product_id": product_id, "order_item_num": 1}],
        },
    )
    assert r.json()["code"] == 200, f"创建订单失败: {r.text}"
    order_id = r.json()["data"]["order_id"]

    return user_id, order_id


class TestFullUserJourney:
    """完整用户旅程: 注册 → 登录 → 下单 → 支付 → AI咨询"""

    def test_full_flow(self, client):
        user_name = _unique_name()
        user_password = "123456"

        # ---- Step 1: 注册 ----
        print(f"\n[1/6] 注册用户: {user_name}")
        r = client.post(
            f"{BASE_URL}/api/user/register",
            json={"user_name": user_name, "user_password": user_password},
        )
        assert r.status_code == 200, f"注册失败: {r.text}"
        assert r.json()["code"] == 200
        user_id = r.json()["data"]["user_id"]
        assert isinstance(user_id, int)
        print(f"       ✅ user_id={user_id}")

        # ---- Step 2: 登录 ----
        print(f"[2/6] 登录")
        r = client.post(
            f"{BASE_URL}/api/user/login",
            json={"user_name": user_name, "user_password": user_password},
        )
        assert r.status_code == 200, f"登录失败: {r.text}"
        assert r.json()["code"] == 200
        assert r.json()["data"]["user_id"] == user_id
        print(f"       ✅ 登录成功")

        # ---- Step 3: 商品列表 ----
        print(f"[3/6] 查商品列表")
        r = client.get(f"{BASE_URL}/api/product/list")
        assert r.status_code == 200
        assert r.json()["code"] == 200
        products = r.json()["data"]["list"]
        assert len(products) > 0, "数据库里没有商品"
        print(f"       ✅ 找到 {len(products)} 个商品")

        # 动态挑一个有库存的商品
        product_id = None
        for p in products:
            detail = client.get(f"{BASE_URL}/api/product/{p['product_id']}")
            d = detail.json().get("data")
            if d and d.get("available_stock", 0) > 0:
                product_id = p["product_id"]
                break
        assert product_id is not None, "所有商品库存都是 0，无法下单"
        print(f"       ✅ 选 product_id={product_id} (有库存)")

        # ---- Step 4: 创建订单 ----
        print(f"[4/6] 创建订单 (product_id={product_id}, 数量=1)")
        r = client.post(
            f"{BASE_URL}/api/order/create",
            json={
                "user_id": user_id,
                "items": [{"product_id": product_id, "order_item_num": 1}],
            },
        )
        assert r.status_code == 200, f"创建订单失败: {r.text}"
        assert r.json()["code"] == 200
        order_data = r.json()["data"]
        order_id = order_data["order_id"]
        assert order_data["order_status"] == 0, "新建订单状态应为 0(待支付)"
        assert len(order_data["items"]) == 1
        print(f"       ✅ order_id={order_id}, status=0(待支付)")

        # 等 MQ 消费者异步扣库存
        print(f"       (等待 MQ 消费者处理...)")
        time.sleep(2)

        # ---- Step 5: 模拟支付 ----
        print(f"[5/6] 模拟支付")
        r = client.post(f"{BASE_URL}/api/order/pay/{order_id}")
        assert r.status_code == 200, f"支付失败: {r.text}"
        assert r.json()["code"] == 200
        pay_data = r.json()["data"]
        assert pay_data["order_status"] == 1, "支付后状态应为 1(已支付)"
        print(f"       ✅ order_status=1(已支付)")

        # ---- Step 6: AI 咨询 ----
        print(f"[6/6] AI 咨询订单状态")
        r = client.post(
            f"{BASE_URL}/api/order/consult/{order_id}",
            json={"question": "我的订单什么时候能送到？"},
        )
        assert r.status_code == 200, f"AI 咨询失败: {r.text}"
        assert r.json()["code"] == 200
        ai_data = r.json()["data"]
        assert ai_data["order_id"] == order_id
        assert len(ai_data["answer"]) > 0, "AI 返回空回答"
        print(f"       ✅ AI 回答: {ai_data['answer'][:50]}...")

        print(f"\n🎉 整条链路测试全部通过!")


class TestErrorScenarios:
    """异常场景测试"""

    def test_order_not_found(self, client):
        """查不存在的订单应返回 OrderNotFoundError"""
        r = client.get(f"{BASE_URL}/api/order/detail/999999?user_id=1")
        assert r.status_code == 400
        assert r.json()["code"] == 400
        assert "不存在" in r.json()["msg"]

    def test_pay_already_paid_order_fails(self, client, user_and_order):
        """已支付的订单再支付应抛 OrderStatusError"""
        _, order_id = user_and_order

        # 正常支付
        r = client.post(f"{BASE_URL}/api/order/pay/{order_id}")
        assert r.json()["code"] == 200

        # 再付一次 → 应该失败
        r = client.post(f"{BASE_URL}/api/order/pay/{order_id}")
        assert r.json()["code"] == 400
        assert "状态" in r.json()["msg"] or "不允许" in r.json()["msg"]

    def test_pay_not_found_order(self, client):
        """支付不存在的订单应返回 OrderNotFoundError"""
        r = client.post(f"{BASE_URL}/api/order/pay/999999")
        assert r.json()["code"] == 400
        assert "不存在" in r.json()["msg"]

    def test_create_order_out_of_stock(self, client):
        """库存不足下单应返回 StockNotEnoughError"""
        # product_id=1 已知库存为 0 (之前测试发现的)
        # 如果以后产品数据变了这里可能需要调整
        r = client.post(
            f"{BASE_URL}/api/order/create",
            json={
                "user_id": 1,
                "items": [{"product_id": 1, "order_item_num": 99999}],
            },
        )
        assert r.json()["code"] == 400