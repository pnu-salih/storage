from flask import Flask, render_template, request, redirect, url_for
import sqlite3

app = Flask(__name__)

# Database setup
DB_NAME = "database.db"

def execute_query(query, params=()):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.commit()
    conn.close()
    return rows

    
def get_db_connection():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row  # Rows are now accessible like dictionaries
    return conn

# Routes
@app.route("/")
def home():
    return render_template("home.html")

@app.route("/inventory", methods=["GET", "POST"])
def inventory():
    if request.method == "POST":
        # Add new inventory item
        item_name = request.form["item_name"]
        category = request.form["category"]
        quantity = request.form["quantity"]
        expiration_date = request.form["expiration_date"]
        user_id = 1  # Default user_id for now (replace with session management later)
        
        # Insert into inventory table
        execute_query("""
            INSERT INTO inventory (user_id, item_name, category, quantity, expiration_date)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, item_name, category, quantity, expiration_date))
        return redirect(url_for("inventory"))
    
    # Fetch all inventory items for the default user
    items = execute_query("SELECT * FROM inventory WHERE user_id = 1")
    return render_template("inventory.html", items=items)

@app.route("/delete_item/<int:inventory_id>", methods=["POST"])
def delete_item(inventory_id):
    user_id = 1  # Replace with the logged-in user ID
    execute_query("DELETE FROM inventory WHERE inventory_id = ? AND user_id = ?", (inventory_id, user_id))
    return redirect(url_for("inventory"))


@app.route("/edit_inventory_item/<int:inventory_id>", methods=["GET", "POST"])
def edit_inventory_item(inventory_id):
    user_id = 1  # Replace with the actual logged-in user ID

    if request.method == "POST":
        # Retrieve the updated quantity
        quantity = int(request.form["quantity"])

        # Update the quantity in the inventory
        execute_query("""
            UPDATE inventory
            SET quantity = ?
            WHERE inventory_id = ? AND user_id = ?
        """, (quantity, inventory_id, user_id))

        return redirect(url_for("inventory"))

    # Fetch the inventory item to edit
    item = execute_query("""
        SELECT * FROM inventory WHERE inventory_id = ? AND user_id = ?
    """, (inventory_id, user_id))

    if not item:
        return "Item not found or access denied.", 404

    item = item[0]  # Since the result is a list, we need the first element
    return render_template("edit_inventory_item.html", item=item)


@app.route("/recipes", methods=["GET", "POST"])
def recipes():
    if request.method == "POST":
        # Recipe details
        recipe_name = request.form["recipe_name"]
        cuisine = request.form["cuisine"]
        diet_type = request.form["diet_type"]
        instructions = request.form["instructions"]
        user_id = 1  # Placeholder for user ID
        
        # Combine ingredients and quantities
        selected_products = request.form.getlist("selected_products[]")
        quantities = request.form.to_dict(flat=False).get("quantities", {})

        ingredients = []
        ingredient_counts = []

        for product in selected_products:
            quantity = request.form.get(f"quantities[{product}]")
            if quantity:
                ingredients.append(product)
                ingredient_counts.append(quantity)

        # Convert to comma-separated strings
        ingredients_str = ", ".join(ingredients)
        ingredient_counts_str = ", ".join(ingredient_counts)

        # Insert into recipes table
        execute_query("""
            INSERT INTO recipes (user_id, recipe_name, cuisine, diet_type, instructions, created_by, ingredients, ingredients_count)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (user_id, recipe_name, cuisine, diet_type, instructions, user_id, ingredients_str, ingredient_counts_str))

        return redirect(url_for("recipes"))

    # Fetch all recipes
    recipes = execute_query("SELECT * FROM recipes")
    supplier_products = execute_query("SELECT product_name FROM supplier_products")

    return render_template("recipes.html", recipes=recipes, supplier_products=supplier_products)

#-------------------------------------------------------------------------------------------------
@app.route("/recipes/filter", methods=["GET"])
def filter_recipes():
    user_id = 1  # Placeholder for current logged-in user

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
    execute_query("DELETE FROM recipe_ingredients WHERE recipe_id = ?", (recipe_id,))
    return redirect(url_for("recipes"))



@app.route("/all_recipes", methods=["GET"])
def all_recipes():
    # Fetch all recipes from the database
    recipes = execute_query("SELECT * FROM recipes")
    return render_template("all_recipes.html", recipes=recipes)


#----------------------------------------suplier_products----------------------------------------------
@app.route("/supplier_products", methods=["GET", "POST"])
def supplier_products():
    # Simulate logged-in user role (replace this with actual session data)
    user_role = "Supplier"
    user_id = 1  # Replace with the logged-in supplier's user_id

    if user_role != "Supplier":
        return "Access denied. Only suppliers can access this page.", 403

    if request.method == "POST":
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
        
        return redirect(url_for("supplier_products"))

    # Fetch all products added by the supplier
    products = execute_query("SELECT * FROM supplier_products WHERE supplier_id = ?", (user_id,))
    return render_template("supplier_products.html", products=products)

#-------------------Edit supplied products-------------------------------
@app.route("/edit_supplier_product/<int:product_id>", methods=["GET", "POST"])
def edit_supplier_product(product_id):
    user_role = "Supplier"
    user_id = 1  # Replace with logged-in supplier's user_id

    if user_role != "Supplier":
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
def supplied_products():
    # Fetch all supplied products with supplier details
    products = execute_query("""
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
            JOIN users ON supplier_products.supplier_id = users.user_id
        """)


    return render_template("supplied_products.html", products=products)



#---init database here---



if __name__ == "__main__":
    app.run(debug=True)
