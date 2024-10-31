import mysql.connector
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="YIZ4.1026yiz7",
    database="JAPGPT"
)
cursor = db.cursor()

drop_table_query = "DROP TABLE IF EXISTS jap_table"

create_table_query  = """
    CREATE TABLE jap_table (
        id INT AUTO_INCREMENT PRIMARY KEY,
        student_id VARCHAR(255) NOT NULL,
        question_text TEXT NOT NULL,
        is_correct BOOLEAN NOT NULL
    )
    """

insert_query = """
INSERT INTO jap_table (student_id, question_text, is_correct)
VALUES (%s, %s, %s)
"""

show_fiverows_query = "SELECT * FROM jap_table LIMIT 5"

select_mistake_query = """
    SELECT * FROM jap_table
    WHERE student_id = %s AND is_correct = 1
    """

# def drop_jap_table(cursor):
#     drop_table_query = "DROP TABLE IF EXISTS jap_table"
#     cursor.execute(drop_table_query)
#     db.commit()

# def create_jap_table(cursor):
#     table_creation_query = """
#     CREATE TABLE jap_table (
#         id INT AUTO_INCREMENT PRIMARY KEY,
#         student_id VARCHAR(255) NOT NULL,
#         question_text TEXT NOT NULL,
#         is_correct BOOLEAN NOT NULL
#     )
#     """
#     cursor.execute(table_creation_query)
#     db.commit()

