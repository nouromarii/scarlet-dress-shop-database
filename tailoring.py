from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app

tailoring_bp = Blueprint('tailoring', __name__, url_prefix='/tailoring')

@tailoring_bp.route('/', methods=['GET', 'POST'])
def manage_services():
    mysql = current_app.mysql
    cur = mysql.connection.cursor()
    try:
        if request.method == 'POST':
            action = request.form.get('action')
            service_id = request.form.get('service_id')
            
            # Get form data
            service_type = request.form.get('type')
            price = request.form.get('price')
            duration = request.form.get('duration')

            if action == 'add':
                if not all([service_type, price]):
                    flash('Service Type and Price are required.', 'danger')
                else:
                    cur.execute(
                        "INSERT INTO TailoringServices (type, price, duration) VALUES (%s, %s, %s)",
                        (service_type, price, duration)
                    )
                    mysql.connection.commit()
                    flash('Tailoring service added successfully!', 'success')

            elif action == 'update' and service_id:
                cur.execute(
                    "UPDATE TailoringServices SET type=%s, price=%s, duration=%s WHERE service_id=%s",
                    (service_type, price, duration, service_id)
                )
                mysql.connection.commit()
                flash('Service updated successfully!', 'success')
            
            elif action == 'delete' and service_id:
                cur.execute("DELETE FROM TailoringServices WHERE service_id=%s", (service_id,))
                mysql.connection.commit()
                flash('Service deleted successfully!', 'success')
            
            return redirect(url_for('tailoring.manage_services'))

        # GET request: Display all services
        cur.execute("SELECT * FROM TailoringServices ORDER BY type")
        services = cur.fetchall()
        return render_template('tailoring_manage.html', services=services)

    except Exception as e:
        flash(f"An error occurred: {str(e)}", "danger")
        return render_template('tailoring_manage.html', services=[])
    finally:
        cur.close()

# In tailoring.py, add this new route function

@tailoring_bp.route('/requests')
def view_requests():
    """Displays a report of all tailoring requests from customers."""
    # This page should be protected, e.g., only for managers/employees
    # You can add session checks here if needed.
    
    mysql = current_app.mysql
    cur = None
    try:
        cur = mysql.connection.cursor()
        
        # This is the powerful new query that joins 4 tables
        query = """
            SELECT
                o.order_id,
                o.order_date,
                o.status AS order_status,
                c.name AS customer_name,
                ts.type AS service_type
            FROM TailorServiceRequest tsr
            JOIN Orders o ON tsr.order_id = o.order_id
            JOIN Customers c ON o.customer_id = c.customer_id
            JOIN TailoringServices ts ON tsr.service_id = ts.service_id
            ORDER BY o.order_date DESC;
        """
        cur.execute(query)
        requests_data = cur.fetchall()
        
        return render_template('tailoring_requests.html', requests=requests_data)

    except Exception as e:
        flash(f"An error occurred while fetching tailoring requests: {str(e)}", "danger")
        return redirect(url_for('tailoring.manage_services')) # Or back to dashboard
    finally:
        if cur:
            cur.close()