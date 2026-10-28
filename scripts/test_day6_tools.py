from app.agent.tools import get_order_info, get_inventory, get_logistics 

ORDER_ID = 666
PRODUCT_ID = 5

print("=== get_order_info ===")
print(get_order_info.invoke({"order_id": ORDER_ID}))

print("\n=== get_inventory ===")
print(get_inventory.invoke({"product_id": PRODUCT_ID}))

print("\n=== get_logistics ===")
print(get_logistics.invoke({"order_id": ORDER_ID}))