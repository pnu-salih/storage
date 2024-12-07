import sqlite3

# Connect to the SQLite database (or create it if it doesn't exist)
conn = sqlite3.connect('database.db')
cursor = conn.cursor()

# Example inventory data to insert
inventory_data = [
    (1, 'Rice', 'Grain', 50, '2025-06-15'),
    (1, 'Olive Oil', 'Oil', 20, '2025-03-22'),
    (2, 'Tomatoes', 'Vegetable', 30, '2024-12-10'),
    (2, 'Lentils', 'Legume', 15, '2025-01-05'),
    (3, 'Chicken Breast', 'Meat', 10, '2024-12-20'),
    (3, 'Broccoli', 'Vegetable', 25, '2024-12-15'),
    (4, 'Almonds', 'Nut', 10, '2025-04-10'),
    (4, 'Cheese', 'Dairy', 5, '2024-11-30')
]

# Insert data into the Inventory table
cursor.executemany('''
    INSERT INTO Inventory (user_id, item_name, category, quantity, expiration_date)
    VALUES (?, ?, ?, ?, ?)
''', inventory_data)

# Commit the transaction
conn.commit()

# Close the connection
conn.close()

print("Data has been inserted successfully.")
