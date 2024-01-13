#!/usr/bin/env python
# coding: utf-8

# In[116]:


import psycopg2
from datetime import datetime, timedelta



conn = psycopg2.connect(
    database='term2',
    user='postgres',
    password='emremir!?',
    host='localhost',  # or the IP address of your database server
    port='5432'  # default PostgreSQL port number
)

# Create a cursor object
cur = conn.cursor()

# Create tables
cur.execute("""
CREATE TABLE Period (
    periodID SERIAL PRIMARY KEY,
    periodIndex INTEGER
);
""")

cur.execute("""
CREATE TABLE Part (
    partID SERIAL PRIMARY KEY,
    leadTime INTEGER,
    initialInventory INTEGER,
    lotSize INTEGER,
    billOfMaterialsLevel INTEGER,
    itemName VARCHAR(255)
);
""")

cur.execute("""
CREATE TABLE BillOfMaterial (
    partID INTEGER REFERENCES Part(partID),
    componentpartID INTEGER REFERENCES Part(partID),
    multiplier INTEGER,
    level INTEGER,
    PRIMARY KEY(partID, componentpartID)
);
""")


cur.execute("""
CREATE TABLE MRP (
    partID INTEGER REFERENCES Part(partID),
    periodID INTEGER REFERENCES Period(periodID),
    demand INTEGER,
    schedulingReceipt INTEGER,
    inventory INTEGER,
    PRIMARY KEY(partID, periodID)
);
""")





# Commit changes and close connection
conn.commit()


# In[117]:


#Sample data for the BOM
bom_data = [
    {'leadTime': 3, 'initialInventory': 50, 'lotSize': 10, 'billOfMaterialsLevel': 1, 'itemName': 'CPU'},
    {'leadTime': 2, 'initialInventory': 10, 'lotSize': 20, 'billOfMaterialsLevel': 2, 'itemName': 'CPU Chip'},
    {'leadTime': 1, 'initialInventory': 15, 'lotSize': 15, 'billOfMaterialsLevel': 2, 'itemName': 'Heat Sink'},
    {'leadTime': 2, 'initialInventory': 20, 'lotSize': 20, 'billOfMaterialsLevel': 3, 'itemName': 'Silicon Die'},
    {'leadTime': 1, 'initialInventory': 100, 'lotSize': 50, 'billOfMaterialsLevel': 3, 'itemName': 'Transistors'},

]

# Function to insert BOM data into the Part table
def insert_bom_data(connection, cursor, data):
    for item in data:
        cursor.execute("""
            INSERT INTO Part (leadTime, initialInventory, lotSize, billOfMaterialsLevel, itemName)
            VALUES (%s, %s, %s, %s, %s);
        """, (item['leadTime'], item['initialInventory'], item['lotSize'], item['billOfMaterialsLevel'], item['itemName']))
    connection.commit()

# Insert BOM data
insert_bom_data(conn, cur, bom_data)


# In[118]:


def insert_component_relationships(connection, cursor, cpu_chip_id, components):
    for component in components:
        cursor.execute("""
            INSERT INTO BillOfMaterial (partID, componentpartID, multiplier, level)
            VALUES (%s, %s, %s, %s);
        """, (cpu_chip_id, component['componentpartID'], component['multiplier'], component['level']))
    connection.commit()

def add_cpu_bom_entries(connection, cursor, cpu_id, cpu_chip_id, heat_sink_id):
    # For 1 CPU, you need 1 CPU Chip
    cursor.execute("""
        INSERT INTO BillOfMaterial (partID, componentpartID, multiplier)
        VALUES (%s, %s, %s);
    """, (cpu_id, cpu_chip_id, 1))

    # For 1 CPU, you need 3 Heat Sinks
    cursor.execute("""
        INSERT INTO BillOfMaterial (partID, componentpartID, multiplier)
        VALUES (%s, %s, %s);
    """, (cpu_id, heat_sink_id, 3))

    connection.commit()

# Assume you have the IDs for the CPU, CPU Chip, Heat Sink, Silicon Die, and Transistors
cpu_id = 1
cpu_chip_id = 2  
heat_sink_id = 3
silicon_die_id = 4  
transistors_id = 5  

# Component relationships for CPU Chip
components_for_cpu_chip = [
    {'componentpartID': silicon_die_id, 'multiplier': 1, 'level': 2},
    {'componentpartID': transistors_id, 'multiplier': 10, 'level': 2},
]

# Insert the component relationships for CPU Chip
insert_component_relationships(conn, cur, cpu_chip_id, components_for_cpu_chip)

# Insert BOM entries for CPU
add_cpu_bom_entries(conn, cur, cpu_id, cpu_chip_id, heat_sink_id)


# In[119]:


def insert_periods(cursor, total_months):
    for month in range(1, total_months + 1):
        cursor.execute("SELECT * FROM Period WHERE periodID = %s", (month,))
        if cursor.fetchone() is None:
            cursor.execute("INSERT INTO Period (periodID) VALUES (%s)", (month,))

def calculate_and_insert_mrp_for_months(conn, product_id, total_months):
    cur = conn.cursor()

    # Ensure all periods are present
    insert_periods(cur, total_months)

    for month in range(1, total_months + 1):
        # Calculate demand for the month (modify as needed)
        monthly_demand = 50  

        # Perform MRP calculation for the month
        # (Similar logic as before, but now for each month)

    conn.commit()
    cur.close()

# Example usage
calculate_and_insert_mrp_for_months(conn, 1, 8)


# In[120]:


import psycopg2

def fetch_all_data_from_db():
    
    cur = conn.cursor()

    # Retrieve all table names
    cur.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public'
    """)
    tables = cur.fetchall()

    # Loop through tables and print their contents
    for table in tables:
        table_name = table[0]
        print(f"Data from table: {table_name}")
        cur.execute(f"SELECT * FROM {table_name};")
        rows = cur.fetchall()
        for row in rows:
            print(row)
        print("\n")

# Call the function
fetch_all_data_from_db()


# In[121]:


import psycopg2
import math

def calculate_mrp(conn, periods, monthly_demand):
    cur = conn.cursor()

    # Fetch all parts with their lead times and lot sizes
    cur.execute("SELECT partID, leadTime, lotSize, initialInventory FROM Part")
    parts_data = cur.fetchall()

    for part_id, lead_time, lot_size, initial_inventory in parts_data:
        # Initialize data structures for MRP
        gross_requirements = [monthly_demand] * (periods + 1)
        projected_inventory = [initial_inventory] + [0] * periods
        planned_order_receipts = [0] * (periods + 1)
        planned_order_releases = [0] * (periods + 1)

        # MRP calculation for each period
        for period in range(1, periods + 1):
            net_requirement = max(gross_requirements[period] - projected_inventory[period - 1], 0)
            if net_requirement > 0:
                # Round up to the nearest lot size
                order_qty = math.ceil(net_requirement / lot_size) * lot_size
                # Ensure we don't exceed the total periods
                receipt_period = min(period + lead_time, periods)
                planned_order_receipts[receipt_period] += order_qty
                planned_order_releases[period] += order_qty
            projected_inventory[period] = projected_inventory[period - 1] + planned_order_receipts[period] - gross_requirements[period]

        # Display the part MRP table
        print(f"MRP Table for Part ID: {part_id}")
        print(f"Period\t\t: {'  '.join(str(i) for i in range(1, periods + 1))}")
        print(f"Gross Requirement\t: {'  '.join(str(gross_requirements[i]) for i in range(1, periods + 1))}")
        print(f"Projected Inventory\t: {'  '.join(str(projected_inventory[i]) for i in range(1, periods + 1))}")
        print(f"Planned Order Receipt\t: {'  '.join(str(planned_order_receipts[i]) for i in range(1, periods + 1))}")
        print(f"Planned Order Release\t: {'  '.join(str(planned_order_releases[i]) for i in range(1, periods + 1))}")
        print("\n")

# Connect to the database and run the MRP calculation
conn = psycopg2.connect(dbname='term2', user='postgres', password='emremir!?', host='localhost', port='5432')
calculate_mrp(conn, 8, 50)  # Calculate MRP for 8 periods with a consistent monthly demand of 50


# In[125]:


import streamlit as st
import psycopg2
import math

# Function to connect to the database
def connect_db():
    return psycopg2.connect(
        database='term2', 
        user='postgres', 
        password='emremir!?', 
        host='localhost', 
        port='5432'
    )
# ... [connect_db function here]

def insert_bom_data(connection, data):
    cursor = connection.cursor()
    for item in data:
        cursor.execute("""
            INSERT INTO Part (leadTime, initialInventory, lotSize, billOfMaterialsLevel, itemName)
            VALUES (%s, %s, %s, %s, %s);
        """, (item['leadTime'], item['initialInventory'], item['lotSize'], item['billOfMaterialsLevel'], item['itemName']))
    connection.commit()

def display_parts(connection):
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM Part")
    parts = cursor.fetchall()
    st.table(parts)



def calculate_mrp(connection, periods, monthly_demand):
    cur = connection.cursor()
    cur.execute("SELECT partID, leadTime, lotSize, initialInventory FROM Part")
    parts_data = cur.fetchall()

    mrp_data = []
    for part_id, lead_time, lot_size, initial_inventory in parts_data:
        # Initialize data structures for MRP
        gross_requirements = [monthly_demand] * (periods + 1)
        projected_inventory = [initial_inventory] + [0] * periods
        planned_order_receipts = [0] * (periods + 1)
        planned_order_releases = [0] * (periods + 1)

        for period in range(1, periods + 1):
            net_requirement = max(gross_requirements[period] - projected_inventory[period - 1], 0)
            if net_requirement > 0:
                order_qty = math.ceil(net_requirement / lot_size) * lot_size
                receipt_period = min(period + lead_time, periods)
                planned_order_receipts[receipt_period] += order_qty
                planned_order_releases[period] += order_qty
            projected_inventory[period] = projected_inventory[period - 1] + planned_order_receipts[period] - gross_requirements[period]

        mrp_data.append((part_id, gross_requirements, projected_inventory, planned_order_receipts, planned_order_releases))
    
    return mrp_data

def display_mrp_results(mrp_results):
    for part_id, gross_requirements, projected_inventory, planned_order_receipts, planned_order_releases in mrp_results:
        st.write(f"MRP Table for Part ID: {part_id}")
        st.table({
            "Period": range(1, len(gross_requirements)),
            "Gross Requirement": gross_requirements[1:],
            "Projected Inventory": projected_inventory[1:],
            "Planned Order Receipt": planned_order_receipts[1:],
            "Planned Order Release": planned_order_releases[1:]
        })

def main():
    st.title("MRP Calculation")
    conn = connect_db()

    periods = st.number_input('Number of Periods', min_value=1, max_value=12, value=6)
    monthly_demand = st.number_input('Monthly Demand', min_value=0)
    if st.button('Calculate MRP'):
        mrp_results = calculate_mrp(conn, periods, monthly_demand)
        display_mrp_results(mrp_results)

    # ... [Other functionalities]

if __name__ == "__main__":
    main()


# In[ ]:





# In[ ]:





# In[ ]:





# In[ ]:





# In[ ]:





# In[ ]:





# In[ ]:





# In[ ]:





# In[ ]:





# In[ ]:





# In[ ]:





# In[ ]:





# In[ ]:





# In[ ]:





# In[ ]:





# In[ ]:





# In[ ]:





# In[ ]:





# In[ ]:





# In[ ]:





# In[ ]:





# In[ ]:





# In[ ]:





# In[ ]:





# In[ ]:





# In[ ]:





# In[ ]:





# In[ ]:





# In[ ]:





# In[ ]:





# In[ ]:





# In[ ]:





# In[ ]:





# In[ ]:





# In[ ]:





# In[ ]:





# In[ ]:





# In[ ]:





# In[ ]:





# In[ ]:





# In[ ]:




