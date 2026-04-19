from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from werkzeug.security import generate_password_hash

customers_bp = Blueprint('customers_bp', __name__, url_prefix='/customers')

@customers_bp.route('/', methods=['GET', 'POST'])
def customers():
    mysql = current_app.mysql
    cur = mysql.connection.cursor()
    try:
        if request.method == 'POST':
            action = request.form.get('action')
            customer_id = request.form.get('customer_id')

            if action == 'add':
                name = request.form.get('name')
                phone = request.form.get('phone')
                email = request.form.get('email')
                address = request.form.get('address')
                password = request.form.get('password')
                if not all([name, email, password]):
                    flash('Name, Email, and Password are required.', 'danger')
                else:
                    hashed_pw = generate_password_hash(password)
                    cur.execute(
                        "INSERT INTO Customers (name, phone, email, address, passwordHash) VALUES (%s, %s, %s, %s, %s)",
                        (name, phone, email, address, hashed_pw)
                    )
                    mysql.connection.commit()
                    flash('Customer added successfully!', 'success')
            
            elif action == 'update' and customer_id:
                name = request.form.get('name')
                phone = request.form.get('phone')
                email = request.form.get('email')
                address = request.form.get('address')
                cur.execute(
                    "UPDATE Customers SET name=%s, phone=%s, email=%s, address=%s WHERE customer_id=%s",
                    (name, phone, email, address, customer_id)
                )
                mysql.connection.commit()
                flash('Customer updated successfully!', 'success')
            
            elif action == 'delete' and customer_id:
                cur.execute("DELETE FROM Customers WHERE customer_id=%s", (customer_id,))
                mysql.connection.commit()
                flash('Customer deleted successfully!', 'success')
            
            return redirect(url_for('customers_bp.customers'))

        search_query = request.args.get('search', '')
        
        base_customer_query = "SELECT customer_id, name, email, phone, address FROM Customers"
        params = []
        if search_query:
            base_customer_query += " WHERE name LIKE %s OR email LIKE %s"
            params.append(f"%{search_query}%")
            params.append(f"%{search_query}%")
        base_customer_query += " ORDER BY name"
        
        cur.execute(base_customer_query, tuple(params))
        customer_list = cur.fetchall()

        performance_query = """
            SELECT c.customer_id, COUNT(o.order_id) AS number_of_orders, COALESCE(SUM(o.total_amount), 0) AS total_spent
            FROM Customers c LEFT JOIN Orders o ON c.customer_id = o.customer_id
            GROUP BY c.customer_id;
        """
        cur.execute(performance_query)
        performance_data = cur.fetchall()

        performance_dict = {
            item['customer_id']: {
                'total_spent': item['total_spent'],
                'number_of_orders': item['number_of_orders']
            } for item in performance_data
        }

        return render_template('customers.html', customers=customer_list, performance=performance_dict, search_query=search_query)

    except Exception as e:
        flash(f"An error occurred: {str(e)}", "danger")
        return render_template('customers.html', customers=[], performance={}, search_query='')
    finally:
        cur.close()