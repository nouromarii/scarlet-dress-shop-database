from flask import Blueprint, render_template, flash, current_app, session, redirect, url_for, request

WarehouseView_bp = Blueprint('WarehouseView_bp', __name__, url_prefix='/WarehouseView')

@WarehouseView_bp.route('/', methods=['GET'])
def view_warehouse():
    if 'loggedin' not in session:
        flash("You must be logged in to view this page.", "warning")
        return redirect(url_for('login'))

    mysql = current_app.mysql
    cur = mysql.connection.cursor()
    try:
        search_query = request.args.get('search', '')

        sql_query = """
            SELECT product_id, name, category, stock_quantity 
            FROM Products 
        """
        
        params = []
        if search_query:
            sql_query += " WHERE name LIKE %s OR category LIKE %s"
            params.append(f"%{search_query}%")
            params.append(f"%{search_query}%")

        sql_query += " ORDER BY name"
        
        cur.execute(sql_query, tuple(params))
        products_stock_data = cur.fetchall()
        
        return render_template(
            'WarehouseView.html', 
            stock_data=products_stock_data, 
            search_query=search_query
        )

    except Exception as e:
        flash(f"An error occurred: {str(e)}", "danger")
        return render_template('WarehouseView.html', stock_data=[], search_query='')
    finally:
        cur.close()