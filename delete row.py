import pyodbc

# Database connection parameters
DB_SERVER = 'Navsuv'
DB_USER = '1c'
DB_PASSWORD = 'xxxx1111*'
DB_NAME = 'Suvtaminoti_venons'
DB_TABLE = 'БотДанныеЗупСувОкава'
ID_TO_DELETE = '4654654654'

# Connection string
connection_string = (
    f'DRIVER={{SQL Server}};'
    f'SERVER={DB_SERVER};'
    f'DATABASE={DB_NAME};'
    f'UID={DB_USER};'
    f'PWD={DB_PASSWORD}'
)

try:
    # Establish connection to the database
    conn = pyodbc.connect(connection_string)
    cursor = conn.cursor()

    # SQL query to delete the row
    query = f'DELETE FROM {DB_TABLE} WHERE IDСотрудник = ?'
    cursor.execute(query, ID_TO_DELETE)

    # Commit the transaction
    conn.commit()

    print(f'Row with IDСотрудник = {ID_TO_DELETE} has been deleted.')

except Exception as e:
    print(f"An error occurred: {e}")

finally:
    # Close the connection
    if conn:
        conn.close()
