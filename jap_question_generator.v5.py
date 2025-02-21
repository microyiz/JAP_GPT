'''Question_Generator'''
import re
import os
import glob
import time
import string
import warnings
import docx
import mysql.connector
from docx import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate  
from langchain.chains import LLMChain   
from langchain_community.document_loaders import UnstructuredWordDocumentLoader
from typing import Any
from openpyxl import Workbook
from openpyxl.styles import Alignment
from openpyxl.worksheet.datavalidation import DataValidation

from jap_paper_revise import produce_new_question_list
from jap_paper_revise import read_docx_to_string_with_format

from jap_vocabulary_processor import vocabulary_points_revise
from jap_excel_processor import parse_questions
from jap_excel_processor import store_questions_to_excel
from jap_excel_processor import process_word_to_excel

def split_into_sentences(text):
    sentence_endings = re.compile(r'(?<=[。！？])\s*')
    sentences = sentence_endings.split(text)
    return sentences


def extract_numbered_content(file_path, start_number, end_number):
    """
    Extracts numbered content (e.g., 1-8) from a Word document, including multiple-choice options and lists with different formats.

    Args:
        file_path (str): The path to the Word document.
        start_number (int): The starting number of the range to extract.
        end_number (int): The ending number of the range to extract.

    Returns:
        tuple: A tuple containing two lists:
            - num: A list of question numbers (e.g., [1, 2])
            - content_list: A list of lists of options (e.g., [['a. くださる', 'b. いただく'], ['a. 経験', 'b. あつい']])
    """
    # Load the Word document
    doc = Document(file_path)
    
    # Compile a regex pattern to match the numbered entries with or without additional details like kanji readings in brackets
    pattern = re.compile(rf"^\s*(\d+)\.\s*([^【]*)(?:【([^】]*)】)?\s*(.*)")
    
    # Lists to store the extracted content
    num = []
    content_list = []

    # Define a function to sanitize strings for file names
    def sanitize_filename(content):
        # Remove invalid characters for filenames (e.g., \ / : * ? " < > |)
        return re.sub(r'[\\/*?:"<>|]', '_', content).strip()

    # Iterate through all paragraphs in the document
    for para in doc.paragraphs:
        match = pattern.match(para.text)
        if match:
            number = int(match.group(1))
            item = match.group(2).strip()
            kanji_reading = match.group(3) if match.group(3) else ""
            additional_text = match.group(4).strip()

            # Prepare the full item content (item + kanji reading if exists)
            full_item = item + ("【" + kanji_reading + "】" if kanji_reading else "")
            full_item = full_item.strip()

            # Sanitize the full item to make it safe for filenames
            sanitized_full_item = sanitize_filename(full_item)

            # Check if the number is within the specified range
            if start_number <= number <= end_number:
                # If the number is already in the list, add to the content list
                if number not in num:
                    num.append(number)
                    content_list.append([f"{sanitized_full_item} {additional_text}"])
                else:
                    index = num.index(number)
                    content_list[index].append(f"{sanitized_full_item} {additional_text}")

    return num, content_list


"""
def extract_grammar_points(docx_file):
    # 读取docx文件
    doc = docx.Document(docx_file)
    
    knowledge_points = []
    
    # 遍历文档的所有段落
    for para in doc.paragraphs:
        print(f"读取的段落内容: {para.text}")
        # 使用正则表达式匹配类似 "1.～あいだ（間）" 的格式
        match = re.match(r'(\d+)\.([^\n]+)', para.text.strip())
        if match:
            # 提取编号和短语部分
            number = match.group(1)
            phrase = match.group(2).strip()
            knowledge_points.append({
                'number': number,
                'phrase': phrase
            })
    
    return knowledge_points


def extract_vocabulary(docx_path):
    doc = Document(docx_path)
    vocabulary_list = []
    number_pattern = r'^\d+\. '  # 匹配以数字和点号开头的行
    
    # 遍历每个段落
    for para in doc.paragraphs:
        # 将每个段落按行分割
        for line in para.text.splitlines():
            # 如果行包含带序号的内容
            if re.match(number_pattern, line.strip()):
                vocabulary_list.append(line.strip())
    
    return vocabulary_list
"""






"""
Main Processor for Grammar
"""

def grammar_points_revise(num, vocabulary_list, output, filepath):
    filename = os.path.splitext(os.path.basename(filepath))[0]
    llm = ChatOpenAI(
        temperature=0.6,
        model='gpt-4o'
    )

    # 遍历每个知识点（从vocabulary_list提取的知识点）
    for knowledge_point, question_number in zip(vocabulary_list, num):
        print(f'Processing grammar {knowledge_point} with number {question_number}...')

        # 动态生成 prompt，要求 GPT 依次为每个词汇出题
        prompt_grammar = ChatPromptTemplate.from_template(
            f'''
    You are an experienced Japanese examiner, well-versed in the N4 and N5 levels of the Japanese Language Proficiency Test (JLPT). Your task is to create 100 multiple-choice questions based on the following grammar knowledge point: **{knowledge_point}**.

    ### Requirements:
    1. Each question should have **4 options**, with only **one correct answer**.
    2. The correct answer must strictly align with the logic of the question stem.
    3. The options should be meaningful, with the incorrect ones being close to the correct answer, yet still clearly wrong in context.
    4. Ensure that the question is unambiguous by adding necessary contextual constraints (e.g., verb tense, sentence structure, or meaning) to eliminate multiple correct answers.
    5. Ensure that the correct option fits naturally in the sentence context and reflects the meaning of the grammar point.
    6. After generating the question, apply a check to ensure that the correct answer is unique, and the other options are incorrect and clearly unsuitable.
    7. Avoid misleading phrasing or unnatural sentence constructions that may confuse test-takers. The question should resemble real exam-level language usage.
    8. Each question must have an `Answer: x` at the end.

            ### Question Formats:

            （  　　　　　 ）に　何を　入れますか。　1・2・3・4から　いちばん　いい　ものを　一つ　えらんで　ください。  
                Q1 かれが　手伝って　（  　　　　　 ）　宿題 (しゅくだい) が　終わらなっかった。  
                1　もらったから			2　くれなかったから		
                3　ほしいから				4　ほしかったから
                Answer: 2

                Q2 うちの　子どもは　勉強 (べんきょう) しないで　（  　　　　　 ）　ばかりいる。
                1　あそび		2　あそぶ		3　あそばない		4　あそんで
                Answer: 4

                Q3  A　「田中さんは　かのじょが　いますか。」
	                B　「いいえ、田中さんは　前の　かのじょと　別れてから、人を好き　（  　　　　　 ）。」
                1　ではありませんでした		    2　にならなくなりました		
                3　でもよくなりました			4　にしなくなりました
                Answer: 2

    ### Additional Notes:
    - The generated questions must maintain high linguistic and contextual accuracy.
    - Avoid using cultural or subjective biases that could confuse learners.
    - Ensure that the sentence structure follows standard Japanese grammar rules. Avoid artificial sentence constructions that do not resemble natural spoken or written Japanese.
    - Limit the use of uncommon words or phrases that may be beyond N4/N5 level unless necessary for testing a specific grammar structure.

    ### Before finalizing, check your output against these rules:
    1. Each question must start with `Qx` (e.g., `Q1`, `Q2`...).
    2. Each question must have exactly 4 options (`1` to `4`).
    3. Each question must have an `Answer: x` at the end.
    4. If any question is missing `Answer: x`, fix it before outputting.
    5. Do not include other comments such as "**"
    '''
        )

        
        # 创建链条来运行LLM
        chain_one = LLMChain(llm=llm, prompt=prompt_grammar)

        # 输入数据
        input_data = {
            'knowledge_point': knowledge_point, 
        }

        # 获取生成的题目
        revise_result = chain_one.run(input_data)

        # 处理生成的题目并保存
        output_doc = Document()
        sentences = split_into_sentences(revise_result)
        
        # 将生成的题目逐句添加到文档中
        for sentence in sentences:
            sentence.replace("**Answers:**", "**Answers**")
            sentence = sentence.replace("＿＿＿", "[ ]")  # 替换空格部分
            output_doc.add_paragraph(sentence)

        output_path = os.path.join(output, f"{filename}_{question_number}_{knowledge_point}.docx")
        output_doc.save(output_path)

        # # 将生成文本解析成题目列表
        # qa_list = parse_questions(revise_result)
        # excel_filename = f"{filename}_new{i}.xlsx"
        # store_questions_to_excel(qa_list, output, excel_filename)
        # # print(f'Generated questions for {knowledge_point} saved to {output_path}')






"""Self Checker"""


def question_revise_simple(rows, filename, revised_newpaper_folder, max_iterations=5):
    llm = ChatOpenAI(
        temperature=0.6,
        model='gpt-4o'
    )
    
    prompt_revise = ChatPromptTemplate.from_template(
    f'''
    Here are the new generated Japanese practice questions: {rows}
    You are an experienced Japanese N4/N5 examiner tasked with reviewing and ensuring that all multiple-choice test questions meet the following criteria:

    1. **No duplicate questions**: Ensure that all questions are unique. If a question is repeated or too similar to another, please revise it to create a new question with a distinct structure or context. Provide specific suggestions on how to modify repeated questions.

    2. **No duplicate options**: All options within a question should be unique, contextually meaningful, and grammatically correct. Avoid options that are too similar to each other. If necessary, suggest how to modify similar options to increase their clarity.

    3. **No duplicate correct answers**: Ensure that only one answer is correct. If two options could be correct, modify the question or options to clarify the correct choice. Provide specific suggestions on how to make the answer clear and unambiguous.

    4. **Grammatical correctness**: The title and stem of each question must be grammatically correct. Review for unnatural sentence structures and revise them to ensure fluency and correctness. If you detect any grammatical errors, please explain how to fix them.

    5. **Relevance of options**: Ensure that the stem clearly indicates what cannot be chosen. One option should be inappropriate or clearly wrong in context, while all other options are suitable. Avoid culturally biased content. Suggest how to improve the incorrect options by reflecting common mistakes learners make.

    6. **Pronunciation and Word Usage**: If the question involves pronunciation, katakana, or hiragana forms, the Japanese word should be enclosed in brackets for clarity. For hiragana or katakana conversion questions, ensure that the word is written in the correct form, and the correct answer is not shown in the question stem. Also, check for spelling inconsistencies.

    7. **General guidance**: Eliminate any ambiguity, revise unclear options, and avoid subjective or culturally biased phrasing. Ensure all questions are at an appropriate difficulty level for the target JLPT level (N4/N5). Avoid complex words or structures outside the typical N4/N5 range.

    8. **Output Format**: Each question must keep the original format:
    - Each question must start with `Qx` (e.g., `Q1`, `Q2`...).
    - Each question must have exactly 4 options (`1` to `4`).
    - Each question must have an `Answer: x` at the end of it.
    - Do not include any other comments such as '**'. Please ensure all formatting is consistent.
   '''
    )

    
    chain = LLMChain(llm=llm, prompt=prompt_revise)
    input_data = {'new_paper': rows}
    
    for iteration in range(max_iterations):
        revised_result = chain.run(input_data)
        errors = check_for_error(revised_result)

        if not errors:
            print(f"No issues found after {iteration + 1} iterations.")
            break

        # Ensure errors is iterable
        print(f"Iteration {iteration + 1}: Detected errors - {', '.join(errors)}")
        input_data['new_paper'] = revised_result

        
        # 保存中间修订结果
        intermediate_path = os.path.join(revised_newpaper_folder, f"{filename}_iteration_{iteration + 1}.docx")
        output_doc = Document()
        sentences = split_into_sentences(revised_result)
        for sentence in sentences:
            output_doc.add_paragraph(sentence)
        output_doc.save(intermediate_path)
        
        # 保存错误日志
        log_path = os.path.join(revised_newpaper_folder, f"{filename}_error_log.txt")
        with open(log_path, 'a', encoding='utf-8') as log_file:
            log_file.write(f"Iteration {iteration + 1} Errors: {', '.join(errors)}\n")
    else:
        print(f"Maximum iterations ({max_iterations}) reached. Errors may still exist.")
    
    # 保存最终修订结果
    output_path = os.path.join(revised_newpaper_folder, f"{filename}_revised.docx")
    output_doc = Document()
    sentences = split_into_sentences(revised_result)
    for sentence in sentences:
        output_doc.add_paragraph(sentence)
    output_doc.save(output_path)

    # 存储到excel
    qa_list = parse_questions(revised_result)
    excel_filename = f"{filename}.xlsx"
    store_questions_to_excel(qa_list, revised_newpaper_folder, excel_filename)





def check_for_error(revised_text):
    """
    Check for errors in the revised question set, including:
    - Multiple correct answers
    - Duplicate questions
    - Errors in the question stem
    - Duplicate options
    
    :param revised_text: The revised text output from GPT.
    :return: List of errors if any are found, empty list otherwise.
    """
    errors = []  # Initialize an empty list to store error messages
    
    try:
        if has_multiple_correct_answers(revised_text):
            errors.append("Multiple correct answers")
        
        if has_duplicate_questions(revised_text):
            errors.append("Duplicate questions")
        
        if has_stem_errors(revised_text):
            errors.append("Stem errors")
        
        if has_duplicate_options(revised_text):
            errors.append("Duplicate options")
        
        return errors  # Return the list of errors (can be empty if no errors)
    
    except Exception as e:
        print(f"Error in check_for_error: {e}")
        return ["Unexpected error in check_for_error"]  # Return a list with an error message if an exception occurs


def has_multiple_correct_answers(text):
    """
    Checks if a Japanese multiple-choice question has more than one possible correct answer.
    
    :param text: The text containing the multiple-choice questions.
    :return: True if multiple correct answers exist, False otherwise.
    """
    llm = ChatOpenAI(
        temperature=0.3,  # Lower temperature for more deterministic output
        model="gpt-4o"
    )
    
    prompt = ChatPromptTemplate.from_template(
        "You are an experienced Japanese N4/N5 examiner reviewing the following multiple-choice questions:\n\n"
        "{new_paper}\n\n"
        "Check if any question has **more than one correct answer**. This means that multiple options are valid for the question given its context.\n"
        "If at least one question has multiple valid correct answers, respond with 'True'. Otherwise, respond with 'False'.\n"
        "Your output must be exactly 'True' or 'False', nothing else."
    )

    chain = LLMChain(llm=llm, prompt=prompt)
    input_data = {'new_paper': text}

    try:
        result = chain.run(input_data).strip().lower()
        return result == "true"
    except Exception as e:
        print(f"Error processing has_multiple_correct_answers: {e}")
        return False  # Default to False if an error occurs


def has_stem_errors(text):
    """
    Checks if there are grammatical errors or ambiguities in the question stems.
    
    :param text: The text containing the multiple-choice questions.
    :return: True if errors exist, False otherwise.
    """
    llm = ChatOpenAI(
        temperature=0.3,  # Lower temperature to improve reliability
        model="gpt-4o"
    )
    
    prompt = ChatPromptTemplate.from_template(
        "You are an experienced Japanese N4/N5 examiner reviewing the following multiple-choice questions:\n\n"
        "{new_paper}\n\n"
        "Check if any **question stem** (the main question part before the options) has errors, such as:\n"
        "- Grammatical mistakes\n"
        "- Unnatural sentence structures\n"
        "- Ambiguous wording\n"
        "If there is at least one issue in the stems, respond with 'True'. Otherwise, respond with 'False'.\n"
        "Your output must be exactly 'True' or 'False', nothing else."
    )

    chain = LLMChain(llm=llm, prompt=prompt)
    input_data = {'new_paper': text}

    try:
        result = chain.run(input_data).strip().lower()
        return result == "true"
    except Exception as e:
        print(f"Error processing has_stem_errors: {e}")
        return False  # Default to False if an error occurs

def has_duplicate_options(text):
        """
        Check for duplicate options in the questions.
        
        :param text: The text to check.
        :return: True if - options are found within a question.
        """
        # Example: Detect duplicate options for a given question.
        questions_with_options = re.findall(
            r'(\d+)\.\s*(.*?)\n(1\.\s*(.*?)\n)(2\.\s*(.*?)\n)(3\.\s*(.*?)\n)(4\.\s*(.*?)\n)',
            text, re.DOTALL
        )

        for question, _, opt1, _, opt2, _, opt3, _, opt4, _ in questions_with_options:
            options = {opt1.strip(), opt2.strip(), opt3.strip(), opt4.strip()}
            if len(options) < 4:  # If any options are duplicates
                print(f"Duplicate options detected in question {question}: {opt1.strip()}, {opt2.strip()}, {opt3.strip()}, {opt4.strip()}")
                return True
        return False




def normalize_text(text):
    """
    Normalize text by:
    1. Converting to lowercase.
    2. Removing non-essential characters such as punctuation and extra spaces.
    
    :param text: The text to normalize.
    :return: Normalized text.
    """
    # Convert to lowercase
    text = text.lower()
    
    # Remove punctuation and extra spaces
    text = text.translate(str.maketrans('', '', string.punctuation))
    text = re.sub(r'\s+', ' ', text).strip()  # Remove extra spaces
    
    return text

def has_duplicate_questions(text):
    """
    Check if any questions are duplicated, considering both the question text and options,
    while ignoring case and non-key characters like spaces and punctuation.
    
    :param text: The text to check.
    :return: True if duplicate questions are detected.
    """
    questions = re.findall(
        r'(\d+)\.\s*(.*?)\n(1\.\s*(.*?)\n)(2\.\s*(.*?)\n)(3\.\s*(.*?)\n)(4\.\s*(.*?)\n)',  # Capture question text and options
        text, re.DOTALL
    )
    
    seen_questions = set()
    
    for question, _, opt1, _, opt2, _, opt3, _, opt4, _ in questions:
        # Normalize question text and options
        question_text = normalize_text(question.strip())
        options = {normalize_text(opt1.strip()), normalize_text(opt2.strip()), 
                   normalize_text(opt3.strip()), normalize_text(opt4.strip())}
        
        # Create a normalized string for comparison: question + sorted options
        normalized_question = f"{question_text} - {', '.join(sorted(options))}"
        
        if normalized_question in seen_questions:
            print(f"Duplicate question detected: {question_text} with options {options}")
            return True  # Duplicate found
        seen_questions.add(normalized_question)
    
    return False




def main():
    # 文件路径定义
    docx_file_grammar = "C:\\Users\\刘宇\\OneDrive - CUHK-Shenzhen\\桌面\\JAP_GPT\\N4N5 material\\N4 Notes 文法_numbered.docx"
    docx_file_vocabulary = "C:\\Users\\刘宇\\OneDrive - CUHK-Shenzhen\\桌面\\JAP_GPT\\N4N5 material\\N4 Notes 語彙_numbered.docx"
    test_knowledge_points = "C:\\Users\\刘宇\\OneDrive - CUHK-Shenzhen\\桌面\\JAP_GPT\\2025_new_db\\new_questions\\test_knowledge_points.docx"
    test_grammar = "C:\\Users\\刘宇\\OneDrive - CUHK-Shenzhen\\桌面\\JAP_GPT\\2025_new_db\\new_questions\\test_grammar.docx"
    test_vocabulary = "C:\\Users\\刘宇\\OneDrive - CUHK-Shenzhen\\桌面\\JAP_GPT\\2025_new_db\\new_questions\\test_vocabulary.docx"

    N4_grammar = "C:\\Users\\刘宇\\OneDrive - CUHK-Shenzhen\\桌面\\JAP_GPT\\N4N5 material\\N4 - Grammar.docx"
    N4_vocabulary = "C:\\Users\\刘宇\\OneDrive - CUHK-Shenzhen\\桌面\\JAP_GPT\\N4N5 material\\N4 - Vocabulary・語彙.docx"
    N5_grammar = "C:\\Users\\刘宇\\OneDrive - CUHK-Shenzhen\\桌面\\JAP_GPT\\N4N5 material\\N5 - Grammar.docx"
    N5_vocabulary = "C:\\Users\\刘宇\\OneDrive - CUHK-Shenzhen\\桌面\\JAP_GPT\\N4N5 material\\N5 - Vocabulary・語彙.docx"

    output_grammar_N4 = "C:\\Users\\刘宇\\OneDrive - CUHK-Shenzhen\\桌面\\JAP_GPT\\2025_new_db\\new_questions\\N4 grammar"
    output_vocabulary_N4 = "C:\\Users\\刘宇\\OneDrive - CUHK-Shenzhen\\桌面\\JAP_GPT\\2025_new_db\\new_questions\\N4 vocabulary"
    output_grammar_N5 = "C:\\Users\\刘宇\\OneDrive - CUHK-Shenzhen\\桌面\\JAP_GPT\\2025_new_db\\new_questions\\N5 grammar"
    output_vocabulary_N5 = "C:\\Users\\刘宇\\OneDrive - CUHK-Shenzhen\\桌面\\JAP_GPT\\2025_new_db\\new_questions\\N5 vocabulary"

    revised_output_vocabualry = "C:\\Users\\刘宇\\OneDrive - CUHK-Shenzhen\\桌面\\JAP_GPT\\2025_new_db\\new_questions\\revised_vocabulary"
    revised_output_grammar = "C:\\Users\\刘宇\\OneDrive - CUHK-Shenzhen\\桌面\\JAP_GPT\\2025_new_db\\new_questions\\revised_grammar"

    # 提取和修订内容
    vocabulary_N4 = extract_numbered_content(N4_vocabulary, 1, 807)[1]
    vocabulary_N5 = extract_numbered_content(N5_vocabulary, 1, 802)[1]
    grammar_N4 = extract_numbered_content(N4_grammar, 1, 92)[1]
    grammar_N5 = extract_numbered_content(N5_grammar, 1, 77)[1]

    vocabulary_num = extract_numbered_content(test_vocabulary, 1, 6)[0]
    vocabulary_test = extract_numbered_content(test_vocabulary, 1, 6)[1]
    grammar_num = extract_numbered_content(test_grammar, 1, 4)[0]
    grammar_test = extract_numbered_content(test_grammar, 1, 4)[1]

    print(vocabulary_test)
    print(grammar_test)

    # 修订词汇和语法点
    vocabulary_points_revise(vocabulary_num, vocabulary_test, revised_output_vocabualry, test_vocabulary)
    process_word_to_excel(revised_output_vocabualry, revised_output_vocabualry)
    grammar_points_revise(grammar_num, grammar_test, revised_output_grammar, test_grammar)

    # 处理新的问题文件并修订
    # for filepath in glob.glob(os.path.join(revised_output_vocabualry, "*.docx")):
    #     filename = os.path.splitext(os.path.basename(filepath))[0]
    #     start_time = time.time()
    #     new_que = read_docx_to_string_with_format(filepath)
    #     question_revise_simple(new_que, filename, revised_output_vocabualry)
    #     end_time = time.time()
    #     print(f"Completed revising new questions {filename} in: {end_time - start_time:.2f} seconds")

    for filepath in glob.glob(os.path.join(revised_output_grammar, "*.docx")):
        filename = os.path.splitext(os.path.basename(filepath))[0]
        start_time = time.time()
        new_que = read_docx_to_string_with_format(filepath)
        question_revise_simple(new_que, filename, revised_output_grammar)
        end_time = time.time()
        print(f"Completed revising new questions {filename} in: {end_time - start_time:.2f} seconds")

if __name__ == "__main__":
    main()
