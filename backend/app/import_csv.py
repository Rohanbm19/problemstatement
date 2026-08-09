import pandas as pd

from app.database import SessionLocal
from app.models.inventory import InventoryItem


CSV_FILE = "data/warehouse_cleaned.csv"


def import_inventory():

    print("Reading CSV...")

    df = pd.read_csv(CSV_FILE)

    print(f"Found {len(df)} rows")

    db = SessionLocal()

    try:

        existing_ids = {
            row[0]
            for row in db.query(InventoryItem.item_id).all()
        }

        records = []

        for _, row in df.iterrows():

            if str(row["item_id"]) in existing_ids:
                continue

            item = InventoryItem(
                item_id=str(row["item_id"]),
                category=str(row["category"]),
                stock_level=int(row["stock_level"]),
                reorder_point=int(row["reorder_point"]),
                reorder_frequency_days=int(
                    row["reorder_frequency_days"]
                ),
                lead_time_days=int(row["lead_time_days"]),
                daily_demand=float(row["daily_demand"]),
                demand_std_dev=float(row["demand_std_dev"]),
                item_popularity_score=float(
                    row["item_popularity_score"]
                ),
                storage_location_id=str(
                    row["storage_location_id"]
                )
            )

            records.append(item)

        db.add_all(records)
        db.commit()

        print(f"Successfully imported {len(records)} records.")

    except Exception as e:

        db.rollback()

        print("ERROR:", e)

    finally:

        db.close()


if __name__ == "__main__":
    import_inventory()