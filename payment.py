from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
from datetime import datetime

payment_bp = Blueprint('payment', __name__, template_folder='templates')

@payment_bp.route('/pay/<int:order_id>', methods=['GET', 'POST'])
def process_payment(order_id):
    mysql = current_app.mysql

    if 'customer_id' not in session:
        flash("Please log in to complete your payment.", "warning")
        return redirect(url_for('login'))

    customer_id = session['customer_id']
    cur = mysql.connection.cursor()

    # Get the order to make sure it exists, belongs to the user, and is pending payment
    cur.execute("""
        SELECT order_id, status, total_amount
        FROM Orders
        WHERE order_id = %s AND customer_id = %s
    """, (order_id, customer_id))
    order = cur.fetchone()

    if not order:
        flash("Order not found or you do not have permission to view it.", "danger")
        return redirect(url_for('my_orders_page')) # Redirect to customer's order history

    if order['status'] != 'Pending Payment':
        flash(f"This order cannot be paid for (Status: {order['status']}).", "info")
        return redirect(url_for('my_orders_page')) # Redirect to customer's order history

    total_amount = order['total_amount']

    # If the form is submitted (user clicks "Pay Now")
    if request.method == 'POST':
        payment_method = request.form.get('payment_method', 'Credit Card') 
        payment_date = datetime.now()

        try:
            # --- DATABASE CHANGE 1: INSERT into payments table ---
            # This query connects to your `payments` table.
            # NOTE: Your table has a column `paymentID`. MySQL is case-insensitive on Windows but not always on Linux.
            # Using lowercase `paymentid` in code is safer, but we will match your schema.
            cur.execute("""
                INSERT INTO payments (order_id, amount, payment_date, payment_method)
                VALUES (%s, %s, %s, %s)
            """, (order_id, total_amount, payment_date, payment_method))

            # --- DATABASE CHANGE 2: UPDATE the order status ---
            # This query updates your `Orders` table.
            cur.execute("""
                UPDATE Orders SET status = 'Completed' WHERE order_id = %s
            """, (order_id,))

            mysql.connection.commit()
            flash("Payment successful! Your order has been confirmed.", "success")
            return redirect(url_for('my_orders_page')) # Redirect to a confirmation/order history page

        except Exception as e:
            mysql.connection.rollback()
            flash(f"An error occurred during payment processing: {e}", "danger")
            return redirect(url_for('payment.process_payment', order_id=order_id))
        finally:
            cur.close()

    # If it's a GET request, just show the payment page
    cur.close()
    return render_template('payment.html', 
                           order=order, 
                           total_amount=total_amount)