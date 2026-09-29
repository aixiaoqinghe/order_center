"""
压测脚本：验证分布式锁防超卖
用法：
    python scripts/load_test.py                    # 用默认参数
    python scripts/load_test.py --concurrency 200 --stock 100
    python scripts/load_test.py --no-lock          # 先跑无锁版，再恢复锁跑有锁版对比
前提：服务端已启动
"""

import argparse
import asyncio
import sys
from collections import Counter

import httpx
from sqlalchemy import create_engine, text

sys.path.insert(0, ".")
from app.config import settings

API_URL = "http://127.0.0.1:8000/api/order/create"

engine = create_engine(settings.database_url)


async def one_request(client: httpx.AsyncClient, product_id: int, user_id: int) -> str:
    payload = {
        "user_id": user_id,
        "items": [{"product_id": product_id, "order_item_num": 1}],
    }
    try:
        resp = await client.post(API_URL, json=payload)
    except Exception as e:
        return f"其他:{type(e).__name__}"

    body = resp.json() if resp.content else {}
    msg = body.get("msg", "")

    if resp.status_code == 200 and body.get("code") == 200:
        return "success"
    if "库存" in msg:
        return "库存不足"
    if "繁忙" in msg or "锁" in msg:
        return "系统繁忙"
    return f"其他: HTTP{resp.status_code}({msg})"


async def run(concurrency: int, stock: int, product_id: int, user_id: int):
    with engine.begin() as conn:
        conn.execute(
            text("UPDATE inventory SET total_stock=:s, locked_stock=0 WHERE product_id=:p"),
            {"s": stock, "p": product_id},
        )

    limits = httpx.Limits(max_connections=concurrency + 50, max_keepalive_connections=50)
    async with httpx.AsyncClient(limits=limits, timeout=httpx.Timeout(30.0, read=60.0)) as client:
        tasks = [one_request(client, product_id, user_id) for _ in range(concurrency)]
        results = await asyncio.gather(*tasks)

    counter = Counter(results)
    success = counter.get("success", 0)

    with engine.begin() as conn:
        row = conn.execute(
            text("SELECT total_stock, locked_stock FROM inventory WHERE product_id=:p"),
            {"p": product_id},
        ).fetchone()

    print("=" * 50)
    print(f"并发数:{concurrency}  库存:{stock}")
    print(f"成功单数:{success}  失败单数:{concurrency - success}")
    if counter.get("success"):
        for reason, cnt in counter.items():
            if reason != "success":
                print(f"  {reason}: {cnt}")
    print(f"最终 total_stock:{row[0]}  locked_stock:{row[1]}")
    print("=" * 50)

    if success > stock:
        print(f">>> 🔴 超卖! 成功单数({success}) > 库存({stock})")
    elif row[1] > stock:
        print(f">>> 🔴 超卖! locked_stock({row[1]}) > 库存({stock})")
    elif success <= stock and success == row[1]:
        print(f">>> 🟢 正常: 成功({success}) ≤ 库存({stock})  锁生效")
    elif success <= stock and success > 0:
        print(f">>> 🟢 正常: 成功({success}) ≤ 库存({stock})  锁生效(有回滚)")
    else:
        print(f">>> 🟡 全部被拒绝")


def main():
    parser = argparse.ArgumentParser(description="分布式锁防超卖压测")
    parser.add_argument("--concurrency", "-c", type=int, default=100, help="并发数")
    parser.add_argument("--stock", "-s", type=int, default=50, help="初始库存")
    parser.add_argument("--product-id", "-p", type=int, default=1, help="商品ID")
    parser.add_argument("--user-id", "-u", type=int, default=1, help="下单用户ID")
    args = parser.parse_args()

    asyncio.run(run(args.concurrency, args.stock, args.product_id, args.user_id))


if __name__ == "__main__":
    main()