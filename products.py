from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from werkzeug.utils import secure_filename
import os

products_bp = Blueprint('products_bp', __name__, url_prefix='/products')

UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@products_bp.route('/', methods=['GET', 'POST'])
def products():
    mysql = current_app.mysql
    cur = mysql.connection.cursor()
    
    upload_path = os.path.join(current_app.root_path, UPLOAD_FOLDER)
    os.makedirs(upload_path, exist_ok=True)
    
    try:
        if request.method == 'POST':
            action = request.form.get('action')
            
            if action == 'add' or action == 'update':
                name = request.form.get('name')
                price = request.form.get('price', type=float)
                stock_quantity = request.form.get('stock_quantity', type=int)
                
                errors = []
                if not name:
                    errors.append("Product name is required.")
                
                if price is None or price <= 0:
                    errors.append("Price must be a positive number.")
                
                if stock_quantity is None or stock_quantity < 0:
                    errors.append("Stock quantity cannot be negative.")

                if errors:
                    for error in errors:
                        flash(error, 'danger')
                    return redirect(url_for('products_bp.products'))
                
                category = request.form.get('category')
                supplier_id = request.form.get('supplier_id')
                image_file = request.files.get('image')
                
                filename = None
                if image_file and image_file.filename != '':
                    if allowed_file(image_file.filename):
                        filename = secure_filename(image_file.filename)
                        image_file.save(os.path.join(upload_path, filename))
                    else:
                        flash('Invalid file type. Allowed types are png, jpg, jpeg, gif, webp.', 'danger')
                        return redirect(url_for('products_bp.products'))
            
            # --- DATABASE ACTIONS ---
            if action == 'add':
                cur.execute(
                    "INSERT INTO Products (name, category, price, stock_quantity, supplier_id, image_filename) VALUES (%s, %s, %s, %s, %s, %s)",
                    (name, category, price, stock_quantity, supplier_id, filename)
                )
                flash('Product added successfully!', 'success')

            elif action == 'update':
                product_id = request.form.get('product_id')
                if filename: 
                    cur.execute(
                        "UPDATE Products SET name=%s, category=%s, price=%s, stock_quantity=%s, supplier_id=%s, image_filename=%s WHERE product_id=%s",
                        (name, category, price, stock_quantity, supplier_id, filename, product_id)
                    )
                else: 
                    # If no new image is uploaded, don't change the existing image
                    cur.execute(
                        "UPDATE Products SET name=%s, category=%s, price=%s, stock_quantity=%s, supplier_id=%s WHERE product_id=%s",
                        (name, category, price, stock_quantity, supplier_id, product_id)
                    )
                flash('Product updated successfully!', 'success')
            
            elif action == 'delete':
                product_id = request.form.get('product_id')
                cur.execute("DELETE FROM Products WHERE product_id=%s", (product_id,))
                flash('Product deleted successfully!', 'success')
            
            mysql.connection.commit()
            return redirect(url_for('products_bp.products'))

        cur.execute("SELECT p.*, s.name as supplier_name FROM Products p LEFT JOIN Suppliers s ON p.supplier_id = s.supplier_id ORDER BY p.product_id DESC")
        products = cur.fetchall()
        cur.execute("SELECT * FROM Suppliers ORDER BY name")
        suppliers = cur.fetchall()
        
        return render_template('products_manage.html', products=products, suppliers=suppliers)
    
    finally:
        if cur:
            cur.close()