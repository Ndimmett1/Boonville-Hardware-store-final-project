import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
from datetime import datetime
import os
import sys

# =====================================================
# DATABASE
# =====================================================

conn = sqlite3.connect("boonville_hardware.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS inventory(
    item_id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_name TEXT NOT NULL,
    category TEXT,
    quantity INTEGER,
    price REAL
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS sales(
    sale_id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_name TEXT,
    quantity_sold INTEGER,
    sale_date TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS users(
    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE,
    password TEXT,
    role TEXT
)
""")

cursor.execute("""
INSERT OR IGNORE INTO users
(username,password,role)
VALUES
('manager','manager123','Manager')
""")

cursor.execute("""
INSERT OR IGNORE INTO users
(username,password,role)
VALUES
('employee','employee123','Employee')
""")

conn.commit()

# =====================================================
# GLOBALS
# =====================================================

current_user = ""
current_role = ""

# =====================================================
# AUTHENTICATION
# =====================================================

def authenticate():

    global current_user
    global current_role

    username = username_entry.get().strip()
    password = password_entry.get().strip()

    cursor.execute("""
    SELECT username, role
    FROM users
    WHERE username=? AND password=?
    """, (username, password))

    user = cursor.fetchone()

    if user:

        current_user = user[0]
        current_role = user[1]

        login_window.destroy()
        launch_inventory_system()

    else:
        messagebox.showerror(
            "Login Failed",
            "Invalid Username or Password"
        )

# =====================================================
# MAIN APPLICATION
# =====================================================

def launch_inventory_system():

    root = tk.Tk()
    root.title(
        f"Boonville Hardware Store - {current_role}"
    )
    root.geometry("1300x750")

    # ==========================================
    # FUNCTIONS
    # ==========================================

    def clear_fields():
        name_entry.delete(0, tk.END)
        category_combo.set("")
        quantity_entry.delete(0, tk.END)
        price_entry.delete(0, tk.END)

    def update_dashboard():

        cursor.execute("SELECT COUNT(*) FROM inventory")
        total_products = cursor.fetchone()[0]

        cursor.execute(
            "SELECT COUNT(*) FROM inventory WHERE quantity <= 5"
        )
        low_stock = cursor.fetchone()[0]

        cursor.execute(
            "SELECT SUM(quantity * price) FROM inventory"
        )

        total_value = cursor.fetchone()[0]

        if total_value is None:
            total_value = 0

        total_products_label.config(
            text=f"Total Products: {total_products}"
        )

        low_stock_label.config(
            text=f"Low Stock Items: {low_stock}"
        )

        inventory_value_label.config(
            text=f"Inventory Value: ${total_value:,.2f}"
        )

    def load_inventory():

        inventory_tree.delete(
            *inventory_tree.get_children()
        )

        cursor.execute(
            "SELECT * FROM inventory"
        )

        rows = cursor.fetchall()

        for row in rows:
            inventory_tree.insert(
                "",
                tk.END,
                values=row
            )

        update_dashboard()

    def add_item():

        try:
            cursor.execute("""
            INSERT INTO inventory
            (item_name, category, quantity, price)
            VALUES (?, ?, ?, ?)
            """,
            (
                name_entry.get(),
                category_combo.get(),
                int(quantity_entry.get()),
                float(price_entry.get())
            ))

            conn.commit()

            load_inventory()
            clear_fields()

            messagebox.showinfo(
                "Success",
                "Item Added"
            )

        except ValueError:
            messagebox.showerror(
                "Error",
                "Enter valid values"
            )

    def update_item():

        selected = inventory_tree.selection()

        if not selected:
            return

        item_id = inventory_tree.item(
            selected[0]
        )["values"][0]

        cursor.execute("""
        UPDATE inventory
        SET item_name=?,
            category=?,
            quantity=?,
            price=?
        WHERE item_id=?
        """,
        (
            name_entry.get(),
            category_combo.get(),
            int(quantity_entry.get()),
            float(price_entry.get()),
            item_id
        ))

        conn.commit()
        load_inventory()

    def delete_item():

        selected = inventory_tree.selection()

        if not selected:
            return

        item_id = inventory_tree.item(
            selected[0]
        )["values"][0]

        cursor.execute(
            "DELETE FROM inventory WHERE item_id=?",
            (item_id,)
        )

        conn.commit()
        load_inventory()

    def select_item(event):

        selected = inventory_tree.selection()

        if selected:

            values = inventory_tree.item(
                selected[0]
            )["values"]

            clear_fields()

            name_entry.insert(0, values[1])
            category_combo.set(values[2])
            quantity_entry.insert(0, values[3])
            price_entry.insert(0, values[4])

    def search_inventory():

        keyword = search_entry.get()

        cursor.execute("""
        SELECT *
        FROM inventory
        WHERE item_name LIKE ?
        OR category LIKE ?
        """,
        (
            f"%{keyword}%",
            f"%{keyword}%"
        ))

        search_tree.delete(
            *search_tree.get_children()
        )

        for row in cursor.fetchall():

            search_tree.insert(
                "",
                tk.END,
                values=row
            )

    def low_stock_report():

        cursor.execute("""
        SELECT item_name, quantity
        FROM inventory
        WHERE quantity <= 5
        """)

        rows = cursor.fetchall()

        report = ""

        for row in rows:
            report += f"{row[0]} - {row[1]}\n"

        if not report:
            report = "No Low Stock Items"

        messagebox.showinfo(
            "Report",
            report
        )

    def record_sale():

        try:

            item_id = int(
                sale_id_entry.get()
            )

            qty_sold = int(
                sale_qty_entry.get()
            )

            cursor.execute("""
            SELECT item_name,
                   quantity
            FROM inventory
            WHERE item_id=?
            """,
            (item_id,))

            result = cursor.fetchone()

            if not result:
                return

            name = result[0]
            quantity = result[1]

            if qty_sold > quantity:

                messagebox.showerror(
                    "Error",
                    "Insufficient Stock"
                )

                return

            cursor.execute("""
            UPDATE inventory
            SET quantity=?
            WHERE item_id=?
            """,
            (
                quantity - qty_sold,
                item_id
            ))

            cursor.execute("""
            INSERT INTO sales
            (item_name,quantity_sold,sale_date)
            VALUES(?,?,?)
            """,
            (
                name,
                qty_sold,
                datetime.now().strftime(
                    "%m/%d/%Y"
                )
            ))

            conn.commit()

            load_inventory()

            messagebox.showinfo(
                "Success",
                "Sale Recorded"
            )

        except ValueError:
            messagebox.showerror(
                "Error",
                "Invalid Input"
            )

    def logout():

        root.destroy()

        os.execl(
            sys.executable,
            sys.executable,
            *sys.argv
        )

    # ==========================================
    # MENU
    # ==========================================

    menubar = tk.Menu(root)

    account_menu = tk.Menu(
        menubar,
        tearoff=0
    )

    account_menu.add_command(
        label="Logout",
        command=logout
    )

    account_menu.add_separator()

    account_menu.add_command(
        label="Exit",
        command=root.destroy
    )

    menubar.add_cascade(
        label="Account",
        menu=account_menu
    )

    root.config(menu=menubar)

    # ==========================================
    # NOTEBOOK
    # ==========================================

    notebook = ttk.Notebook(root)
    notebook.pack(fill="both", expand=True)

    dashboard_tab = ttk.Frame(notebook)
    inventory_tab = ttk.Frame(notebook)
    search_tab = ttk.Frame(notebook)
    reports_tab = ttk.Frame(notebook)
    sales_tab = ttk.Frame(notebook)

    notebook.add(dashboard_tab, text="Dashboard")
    notebook.add(inventory_tab, text="Inventory")
    notebook.add(search_tab, text="Search")
    notebook.add(reports_tab, text="Reports")
    notebook.add(sales_tab, text="Sales")

    # ==========================================
    # DASHBOARD
    # ==========================================

    tk.Label(
        dashboard_tab,
        text="Boonville Hardware Dashboard",
        font=("Arial", 20, "bold")
    ).pack(pady=15)

    tk.Label(
        dashboard_tab,
        text=f"Welcome {current_user}",
        font=("Arial", 16)
    ).pack()

    tk.Label(
        dashboard_tab,
        text=f"Role: {current_role}",
        font=("Arial", 14)
    ).pack()

    total_products_label = tk.Label(
        dashboard_tab,
        font=("Arial", 14)
    )
    total_products_label.pack(pady=10)

    low_stock_label = tk.Label(
        dashboard_tab,
        font=("Arial", 14)
    )
    low_stock_label.pack(pady=10)

    inventory_value_label = tk.Label(
        dashboard_tab,
        font=("Arial", 14)
    )
    inventory_value_label.pack(pady=10)

    # ==========================================
    # INVENTORY TAB
    # ==========================================

    left_frame = tk.Frame(inventory_tab)
    left_frame.pack(
        side=tk.LEFT,
        fill=tk.Y,
        padx=10,
        pady=10
    )

    right_frame = tk.Frame(inventory_tab)
    right_frame.pack(
        side=tk.RIGHT,
        fill=tk.BOTH,
        expand=True
    )

    tk.Label(left_frame,
             text="Item Name").pack()

    name_entry = tk.Entry(left_frame)
    name_entry.pack()

    tk.Label(left_frame,
             text="Category").pack()

    category_combo = ttk.Combobox(
        left_frame,
        values=[
            "Tools",
            "Power Tools",
            "Electrical",
            "Plumbing",
            "Paint",
            "Lumber",
            "Fasteners"
        ]
    )
    category_combo.pack()

    tk.Label(left_frame,
             text="Quantity").pack()

    quantity_entry = tk.Entry(left_frame)
    quantity_entry.pack()

    tk.Label(left_frame,
             text="Price").pack()

    price_entry = tk.Entry(left_frame)
    price_entry.pack()

    add_button = tk.Button(
        left_frame,
        text="Add Item",
        command=add_item
    )
    add_button.pack(pady=5)

    update_button = tk.Button(
        left_frame,
        text="Update Item",
        command=update_item
    )
    update_button.pack(pady=5)

    delete_button = tk.Button(
        left_frame,
        text="Delete Item",
        command=delete_item
    )
    delete_button.pack(pady=5)

    if current_role == "Employee":
        add_button.config(state="disabled")
        update_button.config(state="disabled")
        delete_button.config(state="disabled")

    columns = (
        "ID",
        "Name",
        "Category",
        "Quantity",
        "Price"
    )

    inventory_tree = ttk.Treeview(
        right_frame,
        columns=columns,
        show="headings"
    )

    for col in columns:
        inventory_tree.heading(
            col,
            text=col
        )

    inventory_tree.pack(
        fill=tk.BOTH,
        expand=True
    )

    inventory_tree.bind(
        "<ButtonRelease-1>",
        select_item
    )

    # ==========================================
    # SEARCH TAB
    # ==========================================

    search_entry = tk.Entry(
        search_tab,
        width=40
    )

    search_entry.pack(pady=10)

    tk.Button(
        search_tab,
        text="Search",
        command=search_inventory
    ).pack()

    search_tree = ttk.Treeview(
        search_tab,
        columns=columns,
        show="headings"
    )

    for col in columns:
        search_tree.heading(
            col,
            text=col
        )

    search_tree.pack(
        fill=tk.BOTH,
        expand=True
    )

    # ==========================================
    # REPORTS TAB
    # ==========================================

    tk.Button(
        reports_tab,
        text="Low Stock Report",
        command=low_stock_report
    ).pack(pady=30)

    # ==========================================
    # SALES TAB
    # ==========================================

    tk.Label(
        sales_tab,
        text="Product ID"
    ).pack(pady=5)

    sale_id_entry = tk.Entry(
        sales_tab
    )
    sale_id_entry.pack()

    tk.Label(
        sales_tab,
        text="Quantity Sold"
    ).pack(pady=5)

    sale_qty_entry = tk.Entry(
        sales_tab
    )
    sale_qty_entry.pack()

    tk.Button(
        sales_tab,
        text="Complete Sale",
        command=record_sale
    ).pack(pady=20)

    # ==========================================
    # STATUS BAR
    # ==========================================

    status_bar = tk.Label(
        root,
        text=f"{current_user} | {current_role} | {datetime.now().strftime('%m/%d/%Y %I:%M %p')}",
        bd=1,
        relief=tk.SUNKEN,
        anchor=tk.W
    )

    status_bar.pack(
        side=tk.BOTTOM,
        fill=tk.X
    )

    load_inventory()
    update_dashboard()

    root.mainloop()

# =====================================================
# LOGIN WINDOW
# =====================================================

login_window = tk.Tk()
login_window.title("Boonville Hardware Login")
login_window.geometry("450x350")
login_window.resizable(False, False)

tk.Label(
    login_window,
    text="Boonville Hardware Store",
    font=("Arial", 20, "bold")
).pack(pady=15)

tk.Label(
    login_window,
    text="Inventory Management System"
).pack()

tk.Label(
    login_window,
    text="Username"
).pack(pady=(20, 5))

username_entry = tk.Entry(
    login_window,
    width=30
)

username_entry.pack()

tk.Label(
    login_window,
    text="Password"
).pack(pady=(10, 5))

password_entry = tk.Entry(
    login_window,
    width=30,
    show="*"
)

password_entry.pack()

tk.Button(
    login_window,
    text="Login",
    width=20,
    bg="green",
    fg="white",
    command=authenticate
).pack(pady=20)

tk.Label(
    login_window,
    text=(
        "Demo Accounts\n\n"
        "manager / manager123\n"
        "employee / employee123"
    ),
    fg="gray"
).pack()

login_window.mainloop()

conn.close()