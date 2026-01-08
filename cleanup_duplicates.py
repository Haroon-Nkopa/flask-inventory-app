from app import create_app, db
from app.models import InventoryRecord
from sqlalchemy import func

app = create_app()

with app.app_context():
    duplicates = (
        db.session.query(
            InventoryRecord.product_id,
            InventoryRecord.date,
            func.count(InventoryRecord.id)
        )
        .group_by(InventoryRecord.product_id, InventoryRecord.date)
        .having(func.count(InventoryRecord.id) > 1)
        .all()
    )

    print("Found duplicates:", duplicates)

    for product_id, date, _ in duplicates:
        records = InventoryRecord.query.filter_by(
            product_id=product_id,
            date=date
        ).all()

        total_qty = sum(r.quantity for r in records)

        records[0].quantity = total_qty

        for r in records[1:]:
            db.session.delete(r)

    db.session.commit()
    print("Cleanup complete")
