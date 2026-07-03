@main.route('/api/analytics/daily-cash-split', methods=['GET'])
@shop_required
def daily_cash_split_api():
    shop_id = session.get('shop_id')
    today = date.today()

    try:
        # 1. Fetch all items sold TODAY specifically
        todays_sales = db.session.query(SaleItem).join(Sale).filter(
            Sale.shop_id == shop_id,
            func.date(Sale.created_at) == today
        ).all()

        if not todays_sales:
            return jsonify({
                "total_revenue": 0.0,
                "supplier_restock_fund": 0.0,
                "take_home_profit": 0.0,
                "msg": "No sales recorded today yet."
            }), 200

        total_revenue = 0.0
        supplier_restock_fund = 0.0

        # 2. Extract exactly what cash belongs to who based on TODAY'S transactions
        for item in todays_sales:
            product = Product.query.get(item.product_id)
            
            # Add to total cash sitting in the physical drawer
            total_revenue += float(item.total_price)
            
            # The exact wholesale cost replacement value of what left the store today
            supplier_restock_fund += (int(item.quantity) * float(product.cost_price))

        # 3. Calculate what the owner can safely take home
        take_home_profit = total_revenue - supplier_restock_fund

        return jsonify({
            "status": "success",
            "date": str(today),
            "financial_split": {
                "total_cash_in_drawer": round(total_revenue, 2),
                "untouchable_supplier_money": round(supplier_restock_fund, 2),
                "safe_spendable_profit": round(take_home_profit, 2)
            }
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


[ THE MAIZE MEAL SALE DAY ]
Owner sells 1 bag of Maize Meal ──> Receives R180 Cash in hand.
                                        │
             ┌──────────────────────────┴──────────────────────────┐
             ▼                                                     ▼
     WHAT THE APP SAYS:                                    WHAT THE OWNER DOES:
"Keep R140 for the wholesaler!                      "Wow, R180 extra cash today! 
 Only R40 is yours to spend."                        Let me buy personal things or 
             │                                       extra snacks I don't need."
             ▼                                                     │
[ RESULT: CASH DISAPPEARS ] <──────────────────────────────────────┘
             │
             ▼
Two weeks later, the shelf is empty. 
The owner needs R140, but the money was spent on the day of the sale.