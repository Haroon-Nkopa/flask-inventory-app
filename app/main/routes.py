#import main blueprint
from flask_login import current_user, logout_user
from . import main
from flask import render_template, request, redirect, url_for, flash, session, send_file  
from ..models import Product, InventoryRecord, Shop
from .. import db
from datetime import date , datetime  # Add this import
from ..decorators import shop_required
from ..auth.user_required import user_required
from app.utils.stock_sheet_pdf import generate_stock_sheet_pdf


#at shop decorator 


@main.route('/', methods=['GET', 'POST'])
def enter_shop():
    
    if session.get('shop_id'):
        return redirect(url_for('main.shop'))   
    if request.method == 'POST':
        shop_name = request.form.get('shop_name').strip().title()
        # Case-insensitive match
        shop = Shop.query.filter(Shop.name.ilike(shop_name)).first()
        if shop:
            session['shop_id'] = shop.id  # Save to session
            session['shop_name'] = shop.name  # Save shop name to session
            return redirect(url_for('main.shop', shop_id=shop.id))
        else:
            flash('Shop not found. Please contact admin to register it. 083 224 2491', 'danger')

    return render_template('main/enter_shop.html', year=datetime.now().year)

@main.route('/shop')
@shop_required
@user_required
def shop():
    products = Product.query.filter_by(shop_id=session['shop_id']).all()
    return render_template('main/shop.html', products=products)



@main.route('/add', methods=['GET', 'POST'])
@shop_required
def add_product():
    shop_id = session.get('shop_id')

    if not shop_id:
        flash("No shop selected. Please log in again.", "warning")
        return redirect(url_for('main.enter_shop'))

    if request.method == 'POST':
        # Get values from form
        name = request.form['name'].strip()
        category = request.form['category'].strip()
        price = float(request.form['price'])

        # ✅ New fields
        size = request.form.get('size', '').strip()             # e.g., "2L", "12-pack"
        batch_size = int(request.form.get('batch_size', 1))    # default 1
        batch_price = float(request.form.get('batch_price', 0))  # default 0
        lower_bound = int(request.form.get('lower_bound', 0))     # default 0
        batch_number = request.form.get('batch_number', '').strip()

        # ✅ Check if product exists already in this shop
        existing_product = Product.query.filter_by(name=name, shop_id=shop_id).first()
        if existing_product:
            flash(f"Product '{name}' already exists in your shop.", "warning")
            return redirect(url_for('main.add_product'))

        # ✅ Create new product
        new_product = Product(
            name=name,
            category=category,
            price=price,
            size=size,
            batch_size=batch_size,
            batch_price=batch_price,
            lower_bound=lower_bound,
            batch_number=batch_number,
            shop_id=shop_id
        )
        db.session.add(new_product)
        db.session.flush()  # Flush to get new_product.id before full commit

        # ✅ Step 1: find latest inventory date used in this shop
        latest_record = (
            db.session.query(InventoryRecord.date)
            .join(Product)
            .filter(Product.shop_id == shop_id)
            .order_by(InventoryRecord.date.desc())
            .first()
        )

        if latest_record:
            latest_date = latest_record.date
            # ✅ Step 2: create an inventory record for this product with quantity 0
            new_record = InventoryRecord(
                product_id=new_product.id,
                date=latest_date,
                quantity=0
            )
            db.session.add(new_record)

        db.session.commit()

        flash(f"Product '{name}' added successfully!", "success")
        return redirect(url_for('main.shop', shop_id=shop_id))

    return render_template('main/add_product.html')



@main.route('/stock-history')
@shop_required
def stock_history():
    # Get all unique dates
    shop_id = session.get('shop_id')

    # ✅ Get only dates for this shop
    dates = (
        db.session.query(InventoryRecord.date)
        .join(Product)
        .filter(Product.shop_id == shop_id)
        .distinct()
        .order_by(InventoryRecord.date)
        .all()
    )
    dates = [d[0] for d in dates]

    products = Product.query.filter_by(shop_id=session['shop_id']).all()
    stock_data = {}

    for product in products:
        stock_data[product.name] = {}
        for record in product.records:
            stock_data[product.name][record.date] = record.quantity

    return render_template('main/stock_history.html', dates=dates, stock_data=stock_data)



@main.route('/take-stock', methods=['GET', 'POST'])
@shop_required
def take_stock():
    shop_id = session.get('shop_id')
    products = Product.query.filter_by(shop_id=shop_id).all()
    today_date = date.today()

    if request.method == 'POST':

        # 🚫 First: Check if stock was already captured today
        existing_record = (
            InventoryRecord.query
            .join(Product)
            .filter(Product.shop_id == shop_id, InventoryRecord.date == today_date)
            .first()
        )
        if existing_record:
            flash("Stock was already counted today.", "warning")
            return redirect(url_for('main.shop'))

        # ✅ Step 2: Validate increases only (no stock decreases)
        problematic_products = []  # Collect products with invalid decrease

        for product in products:
            qty_input = request.form.get(f'quantity_{product.id}', 0)

            try:
                qty_input = int(qty_input)
            except ValueError:
                qty_input = 0

            # Get the last recorded stock value (before today)
            previous_record = (
                InventoryRecord.query
                .filter(
                    InventoryRecord.product_id == product.id,
                    InventoryRecord.date < today_date
                )
                .order_by(InventoryRecord.date.desc())
                .first()
            )

            # If a previous record exists, compare
            if previous_record and qty_input > previous_record.quantity:
                problematic_products.append(
                    f"{product.name} (Prev: {previous_record.quantity}, New: {qty_input})"
                )

        # 🚫 If any stock is greater than before, cancel & warn user
        if problematic_products:
            flash("Stock count cannot be greater than the previous record for the following products:", "danger")
            for item in problematic_products:
                flash(f"- {item}", "warning")
            return redirect(url_for('main.take_stock'))

        # ✅ If everything is correct → Save the records
        for product in products:
            qty_input = request.form.get(f'quantity_{product.id}', 0)
            try:
                qty_input = int(qty_input)
            except ValueError:
                qty_input = 0

            new_record = InventoryRecord(
                product_id=product.id,
                date=today_date,
                quantity=qty_input
            )
            db.session.add(new_record)

        db.session.commit()
        flash("Stock captured successfully for today!", "success")
        return redirect(url_for('main.shop'))

    return render_template('main/stock_take.html', products=products, today=today_date)

@main.route('/summary', methods=['GET', 'POST'])
@shop_required
def summary():
    shop_id = session.get('shop_id')

    dates = [
        r[0] for r in db.session.query(InventoryRecord.date)
        .join(Product)
        .filter(Product.shop_id == shop_id)
        .distinct()
        .order_by(InventoryRecord.date)
        .all()
    ]

    if not dates or len(dates) < 2:
        return render_template(
            'main/summary.html',
            message="Not enough stock history to generate a summary.",
            stock_out_products=[],
            fast_selling=[],
            top_earning=[]
        )

    last_date = dates[-1]
    prev_date = dates[-2]

    total_business = 0
    stock_out_products = []
    sales_data = []  # temp list to calculate rankings

    products = Product.query.filter_by(shop_id=shop_id).all()

    for p in products:
        qty_last = db.session.query(InventoryRecord.quantity)\
            .filter_by(product_id=p.id, date=last_date).scalar() or 0

        qty_prev = db.session.query(InventoryRecord.quantity)\
            .filter_by(product_id=p.id, date=prev_date).scalar() or 0

        sold_qty = qty_prev - qty_last
        if sold_qty < 0:
            sold_qty = 0

        revenue = sold_qty * (p.price or 0)
        total_business += revenue

        # Stock-out
        if qty_last == 0:
            stock_out_products.append(p)

        # Collect sales info
        if sold_qty > 0:
            sales_data.append({
                'name': p.name,
                'category': p.category,
                'sold_qty': sold_qty,
                'revenue': revenue
            })

    # 🔥 Rankings
    fast_selling = sorted(
        sales_data, key=lambda x: x['sold_qty'], reverse=True
    )[:10]

    top_earning = sorted(
        sales_data, key=lambda x: x['revenue'], reverse=True
    )[:10]

    message = (
        f"Your business from {prev_date} to {last_date} "
        f"generated R {total_business:.2f}"
    )


    # 📈 Line chart data (sales per date)
    chart_labels = []
    chart_values = []

    for i in range(1, len(dates)):
        current_date = dates[i]
        previous_date = dates[i - 1]

        daily_total = 0

        for p in products:
            qty_curr = db.session.query(InventoryRecord.quantity)\
                .filter_by(product_id=p.id, date=current_date).scalar() or 0

            qty_prev = db.session.query(InventoryRecord.quantity)\
                .filter_by(product_id=p.id, date=previous_date).scalar() or 0
            sold = qty_prev - qty_curr
            if sold < 0:
                sold = 0

            daily_total += sold * (p.price or 0)

        chart_labels.append(str(current_date))
        chart_values.append(round(daily_total, 2))


    return render_template(
        'main/summary.html',
        message=message,
        stock_out_products=stock_out_products,
        fast_selling=fast_selling,
        top_earning=top_earning,
        chart_labels=chart_labels,
        chart_values=chart_values
    )



@main.route('/new-stocks', methods=['GET', 'POST'])
@shop_required
def new_stocks():
    products = Product.query.filter_by(shop_id=session['shop_id']).all()

    if request.method == 'POST':
        product_id = int(request.form.get('product_id'))
        new_qty = int(request.form.get('new_quantity', 0))

        product = Product.query.filter_by(id=product_id, shop_id=session['shop_id']).first()
        if not product:
            flash("Product not found for this shop.", "danger")
            return redirect(url_for('main.add_product'))

        # Get the latest record (the last stock count)
        last_record = (
            InventoryRecord.query
            .join(Product)
            .filter(
                InventoryRecord.product_id == product_id,
                Product.shop_id == session['shop_id']
            )
            .order_by(InventoryRecord.date.desc())
            .first()
        )

        if last_record:
            # Update the *previous* record to include this new stock
            last_record.quantity += new_qty
            db.session.commit()

            flash(f"Added {new_qty} new units to {product.name} (backdated to {last_record.date}).", "success")
        else:
            # If product has no previous record, treat as initial stock
            new_record = InventoryRecord(
                product_id=product_id,
                date=date.today(),
                quantity=new_qty
            )
            db.session.add(new_record)
            db.session.commit()

            flash(f"Created initial stock record for {product.name} with {new_qty} units.", "info")

        return redirect(url_for('main.shop'))

    return render_template('main/new_stocks.html', products=products)

@main.route('/logout')
def logout():
    # Log out the user with Flask-Login
    logout_user()

    # Remove shop info from session
    session.pop('shop_id', None)
    session.pop('shop_name', None)

    flash("You’ve been logged out successfully.", "info")
    return redirect(url_for('main.enter_shop'))


@main.route('/print-stock-sheet')
@shop_required
def print_stock_sheet():
    shop_id = session.get("shop_id")

    if not shop_id:
        flash("No shop selected", "warning")
        return redirect(url_for("main.dashboard"))

    shop = Shop.query.get_or_404(shop_id)
    products = Product.query.filter_by(shop_id=shop_id).order_by(Product.name).all()

    pdf_buffer = generate_stock_sheet_pdf(shop, products)

    return send_file(
        pdf_buffer,
        as_attachment=True,
        download_name=f"stock_sheet_{shop.name}.pdf",
        mimetype="application/pdf"
    )
