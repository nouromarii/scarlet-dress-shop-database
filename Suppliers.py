from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from werkzeug.security import generate_password_hash

Suppliers_bp = Blueprint('Suppliers_bp', __name__)

@Suppliers_bp.route('/Suppliers', methods=['GET', 'POST'])
def Suppliers():
    mysql = current_app.mysql
    cur = mysql.connection.cursor()
    try:
        if request.method == 'POST':
            action = request.form.get('action')
            supplier_id = request.form.get('supplier_id')

            if action == 'add':
                name = request.form.get('name')
                phone = request.form.get('phone')
                email = request.form.get('email')

                if not all([name, email]):
                    flash('Name and Email are required.', 'danger')
                else:
                    cur.execute("INSERT INTO Suppliers (name, phone, email) VALUES (%s, %s, %s)",
                                (name, phone, email))
                    mysql.connection.commit()
                    flash('Supplier added successfully!', 'success')

            elif action == 'update' and supplier_id:
                name = request.form.get('name')
                phone = request.form.get('phone')
                email = request.form.get('email')

                cur.execute(
                    "UPDATE Suppliers SET name=%s, phone=%s, email=%s WHERE supplier_id=%s",
                    (name, phone, email, supplier_id)
                )
                mysql.connection.commit()
                flash('Supplier updated successfully!', 'success')

            elif action == 'delete' and supplier_id:
                cur.execute("DELETE FROM Suppliers WHERE supplier_id=%s", (supplier_id,))
                mysql.connection.commit()
                flash('Supplier deleted successfully!', 'success')

        cur.execute("SELECT * FROM Suppliers ORDER BY supplier_id")
        suppliers = cur.fetchall()
        return render_template('Suppliers.html', Suppliers=suppliers)

    except Exception as e:
        flash(f"Error: {str(e)}", "danger")
        return render_template('Suppliers.html', Suppliers=[])

    finally:
        cur.close()
