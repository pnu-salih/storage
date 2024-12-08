def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()

        # Users table
        cursor.execute(""" 
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                email TEXT NOT NULL UNIQUE,
                password TEXT NOT NULL,
                role TEXT CHECK(role IN ('Admin', 'User', 'Supplier')) NOT NULL,
                date_created TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Inventory table
        cursor.execute(""" 
            CREATE TABLE IF NOT EXISTS inventory (
                inventory_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                item_name TEXT NOT NULL,
                category TEXT,
                quantity INTEGER NOT NULL,
                expiration_date DATE,
                FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE
            )
        """)

        # Supplier Products table
        cursor.execute(""" 
            CREATE TABLE IF NOT EXISTS supplier_products (
                product_id INTEGER PRIMARY KEY AUTOINCREMENT,
                supplier_id INTEGER NOT NULL,
                product_name TEXT NOT NULL,
                category TEXT NOT NULL,
                price REAL NOT NULL,
                quantity INTEGER NOT NULL,
                date_added TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (supplier_id) REFERENCES users (user_id) ON DELETE CASCADE
            )
        """)

        # Recipes table
        cursor.execute(""" 
            CREATE TABLE IF NOT EXISTS recipes (
                recipe_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                recipe_name TEXT NOT NULL,
                cuisine TEXT,
                diet_type TEXT CHECK(diet_type IN ('Vegan', 'Vegetarian', 'Gluten-Free', 'Non-Vegetarian')) NOT NULL,
                instructions TEXT NOT NULL,
                created_by INTEGER,
                FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE,
                FOREIGN KEY (created_by) REFERENCES users (user_id) ON DELETE SET NULL
            )
        """)

        # Recipe Ingredients table
        cursor.execute(""" 
            CREATE TABLE IF NOT EXISTS recipe_ingredients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                recipe_id INTEGER NOT NULL,
                ingredient_name TEXT NOT NULL,
                quantity TEXT NOT NULL,
                FOREIGN KEY (recipe_id) REFERENCES recipes (recipe_id) ON DELETE CASCADE
            )
        """)
