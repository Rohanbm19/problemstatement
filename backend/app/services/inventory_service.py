from app.models.inventory import Inventory


def update_inventory(db, product_id: int, quantity: int):
    inventory_item = db.query(Inventory).filter(Inventory.product_id == product_id).first()
    if inventory_item:
        inventory_item.quantity += quantity
    else:
        inventory_item = Inventory(product_id=product_id, quantity=quantity)
        db.add(inventory_item)
    db.commit()
    db.refresh(inventory_item)
    return inventory_item
