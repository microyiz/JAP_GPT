from jap_paper_revise import return_revised_result
from jap_paper_revise import extract_student_id
import mysql.connector
import os
from db_util import drop_table_query ,create_table_query ,insert_query,show_fiverows_query,select_mistake_query,db,drop_jap_table,create_jap_table

# # 连接到 MySQL 数据库
# question_path = "C:\\Users\\30998\\Desktop\\template paper from CUHK\\Test1\\test 1 paper\\Test 1 Question Paper.docx"
# right_answer_path = "C:\\Users\\30998\\Desktop\\template paper from CUHK\\Test1\\test 1 paper\\Test 1 Model Answer.docx"
# # wrong_answer_path = "C:\\Users\\刘宇\\OneDrive - CUHK-Shenzhen\\桌面\\基于大模型的学习平台开发\\template paper from CUHK\\student paper\\1155142665 Test 1.docx"
# wrong_answer_path = "C:\\Users\\30998\Desktop\\template paper from CUHK\\Test1\\student paper\\1155159595 Test 1.docx"
# filename = os.path.splitext(os.path.basename(question_path))[0]
# student_id = extract_student_id(wrong_answer_path)

# answer = return_revised_result(question_path, right_answer_path, wrong_answer_path, filename)


# cursor = db.cursor()
# #删除已经有的table
# cursor.execute(drop_table_query)
# #创建新的jap_table
# cursor.execute(create_table_query)
# revised_problem_answer_list = answer[0]
# right_or_not = answer[1]
# #insert all the data into the table
# for i in range(len(right_or_not)):
#     cursor.execute(insert_query, (student_id, revised_problem_answer_list[i], right_or_not[i]))
# #show the first five rows of the table
# # cursor.execute(show_fiverows_query)
# # rows = cursor.fetchall()
# # for row in rows:
# #     print(row)

# cursor.execute(select_mistake_query, (student_id,))
# rows = cursor.fetchall()
# for row in rows:
#     print(row)



# table_creation_query = """
# CREATE TABLE jap_table (
#     id INT AUTO_INCREMENT PRIMARY KEY,
#     student_id VARCHAR(255) NOT NULL,
#     question_text TEXT NOT NULL,
#     is_correct BOOLEAN NOT NULL
# )
# """
# cursor.execute(table_creation_query)
# drop_jap_table(db.cursor)
# create_jap_table(db.cursor)



def process_paper_and_store_results(question_path, right_answer_path, wrong_answer_path):
    # 获取文件名和学生ID
    filename = os.path.splitext(os.path.basename(question_path))[0]
    student_id = extract_student_id(wrong_answer_path)

    # 获取修正后的结果
    answer = return_revised_result(question_path, right_answer_path, wrong_answer_path, filename)
    revised_problem_answer_list = answer[0]
    right_or_not = answer[1]

    cursor = db.cursor()
    
    # 删除已经存在的表并创建新表
    cursor.execute(drop_table_query)
    cursor.execute(create_table_query)
    
    # 插入数据到数据库
    for i in range(len(right_or_not)):
        cursor.execute(insert_query, (student_id, revised_problem_answer_list[i], right_or_not[i]))
    db.commit()

    # 查询学生的错误
    cursor.execute(select_mistake_query, (student_id,))
    rows = cursor.fetchall()

    return rows


question_path = "C:\\Users\\30998\\Desktop\\template paper from CUHK\\Test1\\test 1 paper\\Test 1 Question Paper.docx"
right_answer_path = "C:\\Users\\30998\\Desktop\\template paper from CUHK\\Test1\\test 1 paper\\Test 1 Model Answer.docx"
# wrong_answer_path = "C:\\Users\\刘宇\\OneDrive - CUHK-Shenzhen\\桌面\\基于大模型的学习平台开发\\template paper from CUHK\\student paper\\1155142665 Test 1.docx"
wrong_answer_path = "C:\\Users\\30998\Desktop\\template paper from CUHK\\Test1\\student paper\\1155159595 Test 1.docx"
result_rows = process_paper_and_store_results(question_path, right_answer_path, wrong_answer_path)
# for row in result_rows:
#     print(row)
