import mysql.connector
from mysql.connector import Error

def create_database_and_tables():
    try:
        # Connect to MySQL server
        connection = mysql.connector.connect(
            host="localhost",
            user="root",
            password="tiger"
        )

        if connection.is_connected():
            cursor = connection.cursor()

            # Create Database
            cursor.execute("CREATE DATABASE IF NOT EXISTS FaceRecognitionDB")
            print("Database 'FaceRecognitionDB' created successfully.")

            # Use the Database
            cursor.execute("USE FaceRecognitionDB")

            # Create 'Names' Table
            create_names_table_query = """
            CREATE TABLE IF NOT EXISTS Names (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(255) NOT NULL
            )
            """
            cursor.execute(create_names_table_query)
            print("Table 'Names' created successfully.")

            # Create 'Attendance' Table
            create_attendance_table_query = """
            CREATE TABLE IF NOT EXISTS Attendance (
                student_id VARCHAR(50) NOT NULL,
                student_name VARCHAR(255) NOT NULL,
                status VARCHAR(50) DEFAULT 'NA',
                date DATE NOT NULL,  -- Ensure date is NOT NULL
                entry_time TIME,
                PRIMARY KEY (student_id, date)  -- Composite key to handle multiple records per student
            )
            """
            cursor.execute(create_attendance_table_query)
            print("Table 'Attendance' created successfully.")

    except Error as e:
        print(f"Error: {e}")
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()
            print("MySQL connection is closed.")

# Call the function to create the database and tables
create_database_and_tables()
