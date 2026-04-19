from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_mysqldb import MySQL
from flask import jsonify 
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, flash

password = 'pass123'
hashed_password = generate_password_hash(password, method='pbkdf2:sha256')

# --- Blueprint Imports ---
from customers import customers_bp
from order import order_bp
from products import products_bp
from employeeMan import EmployeeMan_bp
from Suppliers import Suppliers_bp
from WarehouseView import WarehouseView_bp
from payment import payment_bp
from tailoring import tailoring_bp

app = Flask(__name__)
app.secret_key = 'a-very-secret-key-for-sessions'  

# --- App Configuration ---
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'Nadeenjaber12nada' 
app.config['MYSQL_DB'] = 'ScarletDressShop'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

mysql = MySQL(app)
app.mysql = mysql

# --- Blueprint Registrations ---
app.register_blueprint(customers_bp)
app.register_blueprint(order_bp)
app.register_blueprint(products_bp)
app.register_blueprint(EmployeeMan_bp)
app.register_blueprint(Suppliers_bp)
app.register_blueprint(WarehouseView_bp)
app.register_blueprint(payment_bp)
app.register_blueprint(tailoring_bp)

@app.context_processor
def inject_dashboard_url():
    """
    Injects a dynamic 'dashboard_url' into all templates.
    This allows the "Back" buttons on shared pages like Order Management
    to point to the correct dashboard for either a manager or an employee.
    """
    if 'manager_loggedin' in session:
        return dict(dashboard_url=url_for('manager_page'))
    
    elif 'employee_loggedin' in session:
        return dict(dashboard_url=url_for('employee_page'))
    
    elif 'customer_id' in session:
        return dict(dashboard_url=url_for('main_page'))
    
    else:
        return dict(dashboard_url=url_for('home'))

# --- Main Routes ---
@app.route('/')
def home():
    return render_template('welcome.html')

# --- Customer Authentication ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form.get('password')

        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM Customers WHERE email = %s", (email,))
        user = cur.fetchone()
        cur.close()

        if user and check_password_hash(user['passwordHash'], password):
            # Set session for a logged-in CUSTOMER
            session['loggedin'] = True
            session['customer_id'] = user['customer_id']
            session['name'] = user['name']
            flash("Welcome back!", "success")
            return redirect(url_for('main_page'))
        else:
            flash("Incorrect email or password.", "danger")
            return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        phone = request.form['phone']
        address = request.form.get('address')
        hashed_pw = generate_password_hash(password)
        
        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO Customers (name, email, passwordHash, phone, address) VALUES (%s, %s, %s, %s, %s)",
                    (name, email, hashed_pw, phone, address))
        mysql.connection.commit()
        cur.close()

        flash("Account created successfully! Please login.", "success")
        return redirect(url_for('login'))
    return render_template('signup.html')

@app.route('/employee_login', methods=['GET', 'POST'])
def employee_login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form.get('password')

        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM Employees WHERE email = %s", (email,))
        user = cur.fetchone()
        cur.close()

        if user and user['passwordHash'] == password:
            if user['role'] == 'Manager':
                flash("Managers must use the Manager Login page.", "warning")
                return redirect(url_for('manager_login'))

            session['loggedin'] = True
            session['employee_loggedin'] = True 
            session['employee_id'] = user['employee_id']
            session['name'] = user['name']
            session['role'] = user['role'] 
            
            flash(f"Welcome back, {user['name']}!", "success")
            return redirect(url_for('employee_page'))
        else:
            flash("Incorrect email or password.", "danger")
            return redirect(url_for('employee_login'))

    return render_template('employee_login.html')

@app.route('/manager_login', methods=['GET', 'POST'])
def manager_login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form.get('password')

        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM Employees WHERE email = %s", (email,))
        user = cur.fetchone()
        cur.close()

        if user and user['passwordHash'] == password and user['role'] == 'Manager':
            session['loggedin'] = True
            session['manager_loggedin'] = True
            session['employee_id'] = user['employee_id']
            session['name'] = user['name']
            session['role'] = 'Manager' 

            flash(f"Welcome back, Manager {user['name']}!", "success")
            return redirect(url_for('manager_page'))
        else:
            flash("Invalid credentials or you are not a manager.", "danger")
            return redirect(url_for('manager_login'))

    return render_template('manager_login.html')

@app.route('/manager')
def manager_page():
    if 'manager_loggedin' not in session:
        flash("You must be logged in as a manager to view this page.", "warning")
        return redirect(url_for('manager_login'))
    
    return render_template('manager.html')

@app.route('/employee')
def employee_page():
    if 'employee_loggedin' not in session:
        flash("You must be logged in as an employee to view this page.", "warning")
        return redirect(url_for('employee_login'))

    return render_template('employee.html')

@app.route('/main')
def main_page():
    if 'customer_id' not in session:
        return redirect(url_for('login'))
    
    cur = mysql.connection.cursor()
    try:
        filter_category = request.args.get('category')
        sort_by = request.args.get('sort', 'name_asc') 
        price_range = request.args.get('price_range')

        base_query = "SELECT * FROM Products WHERE stock_quantity > 0"
        params = []

        if filter_category:
            base_query += " AND category = %s"
            params.append(filter_category)

        if price_range:
            min_price, max_price = price_range.split('-')
            base_query += " AND price BETWEEN %s AND %s"
            params.append(min_price)
            params.append(max_price)
        
        if sort_by == 'price_asc':
            base_query += " ORDER BY price ASC"
        elif sort_by == 'price_desc':
            base_query += " ORDER BY price DESC"
        else: 
            base_query += " ORDER BY name ASC"

        cur.execute(base_query, tuple(params))
        products = cur.fetchall()

        cur.execute("SELECT DISTINCT category FROM Products WHERE stock_quantity > 0 AND category IS NOT NULL ORDER BY category")
        categories = cur.fetchall()

        customer_id = session['customer_id']
        cur.execute("SELECT product_id FROM Wishlist WHERE customer_id = %s", (customer_id,))
        wishlist_items = [item['product_id'] for item in cur.fetchall()]
        
        return render_template('mainPage.html', 
                               products=products, 
                               categories=categories,
                               wishlist=wishlist_items,
                               name=session.get('name'), 
                               current_year=datetime.utcnow().year,
                               selected_category=filter_category,
                               selected_sort=sort_by,
                               selected_price=price_range)
    finally:
        cur.close() 

@app.route('/logout')
def logout(): 
    session.pop('loggedin', None)
    session.pop('customer_id', None)
    session.pop('employee_id', None)
    session.pop('employee_loggedin', None)
    session.pop('manager_loggedin', None)
    session.pop('name', None)
    session.pop('role', None)
        
    flash("You have been logged out. Your cart has been saved.", "success")
    return redirect(url_for('home'))

@app.route('/sales_report')
def sales_report_page():
    if 'manager_loggedin' not in session:
        flash("You must be logged in as a manager to view reports.", "warning")
        return redirect(url_for('manager_login'))

    cur = None
    try:
        cur = mysql.connection.cursor()
        current_time = datetime.now()
        year = request.args.get('year', default=current_time.year, type=int)
        month = request.args.get('month', default=current_time.month, type=int)
        
        query = """
            SELECT 
                o.order_id, c.name AS customer_name, p.name AS product_name, p.category,
                o.order_date, oi.quantity, oi.price_at_time_of_purchase
            FROM OrderItems oi
            JOIN Orders o ON oi.order_id = o.order_id
            JOIN Customers c ON o.customer_id = c.customer_id
            JOIN Products p ON oi.product_id = p.product_id
            WHERE YEAR(o.order_date) = %s AND MONTH(o.order_date) = %s
            ORDER BY o.order_date DESC;
        """
        cur.execute(query, (year, month))
        sales_data = cur.fetchall()
        total_sales = sum(item['quantity'] * item['price_at_time_of_purchase'] for item in sales_data)
        
        return render_template(
            'sales_report.html', sales=sales_data, total_sales=total_sales,
            selected_year=year, selected_month=month, current_year=current_time.year
        )
    except Exception as e:
        flash(f"Database error: {e}. Ensure 'Orders' and 'OrderItems' tables exist.", "danger")
        return render_template('sales_report.html', sales=[], total_sales=0, selected_year=datetime.now().year, selected_month=datetime.now().month, current_year=datetime.now().year)
    finally:
        if cur:
            cur.close()


@app.route('/checkout', methods=['POST'])
def checkout():
    if 'customer_id' not in session: 
        flash("Please log in to place an order.", "warning")
        return redirect(url_for('login'))

    cart = session.get('cart', [])
    if not cart:
        flash("Your cart is empty.", "warning")
        return redirect(url_for('main_page'))

    cur = None
    try:
        customer_id = session['customer_id']
        cur = mysql.connection.cursor()

        # Get current prices for all products in the cart
        product_ids = [item['product_id'] for item in cart]
        if not product_ids:
             flash("Cart is empty.", "warning")
             return redirect(url_for('main_page'))

        format_strings = ','.join(['%s'] * len(product_ids))
        cur.execute(f"SELECT product_id, price FROM Products WHERE product_id IN ({format_strings})", tuple(product_ids))
        products_prices = {str(p['product_id']): p['price'] for p in cur.fetchall()}
        
        total_amount = sum(float(products_prices[str(item['product_id'])]) * int(item['quantity']) for item in cart)

        selected_services_ids = request.form.getlist('tailoring_services') 
        if selected_services_ids:
            format_strings_services = ','.join(['%s'] * len(selected_services_ids))
            cur.execute(f"SELECT service_id, price FROM TailoringServices WHERE service_id IN ({format_strings_services})", tuple(selected_services_ids))
            services_prices = cur.fetchall()
            
            for service in services_prices:
                total_amount += service['price']

        cur.execute(
            "INSERT INTO Orders (customer_id, employee_id, order_date, total_amount, status) VALUES (%s, %s, %s, %s, %s)",
            (customer_id, None, datetime.now(), total_amount, 'Pending Payment')
        )
        order_id = cur.lastrowid

        for item in cart:
            price_at_purchase = products_prices[str(item['product_id'])]
            cur.execute(
                "INSERT INTO OrderItems (order_id, product_id, quantity, price_at_time_of_purchase) VALUES (%s, %s, %s, %s)",
                (order_id, item['product_id'], item['quantity'], price_at_purchase)
            )

        if selected_services_ids:
            for service_id in selected_services_ids:
                cur.execute(
                    "INSERT INTO TailorServiceRequest (order_id, service_id) VALUES (%s, %s)",
                    (order_id, service_id)
                )

        mysql.connection.commit()
        session.pop('cart', None) 
        flash("Order placed successfully! Please complete your payment.", "success")
        
        return redirect(url_for('payment.process_payment', order_id=order_id))

    except Exception as e:
        if cur:
             mysql.connection.rollback() 
        flash(f"An error occurred during checkout: {e}", "danger")
        return redirect(url_for('main_page')) 
    finally:
        if cur:
            cur.close()

@app.route('/update_quantity', methods=['POST'])
def update_quantity():
    product_id = request.form['product_id']
    action = request.form['action']

    cart = session.get('cart', [])

    for item in cart:
        if str(item['product_id']) == str(product_id):
            if action == 'increase':
                item['quantity'] += 1
            elif action == 'decrease' and item['quantity'] > 1:
                item['quantity'] -= 1
            break

    session['cart'] = cart
    return redirect(url_for('ordersss_page'))

@app.route('/cart')
def cart_page():
    if 'loggedin' not in session:
        flash("Please log in to view your cart.", "warning")
        return redirect(url_for('login'))
        
    cart = session.get('cart', [])
    
    total_price = 0
    if cart:
        total_price = sum(float(item['price']) * int(item['quantity']) for item in cart)

    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM TailoringServices ORDER BY type")
    tailoring_services = cur.fetchall()
    cur.close()

    return render_template('cart.html', cart=cart, total_price=total_price, tailoring_services=tailoring_services) 


@app.route('/update_cart/<product_id>', methods=['POST'])
def update_cart(product_id):
    """
    Updates the quantity of a specific item in the cart.
    """
    if 'cart' not in session or not session['cart']:
        return redirect(url_for('cart_page'))

    cart = session['cart']
    action = request.form.get('action') 

    for item in cart:
        if item['product_id'] == product_id:
            if action == 'increase':
                item['quantity'] += 1
            elif action == 'decrease':
                if item['quantity'] > 1:
                    item['quantity'] -= 1
                else:
                    cart.remove(item)
            break
    
    session['cart'] = cart
    return redirect(url_for('cart_page'))


@app.route('/remove_from_cart/<product_id>', methods=['POST'])
def remove_from_cart(product_id):
    """
    Removes an entire item from the cart, regardless of quantity.
    """
    if 'cart' not in session or not session['cart']:
        return redirect(url_for('cart_page'))

    cart = session['cart']

    for item in cart:
        if item['product_id'] == product_id:
            cart.remove(item)
            flash(f"'{item['name']}' removed from your cart.", "info")
            break
            
    session['cart'] = cart
    return redirect(url_for('cart_page'))

@app.route('/manager_settings', methods=['GET', 'POST'])
@app.route('/employee_settings', methods=['GET', 'POST'])
def profile_settings():
    dashboard_url = None
    if 'manager_loggedin' in session:
        dashboard_url = url_for('manager_page')
    elif 'employee_loggedin' in session:
        dashboard_url = url_for('employee_page')
    else:
        flash("You must be logged in to access settings.", "warning")
        return redirect(url_for('home'))

    employee_id = session.get('employee_id')
    cur = mysql.connection.cursor()

    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form.get('password')

        query_parts = ["UPDATE Employees SET name = %s, email = %s"]
        params = [name, email]

        if password:
            hashed_pw = password 
            query_parts.append("passwordHash = %s")
            params.append(hashed_pw)

        query_parts.append("WHERE employee_id = %s")
        params.append(employee_id)
        
        query = ", ".join(query_parts[:-1]) + " " + query_parts[-1] 
        
        cur.execute(query, tuple(params))
        mysql.connection.commit()

        session['name'] = name
        
        flash("Profile updated successfully!", "success")
        return redirect(request.url)

    cur.execute("SELECT name, email FROM Employees WHERE employee_id = %s", (employee_id,))
    user_data = cur.fetchone()
    cur.close()

    if not user_data:
        flash("User not found.", "danger")
        return redirect(dashboard_url)
    
    return render_template('profile_settings.html', user=user_data, dashboard_url=dashboard_url)


@app.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    if 'customer_id' not in session:
        flash("Please log in to add items to your cart.", "warning")
        return redirect(url_for('login'))

    product_id = request.form.get('product_id')
    
    if not product_id:
        flash("Invalid product.", "danger")
        return redirect(url_for('main_page'))

    if 'cart' not in session:
        session['cart'] = []

    cart = session['cart']
    
    found = False
    for item in cart:
        if str(item['product_id']) == str(product_id):
            item['quantity'] += 1
            found = True
            break
    
    if not found:
        cur = mysql.connection.cursor()
        cur.execute("SELECT name, price FROM Products WHERE product_id = %s", (product_id,))
        product = cur.fetchone()
        cur.close()
        
        if product:
            cart.append({
                'product_id': product_id,
                'name': product['name'],
                'price': float(product['price']), 
                'quantity': 1
            })
        else:
            flash("Product not found.", "danger")
            return redirect(url_for('main_page'))

    session['cart'] = cart
    flash(f"'{cart[-1]['name']}' added to cart!", "success")
    return redirect(url_for('main_page'))


@app.route('/toggle_favorite', methods=['POST'])
def toggle_favorite():
    if 'customer_id' not in session:
        return jsonify({'status': 'error', 'message': 'Please log in to add to favorites.'}), 401

    customer_id = session['customer_id']
    product_id = request.form.get('product_id')

    if not product_id:
        
        return jsonify({'status': 'error', 'message': 'Invalid product.'}), 400

    cur = mysql.connection.cursor()

    # Check if the item is already in the wishlist
    cur.execute("SELECT wishlist_id FROM Wishlist WHERE customer_id = %s AND product_id = %s", (customer_id, product_id))
    item = cur.fetchone()

    if item:
        # If it exists, remove it (un-favorite)
        cur.execute("DELETE FROM Wishlist WHERE wishlist_id = %s", (item['wishlist_id'],))
        action = 'removed'
    else:
        # If it doesn't exist, add it (favorite)
        cur.execute("INSERT INTO Wishlist (customer_id, product_id) VALUES (%s, %s)", (customer_id, product_id))
        action = 'added'

    mysql.connection.commit()
    cur.close()

    return jsonify({'status': 'success', 'action': action})

@app.route('/my_orders')
def my_orders_page():
    if 'customer_id' not in session:
        flash("Please log in to view your order history.", "warning")
        return redirect(url_for('login'))

    customer_id = session['customer_id']
    cur = mysql.connection.cursor()
    try:
        cur.execute("SELECT * FROM Orders WHERE customer_id = %s ORDER BY order_date DESC", (customer_id,))
        orders = cur.fetchall()

        order_items = {}
        if orders:
            order_ids = tuple(order['order_id'] for order in orders)
            
            query = """
                SELECT oi.*, p.name as product_name 
                FROM OrderItems oi 
                JOIN Products p ON oi.product_id = p.product_id 
                WHERE oi.order_id IN %s
            """
            cur.execute(query, (order_ids,))
            items = cur.fetchall()

            for item in items:
                if item['order_id'] not in order_items:
                    order_items[item['order_id']] = []
                order_items[item['order_id']].append(item)

        return render_template("my_orders.html", orders=orders, order_items=order_items)

    except Exception as e:
        flash(f"An error occurred while fetching your orders: {str(e)}", "danger")
        return redirect(url_for('main_page'))
    finally:
        if cur:
            cur.close()

@app.route('/unified_sales_report_page')
def unified_sales_report_page():
    """
    This route handles the monthly/yearly Sales Performance report.
    It matches the 'Sales Performance' card.
    """
    if 'manager_loggedin' not in session:
        return redirect(url_for('manager_login'))
    
    cur = None
    try:
        cur = mysql.connection.cursor()
        current_time = datetime.now()
        year = request.args.get('year', default=current_time.year, type=int)
        month = request.args.get('month', default=current_time.month, type=int)

        transaction_list_query = """
            SELECT o.order_id, c.name AS customer_name, p.name AS product_name, o.order_date, oi.quantity, oi.price_at_time_of_purchase
            FROM OrderItems oi
            JOIN Orders o ON oi.order_id = o.order_id
            JOIN Customers c ON o.customer_id = c.customer_id
            JOIN Products p ON oi.product_id = p.product_id
            WHERE YEAR(o.order_date) = %s AND MONTH(o.order_date) = %s
            ORDER BY o.order_date DESC;
        """
        cur.execute(transaction_list_query, (year, month))
        transaction_list = cur.fetchall()
        
        total_sales = sum(item['quantity'] * item['price_at_time_of_purchase'] for item in transaction_list) if transaction_list else 0
        
        return render_template(
            'sales_report.html', 
            sales=transaction_list, 
            total_sales=total_sales,
            selected_year=year, 
            selected_month=month, 
            current_year=current_time.year
        )
    finally:
        if cur:
            cur.close()


@app.route('/advanced_reports_page')
def advanced_reports_page():
    """
    This route handles the combined advanced reports (Top Products, Employees, Customers).
    It matches the 'Advanced Reports' card.
    """
    if 'manager_loggedin' not in session:
        return redirect(url_for('manager_login'))
    
    cur = None
    try:
        cur = mysql.connection.cursor()
        
        # --- QUERY 1: Top Selling Products ---
        cur.execute("""
            SELECT p.name AS product_name, SUM(oi.quantity) AS total_sold
            FROM OrderItems oi JOIN Products p ON oi.product_id = p.product_id
            GROUP BY p.name ORDER BY total_sold DESC LIMIT 10;
        """)
        top_products = cur.fetchall()

        # --- QUERY 2: Top Performing Employees ---
        cur.execute("""
            SELECT e.name AS employee_name, COALESCE(SUM(o.total_amount), 0) AS total_sales
            FROM Employees e LEFT JOIN Orders o ON o.employee_id = e.employee_id
            GROUP BY e.name ORDER BY total_sales DESC;
        """)
        top_employees = cur.fetchall()
        
        # --- QUERY 3: Top Spending Customers ---
        cur.execute("""
            SELECT c.name AS customer_name, SUM(o.total_amount) AS total_spent
            FROM Orders o JOIN Customers c ON o.customer_id = c.customer_id
            GROUP BY c.name ORDER BY total_spent DESC LIMIT 10;
        """)
        top_customers = cur.fetchall()

        return render_template(
            'advanced_reports.html', 
            top_products=top_products,
            top_employees=top_employees,
            top_customers=top_customers
        )
    finally:
        if cur:
            cur.close()

if __name__ == '__main__':
    app.run(debug=True)