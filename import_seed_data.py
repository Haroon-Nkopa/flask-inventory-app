from datetime import datetime
from app import create_app, db
from app.models import Product, InventoryRecord

FILE_PATH = "shop_inventory_seed.txt"  # put file in project root

def parse_seed_file(path):
    products = []
    records = []

    section = None

    with open(path, "r") as f:
        for line in f:
            line = line.strip()

            if not line or line.startswith("#"):
                if "PRODUCTS" in line:
                    section = "products"
                elif "INVENTORY_RECORDS" in line:
                    section = "records"
                continue

            if section == "products":
                products.append(line.split("|"))

            elif section == "records":
                product_index, date, quantity = line.split("|")
                records.append((
                    int(product_index),
                    datetime.strptime(date, "%Y-%m-%d").date(),
                    int(quantity)
                ))

    return products, records


def insert_data():
    app = create_app()
    with app.app_context():

        products_data, inventory_data = parse_seed_file(FILE_PATH)

        print("Inserting products...")
        product_id_map = {}

        for index, p in enumerate(products_data, start=1):
            product = Product(
                name=p[0],
                category=p[1],
                price=float(p[2]),
                batch_size=int(p[3]),
                batch_price=float(p[4]),
                lower_bound=int(p[5]),
                size=p[6],
                shop_id=int(p[7])
            )
            db.session.add(product)
            db.session.flush()  # 👈 gets product.id without commit

            product_id_map[index] = product.id

        db.session.commit()
        print(f"{len(product_id_map)} products inserted.")

        print("Inserting inventory records...")
        for product_index, date, quantity in inventory_data:
            record = InventoryRecord(
                product_id=product_id_map[product_index],
                date=date,
                quantity=quantity
            )
            db.session.add(record)

        db.session.commit()
        print("Inventory records inserted successfully.")

if __name__ == "__main__":
    insert_data()
