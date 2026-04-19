from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app

order_bp = Blueprint('order_bp', __name__, url_prefix='/order')

@order_bp.route('/')
def list_orders():
    """Displays the list of all orders with a status filter and tailoring indicator."""
    mysql = current_app.mysql
    cur = None
    try:
        cur = mysql.connection.cursor()
        status_filter = request.args.get('status', 'All')
        
        # Query 1: Gets the main list of orders
        query = """
            SELECT o.order_id, o.order_date, o.total_amount, o.status, c.name AS customer_name
            FROM Orders o 
            LEFT JOIN Customers c ON o.customer_id = c.customer_id
        """
        params = []
        if status_filter and status_filter != 'All':
            query += " WHERE o.status = %s"
            params.append(status_filter)
        query += " ORDER BY o.order_date DESC"
        cur.execute(query, tuple(params))
        orders = cur.fetchall()

        # Query 2: Gets all Order IDs that have tailoring requests
        # This is the crucial part that was likely missing or incorrect.
        cur.execute("SELECT DISTINCT order_id FROM TailorServiceRequest")
        
        # We create a 'set' of these IDs for a very fast check in the HTML.
        tailored_order_ids = {row['order_id'] for row in cur.fetchall()}
        
        # We pass this set to the template.
        return render_template('order.html', 
                               orders=orders, 
                               current_status=status_filter, 
                               tailored_order_ids=tailored_order_ids)
    except Exception as e:
        flash(f"An error occurred: {str(e)}", "danger")
        return render_template('order.html', orders=[], current_status='All', tailored_order_ids=set())
    finally:
        if cur:
            cur.close()

@order_bp.route('/update_status', methods=['POST'])
def update_status():
    """Dedicated route to handle updating an order's status."""
    mysql = current_app.mysql
    cur = mysql.connection.cursor()
    try:
        order_id = request.form.get('order_id')
        new_status = request.form.get('status')
        cur.execute("UPDATE Orders SET status = %s WHERE order_id = %s", (new_status, order_id))
        mysql.connection.commit()
        flash(f'Order #{order_id} status updated to {new_status}.', 'success')
    finally:
        if cur:
            cur.close()
    return redirect(url_for('order_bp.list_orders', status=request.args.get('status', 'All')))

@order_bp.route('/<int:order_id>')
def view_order(order_id):
    """Displays the details for a single order."""
    mysql = current_app.mysql
    cur = None
    try:
        cur = mysql.connection.cursor()
        
        # Get the main order and customer details by joining Orders and Customers
        cur.execute("""
            SELECT o.*, c.name as customer_name, c.email, c.phone, c.address
            FROM Orders o 
            LEFT JOIN Customers c ON o.customer_id = c.customer_id
            WHERE o.order_id = %s
        """, (order_id,))
        order = cur.fetchone()

        if not order:
            flash("Order not found.", "danger")
            return redirect(url_for('order_bp.list_orders'))

        # Get the products associated with this order by joining OrderItems and Products
        cur.execute("""
            SELECT oi.quantity, oi.price_at_time_of_purchase, p.name AS product_name
            FROM OrderItems oi
            JOIN Products p ON oi.product_id = p.product_id
            WHERE oi.order_id = %s
        """, (order_id,))
        items = cur.fetchall()

        # Get the requested tailoring services for this order
        cur.execute("""
            SELECT ts.type, ts.price
            FROM TailorServiceRequest tsr
            JOIN TailoringServices ts ON tsr.service_id = ts.service_id
            WHERE tsr.order_id = %s
        """, (order_id,))
        requested_services = cur.fetchall()

        # Pass all fetched data to the template
        return render_template('order_details.html', order=order, items=items, requested_services=requested_services)

    except Exception as e:
        flash(f"An error occurred while fetching order details: {str(e)}", "danger")
        return redirect(url_for('order_bp.list_orders'))
    finally:
        if cur:
            cur.close()