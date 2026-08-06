#import main blueprint
from flask_login import current_user, logout_user, login_required
from . import main
from flask import render_template, request, redirect, url_for, flash, session, send_file, jsonify 
from ..models import Product, LiveInventory, DailyInventorySnapshot, PhysicalInventoryCount, Shop, Sale, SaleItem
from .. import db
from datetime import date , datetime, timedelta  # Add this import
from ..decorators import shop_required, roles_required, payment_required
from app.utils.stock_sheet_pdf import generate_stock_sheet_pdf
from sqlalchemy import func
from sqlalchemy.orm import joinedload
from collections import defaultdict
from .helper import get_inventory_discrepancies



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
@login_required
@roles_required('owner', 'manager')
def add_user():
    return render_template('main/add_user.html')

# create a main add_user route, this one is post, only add the user to the database if the 
#they are legible() and 


#making the add route restful

# 1. This just serves the HTML page shell
@main.route('/add')
@roles_required('owner', 'manager', 'employee')
@login_required
@shop_required
def add_product():
    return render_template('main/add_product.html')




# 2. This is the REST API endpoint that does the work
@main.route('/api/products', methods=['POST'])
@login_required
@roles_required('owner', 'manager', 'employee')
@shop_required
def create_product_api():
    shop_id = session.get('shop_id')
    data = request.get_json() # Get JSON data from the fetch request

    if not data:
        return jsonify({"error": "No data provided"}), 400

    name = data.get('name', '').strip().lower()
    
    # Check if product exists
    existing_product = Product.query.filter_by(name=name, shop_id=shop_id).first()
    if existing_product:
        return jsonify({"error": f"Product '{name}' already exists"}), 400

    try:
        # Create new product using data from JSON
        new_product = Product(
            name=name.lower(),
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

        new_live = LiveInventory(
            product_id=new_product.id,
            quantity=0  # Set initial starting inventory state
            # Add other necessary structural columns for LiveInventory here
        )
        db.session.add(new_live)

        db.session.commit()
        return jsonify({"message": f"Product '{name}' added!", "id": new_product.id}), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

#edit product details
@main.route('/edit-product', methods=['GET'])
@roles_required('owner', 'manager', 'employee')
@login_required
@shop_required
def edit_product_page():
    shop_id = session.get('shop_id')
    # Fetch all items sorted alphabetically to keep the dropdown clean
    products = Product.query.filter_by(shop_id=shop_id).order_by(Product.name.asc()).all()
    return render_template('main/edit_product.html', products=products)



#modifying product attributes. 
@main.route('/api/products/<int:product_id>', methods=['PUT'])
@roles_required('owner', 'manager', 'employee')
@login_required
@shop_required
def update_product_api(product_id):
    shop_id = session.get('shop_id')
    data = request.get_json()

    if not data:
        return jsonify({"error": "No data provided"}), 400

    # 1. Look up the product and verify it belongs to this shop
    product = Product.query.filter_by(id=product_id, shop_id=shop_id).first()
    if not product:
        return jsonify({"error": "Product not found or access denied"}), 404

    # 2. Handle product renaming and prevent duplicate name conflicts
    new_name = data.get('name', '').strip()
    if new_name and new_name != product.name:
        existing_product = Product.query.filter_by(name=new_name, shop_id=shop_id).first()
        if existing_product:
            return jsonify({"error": f"Another product named '{new_name}' already exists"}), 400
        product.name = new_name

    try:
        # 3. Apply the updated details if present in JSON payload
        if 'category' in data:
            product.category = data.get('category', 'General').strip()
        if 'price' in data:
            product.price = float(data.get('price', 0))
        if 'size' in data:
            product.size = data.get('size', '').strip()
        if 'batch_size' in data:
            product.batch_size = int(data.get('batch_size', 1))
        if 'batch_price' in data:
            product.batch_price = float(data.get('batch_price', 0))
        if 'lower_bound' in data:
            product.lower_bound = int(data.get('lower_bound', 0))
        if 'batch_number' in data:
            product.batch_number = data.get('batch_number', '').strip()

        db.session.commit()
        return jsonify({"message": f"Product '{product.name}' updated successfully!"}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


#####


#making the stock-history route restful. 
# 1. The Shell Route
@main.route('/stock-history')
@payment_required
@login_required
@roles_required('owner', 'manager')
@shop_required
def stock_history():
    return render_template('main/stock_history.html')


@main.route('/api/stock-history')
@payment_required
@login_required
@roles_required('owner', 'manager')
@shop_required
def get_stock_history_api():
    shop_id = session.get('shop_id')
    
    # Read the query parameter string sent from JS (defaults to 'live')
    report_type = request.args.get('type', 'live').strip().lower()
    
    records_payload = []

    try:
        if report_type == 'live':
            # Fetch products alongside their strict 1-to-1 LiveInventory hook
            products = Product.query.filter_by(shop_id=shop_id).all()
            
            for product in products:
                # Fallback to 0 if live_inventory link hasn't been initialized yet
                qty = product.live_inventory.quantity if product.live_inventory else 0
                
                records_payload.append({
                    "product_name": product.name,
                    "category": product.category or 'General',
                    "size": product.size,
                    "quantity": qty,
                    "lower_bound": product.lower_bound
                })

        elif report_type == 'daily':
            # Query the 1-to-many snapshots table joined against shop products
            daily_records = db.session.query(DailyInventorySnapshot, Product)\
                .join(Product, DailyInventorySnapshot.product_id == Product.id)\
                .filter(Product.shop_id == shop_id)\
                .order_by(DailyInventorySnapshot.date.desc()).all()
                
            for snapshot, product in daily_records:
                records_payload.append({
                    "date": snapshot.date.strftime('%Y-%m-%d %H:%M') if isinstance(snapshot.date, datetime) else str(snapshot.date),
                    "product_name": product.name,
                    "category": product.category or 'General',
                    "quantity": snapshot.quantity
                })

        elif report_type == 'audited':
            # Query the 1-to-many physical count tracking table
            audit_records = db.session.query(PhysicalInventoryCount, Product)\
                .join(Product, PhysicalInventoryCount.product_id == Product.id)\
                .filter(Product.shop_id == shop_id)\
                .order_by(PhysicalInventoryCount.date.desc()).all()
                
            for audit, product in audit_records:
                # Safely pull the user identifier from the User relationship if loaded
                user_display = audit.user.username if (hasattr(audit, 'user') and audit.user) else "System"
                base_note = audit.notes if audit.notes else "No audit notes saved."
                
                records_payload.append({
                    "date": audit.date.strftime('%Y-%m-%d') if hasattr(audit.date, 'strftime') else str(audit.date),
                    "product_name": product.name,
                    "category": product.category or 'General',
                    "quantity": audit.counted_quantity, # FIXED: Changed from .quantity to match model
                    "notes": f"{base_note} (Audited by: {user_display})" # Added auditor name to tracking output
                })
        
        else:
            return jsonify({"error": f"Invalid reporting parameter option: '{report_type}'"}), 400

        # Return structural data array block matching your JS loadStockHistory engine expectation
        return jsonify({"records": records_payload}), 200

    except Exception as e:
        return jsonify({"error": "Failed fetching database records", "details": str(e)}), 500


    except Exception as e:
        return jsonify({"error": "Failed fetching database matrix details", "details": str(e)}), 500


######

@main.route('/take-stock')
@login_required
@payment_required
@roles_required('owner', 'manager', 'employee', 'auditor')
@shop_required
def take_stock():
    # Just serve the shell
    return render_template('main/stock_take.html', today=date.today())

# API to GET the product list for the table
@main.route('/api/stock-take-products', methods=['GET'])
@payment_required
@login_required
@roles_required('owner', 'manager', 'employee', 'auditor')
@shop_required
def get_stock_take_products():
    shop_id = session.get('shop_id')
    products = Product.query.filter_by(shop_id=shop_id).all()
    return jsonify([{"id": p.id, "name": p.name} for p in products])


@main.route('/api/take-stock', methods=['POST'])
@payment_required
@login_required
@roles_required('owner', 'manager', 'employee', 'auditor')
@shop_required
def submit_stock_api():
    shop_id = session.get('shop_id')
    
    products = Product.query.filter_by(shop_id=shop_id).all()
    today_date = date.today()
    data = request.get_json()

    if not data:
        return jsonify({"error": "No data provided"}), 400

    # Extract global operational note if provided across the payload root dictionary
    global_notes = data.get('notes', '').strip() or None

    # 1. Check if physical stock was already counted today
    existing_record = PhysicalInventoryCount.query.join(Product)\
        .filter(Product.shop_id == shop_id, PhysicalInventoryCount.date == today_date).first()
    
    if existing_record:
        return jsonify({"error": "Physical stock was already counted today."}), 400

    # 2. Validate logic (no increases)
    problematic = []
    stock_to_save = []

    for product in products:
        qty_input = int(data.get(str(product.id), 0))

        stock_to_save.append((product.id, qty_input))


    # 3. Save directly into your updated schema matrix mappings
    try:
        for p_id, qty in stock_to_save:
            # Check for individual item level notes, fall back to global audit note input string
            item_note = data.get(f"notes_{p_id}", "").strip() or global_notes
            
            new_audit = PhysicalInventoryCount(
                product_id=p_id, 
                date=today_date, 
                counted_quantity=qty,
                user_id=current_user.username, # Authenticated User Tracking Key
                notes=item_note  # Captured Notes Text Mapping String
            )
            db.session.add(new_audit)
        
        db.session.commit()
        return jsonify({"message": "Physical stock ledger recorded successfully!"}), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Failed to save physical count records", "details": str(e)}), 500

#####

@main.route('/api/inventory/discrepancies', methods=['GET'])
@login_required
@roles_required('owner')
@shop_required
def get_discrepancies_api():
    """
    Executes the helper query logic to calculate variances between
    the latest physical count updates and standard real-time stock balances.
    """
    shop_id = session.get('shop_id')
    
    try:
        # Call the standalone backend engine utility from helper.py
        mismatches = get_inventory_discrepancies(shop_id)
        
        return jsonify({
            "status": "success",
            "count": len(mismatches),
            "discrepancies": mismatches
        }), 200
        
    except Exception as e:
        # Prevent database locks by running a clean engine error catch fallback
        return jsonify({
            "status": "error",
            "message": "Failed to parse underlying database query streams."
        }), 500



# UI Route - Stays light, just serves the dashboard shell
@main.route('/summary')
@login_required
@payment_required
@roles_required('owner')
@shop_required
def summary():
    return render_template('main/summary.html')

@main.route('/api/summary/live', methods=['GET'])
@payment_required
@login_required
@roles_required('owner')
@shop_required
def get_live_summary_api():
    shop_id = session.get('shop_id')
    today_date = date.today()

    # 1. FETCH ALL PRODUCTS & LIVE INVENTORY IN ONE QUERY (Avoids N+1 lazy loading)
    products_with_inv = db.session.query(Product)\
        .outerjoin(Product.live_inventory)\
        .filter(Product.shop_id == shop_id)\
        .all()

    # Initialize data metrics
    stock_out = []
    pot_rev, pot_cost = 0.0, 0.0
    
    for p in products_with_inv:
        qty = p.live_inventory.quantity if p.live_inventory else 0
        unit_cost = (p.batch_price / p.batch_size) if (p.batch_price and p.batch_size) else 0.0
        
        pot_rev += (qty * (p.price or 0.0))
        pot_cost += (qty * unit_cost)
        
        if qty == 0:
            stock_out.append({
                "name": p.name,
                "category": p.category or "-",
                "price": float(p.price or 0.0)
            })

    # 2. GROUPED SALES METRICS (Fetches total quantity and revenue for ALL products at once)
    sales_query = db.session.query(
            SaleItem.product_id,
            Product.name,
            Product.category,
            func.sum(SaleItem.quantity).label('sold_qty'),
            func.sum(SaleItem.total_price).label('revenue')
        )\
        .join(Sale, SaleItem.sale_id == Sale.id)\
        .join(Product, SaleItem.product_id == Product.id)\
        .filter(Sale.shop_id == shop_id, func.date(Sale.timestamp) == today_date)\
        .group_by(SaleItem.product_id, Product.name, Product.category)\
        .all()

    sales_data = []
    today_revenue = 0.0

    for product_id, name, category, sold_qty, revenue in sales_query:
        sold_qty = int(sold_qty or 0)
        revenue = float(revenue or 0.0)
        today_revenue += revenue  # Accumulate today's revenue directly from product sums
        
        sales_data.append({
            'name': name,
            'category': category or "-",
            'sold_qty': sold_qty,
            'revenue': revenue
        })

    # 3. GROUPED 7-DAY TREND (Fetches historical values in a single database aggregation)
    start_date = today_date - timedelta(days=6)
    trend_query = db.session.query(
            func.date(Sale.timestamp).label('sale_date'),
            func.sum(SaleItem.total_price).label('day_rev')
        )\
        .join(Sale, SaleItem.sale_id == Sale.id)\
        .filter(Sale.shop_id == shop_id, func.date(Sale.timestamp) >= start_date)\
        .group_by(func.date(Sale.timestamp))\
        .all()

    # Map database trend results into a dictionary lookup
    # Note: Depending on your DB engine, 'sale_date' may return a date object or a string.
    trend_map = {str(row.sale_date): float(row.day_rev or 0.0) for row in trend_query}

    chart_labels, chart_values = [], []
    for d in range(6, -1, -1):
        target_day = today_date - timedelta(days=d)
        chart_labels.append(target_day.strftime("%A, %d %B"))
        # Match against our trend lookup dictionary
        chart_values.append(round(trend_map.get(str(target_day), 0.0), 2))

    return jsonify({
        "summary_type": "Live Summary (Today)",
        "total_revenue": round(today_revenue, 2),
        "potential_profit": round(pot_rev - pot_cost, 2),
        "stock_out": stock_out,
        "fast_selling": sorted(sales_data, key=lambda x: x['sold_qty'], reverse=True)[:10],
        "top_earning": sorted(sales_data, key=lambda x: x['revenue'], reverse=True)[:10],
        "chart": {"labels": chart_labels, "values": chart_values}
    }), 200



# 2. HISTORICAL DAILY COUNT SUMMARY (Utilises 'daily_inventory_snapshot' model)
@main.route('/api/summary/daily-count', methods=['GET'])
@payment_required
@login_required
@roles_required('owner')
@shop_required
def get_daily_count_summary_api():
    shop_id = session.get('shop_id')
    start_str = request.args.get('start_date')
    end_str = request.args.get('end_date')

    # Query unique snapshot log dates linked to this shop
    dates_query = db.session.query(DailyInventorySnapshot.date)\
        .join(Product)\
        .filter(Product.shop_id == shop_id)\
        .distinct()\
        .order_by(DailyInventorySnapshot.date)\
        .all()
    dates = [d[0] for d in dates_query]

    if len(dates) < 2:
        return jsonify({"error": "Not enough historical closing records available yet."}), 400

    # Apply date filters if submitted by frontend mini form
    if start_str and end_str:
        try:
            start_d = datetime.strptime(start_str, "%Y-%m-%d").date()
            end_d = datetime.strptime(end_str, "%Y-%m-%d").date()
            target_dates = [d for d in dates if start_d <= d <= end_d]
            if len(target_dates) < 2:
                return jsonify({"error": "Selected range must span at least 2 snapshot logs."}), 400
        except ValueError:
            return jsonify({"error": "Invalid date query formats."}), 400
    else:
        target_dates = dates[-7:] if len(dates) > 7 else dates # Default view window

    products = Product.query.filter_by(shop_id=shop_id).all()
    chart_labels, chart_values = [], []
    sales_data, stock_out = [], []
    total_business = 0.0

    # Calculate difference changes between subsequent historical ledger entries
    for i in range(1, len(target_dates)):
        daily_rev = 0.0
        for p in products:
            q_curr = db.session.query(DailyInventorySnapshot.closing_quantity)\
                .filter_by(product_id=p.id, date=target_dates[i]).scalar() or 0
            q_prev = db.session.query(DailyInventorySnapshot.closing_quantity)\
                .filter_by(product_id=p.id, date=target_dates[i-1]).scalar() or 0
            
            sold = max(0, q_prev - q_curr)
            rev = sold * (p.price or 0.0)
            daily_rev += rev
            
            # Populate aggregate stats for the active visual window
            if i == len(target_dates) - 1:
                total_business += rev
                if q_curr == 0:
                    stock_out.append({"name": p.name, "category": p.category or "-", "price": float(p.price or 0.0)})
                if sold > 0:
                    sales_data.append({'name': p.name, 'category': p.category or "-", 'sold_qty': sold, 'revenue': float(rev)})
                    
        chart_labels.append(target_dates[i].strftime("%A, %d %B"))
        chart_values.append(round(daily_rev, 2))

    return jsonify({
        "summary_type": f"Daily Stock Counts ({target_dates[0]} to {target_dates[-1]})",
        "total_revenue": round(total_business, 2),
        "stock_out": stock_out,
        "fast_selling": sorted(sales_data, key=lambda x: x['sold_qty'], reverse=True)[:10],
        "top_earning": sorted(sales_data, key=lambda x: x['revenue'], reverse=True)[:10],
        "chart": {"labels": chart_labels, "values": chart_values}
    }), 200


# 3. AUDITED SUMMARY ENDPOINT (Utilises 'physical_inventory_count' model)
@main.route('/api/summary/audited', methods=['GET'])
@payment_required
@login_required
@roles_required('owner')
@shop_required
def get_audited_summary_api():
    shop_id = session.get('shop_id')
    start_str = request.args.get('start_date')
    end_str = request.args.get('end_date')

    # Base query for physical counts matching the shop context
 # Base query for physical counts matching the shop context (User mapping removed)
    audit_query = db.session.query(PhysicalInventoryCount, Product.name)\
        .join(Product, PhysicalInventoryCount.product_id == Product.id)\
        .filter(Product.shop_id == shop_id)

    if start_str and end_str:
        try:
            start_d = datetime.strptime(start_str, "%Y-%m-%d").date()
            end_d = datetime.strptime(end_str, "%Y-%m-%d").date()
            audit_query = audit_query.filter(PhysicalInventoryCount.date.between(start_d, end_d))
        except ValueError:
            return jsonify({"error": "Invalid date metrics formatting"}), 400
    else:
        # Default to the last 30 days if no date parameters are set
        audit_query = audit_query.filter(PhysicalInventoryCount.date >= date.today() - timedelta(days=30))

    audits = audit_query.order_by(PhysicalInventoryCount.timestamp.desc()).all()
    
    # Structure variance logs for audit tables tracking user operational signatures
    audit_logs = []
    for count_record, prod_name, staff_member in audits:
        audit_logs.append({
            "date": count_record.date.strftime("%Y-%m-%d"),
            "timestamp": count_record.timestamp.strftime("%H:%M:%S"),
            "product_name": prod_name,
            "counted_qty": count_record.counted_quantity,
            "logged_by": staff_member,
            "notes": count_record.notes or ""
        })

    return jsonify({
        "summary_type": "Audited Internal Ledger Log",
        "audit_records": audit_logs,
        # Charts/values arrays empty or populated depending on custom variance logic
        "chart": {"labels": [log["date"] for log in audit_logs[:7]], "values": [log["counted_qty"] for log in audit_logs[:7]]}
    }), 200


@main.route('/logout', methods=['POST']) # Change GET to POST for security
def logout():
    logout_user()
    session.clear()
    return jsonify({"success": True, "redirect": url_for('main.enter_shop')}), 200

#######
@main.route('/print-stock-sheet')
@login_required
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
@login_required
@roles_required('owner', 'manager', 'employee', 'auditor')
@shop_required
def pos():
    return render_template('main/pos.html')


# 1. GET POS PRODUCTS - Now checks LiveInventory to return real stock quantities
@main.route('/api/pos/products', methods=['GET'])
@login_required
@payment_required
@roles_required('owner', 'manager', 'employee', 'auditor')
@shop_required
def get_pos_products():
    shop_id = session.get('shop_id')
    
    # Query products for this shop
    products = Product.query.filter_by(shop_id=shop_id).order_by(Product.name).all()
    
    payload = []
    for p in products:
        # Respect your strict 1-to-1 live_inventory relationship hook
        qty = p.live_inventory.quantity if p.live_inventory else 0
        
        payload.append({
            "id": p.id, 
            "name": p.name, 
            "price": p.price,       # Included for POS calculations
            "live_stock": qty       # Added so the frontend POS knows the active stock limit
        })
        
    return jsonify(payload), 200


# 2. POST POS CHECKOUT - Now updates LiveInventory directly and cuts out all old snapshots
@main.route('/api/pos/checkout', methods=['POST'])
@login_required
@payment_required
@roles_required('owner', 'manager', 'employee', 'auditor')
@shop_required
def pos_checkout_api():
    data = request.get_json() or {}
    items = data.get('items', [])

    if not items:
        return jsonify({"error": "No items in cart"}), 400

    shop_id = session.get('shop_id')
    user_id = session.get('user_id') # Pull operational user footprint from active session

    try:
        # Consolidate duplicate cart items
        cart = defaultdict(int)
        for item in items:
            try:
                product_id = int(item.get('product_id'))
                quantity = int(item.get('quantity', 0))
            except (TypeError, ValueError):
                return jsonify({"error": "Invalid product or quantity format supplied."}), 400

            if quantity <= 0:
                continue

            cart[product_id] += quantity

        if not cart:
            return jsonify({"error": "No valid items in cart"}), 400

        cart_product_ids = list(cart.keys())

        # Load cart products in ONE optimized database query
        products = Product.query.filter(Product.id.in_(cart_product_ids)).all()
        product_map = {product.id: product for product in products}

        # ---------------------------------------------------------
        # PHASE 1: Strictly Validate Everything Against Live Stock First
        # ---------------------------------------------------------
        running_total = 0.0

        for product_id, sold_qty in cart.items():
            product = product_map.get(product_id)

            # Security and existence checks
            if not product or product.shop_id != shop_id:
                return jsonify({"error": f"Product ID {product_id} not found in this shop registry."}), 400

            # Access the live inventory state via your model constraint hook
            live_inventory = product.live_inventory

            if not live_inventory:
                return jsonify({"error": f"No active live stock record found initialized for {product.name}."}), 400

            if live_inventory.quantity < sold_qty:
                return jsonify({"error": f"Insufficient stock for {product.name}. Available: {live_inventory.quantity}, Cart: {sold_qty}"}), 400

            running_total += float(product.price) * sold_qty

        # ---------------------------------------------------------
        # PHASE 2: Create Sale and Sub-Items (Matching Sale schema fields)
        # ---------------------------------------------------------
        new_sale = Sale(
            shop_id=shop_id,
            user_id=user_id,                         # Track which employee finalized transaction
            total_amount=running_total,
            timestamp=datetime.utcnow()             # Respect standard UTC timestamps
        )
        db.session.add(new_sale)
        db.session.flush() # Yields the absolute new_sale.id cleanly

        sale_items = []

        # ---------------------------------------------------------
        # PHASE 3: Deduct Live Stocks directly and save transaction
        # ---------------------------------------------------------
        for product_id, sold_qty in cart.items():
            product = product_map[product_id]
            live_inventory = product.live_inventory # Guaranteed to exist from phase 1
            unit_price = float(product.price)

            # Build line item detail matching your exact SaleItem naming attributes
            sale_items.append(
                SaleItem(
                    sale_id=new_sale.id,
                    product_id=product_id,
                    quantity=sold_qty,
                    unit_price=unit_price,
                    total_price=unit_price * sold_qty
                )
            )

            # DIRECT CHANGE TO THE LIVE DATA ONLY: Update the live rolling balance quantity
            live_inventory.quantity -= sold_qty
            
            # Update the custom track timestamp property explicitly
            live_inventory.last_updated = datetime.utcnow()

        # Batch save items to keep performance fast
        db.session.bulk_save_objects(sale_items)
        
        # Save structural adjustments safely across transactions
        db.session.commit()

        return jsonify({
            "status": "success",
            "sale_id": new_sale.id,
            "total_amount": running_total,
            "message": "Live stock balance deducted. Transaction and sales logs updated successfully."
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Server processing error: {str(e)}"}), 500


@main.route('/sales-history')
@login_required
@payment_required
@roles_required('owner', 'manager', 'auditor')
@shop_required
def sales_history():
    # Serves the HTML structure safely; data is fetched via JS on the client side
    return render_template('main/sales_history.html')


@main.route('/api/sales-history', methods=['GET'])
@login_required
@payment_required
@roles_required('owner', 'manager', 'auditor')
@shop_required
def get_sales_history_api():
    shop_id = session.get('shop_id')
    page = request.args.get('page', 1, type=int)
    per_page = 20 

    # FIXED: Added joinedload(Sale.items).joinedload(SaleItem.product)
    # This forces SQLAlchemy to fetch ALL data in 1 query instead of hitting the DB 60+ times.
    sales_pagination = Sale.query.filter_by(shop_id=shop_id)\
        .options(joinedload(Sale.items).joinedload(SaleItem.product))\
        .order_by(Sale.timestamp.desc())\
        .paginate(page=page, per_page=per_page, error_out=False)

    return jsonify({
        "sales": [{
            "id": s.id,
            "timestamp": s.timestamp.strftime('%d %b %Y, %H:%M'),
            "total": float(s.total_amount),
            "items": [{
                # Safe relationship queries because data is pre-cached via joinedload
                "product_name": item.product.name if item.product else "Deleted Product",
                "category": (item.product.category if item.product else "-") or "-",
                "quantity": item.quantity,
                "unit_price": float(item.unit_price),
                "total_price": float(item.total_price)
            } for item in s.items]
        } for s in sales_pagination.items],
        "total_pages": sales_pagination.pages,
        "current_page": sales_pagination.page
    }), 200



@main.route('/api/check-session', methods=['GET'])
@roles_required('owner', 'manager', 'employee', 'auditor')
def check_session():
    if session.get('shop_id'):
        return jsonify({
            "authenticated": True, 
            "shop_name": session.get('shop_name')
        }), 200
    return jsonify({"authenticated": False}), 200



# 1. Add the UI Route view handler to your main routes file
@main.route('/new-stocks')
@login_required
@roles_required('owner', 'manager', 'employee', 'auditor')
@shop_required
def new_stocks():
    return render_template('main/new_stocks.html')


# Add this API endpoint to your main blueprint routes file
@main.route('/api/products-list', methods=['GET'])
@login_required
@roles_required('owner', 'manager', 'employee', 'auditor')
@shop_required
def get_products_list():
    shop_id = session.get('shop_id')
    products = Product.query.filter_by(shop_id=shop_id).order_by(Product.name).all()
    
    return jsonify([
        {"id": p.id, "name": p.name} 
        for p in products
    ]), 200



# Add this API endpoint to your main blueprint routes file (app/main/routes.py)
@main.route('/api/new-stocks', methods=['POST'])
@login_required
@roles_required('owner', 'manager', 'employee', 'auditor')
@shop_required
def add_new_stock_api():
    shop_id = session.get('shop_id')
    data = request.get_json()

    if not data:
        return jsonify({"error": "No data provided"}), 400

    try:
        product_id = int(data.get('product_id'))
        new_qty = int(data.get('new_quantity', 0))
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid numerical parameters supplied."}), 400

    # Verify product belongs to the active shop context context
    product = Product.query.filter_by(id=product_id, shop_id=shop_id).first()
    if not product:
        return jsonify({"error": "Product not found for this shop."}), 404

    try:
        # TARGET THE NEW LIVE INVENTORY ARCHITECTURE DIRECTLY
        live_record = LiveInventory.query.filter_by(product_id=product_id).first()

        if live_record:
            live_record.quantity += new_qty
            message = f"Added {new_qty} units to live stock for {product.name}. Current rolling total: {live_record.quantity}"
        else:
            live_record = LiveInventory(
                product_id=product_id,
                quantity=new_qty
            )
            db.session.add(live_record)
            message = f"Initialized active live stock record for {product.name} with {new_qty} units."

        db.session.commit()
        return jsonify({"message": message, "new_total": live_record.quantity}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Failed to update live inventory balances", "details": str(e)}), 500
