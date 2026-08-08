from app.models.supplier import Supplier


def get_supplier_by_name(db, name: str):
    return db.query(Supplier).filter(Supplier.name == name).first()
