from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from werkzeug.security import generate_password_hash

EmployeeMan_bp = Blueprint('EmployeeMan_bp', __name__, url_prefix='/EmployeeMan')

@EmployeeMan_bp.route('/', methods=['GET', 'POST'])
def manage_employees():
    mysql = current_app.mysql
    cur = mysql.connection.cursor()

    try:
        if request.method == 'POST':
            action = request.form.get('action')
            employee_id = request.form.get('employee_id')
            
            if action == 'add':
                name = request.form.get('name')
                role = request.form.get('role')
                salary = request.form.get('salary') or 0
                join_date = request.form.get('join_date')
                email = request.form.get('email')
                password = request.form.get('password')
                if not all([name, role, email, password]):
                    flash('Name, Role, Email, and Password are required.', 'danger')
                else:
                    pw_hash = password 
                    cur.execute("INSERT INTO Employees (name, role, salary, join_date, email, passwordHash) VALUES (%s, %s, %s, %s, %s, %s)",
                                (name, role, salary, join_date, email, pw_hash))
                    mysql.connection.commit()
                    flash('Employee added successfully!', 'success')
            
            elif action == 'update' and employee_id:
                name = request.form.get('name')
                role = request.form.get('role')
                salary = request.form.get('salary')
                join_date = request.form.get('join_date')
                email = request.form.get('email')
                password = request.form.get('password')
                if password:
                    pw_hash = password
                    cur.execute("UPDATE Employees SET name=%s, role=%s, salary=%s, join_date=%s, email=%s, passwordHash=%s WHERE employee_id=%s",
                                (name, role, salary, join_date, email, pw_hash, employee_id))
                else:
                    cur.execute("UPDATE Employees SET name=%s, role=%s, salary=%s, join_date=%s, email=%s WHERE employee_id=%s",
                                (name, role, salary, join_date, email, employee_id))
                mysql.connection.commit()
                flash('Employee updated successfully!', 'success')

            elif action == 'delete' and employee_id:
                cur.execute("DELETE FROM Employees WHERE employee_id=%s", (employee_id,))
                mysql.connection.commit()
                flash('Employee deleted successfully!', 'success')
            
            return redirect(url_for('EmployeeMan_bp.manage_employees'))

        search_query = request.args.get('search', '')

        # Query 1: Get the list of all employees, filtered by search term if provided
        base_employee_query = "SELECT employee_id, name, role, salary, join_date, email FROM Employees"
        params = []
        if search_query:
            # Search by name, email, or role
            base_employee_query += " WHERE name LIKE %s OR email LIKE %s OR role LIKE %s"
            search_term = f"%{search_query}%"
            params.extend([search_term, search_term, search_term])
        base_employee_query += " ORDER BY name"
        
        cur.execute(base_employee_query, tuple(params))
        employees = cur.fetchall()

        # Query 2: Get sales performance data (this query doesn't need to be filtered)
        performance_query = """
            SELECT e.employee_id, COUNT(o.order_id) AS total_orders_handled, COALESCE(SUM(o.total_amount), 0) AS total_sales
            FROM Employees e LEFT JOIN Orders o ON o.employee_id = e.employee_id
            GROUP BY e.employee_id;
        """
        cur.execute(performance_query)
        performance_data = cur.fetchall()

        performance_dict = {
            item['employee_id']: {
                'total_sales': item['total_sales'],
                'total_orders_handled': item['total_orders_handled']
            } for item in performance_data
        }

        return render_template('EmployeeMan.html', employees=employees, performance=performance_dict, search_query=search_query)

    except Exception as e:
        flash(f"An error occurred: {str(e)}", "danger")
        return render_template('EmployeeMan.html', employees=[], performance={}, search_query='')
    finally:
        cur.close()