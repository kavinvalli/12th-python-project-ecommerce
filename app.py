import pymysql as pm
import pickle

db = pm.connect(host='127.0.0.1', user='root', database="ecommerce")
c = db.cursor()

#########################################################################
########################### DATABASE PREPERATION ########################
#########################################################################

############################## CREATE TABLES ############################
c.execute("CREATE TABLE IF NOT EXISTS users (id INT(20) NOT NULL AUTO_INCREMENT PRIMARY KEY, name VARCHAR(255) NOT NULL, email VARCHAR(255) UNIQUE NOT NULL, admin TINYINT DEFAULT 0, password VARCHAR(255) NOT NULL);")
c.execute("CREATE TABLE IF NOT EXISTS products (id INT(20) NOT NULL AUTO_INCREMENT PRIMARY KEY, name VARCHAR(255) NOT NULL, description TEXT, price FLOAT(10,2) NOT NULL, inventory INT(20) DEFAULT 0);")
c.execute("CREATE TABLE IF NOT EXISTS carts (id INT(20) NOT NULL AUTO_INCREMENT PRIMARY KEY, user_id INT(20) NOT NULL, status ENUM('ACTIVE', 'ORDERED') DEFAULT 'ACTIVE', FOREIGN KEY(user_id) REFERENCES users(id));")
c.execute("CREATE TABLE IF NOT EXISTS cart_items (id INT(20) NOT NULL AUTO_INCREMENT PRIMARY KEY, cart_id INT(20) NOT NULL, product_id INT(20) NOT NULL, quantity INT NOT NULL DEFAULT 1, FOREIGN KEY(cart_id) REFERENCES carts(id), FOREIGN KEY(product_id) REFERENCES products(id));")
c.execute("CREATE TABLE IF NOT EXISTS orders (id INT(20) NOT NULL AUTO_INCREMENT PRIMARY KEY, cart_id INT(20) NOT NULL, status ENUM('ORDERED', 'SHIPPED', 'DELIVERED') DEFAULT 'ORDERED',  FOREIGN KEY(cart_id) REFERENCES carts(id));")
db.commit()
############################ CREATE TABLES OVER #########################

####################### SEED PRODUCTS INTO DATABASE #####################
default_products = [
    ("Echo Dot (3rd Gen) – New and improved smart speaker with Alexa (Black)",
     """Echo Dot is a smart speaker that can be operated by voice, is compact and can fit in your favorite places.""", 3499.00, 20),
    ("Apple iPhone 13 (128GB) - Midnight",
     "15 cm (6.1-inch) Super Retina XDR display phone", 70900.00, 10),
    ("Harry Potter Box Set: The Complete Collection (Set of 7 Volumes)", """A beautiful boxed set containing all seven Harry Potter novels in paperback. These new editions of the classic and internationally bestselling, multi-award-winning series feature instantly pick-up-able new jackets by Jonny Duddle, with huge child appeal, to bring Harry Potter to the next generation of readers. It's time to PASS THE MAGIC ON.""", 3110.00, 2),
    ("2021 Apple iMac with 4.5K Retina Display (24-inch/60.96 cm, Apple M1 chip with 8‑core CPU and 8‑core GPU, 8GB RAM, 256GB) - Silver",
     """Immersive 60.96 cm (24-inch) 4.5K Retina display with P3 wide color gamut and 500 nits of brightness""", 130990.00, 5)
]
c.execute("SELECT * from products")
if c.rowcount == 0:
    c.executemany(
        "INSERT INTO products (name, description, price, inventory) VALUES (%s, %s, %s, %s)", default_products)
    db.commit()
##################### SEED PRODUCTS INTO DATABASE OVER ###################

######################### SEED USERS INTO DATABASE #######################
c.execute("SELECT * from users where admin=1")
if c.rowcount == 0:
    c.execute("INSERT INTO users (name, email, admin, password) VALUES ('Admin', 'admin@admin.com', 1, 'adminadmin')")
db.commit()
###################### SEED USERS INTO DATABASE OVER #####################

############################## CREATE user.dat ###########################
file = open("user.dat", "rb+")
try:
    content = pickle.load(file)
except EOFError:
    pickle.dump((), file)
file.close()
########################### CREATE user.dat OVER #########################

#########################################################################
######################### DATABASE PREPERATION OVER #####################
#########################################################################

logged_in = False
logged_in_user = None
USER_INPUT = """1. Show All Products
2. Search Products
3. Sort Products and List
4. Add Product to Cart
5. Show Active Cart (Remove/Change Quantity)
6. Clear Cart
7. Place Order
8. View Orders
9. Logout
10. Quit
What do you want to do? """
ADMIN_INPUT = """1. Show All Products
2. Search Products
3. Sort Products and List
4. Add New Product
5. Change Inventory of a Product
6. View all orders
7. Update order status
8. Logout
9. Quit
What do you want to do? """
NOT_LOGGED_IN_INPUT = """1. Login
2. Register
3. Quit
What do you want to do?: """
ORDER_STATUS_INPUT = """1. Ordered
2. Shipped
3. Delivered
Enter new status: """
CART_ACTIONS_INPUT = """1. Remove something from the cart
2. Change quantity of item
3. Clear Cart
4. Done
What do you want to do? """

#########################################################################
############################ UTILITY FUNCTIONS ##########################
#########################################################################


def store_user(user):
    """
    Stores user in user.txt

    Args:
    ---
        user : tuple
            the user object to be stored
    """
    file = open("user.dat", "wb")
    pickle.dump(user, file)
    file.close()


def list_products(products):
    """
    Prints all the products in the desired format

    Args:
    ---
        products : list[tuple[int, str, str, float, int]]
            list of products to be printed
    """
    for product in products:
        print(f"""ID: {product[0]}
Name: {product[1]}
Description: {product[2]}
Price: Rs. {product[3]}
Availability: {"Yes" if product[4] > 0 else "No"}({product[4]})\n""")


def delete_cart(cart_id):
    """
    Deleted the cart with `cart_id`

    Args:
    ---
        cart_id : int
            The id of the cart to be deleted
    """
    c.execute("DELETE FROM carts where id=%s", (cart_id))
    db.commit()


def remove_from_cart(cart_id, product_id):
    """
    Removes a product from the cart

    Args:
    ---
        cart_id : int
            The id of the cart in which the product is
        product_id : int
            The id of the product of which the quantity is to be changed
    """
    c.execute("SELECT * FROM cart_items where cart_id=%s and product_id=%s",
              (cart_id, product_id))
    if c.rowcount == 0:
        print("Item does not exist in cart")
    else:
        c.execute(
            "delete from cart_items where cart_id=%s and product_id=%s", (cart_id, product_id))
        c.execute("SELECT * FROM cart_items where cart_id=%s and product_id=%s",
                  (cart_id, product_id))
        if c.rowcount == 0:
            delete_cart(cart_id)
        db.commit()


def change_cart_item_quantity(cart_id, product_id, quantity):
    """
    Changes the quantity of the product in the cart
    - In case the passed in quantity > total inventory, the total inventory is set as the quantity
    - In case the passed quantity is 0, it removes the item from the cart

    Args:
    ---
        cart_id : int
            The id of the cart in which the product is
        product_id : int
            The id of the product of which the quantity is to be changed
        quantity : int
            The updated quantity
    """
    if quantity == 0:
        remove_from_cart(cart_id, product_id)
    c.execute("select * from products where id=%s LIMIT 1", (product_id))
    product = c.fetchone()
    if product and product[4] < quantity:
        quantity = product[4]
        print(
            f"Only {quantity} items are available. Adding {quantity} to cart.")
    else:
        c.execute("update cart_items set quantity=%s where cart_id=%s and product_id=%s",
                  (quantity, cart_id, product_id))
        db.commit()


def check_if_cart_exists(user_id):
    """
    Checks if cart exists and returns cart if exists else False

    Args:
    ---
        user_id : int
            The id of the user of whose cart we have to check if exists

    Returns:
    ---
        The cart tuple if it exists, else False
    """
    c.execute(
        "SELECT * FROM carts where user_id=%s and status='ACTIVE' LIMIT 1", (user_id))
    if c.rowcount > 0:
        cart = c.fetchone()
        return cart
    return False


def clear_cart(cart_id):
    """
    Deleted all items from the cart and calls the delete_cart function to delete the cart

    Args:
    ---
        cart_id : int
            The id of the cart to be cleared
    """
    c.execute("DELETE FROM cart_items where cart_id=%s", (cart_id))
    delete_cart(cart_id)


def get_cart_items(cart_id):
    """
    Returns a list of all items in cart with cart_id as argument

    Args:
    ---
        cart_id : int
            The id of the cart of which the items are to be found out

    Returns:
    ---
        List of products
    """
    items = []
    c.execute(
        "SELECT * FROM cart_items c, products p where c.product_id=p.id and c.cart_id=%s", (cart_id))
    cart_items = c.fetchall()
    for item in cart_items:
        _, cart_id, product_id, quantity, _, product_name, product_description, product_price, total_product_inventory = item
        items.append((product_id, product_name, product_description,
                     product_price, quantity, total_product_inventory))
    return items


def list_cart_items(cart_id):
    """
    List all the items in the cart of which the id is passed as argument

    Args:
    ---
        cart_id : int
            The id of the cart to be cleared
    """
    products = get_cart_items(cart_id)
    for product in products:
        print(f"""ID: {product[0]}
Name: {product[1]}
Description: {product[2]}
Price: Rs. {product[3]}
Quantity: {product[4]}\n""")

#########################################################################
########################## UTILITY FUNCTIONS OVER #######################
#########################################################################

#########################################################################
############################## MENU FUNCTIONS ###########################
#########################################################################


def login():
    """
    Login User
    - Takes email and password input (not parameters).
    - Checks for user with email.
    - Checks password.
    - Sets `logged_in = True`.
    - Sets `logged_in_user` to the user who was logged in.
    """
    while True:
        email = input("Enter email: ")
        password = input("Enter password: ")
        c.execute("SELECT * FROM users where email=%s LIMIT 1", (email))
        if c.rowcount == 0:
            print("Incorrect email. Please check the entered email ID.")
            reg = input("Do you want to register instead? (Y/N)")
            if reg in "yY":
                register()
                break
        else:
            user = c.fetchone()
            if user and user[4] == password:
                store_user(user)
                global logged_in, logged_in_user
                logged_in = True
                logged_in_user = user
                print("Logged in")
                print(logged_in_user)
                break
            else:
                print("Incorrect Password. Try again.")


def register():
    """
    Register User
    - Takes name, email, password input and validates
    - Checks if user with email already exists
    - Creates new user with admin=0
    """
    name = input("Enter name: ")
    email = input("Enter email: ")
    password = input("Enter password: ")
    while name == None or len(name) < 2:
        print("Invalid name. Please try again.")
        name = input("Enter name: ")
    while email == None or len(email) < 2 or "@" not in email:
        print("Invalid email. Please try again.")
        email = input("Enter email: ")
    while password == None or len(password) < 8:
        print("Password has to be atleast 8 characters long. Please try again.")
        password = input("Enter password: ")
    c.execute("SELECT * FROM users where email=%s", (email))
    if c.rowcount > 0:
        lgn = input(
            "User with email already exists. Do you want to login instead(Y/N)? ")
        if lgn in "yY":
            login()
    else:
        c.execute("INSERT INTO users (name, email, password) VALUES (%s, %s, %s)",
                  (name, email, password))
        db.commit()
        c.execute(
            "SELECT id,name,email,admin FROM users WHERE id=%s LIMIT 1", (c.lastrowid))
        user = c.fetchone()
        print(user)
        global logged_in, logged_in_user
        store_user(user)
        logged_in = True
        logged_in_user = user


def logout():
    file = open("user.dat", "wb")
    pickle.dump((), file)
    file.close()


def show_all_products():
    """
    Shows all the products
    """
    c.execute("SELECT * FROM products")
    products = c.fetchall()
    list_products(products)


def search_products():
    """
    Shows all the prodcts after taking a search query
    """
    search_query = input("Search: ")
    c.execute(
        "SELECT * from products WHERE name LIKE CONCAT('%%', %s, '%%')", (search_query))
    products = c.fetchall()
    list_products(products)


def sort_products():
    """
    Lists products after taking condition for sorting input
    """
    u_sort_by = input("""Sort by:
1. Name
2. Price
Which one do you want? """)
    u_sort_order = input("Ascending / Descending (A/D)")
    sort_by = "name" if u_sort_by == "1" else "price"
    sort_order = "ASC" if u_sort_order in "aA" else "DESC"
    print(sort_by, sort_order)
    c.execute(f"SELECT * FROM products ORDER BY {sort_by} {sort_order}")
    products = c.fetchall()
    list_products(products)


def add_to_cart():
    """
    Adds to cart after taking input `product_id` and `quantity`
    - In case the product already exists in cart, changes the quantity to existing quantity + the quantity specified by the user
    """
    while True:
        product_id = input(
            "Enter Product ID (if you don't know which products, press enter without typing anything): ")
        while not product_id or product_id == "":
            show_all_products()
            product_id = input(
                "Enter Product ID (if you don't know which products, press enter without typing anything): ")
        product_id = int(product_id)
        quantity = int(input("Enter Quantity to be added: "))
        user_id = logged_in_user[0]
        c.execute("SELECT * FROM products WHERE id=%s", (product_id))
        product = c.fetchone()
        c.execute(
            "SELECT * FROM carts where user_id=%s and status='ACTIVE' LIMIT 1", (user_id))
        cart = c.fetchone()
        cart_id = 0
        if cart:
            cart_id = cart[0]
        if c.rowcount != 1:
            c.execute("INSERT INTO carts (user_id) VALUES (%s)", (user_id))
            db.commit()
            cart_id = c.lastrowid
        c.execute(
            "SELECT * FROM cart_items WHERE product_id=%s and cart_id=%s LIMIT 1", (product_id, cart_id))
        cart_item = c.fetchone()
        if c.rowcount > 0 and cart_item:
            print(
                f"Product already exists in cart. Adding {quantity} products to existing {cart_item[3]}...")
            change_cart_item_quantity(
                cart_id, product_id, cart_item[3] + quantity)

        else:
            if not product:
                print("Product does not exist. Try again.")
                break
            if product and product[4] < quantity:
                quantity = product[4]
                print(
                    f"Only {quantity} items are available. Adding {quantity} to cart...")
            try:
                c.execute("INSERT INTO cart_items (cart_id, product_id, quantity) VALUES (%s, %s, %s)",
                          (cart_id, product_id, quantity))
                db.commit()
                list_cart_items(cart_id)
                break
            except:
                print("Something went wrong")
                break


def show_active_cart():
    """
    Lists all the products in the cart and provides the following actions:
        - Remove a product
        - Change quantity of a product
    """
    user_id = logged_in_user[0]
    cart = check_if_cart_exists(user_id)
    if not cart:
        print("Your cart is empty. Add new items by using option 4.")
    else:
        if cart:
            cart_id = cart[0]
            list_cart_items(cart_id)
            action = input(CART_ACTIONS_INPUT)
            if action == "1":
                product_id = int(input("Which product to remove (enter ID)? "))
                remove_from_cart(cart_id, product_id)
            elif action == "2":
                product_id = int(input("Which product (enter ID)? "))
                quantity = int(input("Enter new quantity: "))
                change_cart_item_quantity(cart_id, product_id, quantity)
            elif action == "3":
                clear_cart(cart_id)


def place_order():
    """
    Place an order
    - Add a record to order
    - Change cart status to ORDERED
    """
    user_id = logged_in_user[0]
    cart = check_if_cart_exists(user_id)
    if not cart:
        print("Your cart is empty. You can add something to the cart with option 4.")
    else:
        c.execute(
            "INSERT INTO orders (cart_id) VALUES (%s)", (cart[0]))
        c.execute(
            "UPDATE carts SET status='ORDERED' WHERE id=%s", (cart[0]))
        products = get_cart_items(cart[0])
        for product in products:
            c.execute("UPDATE products SET inventory=%s WHERE id=%s",
                      (product[5] - product[4], product[0]))
        print("Order placed!")
        db.commit()


def view_orders():
    """
    View orders of logged in user
    """
    # c.execute("SELECT * FROM orders INNER JOIN carts ON orders.cart_id=carts.id INNER JOIN cart_items ON cart_items.cart_id=carts.id INNER JOIN products ON products.id=cart_items.product_id WHERE carts.user_id=%s",
    #           (logged_in_user[0]))
    c.execute("SELECT * FROM orders WHERE cart_id=(SELECT id from carts where user_id=%s)",
              (logged_in_user[0]))
    orders = c.fetchall()
    for order in orders:
        print(f"ORDER #{order[0]} - {order[2]}")
        cart_id = order[1]
        items = get_cart_items(cart_id)
        list_products(items)

#########################################################################
########################### MENU FUNCTIONS OVER #########################
#########################################################################

#########################################################################
############################# ADMIN FUNCTIONS ###########################
#########################################################################


def add_new_product():
    """
    Add a new product to products list
    """
    name = input("Enter Product Name: ")
    description = input("Enter Product Description: ")
    price = float(input("Enter Product Price: "))
    inventory = int(input("Enter Product Inventory: "))
    c.execute(
        "INSERT INTO products (name, description, price, inventory) VALUES (%s, %s, %s, %s)", (name, description, price, inventory))
    db.commit()


def change_product_inventory():
    """
    Change inventory of a product
    """
    product_id = int(input("Enter Product ID: "))
    c.execute("SELECT * FROM products WHERE id=%s LIMIT 1", (product_id))
    if c.rowcount == 0:
        print("Product not found. Please check entered ID.")
    inventory = int(input("Enter New Inventory: "))
    c.execute("UPDATE products SET inventory=%s WHERE id=%s",
              (inventory, product_id))
    db.commit()


def view_all_orders():
    """
    View all orders
    """
    c.execute("SELECT * FROM orders")
    orders = c.fetchall()
    for order in orders:
        print(f"ORDER #{order[0]} - {order[2]}")
        cart_id = order[1]
        items = get_cart_items(cart_id)
        list_products(items)


def update_order_status():
    """
    Update status of an order
    """
    order_id = int(input("Enter Order ID: "))
    c.execute("SELECT * FROM orders WHERE id=%s LIMIT 1", (order_id))
    if c.rowcount == 0:
        print("Order not found. Please check entered ID.")
    status = ('ORDERED', 'SHIPPED', 'DELIVERED')[
        int(input(ORDER_STATUS_INPUT)) - 1]
    print(status)
    c.execute("UPDATE orders SET status=%s WHERE id=%s", (status, order_id))


#########################################################################
########################## ADMIN FUNCTIONS OVER #########################
#########################################################################


while True:
    file = open("user.dat", "rb")
    user = pickle.load(file)
    if user:
        logged_in = True
        logged_in_user = user
    file.close()
    if not logged_in:
        choice = input(NOT_LOGGED_IN_INPUT)
        if choice == "1":
            login()
        elif choice == "2":
            register()
        else:
            break
    else:
        if logged_in_user and logged_in_user[3] == 1:  # admin
            choice = input(ADMIN_INPUT)
            if choice == "1":
                show_all_products()
            elif choice == "2":
                search_products()
            elif choice == "3":
                sort_products()
            elif choice == "4":
                add_new_product()
            elif choice == "5":
                change_product_inventory()
            elif choice == "6":
                view_all_orders()
            elif choice == "7":
                update_order_status()
            elif choice == "8":
                logout()
                break
            elif choice == "9":
                break
        else:  # normal user
            choice = input(USER_INPUT)
            if choice == "1":
                show_all_products()
            elif choice == "2":
                search_products()
            elif choice == "3":
                sort_products()
            elif choice == "4":
                add_to_cart()
            elif choice == "5":
                show_active_cart()
            elif choice == "6":
                cart = check_if_cart_exists(logged_in_user[0])
                if not cart:
                    print("You have an empty cart.")
                else:
                    clear_cart(cart[0])
            elif choice == "7":
                place_order()
            elif choice == "8":
                view_orders()
            elif choice == "9":
                logout()
                break
            elif choice == "10":
                break
db.close()
