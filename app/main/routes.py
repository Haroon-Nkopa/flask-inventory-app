#import main blueprint
from flask_login import current_user, logout_user
from . import main
from flask import render_template, request, redirect, url_for, flash, session, send_file, jsonify  
from ..models import Product, InventoryRecord, Shop, Sale, SaleItem
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



#making the add route restful

# 1. This just serves the HTML page shell
@main.route('/add')
@shop_required
def add_product():
    return render_template('main/add_product.html')

# 2. This is the REST API endpoint that does the work
@main.route('/api/products', methods=['POST'])
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
@shop_required
def stock_history():
    return render_template('main/stock_history.html')

# 2. The Data API
@main.route('/api/stock-history')
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
@shop_required
def take_stock():
    # Just serve the shell
    return render_template('main/stock_take.html', today=date.today())

# API to GET the product list for the table
@main.route('/api/stock-take-products', methods=['GET'])
@shop_required
def get_stock_take_products():
    shop_id = session.get('shop_id')
    products = Product.query.filter_by(shop_id=shop_id).all()
    return jsonify([{"id": p.id, "name": p.name} for p in products])


@main.route('/api/take-stock', methods=['POST'])
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
@shop_required
def summary():
    return render_template('main/summary.html')


@main.route('/api/summary')
@shop_required
def get_summary_api():
    shop_id = session.get('shop_id')
    dates_query = db.session.query(InventoryRecord.date).join(Product)\
        .filter(Product.shop_id == shop_id).distinct().order_by(InventoryRecord.date).all()
    dates = [d[0] for d in dates_query]

    if len(dates) < 2:
        return jsonify({"error": "Not enough history"}), 200

    last_date, prev_date = dates[-1], dates[-2]
    products = Product.query.filter_by(shop_id=shop_id).all()
    
    total_business = 0
    stock_out = []
    sales_data = []

    # Daily Chart Data
    chart_labels = []
    chart_values = []
    for i in range(1, len(dates)):
        daily_rev = 0
        for p in products:
            q_curr = db.session.query(InventoryRecord.quantity).filter_by(product_id=p.id, date=dates[i]).scalar() or 0
            q_prev = db.session.query(InventoryRecord.quantity).filter_by(product_id=p.id, date=dates[i-1]).scalar() or 0
            daily_rev += max(0, q_prev - q_curr) * (p.price or 0)
        chart_labels.append(str(dates[i]))
        chart_values.append(round(daily_rev, 2))

    # Potential Profit Logic
    pot_rev, pot_cost = 0, 0
    for p in products:
        latest = InventoryRecord.query.filter_by(product_id=p.id).order_by(InventoryRecord.date.desc()).first()
        qty = latest.quantity if latest else 0
        unit_cost = (p.batch_price / p.batch_size) if (p.batch_price and p.batch_size) else 0
        
        pot_rev += (qty * (p.price or 0))
        pot_cost += (qty * unit_cost)
        
        q_l = db.session.query(InventoryRecord.quantity).filter_by(product_id=p.id, date=last_date).scalar() or 0
        q_p = db.session.query(InventoryRecord.quantity).filter_by(product_id=p.id, date=prev_date).scalar() or 0
        sold = max(0, q_p - q_l)
        rev = sold * (p.price or 0)
        total_business += rev
        
        # FIX: Append objects so JS can read properties like .category and .price
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

    # THIS RETURN MUST BE ALIGNED WITH THE 'FOR' LOOP (4 spaces from the start)
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
@shop_required
def new_stocks():
    return render_template('main/new_stocks.html')

# 2. API GET - Returns the product list for the dropdown/list
@main.route('/api/products-list', methods=['GET'])
@shop_required
def get_products_list():
    shop_id = session.get('shop_id')
    products = Product.query.filter_by(shop_id=shop_id).all()
    return jsonify([{"id": p.id, "name": p.name} for p in products])

# 3. API POST - Processes the stock addition
@main.route('/api/new-stocks', methods=['POST'])
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
@shop_required
def pos():
    return render_template('main/pos.html')



@main.route('/api/pos/products', methods=['GET'])
@shop_required
def get_pos_products():
    shop_id = session.get('shop_id')
    products = Product.query.filter_by(shop_id=shop_id).order_by(Product.name).all()
    
    return jsonify([{
        "id": p.id, 
        "name": p.name, 
        "price": p.price  # Included for POS calculations
    } for p in products])


@main.route('/api/pos/checkout', methods=['POST'])
@shop_required
def pos_checkout_api():
    data = request.get_json()
    items = data.get('items', [])
    today = date.today()

    if not items:
        return jsonify({"error": "No items in cart"}), 400

    try:
        for item in items:
            p_id = item.get('product_id')
            sold_qty = int(item.get('quantity', 0))

            # Fetch the most recent inventory record
            last_record = InventoryRecord.query.filter_by(product_id=p_id)\
                .order_by(InventoryRecord.date.desc()).first()

            if not last_record:
                return jsonify({"error": f"No inventory record found for product ID {p_id}"}), 400

            # Validation
            if last_record.quantity < sold_qty:
                return jsonify({"error": f"Insufficient stock for {last_record.product.name}"}), 400

            # Logic: Update today or create new record for today
            new_qty = last_record.quantity - sold_qty
            
            if last_record.date == today:
                last_record.quantity = new_qty
            else:
                db.session.add(InventoryRecord(
                    product_id=p_id,
                    date=today,
                    quantity=new_qty
                ))

        db.session.commit()
        return jsonify({"status": "success", "message": "Transaction completed"}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Server error: {str(e)}"}), 500



@main.route('/sales-history')
@shop_required
def sales_history():
    # Serves the HTML structure; data is fetched via JS on the client side
    return render_template('main/sales_history.html')

@main.route('/api/sales-history', methods=['GET'])
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
