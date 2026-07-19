#import main blueprint
from flask_login import current_user, logout_user
from . import main
from flask import render_template, request, redirect, url_for, flash, session, send_file, jsonify 
from ..models import Product, InventoryRecord, Shop, Sale, SaleItem
from .. import db
from datetime import date , datetime  # Add this import
from ..decorators import shop_required, roles_required, payment_required
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
            session['shop_paid'] = shop.paid # payment satus of the shop
            return redirect(url_for('main.shop', shop_id=shop.id))
        else:
            flash('Shop not found. Please contact admin to register it. 083 224 2491', 'danger')

    return render_template('main/enter_shop.html', year=datetime.now().year)

@main.route('/shop')
@shop_required
@roles_required('owner', 'admin', 'manager', 'auditor', 'employee')
def shop():
    products = Product.query.filter_by(shop_id=session['shop_id']).all()
    return render_template('main/shop.html', products=products)


#a route that renders add_user.html
@main.route('/add_user')
@shop_required
@roles_required('owner', 'manager')
def add_user():
    return render_template('main/add_user.html')

# create a main add_user route, this one is post, only add the user to the database if the 
#they are legible() and 


#making the add route restful

# 1. This just serves the HTML page shell
@main.route('/add')
@roles_required('owner', 'manager', 'employee')
@shop_required
def add_product():
    return render_template('main/add_product.html')

# 2. This is the REST API endpoint that does the work
@main.route('/api/products', methods=['POST'])
@roles_required('owner', 'manager', 'employee')
@shop_required
def create_product_api():
    shop_id = session.get('shop_id')
    data = request.get_json() # Get JSON data from the fetch request

    if not data:
        return jsonify({"error": "No data provided"}), 400

    name = data.get('name', '').strip()
    
    # Check if product exists
    existing_product = Product.query.filter_by(name=name, shop_id=shop_id).first()
    if existing_product:
        return jsonify({"error": f"Product '{name}' already exists"}), 400

    try:
        # Create new product using data from JSON
        new_product = Product(
            name=name,
            category=data.get('category', 'General').strip(),
            price=float(data.get('price', 0)),
            size=data.get('size', '').strip(),
            batch_size=int(data.get('batch_size', 1)),
            batch_price=float(data.get('batch_price', 0)),
            lower_bound=int(data.get('lower_bound', 0)),
            batch_number=data.get('batch_number', '').strip(),
            shop_id=shop_id
        )
        db.session.add(new_product)
        db.session.flush()

        # Handle latest inventory record (keeping your logic)
        latest_record = db.session.query(InventoryRecord.date)\
            .join(Product).filter(Product.shop_id == shop_id)\
            .order_by(InventoryRecord.date.desc()).first()

        if latest_record:
            new_record = InventoryRecord(
                product_id=new_product.id,
                date=latest_record.date,
                quantity=0
            )
            db.session.add(new_record)

        db.session.commit()
        return jsonify({"message": f"Product '{name}' added!", "id": new_product.id}), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500



#####


#making the stock-history route restful. 
# 1. The Shell Route
@main.route('/stock-history')
@payment_required
@roles_required('owner', 'manager')
@shop_required
def stock_history():
    return render_template('main/stock_history.html')

# 2. The Data API
@main.route('/api/stock-history')
@payment_required
@roles_required('owner', 'manager')
@shop_required
def get_stock_history_api():
    shop_id = session.get('shop_id')

    # Get unique dates
    date_query = db.session.query(InventoryRecord.date)\
        .join(Product).filter(Product.shop_id == shop_id)\
        .distinct().order_by(InventoryRecord.date).all()
    
    dates = [d[0].strftime('%Y-%m-%d') for d in date_query]

    # Get stock data
    products = Product.query.filter_by(shop_id=shop_id).all()
    stock_data = []

    for product in products:
        # Create a dictionary for each product's history
        history = {record.date.strftime('%Y-%m-%d'): record.quantity for record in product.records}
        stock_data.append({
            "name": product.name,
            "history": history
        })

    return jsonify({
        "dates": dates,
        "stock_data": stock_data
    })

######

@main.route('/take-stock')
@payment_required
@roles_required('owner', 'manager', 'employee', 'auditor')
@shop_required
def take_stock():
    # Just serve the shell
    return render_template('main/stock_take.html', today=date.today())

# API to GET the product list for the table
@main.route('/api/stock-take-products', methods=['GET'])
@payment_required
@roles_required('owner', 'manager', 'employee', 'auditor')
@shop_required
def get_stock_take_products():
    shop_id = session.get('shop_id')
    products = Product.query.filter_by(shop_id=shop_id).all()
    return jsonify([{"id": p.id, "name": p.name} for p in products])


@main.route('/api/take-stock', methods=['POST'])
@payment_required
@roles_required('owner', 'manager', 'employee', 'auditor')
@shop_required
def submit_stock_api():
    shop_id = session.get('shop_id')
    products = Product.query.filter_by(shop_id=shop_id).all()
    today_date = date.today()
    data = request.get_json()  # Get JSON from JS fetch

    # 1. Check if already captured today
    existing_record = InventoryRecord.query.join(Product)\
        .filter(Product.shop_id == shop_id, InventoryRecord.date == today_date).first()
    
    if existing_record:
        return jsonify({"error": "Stock was already counted today."}), 400

    # 2. Validate logic (no increases)
    problematic = []
    stock_to_save = []

    for product in products:
        # Match product ID from the incoming JSON data
        qty_input = int(data.get(str(product.id), 0))

        previous_record = InventoryRecord.query.filter(
            InventoryRecord.product_id == product.id,
            InventoryRecord.date < today_date
        ).order_by(InventoryRecord.date.desc()).first()

        if previous_record and qty_input > previous_record.quantity:
            problematic.append(f"{product.name} (Prev: {previous_record.quantity}, New: {qty_input})")
        
        stock_to_save.append((product.id, qty_input))

    if problematic:
        return jsonify({
            "error": "Stock count cannot be greater than previous records.",
            "details": problematic
        }), 400

    # 3. Save
    for p_id, qty in stock_to_save:
        db.session.add(InventoryRecord(product_id=p_id, date=today_date, quantity=qty))
    
    db.session.commit()
    return jsonify({"message": "Stock captured successfully for today!"}), 201

#####


@main.route('/summary')
@payment_required
@roles_required('owner')
@shop_required
def summary():
    return render_template('main/summary.html')

from sqlalchemy import func

@main.route('/api/summary')
@payment_required
@roles_required('owner')
@shop_required
def get_summary_api():
    shop_id = session.get('shop_id')
    
    # 1. Fetch available dates for this specific shop
    dates_query = db.session.query(InventoryRecord.date).join(Product)\
        .filter(Product.shop_id == shop_id).distinct().order_by(InventoryRecord.date).all()
    dates = [d[0] for d in dates_query]

    if len(dates) < 2:
        return jsonify({"error": "Not enough history"}), 200

    last_date, prev_date = dates[-1], dates[-2]
    products = Product.query.filter_by(shop_id=shop_id).all()
    
    # 2. BATCH QUERY 1: Fetch ALL historical inventory records for these products in ONE shot
    product_ids = [p.id for p in products]
    all_historical_records = InventoryRecord.query.filter(
        InventoryRecord.product_id.in_(product_ids),
        InventoryRecord.date.in_(dates)
    ).all()
    
    # Map to memory dictionary lookup speed: {(product_id, date): quantity}
    history_map = {
        (r.product_id, r.date): r.quantity for r in all_historical_records
    }

    # 3. BATCH QUERY 2: Fetch LATEST quantities for Potential Profit calculations in ONE shot
    subq = db.session.query(
        InventoryRecord.product_id,
        func.max(InventoryRecord.date).label('max_date')
    ).filter(InventoryRecord.product_id.in_(product_ids)).group_by(InventoryRecord.product_id).subquery()

    latest_records = db.session.query(InventoryRecord).join(
        subq, (InventoryRecord.product_id == subq.c.product_id) & (InventoryRecord.date == subq.c.max_date)
    ).all()
    
    # Map to memory dictionary lookup speed: {product_id: quantity}
    latest_qty_map = {r.product_id: r.quantity for r in latest_records}

    # --- Start Processing Data Entirely in Memory ---
    total_business = 0
    stock_out = []
    sales_data = []

    # Daily Chart Data Processing (Now runs instantly)
    chart_labels = []
    chart_values = []
    for i in range(1, len(dates)):
        daily_rev = 0
        for p in products:
            q_curr = history_map.get((p.id, dates[i]), 0)
            q_prev = history_map.get((p.id, dates[i-1]), 0)
            daily_rev += max(0, q_prev - q_curr) * (p.price or 0)
        chart_labels.append(str(dates[i]))
        chart_values.append(round(daily_rev, 2))

    # Potential Profit & Analytics Logic Processing (Now runs instantly)
    pot_rev, pot_cost = 0, 0
    for p in products:
        qty = latest_qty_map.get(p.id, 0)
        unit_cost = (p.batch_price / p.batch_size) if (p.batch_price and p.batch_size) else 0
        
        pot_rev += (qty * (p.price or 0))
        pot_cost += (qty * unit_cost)
        
        q_l = history_map.get((p.id, last_date), 0)
        q_p = history_map.get((p.id, prev_date), 0)
        sold = max(0, q_p - q_l)
        rev = sold * (p.price or 0)
        total_business += rev
        
        if q_l == 0: 
            stock_out.append({
                "name": p.name,
                "category": p.category or "-",
                "price": float(p.price or 0)
            })
            
        if sold > 0: 
            sales_data.append({
                'name': p.name, 
                'category': p.category or "-",
                'sold_qty': sold, 
                'revenue': float(rev)
            })

    return jsonify({
        "message": f"Business from {prev_date} to {last_date}: R {total_business:.2f}",
        "total_revenue": total_business,
        "potential_profit": round(pot_rev - pot_cost, 2),
        "stock_out": stock_out,
        "fast_selling": sorted(sales_data, key=lambda x: x['sold_qty'], reverse=True)[:10],
        "top_earning": sorted(sales_data, key=lambda x: x['revenue'], reverse=True)[:10],
        "chart": {"labels": chart_labels, "values": chart_values}
    })

#####


# 1. UI Route - Just serves the HTML shell
@main.route('/new-stocks')
@roles_required('owner', 'manager', 'employee', 'auditor')
@shop_required
def new_stocks():
    return render_template('main/new_stocks.html')

# 2. API GET - Returns the product list for the dropdown/list
@main.route('/api/products-list', methods=['GET'])
@roles_required('owner', 'manager', 'employee', 'auditor')
@shop_required
def get_products_list():
    shop_id = session.get('shop_id')
    products = Product.query.filter_by(shop_id=shop_id).all()
    return jsonify([{"id": p.id, "name": p.name} for p in products])

# 3. API POST - Processes the stock addition
@main.route('/api/new-stocks', methods=['POST'])
@roles_required('owner', 'manager', 'employee', 'auditor')
@shop_required
def add_new_stock_api():
    shop_id = session.get('shop_id')
    data = request.get_json()

    if not data:
        return jsonify({"error": "No data provided"}), 400

    product_id = int(data.get('product_id'))
    new_qty = int(data.get('new_quantity', 0))

    # Verify product belongs to the shop
    product = Product.query.filter_by(id=product_id, shop_id=shop_id).first()
    if not product:
        return jsonify({"error": "Product not found for this shop."}), 404

    try:
        # Get the latest record for backdating or initial entry
        last_record = (
            InventoryRecord.query
            .join(Product)
            .filter(
                InventoryRecord.product_id == product_id,
                Product.shop_id == shop_id
            )
            .order_by(InventoryRecord.date.desc())
            .first()
        )

        if last_record:
            # Update the existing record (backdating logic)
            last_record.quantity += new_qty
            message = f"Added {new_qty} units to {product.name}. Total for {last_record.date}: {last_record.quantity}"
        else:
            # Create initial stock record
            last_record = InventoryRecord(
                product_id=product_id,
                date=date.today(),
                quantity=new_qty
            )
            db.session.add(last_record)
            message = f"Created initial stock record for {product.name} with {new_qty} units."

        db.session.commit()
        return jsonify({"message": message, "new_total": last_record.quantity}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@main.route('/logout', methods=['POST']) # Change GET to POST for security
def logout():
    logout_user()
    session.clear()
    return jsonify({"success": True, "redirect": url_for('main.enter_shop')}), 200

#######
@main.route('/print-stock-sheet')
@roles_required('owner', 'manager','employee', 'auditor')
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

######



@main.route('/pos')
@payment_required
@roles_required('owner', 'manager', 'employee', 'auditor')
@shop_required
def pos():
    return render_template('main/pos.html')



@main.route('/api/pos/products', methods=['GET'])
@payment_required
@roles_required('owner', 'manager', 'employee', 'auditor')
@shop_required
def get_pos_products():
    shop_id = session.get('shop_id')
    products = Product.query.filter_by(shop_id=shop_id).order_by(Product.name).all()
    
    return jsonify([{
        "id": p.id, 
        "name": p.name, 
        "price": p.price  # Included for POS calculations
    } for p in products])


from collections import defaultdict
from datetime import date
from sqlalchemy import func


@main.route('/api/pos/checkout', methods=['POST'])
@payment_required
@roles_required('owner', 'manager', 'employee', 'auditor')
@shop_required
def pos_checkout_api():
    data = request.get_json() or {}
    items = data.get('items', [])

    if not items:
        return jsonify({"error": "No items in cart"}), 400

    today = date.today()
    shop_id = session.get('shop_id')

    try:
        # ----------------------------------------
        # Consolidate duplicate cart items
        # ----------------------------------------
        cart = defaultdict(int)

        for item in items:
            try:
                product_id = int(item.get('product_id'))
                quantity = int(item.get('quantity', 0))
            except (TypeError, ValueError):
                return jsonify({
                    "error": "Invalid product or quantity"
                }), 400

            if quantity <= 0:
                continue

            cart[product_id] += quantity

        if not cart:
            return jsonify({
                "error": "No valid items in cart"
            }), 400

        # --- OPTIMIZATION STEP: Get ALL shop product IDs for complete syncing ---
        all_shop_product_ids = [
            p.id for p in db.session.query(Product.id).filter_by(shop_id=shop_id).all()
        ]
        
        # Pull items from cart keys
        cart_product_ids = list(cart.keys())

        # ----------------------------------------
        # Load cart products in ONE query
        # ----------------------------------------
        products = Product.query.filter(
            Product.id.in_(cart_product_ids)
        ).all()

        product_map = {
            product.id: product
            for product in products
        }

        # ----------------------------------------
        # Get latest inventory record per product (Expanded for ALL shop products)
        # ----------------------------------------
        latest_dates = db.session.query(
            InventoryRecord.product_id,
            func.max(InventoryRecord.date).label('latest_date')
        ).filter(
            InventoryRecord.product_id.in_(all_shop_product_ids)  # Pull historical records for everything
        ).group_by(
            InventoryRecord.product_id
        ).subquery()

        inventory_records = db.session.query(
            InventoryRecord
        ).join(
            latest_dates,
            (
                InventoryRecord.product_id ==
                latest_dates.c.product_id
            ) &
            (
                InventoryRecord.date ==
                latest_dates.c.latest_date
            )
        ).all()

        inventory_map = {
            record.product_id: record
            for record in inventory_records
        }

        # ----------------------------------------
        # Validate everything first
        # ----------------------------------------
        running_total = 0.0

        for product_id, sold_qty in cart.items():

            product = product_map.get(product_id)

            if not product:
                return jsonify({
                    "error": f"Product ID {product_id} not found"
                }), 400

            # Same ownership check as original
            if product.shop_id != shop_id:
                return jsonify({
                    "error": f"Product ID {product_id} not found"
                }), 400

            inventory = inventory_map.get(product_id)

            if not inventory:
                return jsonify({
                    "error":
                    f"No inventory record found for {product.name}"
                }), 400

            if inventory.quantity < sold_qty:
                return jsonify({
                    "error":
                    f"Insufficient stock for {product.name}"
                }), 400

            running_total += (
                float(product.price) * sold_qty
            )

        # ----------------------------------------
        # Create sale
        # ----------------------------------------
        new_sale = Sale(
            shop_id=shop_id,
            total_amount=running_total
        )

        db.session.add(new_sale)
        db.session.flush()

        # ----------------------------------------
        # Create sale items and update inventory
        # ----------------------------------------
        sale_items = []
        synced_today_ids = set()  # Track which IDs have an active record for 'today'

        for product_id, sold_qty in cart.items():

            product = product_map[product_id]
            inventory = inventory_map[product_id]

            unit_price = float(product.price)

            sale_items.append(
                SaleItem(
                    sale_id=new_sale.id,
                    product_id=product_id,
                    quantity=sold_qty,
                    unit_price=unit_price,
                    total_price=unit_price * sold_qty
                )
            )

            new_qty = inventory.quantity - sold_qty

            if inventory.date == today:
                inventory.quantity = new_qty
            else:
                db.session.add(
                    InventoryRecord(
                        product_id=product_id,
                        date=today,
                        quantity=new_qty
                    )
                )
            
            synced_today_ids.add(product_id)

        db.session.bulk_save_objects(sale_items)

        # ----------------------------------------
        # NEW LOGIC: In-Memory Daily Snapshot Sync
        # ----------------------------------------
        # Iterate over ALL products to catch any items not purchased today
        for p_id in all_shop_product_ids:
            if p_id in synced_today_ids:
                continue  # Already updated during checkout loop
                
            last_record = inventory_map.get(p_id)
            
            if last_record and last_record.date < today:
                # Copy previous snapshot count into today
                db.session.add(
                    InventoryRecord(
                        product_id=p_id,
                        date=today,
                        quantity=last_record.quantity
                    )
                )
            elif not last_record:
                # Brand new product edge-case safety net
                db.session.add(
                    InventoryRecord(
                        product_id=p_id,
                        date=today,
                        quantity=0
                    )
                )

        # ----------------------------------------
        # Commit all transitions safely
        # ----------------------------------------
        db.session.commit()

        return jsonify({
            "status": "success",
            "sale_id": new_sale.id,
            "total_amount": running_total,
            "message": "Transaction and sales log completed"
        }), 200

    except Exception as e:
        db.session.rollback()

        return jsonify({
            "error": f"Server error: {str(e)}"
        }), 500


@main.route('/sales-history')
@payment_required
@roles_required('owner', 'manager', 'auditor')
@shop_required
def sales_history():
    # Serves the HTML structure; data is fetched via JS on the client side
    return render_template('main/sales_history.html')

@main.route('/api/sales-history', methods=['GET'])
@payment_required
@roles_required('owner', 'manager', 'auditor')
@shop_required
def get_sales_history_api():
    shop_id = session.get('shop_id')
    page = request.args.get('page', 1, type=int)
    per_page = 20 

    sales_pagination = Sale.query.filter_by(shop_id=shop_id)\
        .order_by(Sale.timestamp.desc())\
        .paginate(page=page, per_page=per_page)

    return jsonify({
        "sales": [{
            "id": s.id,
            "timestamp": s.timestamp.strftime('%d %b %Y, %H:%M'),
            "total": float(s.total_amount),
            # NEW: Add the nested items list here
            "items": [{
                "product_name": item.product.name,
                "category": item.product.category,
                "quantity": item.quantity,
                "unit_price": float(item.unit_price),
                "total_price": float(item.total_price)
            } for item in s.items]
        } for s in sales_pagination.items],
        "total_pages": sales_pagination.pages,
        "current_page": sales_pagination.page
    })



@main.route('/api/check-session', methods=['GET'])
@roles_required('owner', 'manager', 'employee', 'auditor')
def check_session():
    if session.get('shop_id'):
        return jsonify({
            "authenticated": True, 
            "shop_name": session.get('shop_name')
        }), 200
    return jsonify({"authenticated": False}), 200


