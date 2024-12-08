from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "123"


# Database setup
DB_NAME = "database.db"

def execute_query(query, params=(), fetch_one=False):
    conn = get_db_connection()
    conn.row_factory = sqlite3.Row  # Ensures rows act like dictionaries

    cursor = conn.cursor()
    cursor.execute(query, params)
    if fetch_one:
        rows = cursor.fetchone()  # Fetch only one row
    else:
        rows = cursor.fetchall()  # Fetch all rows

    conn.commit()
    conn.close()
    return rows
    
def get_db_connection():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    return conn

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        email = request.form["email"]
        password = request.form["password"]
        role = request.form["role"].lower()
        diet_type = request.form["diet_type"]
        allergies = request.form["allergies"]

        # Hash the password
        hashed_password = generate_password_hash(password)

        conn = get_db_connection()
        try:
            # Insert user details into 'users' table
            conn.execute(
                "INSERT INTO users (username, email, password, role) VALUES (?, ?, ?, ?)",
                (username, email, hashed_password, role),
            )
            conn.commit()

            # Get the user_id of the newly inserted user
            user_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

            # Insert user preferences into 'user_preferences' table
            conn.execute(
                "INSERT INTO user_preferences (user_id, diet_type, allergies) VALUES (?, ?, ?)",
                (user_id, diet_type, allergies),
            )
            conn.commit()
        except sqlite3.IntegrityError:
            return "Username or email already exists."
        finally:
            conn.close()

        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"].strip()

        conn = get_db_connection()
        user = conn.execute(
            "SELECT * FROM users WHERE username = ?", (username,)
        ).fetchone()
        conn.close()

        if user and check_password_hash(user["password"], password):
            # Successful login
            session["user_id"] = user["user_id"]  # Save user_id in session
            session["username"] = user["username"]
            session["role"] = user["role"]
            return redirect(url_for("home"))  # Redirect to home page after login
        else:
            return "Invalid username or password."

    return render_template("login.html")




@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("register"))

from functools import wraps

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "username" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function



# Routes
@app.route("/")
@login_required
def home():
    return render_template("home.html")

@app.route("/inventory", methods=["GET", "POST"])
@login_required
def inventory():
    if request.method == "POST":
        # Add new inventory item
        item_name = request.form["item_name"]
        category = request.form["category"]
        quantity = int(request.form["quantity"])  # Ensure quantity is an integer
        expiration_date = request.form["expiration_date"]
        user_id = session.get("user_id")  # Get user_id from the session
        if not user_id:
            return redirect(url_for("login"))
        
        # Insert into inventory table
        execute_query("""
            INSERT INTO inventory (user_id, item_name, category, quantity, expiration_date)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, item_name, category, quantity, expiration_date))
        
        # Remove items with quantity < 1
        execute_query("DELETE FROM inventory WHERE quantity < 1")

        return redirect(url_for("inventory"))
    
    # Fetch all inventory items for the default user
    items = execute_query("SELECT * FROM inventory WHERE user_id = ?", (session["user_id"],))
    return render_template("inventory.html", items=items)

@app.route("/delete_item/<int:inventory_id>", methods=["POST"])
def delete_item(inventory_id):
    user_id = session.get("user_id")  # Get user_id from the session
    if not user_id:
        return redirect(url_for("login"))
    execute_query("DELETE FROM inventory WHERE inventory_id = ? AND user_id = ?", (inventory_id, user_id))
    return redirect(url_for("inventory"))


@app.route("/edit_inventory_item/<int:inventory_id>", methods=["GET", "POST"])
@login_required
def edit_inventory_item(inventory_id):
    user_id = session.get("user_id")  # Get user_id from the session
    if not user_id:
        return redirect(url_for("login"))

    if request.method == "POST":
        # Retrieve the updated quantity
        quantity = int(request.form["quantity"])

        # Update the quantity in the inventory
        execute_query("""
            UPDATE inventory
            SET quantity = ?
            WHERE inventory_id = ? AND user_id = ?
        """, (quantity, inventory_id, user_id))

        # Remove items with quantity < 1
        execute_query("DELETE FROM inventory WHERE quantity < 1")

        return redirect(url_for("inventory"))


    # Fetch the inventory item to edit
    item = execute_query("""
        SELECT * FROM inventory WHERE inventory_id = ? AND user_id = ?
    """, (inventory_id, user_id))

    if not item:
        return "Item not found or access denied.", 404

    return render_template("edit_inventory_item.html", item=item[0])





import os
from werkzeug.utils import secure_filename

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
UPLOAD_FOLDER = os.path.join('static', 'upload')

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route("/recipes", methods=["GET", "POST"])
@login_required
def recipes():
    user_id = session.get("user_id")  # Get user_id from the session
    if not user_id:
        return redirect(url_for("login"))
    if request.method == "POST":
        # Recipe details
        recipe_name = request.form["recipe_name"]
        cuisine = request.form["cuisine"]
        diet_type = request.form["diet_type"]
        instructions = request.form["instructions"]
        user_id = session.get("user_id")  # Get user_id from the session
        if not user_id:
            return redirect(url_for("login"))

        # Handle image upload
        recipe_image = request.files.get("recipe_image")
        image_name = None
        if recipe_image and allowed_file(recipe_image.filename):
            ext = recipe_image.filename.rsplit('.', 1)[1].lower()
            image_name = f"{recipe_name}_{user_id}.{ext}"
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(image_name))
            recipe_image.save(image_path)

        # Combine ingredients and quantities
        selected_products = request.form.getlist("selected_products[]")
        quantities = request.form.to_dict(flat=False).get("quantities", {})

        ingredients = []
        ingredient_counts = []

        for product in selected_products:
            quantity = request.form.get(f"quantities[{product}]")
            if quantity and quantity.isdigit():
                ingredients.append(product)
                ingredient_counts.append(quantity)

        custom_ingredients = request.form.getlist("custom_ingredients")
        for custom_ingredient in custom_ingredients:
            if ":" in custom_ingredient:
                ingredient, quantity = custom_ingredient.split(":", 1)
                if quantity.strip().isdigit():
                    ingredients.append(ingredient.strip())
                    ingredient_counts.append(quantity.strip())

        ingredients_str = ", ".join(ingredients)
        ingredient_counts_str = ", ".join(ingredient_counts)

        # Insert into recipes table
        execute_query("""
            INSERT INTO recipes (user_id, recipe_name, cuisine, diet_type, instructions, created_by, ingredients, ingredients_count, image_name)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (user_id, recipe_name, cuisine, diet_type, instructions, user_id, ingredients_str, ingredient_counts_str, image_name))

        return redirect(url_for("recipes"))

    # Fetch recipes created by the current user
    user_recipes = execute_query("SELECT * FROM recipes WHERE user_id = ?", (user_id,)) 

    # Fetch recipes
    recipes = execute_query("SELECT * FROM recipes")
    supplier_products = execute_query("SELECT product_name FROM supplier_products")
    supplier_products = [{"product_name": product["product_name"]} for product in supplier_products]

    return render_template(
        "recipes.html", 
        recipes=recipes, 
        supplier_products=supplier_products, 
        user_recipes=user_recipes
    )



@app.route('/search_ingredients', methods=['GET'])
def search_ingredients():
    # Get the query from the request
    query = request.args.get('q', '').strip()
    if not query:
        return jsonify([])  # Return an empty list if no query is provided

    # Fetch matching items from the supplier_products table
    results = execute_query("""
        SELECT product_name FROM supplier_products
        WHERE product_name LIKE ? LIMIT 10
    """, (f"%{query}%",))  # Use wildcard search for partial matches

    # Format the results as a simple list of product names
    suggestions = [row['product_name'] for row in results]
    return jsonify(suggestions)

#-------------------------------------------------------------------------------------------------
@app.route("/recipes/filter", methods=["GET"])
def filter_recipes():
    user_id = session.get("user_id")  # Get user_id from the session
    if not user_id:
        return redirect(url_for("login"))

    # Fetch inventory items for the user
    inventory_items = execute_query("""
        SELECT item_name, quantity
        FROM inventory
        WHERE user_id = ?
    """, (user_id,))

    # Fetch recipes
    recipes = execute_query("SELECT * FROM recipes")

    # Check recipes against inventory
    available_recipes = []
    for recipe in recipes:
        ingredient_list = recipe["ingredients"].split(", ")
        quantity_list = list(map(int, recipe["ingredients_count"].split(", ")))

        missing_ingredients = []
        can_make = True

        for ingredient, needed_quantity in zip(ingredient_list, quantity_list):
            # Check if the ingredient exists in inventory with enough quantity
            inventory_item = next((item for item in inventory_items if item["item_name"] == ingredient), None)
            if not inventory_item or inventory_item["quantity"] < needed_quantity:
                can_make = False
                missing_ingredients.append(f"{ingredient} ({needed_quantity} required)")
                break

        if can_make:
            # Append the recipe along with the required quantities
            available_recipes.append({
                "recipe_name": recipe["recipe_name"],
                "ingredients": ", ".join([f"{i} ({q} required)" for i, q in zip(ingredient_list, quantity_list)])
            })

    return render_template("filtered_recipes.html", recipes=available_recipes)





@app.route("/delete_recipe/<int:recipe_id>", methods=["POST"])
def delete_recipe(recipe_id):
    execute_query("DELETE FROM recipes WHERE recipe_id = ?", (recipe_id,))
    return redirect(url_for("recipes"))



@app.route("/all_recipes", methods=["GET"])
@login_required
def all_recipes():
    recipes = execute_query("SELECT * FROM recipes")
    return render_template("all_recipes.html", recipes=recipes)



@app.route("/edit_recipe/<int:recipe_id>", methods=["GET", "POST"])
@login_required
def edit_recipe(recipe_id):
    if request.method == "POST":
        # Fetch form data
        recipe_name = request.form["recipe_name"]
        cuisine = request.form["cuisine"]
        diet_type = request.form["diet_type"]
        instructions = request.form["instructions"]

        # Update the recipe in the database
        execute_query("""
            UPDATE recipes
            SET recipe_name = ?, cuisine = ?, diet_type = ?, instructions = ?
            WHERE recipe_id = ?
        """, (recipe_name, cuisine, diet_type, instructions, recipe_id))

        return redirect(url_for("recipes"))

    # Fetch the recipe details for the given recipe_id
    recipe = execute_query("SELECT * FROM recipes WHERE recipe_id = ?", (recipe_id,), fetch_one=True)
    if not recipe:
        return "Recipe not found", 404

    return render_template("edit_recipe.html", recipe=recipe)



@app.route("/recipes/preferences", methods=["GET"])
def filter_recipes_by_preferences():
    user_id = session.get("user_id")  # Get user_id from the session
    if not user_id:
        return redirect(url_for("login"))

    # Get the user's preferences
    user_preferences = execute_query("""
        SELECT diet_type, allergies
        FROM user_preferences
        WHERE user_id = ?
    """, (user_id,))

    if not user_preferences:
        return "No preferences found for the user.", 404

    diet_type = user_preferences[0]["diet_type"]
    allergies = user_preferences[0]["allergies"]

    # Fetch recipes that match the user's diet type and exclude allergens
    if allergies:
        allergens = allergies.split(", ")
        allergens_placeholders = ", ".join(["?"] * len(allergens))
        query = f"""
            SELECT *
            FROM recipes
            WHERE (diet_type = ? OR diet_type IS NULL)
            AND NOT (
                { ' OR '.join(['ingredients LIKE ?'] * len(allergens)) }
            )
        """
        params = [diet_type] + [f"%{allergen}%" for allergen in allergens]
    else:
        query = """
            SELECT *
            FROM recipes
            WHERE diet_type = ? OR diet_type IS NULL
        """
        params = [diet_type]

    filtered_recipes = execute_query(query, params)

    return render_template("all_recipes.html", recipes=filtered_recipes)





@app.route("/shopping_list", methods=["GET"])
@login_required
def shopping_list():
    user_id = session.get("user_id")  # Get user_id from the session
    if not user_id:
        return redirect(url_for("login"))

    # Fetch shopping list items for the user
    shopping_list = execute_query("""
        SELECT item_id, ingredient_name, quantity
        FROM shopping_list
        WHERE user_id = ?
    """, (user_id,))

    return render_template("shopping_list.html", shopping_list=shopping_list)

@app.route("/generate_shopping_list", methods=["POST"])
def generate_shopping_list():
    user_id = session.get("user_id")  # Get user_id from the session
    if not user_id:
        return redirect(url_for("login"))
    recipe_id = request.form.get("recipe_id")

    # Fetch the selected recipe
    recipe = execute_query("SELECT * FROM recipes WHERE recipe_id = ?", (recipe_id,))[0]

    # Fetch user inventory
    inventory = execute_query("SELECT item_name, quantity FROM inventory WHERE user_id = ?", (user_id,))
    inventory_dict = {item["item_name"].strip().lower(): item["quantity"] for item in inventory}

    missing_ingredients = {}

    # Process the ingredients of the selected recipe
    ingredient_list = [ing.strip().lower() for ing in recipe["ingredients"].split(", ")]
    raw_counts = recipe["ingredients_count"].replace(" ", "").split(",")
    ingredient_counts = list(map(int, raw_counts)) 

    for ingredient, required_quantity in zip(ingredient_list, ingredient_counts):
        current_quantity = inventory_dict.get(ingredient, 0)
        if current_quantity < required_quantity:
            missing_quantity = required_quantity - current_quantity
            missing_ingredients[ingredient] = missing_ingredients.get(ingredient, 0) + missing_quantity

    # Add missing ingredients to the shopping list
    for ingredient, quantity in missing_ingredients.items():
        existing_item = execute_query("""
            SELECT * FROM shopping_list
            WHERE user_id = ? AND ingredient_name = ?
        """, (user_id, ingredient))

        if existing_item:
            new_quantity = int(existing_item[0]["quantity"]) + quantity
            execute_query("""
                UPDATE shopping_list
                SET quantity = ?
                WHERE user_id = ? AND ingredient_name = ?
            """, (new_quantity, user_id, ingredient))
        else:
            execute_query("""
                INSERT INTO shopping_list (user_id, ingredient_name, quantity)
                VALUES (?, ?, ?)
            """, (user_id, ingredient, quantity))

    return redirect(url_for("shopping_list"))


@app.route("/delete_shopping_item/<int:item_id>", methods=["POST"])
def delete_shopping_item(item_id):
    user_id = session.get("user_id")  # Get user_id from the session
    if not user_id:
        return redirect(url_for("login"))

    # Delete the specified item from the shopping list
    execute_query("DELETE FROM shopping_list WHERE item_id = ? AND user_id = ?", (item_id, user_id))

    return redirect(url_for("shopping_list"))



#----------------------------------------suplier_products----------------------------------------------
@app.route("/supplier_products", methods=["GET", "POST"])
@login_required
def supplier_products():
    user_id = session.get("user_id")  # Get user_id from the session
    if not user_id:
        return redirect(url_for("login"))

    if request.method == "POST":
        # Retrieve form data
        product_name = request.form["product_name"]
        category = request.form["category"]
        price = float(request.form["price"])
        quantity = int(request.form["quantity"])

        # Insert the product into the supplier_products table with correct supplier_id
        execute_query("""
            INSERT INTO supplier_products (supplier_id, product_name, category, price, quantity)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, product_name, category, price, quantity))

        return redirect(url_for("supplier_products"))

    # Fetch all products added by the supplier
    products = execute_query("SELECT * FROM supplier_products WHERE supplier_id = ?", (user_id,))
    return render_template("supplier_products.html", products=products)




@app.route("/add_product", methods=["POST"])
def add_product():
    user_id = session.get("user_id")  # Use the logged-in user's ID
    if not user_id:
        return redirect(url_for("login"))

    user_role = session.get("role", "").lower()  # Normalize role
    if user_role != "supplier":
        return "Access denied. Only suppliers can add products.", 403

    # Retrieve form data
    product_name = request.form["product_name"]
    category = request.form["category"]
    price = float(request.form["price"])
    quantity = int(request.form["quantity"])

    # Insert the product into the supplier_products table
    execute_query("""
        INSERT INTO supplier_products (supplier_id, product_name, category, price, quantity)
        VALUES (?, ?, ?, ?, ?)
    """, (user_id, product_name, category, price, quantity))

    # Redirect back to the supplier_products page
    return redirect(url_for("supplier_products"))



@app.route("/delete_product/<int:product_id>", methods=["POST"])
def delete_product(product_id):
    user_id = session.get("user_id")  # Use the logged-in user's ID
    if not user_id:
        return redirect(url_for("login"))

    user_role = session.get("role", "").lower()
    if user_role != "supplier":
        return "Access denied. Only suppliers can delete products.", 403

    # Delete the product from the database
    execute_query("DELETE FROM supplier_products WHERE id = ? AND supplier_id = ?", (product_id, user_id))

    # Redirect back to the supplier_products page
    return redirect(url_for("supplier_products"))



#-------------------Edit supplied products-------------------------------
@app.route("/edit_supplier_product/<int:product_id>", methods=["GET", "POST"])
@login_required
def edit_supplier_product(product_id):
    user_id = session.get("user_id")  # Use the logged-in user's ID
    if not user_id:
        return redirect(url_for("login"))

    user_role = session.get("role", "").lower()
    if user_role != "supplier":
        return "Access denied. Only suppliers can access this page.", 403

    if request.method == "POST":
        # Retrieve updated data from the form
        price = float(request.form["price"])
        quantity = int(request.form["quantity"])

        # Update the product in the supplier_products table
        execute_query("""
            UPDATE supplier_products
            SET price = ?, quantity = ?
            WHERE id = ? AND supplier_id = ?
        """, (price, quantity, product_id, user_id))

        return redirect(url_for("supplier_products"))

    # Fetch the product to edit
    product = execute_query("""
        SELECT * FROM supplier_products WHERE id = ? AND supplier_id = ?
    """, (product_id, user_id))

    if not product:
        return "Product not found or access denied.", 404

    product = product[0]  # Since the result is a list, we need the first element
    return render_template("edit_supplier_product.html", product=product)




#---------------------------------------------------------------------------------------------------------

#---------------suplied_products----------------------
@app.route("/supplied_products", methods=["GET"])
@login_required
def supplied_products():
    # Fetch all supplied products with supplier details
    query = """
        SELECT 
            supplier_products.id AS product_id,
            supplier_products.product_name,
            supplier_products.category,
            supplier_products.price,
            supplier_products.quantity,
            supplier_products.date_added,
            users.username AS supplier_name,
            users.email AS supplier_contact
        FROM supplier_products
        LEFT JOIN users ON supplier_products.supplier_id = users.user_id
    """
    products = execute_query(query)
    
    # Debugging: Log results
    print(f"Fetched Products: {products}")
    
    return render_template("supplied_products.html", products=products)





@app.route("/admin")
@login_required
def admin():
    user_id = session.get("user_id")  # Ensure the user is logged in
    if not user_id:
        return redirect(url_for("login"))
    
    user_role = session.get("role", "").lower()  # Normalize the role for comparison
    if user_role != "admin":
        return "Access denied. Only admins can access this page.", 403  # Deny access if not admin
    
    # Render the admin page for users with the admin role
    return render_template("admin.html")



@app.route("/admin/manage_users")
def manage_users():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row  # Allow dictionary-like access to rows
    cur = conn.cursor()
    
    cur.execute("SELECT * FROM users")
    users = cur.fetchall()
    
    conn.close()
    return render_template("manage_users.html", users=users)

@app.route("/admin/update_user/<int:user_id>", methods=["GET", "POST"])
def update_user(user_id):
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    if request.method == "POST":
        username = request.form["username"]
        email = request.form["email"]
        role = request.form["role"]
        
        cur.execute("""
            UPDATE users
            SET username = ?, email = ?, role = ?
            WHERE user_id = ?
        """, (username, email, role, user_id))
        conn.commit()
        conn.close()
        
        flash("User updated successfully!")
        return redirect(url_for("manage_users"))
    
    cur.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = cur.fetchone()
    conn.close()
    
    return render_template("update_user.html", user=user)

@app.route("/admin/delete_user/<int:user_id>", methods=["POST"])
def delete_user(user_id):
    conn = sqlite3.connect('database.db')
    cur = conn.cursor()
    
    cur.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()
    
    flash("User deleted successfully!")
    return redirect(url_for("manage_users"))



@app.route("/admin/manage_recipes")
def manage_recipes():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("SELECT * FROM recipes")
    recipes = cur.fetchall()

    conn.close()
    return render_template("manage_recipes.html", recipes=recipes)

@app.route("/admin/update_recipe_admin/<int:recipe_id>", methods=["GET", "POST"])
def update_recipe(recipe_id):
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    if request.method == "POST":
        recipe_name = request.form["recipe_name"]
        cuisine = request.form["cuisine"]
        diet_type = request.form["diet_type"]
        instructions = request.form["instructions"]
        ingredients = request.form["ingredients"]
        ingredients_count = request.form["ingredients_count"]

        cur.execute("""
            UPDATE recipes
            SET recipe_name = ?, cuisine = ?, diet_type = ?, instructions = ?, ingredients = ?, ingredients_count = ?
            WHERE recipe_id = ?
        """, (recipe_name, cuisine, diet_type, instructions, ingredients, ingredients_count, recipe_id))
        conn.commit()
        conn.close()

        flash("Recipe updated successfully!")
        return redirect(url_for("manage_recipes"))

    cur.execute("SELECT * FROM recipes WHERE recipe_id = ?", (recipe_id,))
    recipe = cur.fetchone()
    conn.close()

    return render_template("update_recipes_admin.html", recipe=recipe)

@app.route("/admin/delete_recipe_admin/<int:recipe_id>", methods=["POST"])
def delete_recipe_entry(recipe_id):
    conn = sqlite3.connect('database.db')
    cur = conn.cursor()

    cur.execute("DELETE FROM recipes WHERE recipe_id = ?", (recipe_id,))
    conn.commit()
    conn.close()

    flash("Recipe deleted successfully!")
    return redirect(url_for("manage_recipes"))




@app.route("/admin/manage_suppliers")
def manage_suppliers():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Fetch suppliers with role='supplier'
    cursor.execute("SELECT user_id, username, email, role, date_created FROM users WHERE role = 'supplier'")
    suppliers = cursor.fetchall()

    conn.close()
    return render_template("manage_suppliers.html", suppliers=suppliers)


@app.route("/admin/remove_supplier/<int:supplier_id>", methods=["POST"])
def remove_supplier(supplier_id):
    conn = sqlite3.connect('your_database.db')
    cursor = conn.cursor()

    # Delete supplier by user_id
    cursor.execute("DELETE FROM users WHERE user_id = ?", (supplier_id,))
    conn.commit()
    conn.close()

    flash("Supplier removed successfully!", "success")
    return redirect(url_for("manage_suppliers"))




@app.route("/admin/settings", methods=["GET", "POST"])
def settings():
    settings = {'theme': 'dark', 'notifications': True}  # Example settings
    return render_template("settings.html", settings=settings)


@app.route("/admin/assign_roles", methods=["GET", "POST"])
def assign_roles():
    if request.method == "POST":
        user_id = request.form.get("user_id")
        new_role = request.form.get("role")

        if not user_id or not new_role:
            flash("Both User ID and Role are required!", "error")
            return redirect(url_for("assign_roles"))

        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()

        # Check if the user exists
        cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        user = cursor.fetchone()

        if not user:
            flash("User not found!", "error")
            conn.close()
            return redirect(url_for("assign_roles"))

        # Update the user's role
        cursor.execute("UPDATE users SET role = ? WHERE user_id = ?", (new_role, user_id))
        conn.commit()
        conn.close()

        flash(f"Role successfully updated to '{new_role}' for User ID {user_id}!", "success")
        return redirect(url_for("assign_roles"))

    # Fetch all users
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users")
    users = cursor.fetchall()
    conn.close()

    return render_template("assign_roles.html", users=users)



@app.route("/admin/audit_log")
def audit_log():
    # Add logic to display and manage system audit logs
    return render_template("audit_log.html")




if __name__ == "__main__":
    app.run(debug=True)
