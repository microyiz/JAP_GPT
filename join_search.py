def join_search():
    """
    import mysql.connector

    #连接数据库
    db = mysql.connector.connect(
        host="localhost",
        user="root",
        password="123",
        database="JAPGPT"
    )
    """
    #多次查询输入
    '''
    Please input the query info for student 1, or input "end" to finish the query: Lam Tzy Mang
    Please input the query info for student 2, or input "end" to finish the query: Li Ching Yin Cathy
    Please input the query info for student 3, or input "end" to finish the query: end
    '''
    inputs = []
    i = 1
    while True:
        query = input(f'Please input the query info for student {i}, or input "end" to finish the query: ')
        if query == 'end':
            break
        inputs.append(query)
        i += 1
    inputs.append('end')

    #逐行信息内连接查询
    j = 1
    while inputs[j-1] != 'end':

        info = inputs[j-1].split(',')
        Column_student = ''
        Column_question = ''
        constrain_student = ''
        constrain_question = ''

        info = [i.strip() for i in info]

        #整理查询信息
        for query in info:
            try:
                query = int(query)
            except:
                pass
            if isinstance(query, int):
                if query >= 2:
                    Column_student += 'students.student_no,'
                    constrain_student += 'students.student_no =' + str(query) + ' AND '

                elif query < 2:
                    Column_question += 'questions.is_gpt,'
                    constrain_question += 'questions.is_gpt =' + str(query) + ' AND '

            elif isinstance(query, str):
                if query.startswith('N') and len(query) == 2:
                    Column_question += 'questions.level,'
                    constrain_question += 'questions.level =\'' + query + '\' AND '

                elif '@' in query:
                    Column_student += 'students.email,'
                    constrain_student += 'students.email =\'' + query + '\' AND '

                elif query.startswith('Table'):
                    Column_question += 'questions.question_index,'
                    constrain_question += 'questions.question_index =\'' + query + '\' AND '

                elif query.upper() == 'VOCABULARY' or query.upper() == 'GRAMMAR':
                    Column_question += 'questions.type,'
                    constrain_question += 'questions.type =\'' + query + '\' AND '
                
                elif query[0].isalpha():
                    Column_student += 'students.name,'
                    constrain_student += 'students.name = \'' + query + '\' AND '

                else:
                    Column_question += 'questions.content,'
                    constrain_question += 'questions.content =\'' + '%' + query + '%' + '\' AND '


        inner_search_questions_exam_constrain = ''
        inner_search_students_exam_constrain = ''

        #内连接
        if Column_student != '':
            inner_search_students_exam_constrain=f"""(SELECT students.student_no FROM students WHERE {constrain_student.rstrip(' AND ')}) = exam_results.student_id"""
        if Column_question != '':
            inner_search_questions_exam_constrain=f"""(SELECT questions.question_id FROM questions WHERE {constrain_question.rstrip(' AND ')}) = exam_results.question_id"""

        whole_constrain = ''
        for i in (constrain_student.rstrip(' AND '), constrain_question.rstrip(' AND '), inner_search_students_exam_constrain, inner_search_questions_exam_constrain):
            if i != '':
                whole_constrain += ' AND ' + i
        whole_constrain = whole_constrain.lstrip(' AND ')

        inner_search_query =f"""
        SELECT students.*, questions.*, exam_results.* FROM students, questions, exam_results
        WHERE {whole_constrain} AND students.student_no = exam_results.student_id AND questions.question_id = exam_results.question_id;
        """

        cursor = db.cursor()
        cursor.execute(inner_search_query)
        result = cursor.fetchall()
        for row in result:
            print(row)

        j += 1
