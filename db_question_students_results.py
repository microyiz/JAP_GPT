import mysql.connector

# 连接到数据库
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="123", 
    database="JAPGPT"  
)
cursor = db.cursor()

# 删除旧表（如果存在）
drop_questions_table_query = "DROP TABLE IF EXISTS questions"
drop_students_table_query = "DROP TABLE IF EXISTS students"
drop_exam_results_table_query = "DROP TABLE IF EXISTS exam_results"


# 创建 `questions` 表
# NOT NULL UNIQUE 非空且唯一
create_questions_table_query = """
CREATE TABLE questions (
    question_id INT AUTO_INCREMENT PRIMARY KEY,
    question_index VARCHAR(255) NOT NULL UNIQUE COMMENT '用户查找题目时的索引号（题目编号）',
    content TEXT NOT NULL COMMENT '题目内容',
    correct_answer TEXT NOT NULL COMMENT '题目的正确答案',
    type TEXT NOT NULL COMMENT '题目类型，存储多个知识点',
    level ENUM('N4', 'N5') NOT NULL COMMENT '难度级别',
    is_gpt BOOLEAN NOT NULL DEFAULT 0 COMMENT '是否由AI生成'
)
"""


# 创建 `students` 表
create_students_table_query = """
CREATE TABLE students (
    student_id INT AUTO_INCREMENT PRIMARY KEY,
    student_no BIGINT NOT NULL UNIQUE COMMENT '学生学号',
    name VARCHAR(100) NOT NULL COMMENT '学生姓名',
    email VARCHAR(255) NOT NULL UNIQUE COMMENT '学生的电子邮箱'
)
"""

# # 创建 `students` 表
# create_students_table_query = """
# CREATE TABLE students (
#     student_no BIGINT PRIMARY KEY COMMENT '学生学号',
#     name VARCHAR(100) NOT NULL COMMENT '学生姓名',
#     email VARCHAR(255) NOT NULL UNIQUE COMMENT '学生的电子邮箱'
# )
# """



# 创建 `exam_results` 表
create_exam_results_table_query = """
CREATE TABLE exam_results (
    result_id INT AUTO_INCREMENT PRIMARY KEY,
    question_id INT NOT NULL,
    student_id INT NOT NULL,
    student_answer TEXT NOT NULL,
    is_correct BOOLEAN NOT NULL,
    FOREIGN KEY (question_id) REFERENCES questions(question_id) ON DELETE CASCADE,
    FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE
)
"""

select_mistake_query = """
    SELECT * FROM exam_results
    WHERE is_correct = 0
    """

select_all_query = """
    SELECT * FROM exam_results
    """

insert_questions_query = """
INSERT INTO questions (question_index, content, correct_answer, type, level, is_gpt)
VALUES (%s, %s, %s, %s, %s, %s)
"""

insert_students_query = """
INSERT INTO students (student_no, name, email)
VALUES (%s, %s, %s)
"""

insert_exam_results_query = """
INSERT INTO exam_results (question_id, student_id, student_answer, is_correct)
VALUES (%s, %s, %s, %s)
"""



import mysql.connector

# 连接到数据库
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="123",
    database="JAPGPT"
)
cursor = db.cursor()

# 删除旧表（如果存在）
drop_questions_table_query = "DROP TABLE IF EXISTS questions"
drop_students_table_query = "DROP TABLE IF EXISTS students"
drop_exam_results_table_query = "DROP TABLE IF EXISTS exam_results"

try:
    # 删除表，注意删除顺序，避免外键约束冲突
    cursor.execute(drop_exam_results_table_query)  # 先删除依赖于其他表的表
    cursor.execute(drop_students_table_query)  # 再删除学生表
    cursor.execute(drop_questions_table_query)  # 最后删除题目表

    print("旧表已删除")

    # 创建 `questions` 表
    create_questions_table_query = """
    CREATE TABLE questions (
        question_id INT AUTO_INCREMENT PRIMARY KEY,
        question_index VARCHAR(255) NOT NULL UNIQUE COMMENT '用户查找题目时的索引号（题目编号）',
        content TEXT NOT NULL COMMENT '题目内容',
        correct_answer TEXT NOT NULL COMMENT '题目的正确答案',
        type TEXT NOT NULL COMMENT '题目类型，存储多个知识点',
        level ENUM('N4', 'N5') NOT NULL COMMENT '难度级别',
        is_gpt BOOLEAN NOT NULL DEFAULT 0 COMMENT '是否由AI生成'
    )
    """
    cursor.execute(create_questions_table_query)
    print("questions 表已创建")

    # 创建 `students` 表
    create_students_table_query = """
    CREATE TABLE students (
        student_id INT AUTO_INCREMENT PRIMARY KEY,
        student_no BIGINT NOT NULL UNIQUE COMMENT '学生学号',
        name VARCHAR(100) NOT NULL COMMENT '学生姓名',
        email VARCHAR(255) NOT NULL UNIQUE COMMENT '学生的电子邮箱'
    )
    """
    cursor.execute(create_students_table_query)
    print("students 表已创建")

    # 创建 `exam_results` 表
    create_exam_results_table_query = """
    CREATE TABLE exam_results (
        result_id INT AUTO_INCREMENT PRIMARY KEY,
        question_id INT NOT NULL,
        student_id INT NOT NULL,
        student_answer TEXT NOT NULL,
        is_correct BOOLEAN NOT NULL,
        FOREIGN KEY (question_id) REFERENCES questions(question_id) ON DELETE CASCADE,
        FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE
    )
    """
    cursor.execute(create_exam_results_table_query)
    print("exam_results 表已创建")

except mysql.connector.Error as err:
    print(f"Error: {err}")

finally:
    # 提交更改并关闭连接
    db.commit()
    cursor.close()
    db.close()
    print("数据库操作完成")


'''

import mysql.connector

def alter_database_structure():
    # 连接到数据库
    db = mysql.connector.connect(
        host="localhost",        # 数据库主机
        user="root",        # 数据库用户名
        password="123",# 数据库密码
        database="japgpt" # 数据库名称
    )

    cursor = db.cursor()

    try:
        # 检查 exam_results 表是否包含 student_id 列
        cursor.execute("DESCRIBE exam_results")
        columns = cursor.fetchall()

        # 判断是否存在 student_id 列
        column_names = [column[0] for column in columns]
        if 'student_id' not in column_names:
            print("Adding student_id column to exam_results table...")
            cursor.execute("""
                ALTER TABLE exam_results 
                ADD COLUMN student_id INT
            """)
            print("student_id column added successfully.")

            # 确保外键约束存在
            cursor.execute("""
                ALTER TABLE exam_results 
                ADD CONSTRAINT fk_student_id
                FOREIGN KEY (student_id) REFERENCES students(student_id)
            """)
            print("Foreign key constraint added successfully.")
        
        else:
            print("student_id column already exists in exam_results table.")

        db.commit()

    except mysql.connector.Error as err:
        print(f"Error: {err}")
        db.rollback()
    
    finally:
        cursor.close()
        db.close()

if __name__ == "__main__":
    alter_database_structure()
'''

# import mysql.connector

# # 连接到 MySQL 数据库
# db_config = {
#     'host': 'localhost',         # 数据库主机名
#     'user': 'root',     # 数据库用户名
#     'password': '123', # 数据库密码
#     'database': 'japgpt'  # 数据库名称
# }

# try:
#     # 创建数据库连接
#     conn = mysql.connector.connect(**db_config)
#     cursor = conn.cursor()

#     # 检查调试数据（可选）
#     print("调试数据（删除前）：")
#     cursor.execute("""
#         SELECT * FROM exam_results
#         WHERE student_id IS NULL
#            OR question_id IS NULL
#            OR student_answer IS NULL
#            OR student_answer LIKE '%选项%';
#     """)
#     debug_data = cursor.fetchall()
#     for row in debug_data:
#         print(row)

#     # 删除调试数据
#     delete_query = """
#         DELETE FROM exam_results
#         WHERE student_id IS NULL
#            OR question_id IS NULL
#            OR student_answer IS NULL
#            OR student_answer LIKE '%选项%';
#     """
#     cursor.execute(delete_query)
#     conn.commit()  # 提交更改
#     print(f"已删除 {cursor.rowcount} 条调试数据。")

#     # 检查删除后的数据（可选）
#     print("调试数据（删除后）：")
#     cursor.execute("""
#         SELECT * FROM exam_results
#         WHERE student_id IS NULL
#            OR question_id IS NULL
#            OR student_answer IS NULL
#            OR student_answer LIKE '%选项%';
#     """)
#     remaining_data = cursor.fetchall()
#     if not remaining_data:
#         print("所有调试数据已成功删除！")
#     else:
#         for row in remaining_data:
#             print(row)

# except mysql.connector.Error as err:
#     print(f"数据库错误: {err}")
# finally:
#     # 关闭数据库连接
#     if conn.is_connected():
#         cursor.close()
#         conn.close()

# import mysql.connector

# # 连接到数据库
# db = mysql.connector.connect(
#     host="localhost",
#     user="root",
#     password="123",
#     database="japgpt"
# )

# cursor = db.cursor()

# # 执行 ALTER TABLE 语句来修改 type 列的数据类型
# alter_query = """
# ALTER TABLE questions
# MODIFY COLUMN type TEXT NOT NULL COMMENT '题目类型，存储多个知识点';
# """

# try:
#     cursor.execute(alter_query)
#     db.commit()  # 提交更改
#     print("Column 'type' modified successfully.")
# except mysql.connector.Error as err:
#     print(f"Error: {err}")
#     db.rollback()  # 如果发生错误，回滚事务
# finally:
#     cursor.close()
#     db.close()


# # 插入测试数据
# cursor.execute(drop_exam_results_table_query)
# cursor.execute(drop_questions_table_query)
# cursor.execute(drop_students_table_query)


# insert_questions_query = """
# INSERT INTO questions (question_index, content, correct_answer, type, level, is_gpt)
# VALUES (%s, %s, %s, %s, %s, %s)
# """
# questions_data = [
#     ('Q001', '猫的日语是什么？', 'ねこ', 'VOCABULARY', 'N5', True),
#     ('Q002', '以下哪些选项是正确的？', '选项1,选项3', 'VOCABULARY', 'N4', False),
#     ('Q003', '地球是平的吗？', '否', 'GRAMMAR', 'N4', False)
# ]
# cursor.executemany(insert_questions_query, questions_data)

# insert_students_query = """
# INSERT INTO students (student_no, name, email)
# VALUES (%s, %s, %s)
# """
# students_data = [
#     (122090351, '张三', 'zhangsan@example.com'),
#     (122090352, '李四', 'lisi@example.com'),
#     (122090353, '王五', 'wangwu@example.com')
# ]
# cursor.executemany(insert_students_query, students_data)

# insert_exam_results_query = """
# INSERT INTO exam_results (question_id, student_id, student_answer, is_correct)
# VALUES (%s, %s, %s, %s)
# """
# exam_results_data = [
#     (1, 1, 'ねこ', True),  # 张三回答正确
#     (2, 2, '选项1,选项2', False),  # 李四回答错误
#     (3, 3, '否', True)  # 王五回答正确
# ]
# cursor.executemany(insert_exam_results_query, exam_results_data)




# # 提交事务
# db.commit()

# # 查询前 5 行 `questions` 表中的数据
# cursor.execute("SELECT * FROM questions LIMIT 5")
# for row in cursor.fetchall():
#     print(row)

# # 查询前 5 行 `students` 表中的数据
# cursor.execute("SELECT * FROM students LIMIT 5")
# for row in cursor.fetchall():
#     print(row)

# # 查询学生回答错误的记录
# # cursor.execute("SELECT * FROM exam_results WHERE is_correct = 0")
# cursor.execute(select_mistake_query)
# for row in cursor.fetchall():
#     print(row)


# # 关闭连接
# cursor.close()
# db.close()

