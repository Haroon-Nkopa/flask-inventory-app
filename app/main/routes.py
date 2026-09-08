#import main blueprint
from flask_login import current_user, logout_user, login_required
from . import main
from flask import app, render_template, request, redirect, url_for, flash, session, send_file, jsonify, abort
from ..models import Product, LiveInventory, DailyInventorySnapshot, PhysicalInventoryCount, Shop, Sale, SaleItem, CashlessTransaction, StockReceivedLog
from .. import db
from datetime import date , datetime, timedelta, timezone  # Add this import
from ..decorators import shop_required, roles_required, payment_required
from app.utils.stock_sheet_pdf import generate_stock_sheet_pdf
from sqlalchemy import func
from sqlalchemy.orm import joinedload
from collections import defaultdict
from .helper import  execute_inventory_merge, get_product_discrepancies_timeline



@main.route('/', methods=['GET', 'POST']) 
def enter_shop():
    
    if session.get('shop_id'):
        return redirect(url_for('main.shop'))   
    if request.method == 'POST':
        shop_name = request.form.get('shop_name').strip().title()
        print(shop_name)
        # Case-insensitive match
        shop = Shop.query.filter(Shop.name == shop_name).first()
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
    # Default explicitly to 'live' to match your HTML dropdown's initial state
    report_type = request.args.get('type', 'live').strip().lower()

    try:
        # --- PATHWAY 1: LIVE REPORT ---
        if report_type == 'live':
            products = Product.query.filter_by(shop_id=shop_id).all()
            records_payload = []
            for product in products:
                qty = product.live_inventory.quantity if product.live_inventory else 0
                records_payload.append({
                    "product_name": product.name,
                    "category": product.category or 'General',
                    "size": product.size,
                    "quantity": qty,
                    "lower_bound": product.lower_bound
                })
            return jsonify({"report_type": "live", "records": records_payload}), 200

        # --- PATHWAY 2 & 3: MATRIX STRUCTURES ('daily' or 'audited') ---
        if report_type == 'audited':
            db_records = db.session.query(PhysicalInventoryCount, Product)\
                .join(Product, PhysicalInventoryCount.product_id == Product.id)\
                .filter(Product.shop_id == shop_id)\
                .order_by(PhysicalInventoryCount.date.desc()).all()
        elif report_type == 'daily':
            db_records = db.session.query(DailyInventorySnapshot, Product)\
                .join(Product, DailyInventorySnapshot.product_id == Product.id)\
                .filter(Product.shop_id == shop_id)\
                .order_by(DailyInventorySnapshot.date.desc()).all()
        else:
            return jsonify({"error": f"Invalid type parameter: {report_type}"}), 400

        # Diagnostics: Print to console to see if rows exist in DB
        print(f"DEBUG LOG: Found {len(db_records)} records for report type '{report_type}' in shop {shop_id}")

        unique_dates_set = set()
        matrix_map = defaultdict(lambda: {"name": "", "category": "", "history": {}, "notes": {}})

        for record_item, product in db_records:
            # Safely handle diverse database date formats
            if hasattr(record_item.date, 'strftime'):
                date_str = record_item.date.strftime('%Y-%m-%d')
            else:
                date_str = str(record_item.date)[:10] # Grab just the YYYY-MM-DD component string

            unique_dates_set.add(date_str)
            
            matrix_map[product.id]["name"] = product.name
            matrix_map[product.id]["category"] = product.category or 'General'
            
            if report_type == 'audited':
                matrix_map[product.id]["history"][date_str] = record_item.counted_quantity
                user_display = record_item.user.username if (hasattr(record_item, 'user') and record_item.user) else "System"
                base_note = record_item.notes if record_item.notes else "No notes."
                matrix_map[product.id]["notes"][date_str] = f"{base_note} (By: {user_display})"
            else:
                # FIXED: Pointed directly to your explicit model property assignment attribute
                matrix_map[product.id]["history"][date_str] = record_item.closing_quantity

        sorted_dates = sorted(list(unique_dates_set), reverse=True)

        stock_data_output = []
        for p_id, item_data in matrix_map.items():
            stock_data_output.append({
                "name": item_data["name"],
                "category": item_data["category"],
                "history": item_data["history"],
                "notes": item_data["notes"]
            })

        return jsonify({
            "report_type": report_type,
            "dates": sorted_dates,
            "stock_data": stock_data_output
        }), 200

    except Exception as e:
        import traceback
        print(traceback.format_exc()) # Prints the exact line that broke to your server terminal
        return jsonify({"error": "Failed generating stock matrix payload", "details": str(e)}), 500

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

####
from datetime import datetime, timezone

@main.route('/api/inventory/discrepancies', methods=['GET'])
@login_required
@roles_required('owner')
@shop_required
def get_discrepancies_api():
    shop_id = session.get('shop_id')
    
    try:
        # Unpack the underlying engine helper tuple payload data
        counts_data, timeline_data = get_product_discrepancies_timeline(shop_id)
        
        tabular_mismatches = []
        oldest_audit_date = None

        # Structure the final list format calculating variance variations dynamically
        for prod_id, info in counts_data.items():
            variance = info['live_quantity'] - info['audited_quantity']
            
            # Extract selling price passed down from the engine dictionary payload
            selling_price = info.get('selling_price', 0.0)
            
            # Extract the raw string date for tracking the global range
            last_audit_str = info.get('last_audit_date')
            if last_audit_str:
                if oldest_audit_date is None or last_audit_str < oldest_audit_date:
                    oldest_audit_date = last_audit_str

            tabular_mismatches.append({
                "product_id": prod_id,
                "product_name": info['product_name'],
                "live_quantity": info['live_quantity'],
                "audited_quantity": info['audited_quantity'],
                "difference": variance,
                "selling_price": float(selling_price) # Guarantees JavaScript gets a clean number
            })
            
        return jsonify({
            "status": "success",
            "tabular_data": tabular_mismatches,
            "timeline_data": timeline_data,
            "last_audit_date": oldest_audit_date if oldest_audit_date else "the last count date",
            "today_date": datetime.now(timezone.utc).strftime("%Y-%m-%d")
        }), 200
        
    except Exception as e:
        print(f"Discrepancy API Parse Stream Fail: {str(e)}")
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

    # 1. AGGREGATE FINANCIALS & STOCK-OUTS IN DATABASE (Fixed with select_from)
    unit_cost_expr = func.coalesce(Product.batch_price / Product.batch_size, 0.0)
    qty_expr = func.coalesce(LiveInventory.quantity, 0)
    
    financials = db.session.query(
        func.sum(qty_expr * func.coalesce(Product.price, 0.0)).label('pot_rev'),
        func.sum(qty_expr * unit_cost_expr).label('pot_cost')
    ).select_from(Product)\
     .outerjoin(LiveInventory, Product.id == LiveInventory.product_id)\
     .filter(Product.shop_id == shop_id).first()

    pot_rev = float(financials.pot_rev or 0.0)
    pot_cost = float(financials.pot_cost or 0.0)

    # NEW: Fetch unverified cashless transactions joined with Product details
    unverified_cashless_query = db.session.query(
            CashlessTransaction.id,
            Product.name,
            CashlessTransaction.quantity,
            CashlessTransaction.total_value,
            CashlessTransaction.allocation_type,
            CashlessTransaction.timestamp
        )\
        .join(Product, CashlessTransaction.product_id == Product.id)\
        .filter(
            CashlessTransaction.shop_id == shop_id, 
            func.coalesce(CashlessTransaction.verified, False) == False
        ).all()

    unverified_transactions = [
        {
            "transaction_id": tx_id,
            "product_name": name,
            "quantity": qty,
            "total_value": float(val or 0.0),
            "type": alloc_type,
            "timestamp": timestamp.isoformat() if timestamp else None
        }
        for tx_id, name, qty, val, alloc_type, timestamp in unverified_cashless_query
    ]

    # Fetch only products that are actually out of stock
    stock_out_query = db.session.query(Product.name, Product.category, Product.price)\
        .outerjoin(LiveInventory, Product.id == LiveInventory.product_id)\
        .filter(Product.shop_id == shop_id, func.coalesce(LiveInventory.quantity, 0) == 0).all()

    stock_out = [
        {"name": name, "category": category or "-", "price": float(price or 0.0)}
        for name, category, price in stock_out_query
    ]

    # 2. OPTIMISED GROUPED SALES METRICS (Fixed join targets)
    sales_query = db.session.query(
            Product.name,
            Product.category,
            func.sum(SaleItem.quantity).label('sold_qty'),
            func.sum(SaleItem.total_price).label('revenue')
        )\
        .select_from(SaleItem)\
        .join(Sale, SaleItem.sale_id == Sale.id)\
        .join(Product, SaleItem.product_id == Product.id)\
        .filter(Sale.shop_id == shop_id, Sale.timestamp >= today_date)\
        .group_by(Product.id, Product.name, Product.category)\
        .all()

    sales_data = []
    today_revenue = 0.0

    for name, category, sold_qty, revenue in sales_query:
        rev_val = float(revenue or 0.0)
        today_revenue += rev_val
        sales_data.append({
            'name': name,
            'category': category or "-",
            'sold_qty': int(sold_qty or 0),
            'revenue': rev_val
        })

    # 3. OPTIMISED 7-DAY TREND (Fixed to start securely from Sale table)
    start_date = today_date - timedelta(days=6)
    trend_query = db.session.query(
            func.date(Sale.timestamp).label('sale_date'),
            func.sum(SaleItem.total_price).label('day_rev')
        )\
        .select_from(Sale)\
        .join(SaleItem, SaleItem.sale_id == Sale.id)\
        .filter(Sale.shop_id == shop_id, Sale.timestamp >= start_date)\
        .group_by(func.date(Sale.timestamp))\
        .all()

    trend_map = {str(row.sale_date): float(row.day_rev or 0.0) for row in trend_query}

    chart_labels, chart_values = [], []
    for d in range(6, -1, -1):
        target_day = today_date - timedelta(days=d)
        chart_labels.append(target_day.strftime("%A, %d %B"))
        chart_values.append(round(trend_map.get(str(target_day), 0.0), 2))

    return jsonify({
        "summary_type": "Live Summary (Today)",
        "total_revenue": round(today_revenue, 2),
        "potential_profit": round(pot_rev - pot_cost, 2),
        "stock_out": stock_out,
        "unverified_cashless_transactions": unverified_transactions,  # Injected mapped data list here
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
    
    # PULL AUTHENTICATED USER FOOTPRINT DIRECTLY FROM FLASK-LOGIN CURRENT_USER
    user_id = current_user.id 

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
            user_id=user_id,                         # Tracks exact user primary key bindings securely
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


# @main.route('/api/inventory/discrepancies', methods=['GET'])
# @login_required
# def api_get_inventory_discrepancies():
#     shop_id = session.get('current_shop_id')

 
#     try:
#         # 1. Run your original helper function exactly as it stands
#         counts_metadata, timeline_phrases = get_product_discrepancies_timeline(shop_id)
#         print(counts_metadata)

#         formatted_tabular_data = []
#         oldest_audit_date = None

#         # 2. Complete the data map using the actual models
#         for product_id, item_data in counts_metadata.items():
#             print(product_id)
#             # Direct database lookups for the items left out by the helper
#             product = db.session.query(Product).get(product_id)
#             selling_price = product.price if product else 0.0
            

#             last_audit = db.session.query(PhysicalInventoryCount)\
#                 .filter(PhysicalInventoryCount.product_id == product_id)\
#                 .order_by(PhysicalInventoryCount.timestamp.desc())\
#                 .first()
            
#             last_audit_str = last_audit.date.strftime('%Y-%m-%d') if last_audit else None

#             # Calculate oldest audit date for the summary range block
#             if last_audit_str:
#                 if oldest_audit_date is None or last_audit_str < oldest_audit_date:
#                     oldest_audit_date = last_audit_str

                 
#             formatted_tabular_data.append({
#                 "product_id": product_id,
#                 "product_name": item_data.get("product_name", ""),
#                 "live_quantity": item_data.get("live_quantity", 0),
#                 "audited_quantity": item_data.get("audited_quantity", 0),
#                 "selling_price": float(selling_price) # Guarantees JavaScript gets a clean number
#             })
        
#         return jsonify({
#             "status": "success",
#             "tabular_data": formatted_tabular_data,
#             "timeline_data": timeline_phrases,
#             "last_audit_date": oldest_audit_date if oldest_audit_date else "the last count date",
#             "today_date": datetime.now(timezone.utc).strftime("%Y-%m-%d")
#         }), 200

#     except Exception as e:
#         print("DISCREPANCY API ERROR:", str(e))
#         return jsonify({
#             "status": "error",
#             "error": str(e)
#         }), 500



@main.route('/api/inventory/merge-variance', methods=['POST'])
@login_required
def api_merge_variance():
    # 1. Parse incoming body parameters
    data = request.get_json() or {}
    
    product_id = data.get('product_id')
    actual_count = data.get('actual_count')
    reason = data.get('reason')

    # 2. Defensive validations
    if product_id is None or actual_count is None or not reason:
        return jsonify({'message': 'Missing operational data fields inside post body.'}), 400
        
    # 3. Offload processing tasks to the core helper function
    success, message = execute_inventory_merge(
        product_id=product_id,
        actual_count=actual_count,
        reason=reason,
        current_user_id=current_user.id
    )
    
    # 4. Return matching API engine response states
    if not success:
        return jsonify({'message': message}), 500 if "engine error" in message else 404
        
    return jsonify({
        'status': 'success', 
        'message': message
    }), 200



@main.route('/api/pos/cashless', methods=['POST'])
@login_required
def pos_cashless_api():
    # Fetch target operation scope out of safe active tracking configurations
    shop_id = session.get('shop_id')
    if not shop_id:
        return jsonify({"error": "No active shop found in session context"}), 400

    data = request.get_json() or {}
    allocation_type = data.get('allocation_type')
    explanation = data.get('explanation')
    items = data.get('items', [])

    # Structural Payload Verification
    if not allocation_type or allocation_type not in ['personal', 'stoloto', 'other']:
        return jsonify({"error": "Invalid or missing allocation type selection"}), 400

    if allocation_type == 'other' and not explanation:
        return jsonify({"error": "Explanation details missing for category context choice 'other'"}), 400

    if not items:
        return jsonify({"error": "Transaction payload contains no item lines"}), 400

    try:
        # Process transaction using an atomised execution architecture to safely roll back on database faults
        for item in items:
            p_id = item.get('product_id')
            qty = int(item.get('quantity', 0))

            if qty <= 0:
                return jsonify({"error": "Product line quantities must be values greater than 0"}), 400

            # 1. Look up data item details checking scope ownership
            product = Product.query.filter_by(id=p_id, shop_id=shop_id).first()
            if not product:
                return jsonify({"error": f"Product key allocation missing or inaccessible: ID {p_id}"}), 404

            # 2. Inspect real-time stock balances 
            live_stock = LiveInventory.query.filter_by(product_id=product.id).first()
            if not live_stock or live_stock.quantity < qty:
                return jsonify({"error": f"Insufficient inventory for: '{product.name}'. Stock left: {live_stock.quantity if live_stock else 0}"}), 400

            # 3. Deduct transaction item total counts directly from LiveInventory tracking logs
            live_stock.quantity -= qty
            live_stock.last_updated = datetime.now(timezone.utc)

            # 4. Generate internal bookkeeping audit logs inside your custom CashlessTransaction structure
            unit_price = float(product.price)
            total_value = unit_price * qty

            new_record = CashlessTransaction(
                shop_id=shop_id,
                user_id=current_user.id,
                product_id=product.id,
                quantity=qty,
                unit_price=unit_price,
                total_value=total_value,
                allocation_type=allocation_type,
                explanation=explanation,
                date=datetime.now(timezone.utc).date(),
                timestamp=datetime.now(timezone.utc)
            )
            db.session.add(new_record)

        

        # Flush operational cache mutations safely out to your active target relational storage database
        db.session.commit()
        return jsonify({"success": True, "message": "Cashless transaction processing complete"}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Internal critical accounting ledger error tracking database save: {str(e)}"}), 500




@main.route('/api/cashless-transaction/<int:tx_id>/verify', methods=['POST'])
@login_required
@roles_required('owner')
@shop_required
def verify_cashless_transaction(tx_id):
    shop_id = session.get('shop_id')
    
    # Query row entry asserting correct tenant scoping ownership isolation
    transaction = CashlessTransaction.query.filter_by(id=tx_id, shop_id=shop_id).first()
    
    if not transaction:
        return jsonify({"error": "Transaction log entry not found or unauthorized access"}), 404
        
    try:
        # Reconcile book value flag
        transaction.verified = True
        db.session.commit()
        return jsonify({"message": "Transaction verified and inventory records reconciled."}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Database mutation crash tracking anomaly: {str(e)}"}), 500


@main.route('/financials', methods=['GET'])
@login_required
@roles_required('owner')
@shop_required
def financial_management():
    # Render your new interface context page here
    return render_template('main/financial_management.html')


@main.route('/api/financials/management-data', methods=['GET'])
@login_required
@roles_required('owner')
@shop_required
def get_financial_management_data_api():
    shop_id = session.get('shop_id')
    
    # 1. Fetch all products belonging to the active isolated tenant shop profile
    products = Product.query.filter_by(shop_id=shop_id).all()
    
    under_priced = []  # Stores items where cost per unit >= selling price

    for product in products:
        b_price = product.batch_price or 0.0
        b_size = product.batch_size or 1  # Default fallback constraint if structural integer is missing

        # Guard against zero division errors safely
        if b_size <= 0:
            continue

        # Calculate cost per unit (min_price_per_product)
        min_price_per_product = b_price / b_size
        
        # In your model, product.price represents the selling unit_price
        selling_price = product.price or 0.0

        # Evaluation Condition: If cost per unit is greater than or equal to selling price
        if min_price_per_product >= selling_price:
            under_priced.append({
                "product_id": product.id,
                "name": product.name,
                "category": product.category or "-",
                "min_price_per_product": round(min_price_per_product, 2),
                "selling_price": round(selling_price, 2),
                "margin_loss": round(min_price_per_product - selling_price, 2)
            })

    return jsonify({
        "status": "success",
        "shop_id": shop_id,
        "total_products_checked": len(products),
        "under_priced_count": len(under_priced),
        "under_priced": under_priced  # Returns the array of matching objects
    }), 200



#lets create a route that get all product and lists all the profict magins per product
@main.route('/api/financials/profit-margins', methods=['GET'])
@login_required
@roles_required('owner')
@shop_required
def get_profit_margins_api():
    shop_id = session.get('shop_id')
    
    # Fetch all products for the active shop
    products = Product.query.filter_by(shop_id=shop_id).all()
    
    profit_margins = []

    for product in products:
        b_price = product.batch_price or 0.0
        b_size = product.batch_size or 1

        if b_size <= 0:
            continue

        min_price_per_product = b_price / b_size
        selling_price = product.price or 0.0

        margin = selling_price - min_price_per_product
        profit_margins.append({
            "product_id": product.id,
            "name": product.name,
            "category": product.category or "-",
            "min_price_per_product": round(min_price_per_product, 2),
            "selling_price": round(selling_price, 2),
            "profit_margin": round(margin, 2)
        })

    return jsonify({
        "status": "success",
        "shop_id": shop_id,
        "total_products_checked": len(products),
        "profit_margins": profit_margins
    }), 200



@main.route('/api/financials/business-health', methods=['GET'])
@login_required
@roles_required('owner')
@shop_required
def get_business_health_analysis_api():
    shop_id = session.get('shop_id')
    
    # Fetch all products belonging to the active shop
    products = Product.query.filter_by(shop_id=shop_id).all()
    
    product_breakdown = []
    total_restock_budget_needed = 0.0
    total_realised_revenue = 0.0
    total_realised_profit = 0.0

    for product in products:
        # 1. Determine sales since last batch delivery day (NP)
        last_received_log = StockReceivedLog.query.filter_by(
            shop_id=shop_id, 
            product_id=product.id
        ).order_by(StockReceivedLog.date.desc()).first()
        
        np = 0
        if last_received_log:
            sales_since_delivery = db.session.query(func.sum(SaleItem.quantity))\
                .select_from(SaleItem)\
                .join(Sale, SaleItem.sale_id == Sale.id)\
                .filter(
                    Sale.shop_id == shop_id,
                    SaleItem.product_id == product.id,
                    func.date(Sale.timestamp) >= last_received_log.date
                ).scalar()
            np = int(sales_since_delivery or 0)
        else:
            sales_historical = db.session.query(func.sum(SaleItem.quantity))\
                .filter(SaleItem.product_id == product.id).scalar()
            np = int(sales_historical or 0)

        # 2. Extract pricing metrics
        live_qty = int(product.live_inventory.quantity if product.live_inventory else 0)
        selling_price = float(product.price or 0.0)
        batch_cost = float(product.batch_price or 0.0)
        batch_size = int(product.batch_size or 1)
        
        if batch_size <= 0:
            batch_size = 1

        # 3. Core Formulation Logic
        unit_cost = batch_cost / batch_size
        
        # Actual cash generated by this product from real sales
        product_revenue = np * selling_price
        
        # CRITICAL: This is the money you MUST save from your sales to afford the next batch
        product_restock_budget = np * unit_cost
        
        # True profit earned from actual sales after deducting the replacement cost
        product_profit = product_revenue - product_restock_budget

        # Accumulate shop-wide metrics
        total_restock_budget_needed += product_restock_budget
        total_realised_revenue += product_revenue
        total_realised_profit += product_profit

        product_breakdown.append({
            "product_id": product.id,
            "product_name": product.name,
            "live_quantity": live_qty,
            "units_sold_since_delivery": np,
            "unit_cost": round(unit_cost, 2),
            "revenue_earned": round(product_revenue, 2),
            "allocated_restock_budget": round(product_restock_budget, 2),
            "realised_profit": round(product_profit, 2)
        })

    # 4. Strategic Business Quality Evaluation
    # If the owner took more money out than total_realised_profit, they are dipping into stock money
    business_quality = (
        f"To restock your store seamlessly, you must have R {round(total_restock_budget_needed, 2)} "
        f"saved in your bank account right now. Your true real-world profit so far is R {round(total_realised_profit, 2)}."
    )
    
    if total_realised_profit > 0:
        health_status_code = "HEALTHY"
    else:
        health_status_code = "WARNING"

    return jsonify({
        "status": "success",
        "shop_id": shop_id,
        "business_quality": business_quality,
        "health_status_code": health_status_code,
        "summary": {
            "total_realised_revenue": round(total_realised_revenue, 2),
            "total_restock_budget_to_save": round(total_restock_budget_needed, 2),
            "total_realised_profit": round(total_realised_profit, 2),
            "total_products_tracked": len(products)
        },
        "products": product_breakdown
    }), 200
        
