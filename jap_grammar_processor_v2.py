'''Question_Generator'''
import re
import os
import glob
from tabnanny import verbose
import time
import string
import warnings
import docx
import mysql.connector
import openai
from docx import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate  
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain   
from langchain.memory import ConversationSummaryMemory
from langchain.memory import ConversationSummaryBufferMemory
from langchain_community.document_loaders import UnstructuredWordDocumentLoader
from typing import Any
from openpyxl import Workbook
from openpyxl.styles import Alignment
from openpyxl.worksheet.datavalidation import DataValidation

from jap_paper_revise import read_docx_to_string_with_format

from jap_vocabulary_processor import vocabulary_points_revise
from jap_excel_processor import parse_questions
from jap_excel_processor import store_questions_to_excel
from jap_excel_processor import process_word_to_excel

#from dotenv import load_dotenv
#load_dotenv('.env')



#os.environ["http_proxy"] = "http://127.0.0.1:7890"
#os.environ["https_proxy"] = "http://127.0.0.1:7890"

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




# ---------------------------
# 第一部分：题目生成相关函数
# ---------------------------
def generate_prompt(knowledge_point: str, question_format: int, num_questions: int) -> str:
    """生成题目生成的prompt文本"""
    if question_format not in (1, 2):
        raise ValueError("question_format must be between 1 and 2")
    if not isinstance(num_questions, int) or num_questions <= 0:
        raise ValueError("num_questions must be a positive integer")
    
    format_descriptions = {
    1:"""[もんだい1: Direct Questioning Format]
        The prompt provides the outcome/result, and the task is to choose the cause or reason that connects to that outcome.
        Examples:
            かれが　手伝って　（　　　　　）　宿題 (しゅくだい) が　終わらなっかった。
            1 もらったから   2 くれなかったから   3 ほしいから   4 ほしかったから
            Answer: 2
        Explanation:
            Structure: The sentence provides the result ("宿題が終わらなかった") and asks for the connector that gives the reason for this outcome.
            Knowledge Point Tested: It tests understanding of how to express a reason using the appropriate form (in this case “くれなかったから”).
            Alignment: This aligns perfectly with the Direct questioning format where the result is given and the student must select the relevant cause.
    """,

    2:"""[もんだい2: Indirect Questioning Format]
        The prompt provides a condition or reason, and the task is to choose the result or action that logically follows.
        Examples:
            もし　1000万円　もらったら、　わたしは　いろいろな　国を　（　　　　　）。
            1 旅行したがる   2. 旅行したがっている   3. 旅行したい   4. 旅行したかった
            Answer: 3
        Explanation:
            Structure: The prompt provides a hypothetical or conditional scenario and asks the student to choose the expression that reflects the intended result or action.
            Knowledge Point Tested: It assesses understanding of expressing a result or intention in response to a hypothetical condition.
            Alignment: This example satisfies the requirements of the Indirect questioning format, where the condition and resultant action (旅行したい) are connected appropriately.
    """
    }


    validation_prompt = """
        Generated questions must undergo the following quality validations:
        1. Grammatical accuracy: The grammar of the questions and options must be correct and meet the standards of Japanese N4/N5 level.
        2. Distractor validity: Distractors should be confusing, but can be eliminated with correct grammatical knowledge.
        3. Reasonable difficulty: Design questions according to different difficulty levels to ensure a reasonable distribution of difficulty.
        4. Contextual naturalness: The context of the sentence should be consistent with the actual situation in daily communication or exams.
            Ensure that the conditional clauses in Indirect Questioning Format questions are expressed in diverse forms and do not all start with the same word such as ‘もし’.
        5. Context authenticity: Sentence scenarios must meet the following requirements:
            - Daily conversations (such as chatting with friends, shopping)
            - Common exam scenarios (such as email writing, schedule planning)
            - Avoid artificial contexts (such as science fiction or professional fields)
    """

    CoT_instructions = """
        When you see a grammar question, please first determine if it is a Direct or Indirect question by identifying whether the provided sentence gives a result or a condition. 
        Then, explain your reasoning step-by-step before selecting the answer option. 
        For instance:
            Step 1: Identify the type of question.
            Step 2: Determine the function of the blank (is it asking for a cause or a result?).
            Step 3: Analyze the options in the context of the sentence.
            Step 4: Choose the appropriate option and provide a brief explanation for your decision.
        After solving the question, please reflect briefly on whether it was processed as a Direct or Indirect question and summarize your reasoning process.
    """

    CoT_Instructions_with_format = {
        1: """
        Chain-of-Thought Reasoning:
            Step 1: Identify the Given Outcome
                The sentence provides the result: 宿題が終わらなかった (the homework wasn't finished). The task is to choose the connector that explains why this outcome happened.
            Step 2: Determine the Role of the Blank
                The blank should express the reason (or cause) that led to the homework not being completed. This means the correct answer will include a causal connector in the form of a reason.
            Step 3: Evaluate Each Option
                Option 1: もらったから
                    Interpretation: “Because (I) received…”
                    Why Not: This option implies that something was received, which doesn't explain why the homework wasn't finished. The sentence context requires a negative reason related to the help received, not a positive receipt.
                Option 2: くれなかったから
                    Interpretation: “Because (he/she) did not give (help)”
                    Why Chosen: This option correctly explains the cause—the expected help was not given—directly relating to why the homework was left unfinished.
                Option 3: ほしいから
                    Interpretation: “Because (someone) wants…”
                    Why Not: This option indicates a desire, but it neither logically explains the lack of assistance nor connects to the outcome of the homework not being completed.
                Option 4: ほしかったから
                    Interpretation: “Because (someone) wanted (in the past)…”
                    Why Not: Although it is similar in concept to Option 3, this past form still does not provide a logical cause for the unfinished homework. It fails to account for the necessary causal relationship in the given context.
            Step 4: Conclude the Answer
                Based on the analysis, Option 2 (“くれなかったから”) is the only choice that directly states the reason the homework wasn't finished—help was not given.
    """,

        2: """
        Chain-of-Thought Reasoning:
            Step 1: Identify the Given Condition
                The sentence starts with the condition: もし1000万円もらったら ("If I received 10 million yen…"). This tells us that the blank should be filled with the resulting action or desire following this hypothetical condition.
            Step 2: Determine the Role of the Blank
                The blank should convey the speaker's intended action or desire as a consequence of the condition. The focus is on expressing a current intention or desire in a hypothetical situation.
            Step 3: Evaluate Each Option
                Option 1: 旅行したがる
                    Interpretation: “To tend to want to travel” (usually describing a third person's observable inclination).
                    Why Not: This form is typically used to describe someone else's behavior, not a self-expressed desire in a hypothetical situation.
                Option 2: 旅行したがっている
                    Interpretation: “To be in a state of wanting to travel”
                    Why Not: Although it expresses desire, this continuous form again fits better for describing someone's current visible desire rather than a hypothetical decision. It does not directly capture the speaker's personal intent in a simple, future context.
                Option 3: 旅行したい
                    Interpretation: “Want to travel”
                    Why Chosen: This form directly expresses the speaker's desire or intention in response to the condition. It's plain, direct, and perfectly fits the hypothetical scenario by stating the intention clearly.
                Option 4: 旅行したかった
                    Interpretation: “Wanted to travel (in the past)”
                    Why Not: The past tense is inconsistent with the hypothetical future condition ("もし1000万円もらったら"). It does not logically correspond to a future action resulting from the condition.
            Step 4: Conclude the Answer
                With the condition clearly requiring a direct expression of desire following a hypothetical gain, Option 3 (“旅行したい”) is the best fit.
    """
    }
 
    
    prompt = (
        f"You are an experienced Japanese examiner for JLPT N4/N5. Create exactly {num_questions} questions "
        f"for the grammar point: **{knowledge_point}**.\n\n"
        f"Question Format {question_format}: {format_descriptions.get(question_format, '')}\n\n"
        # f"Interference Rules: {interference_rules.get(question_format, '')}\n\n"
        f"{CoT_instructions}: {CoT_Instructions_with_format.get(question_format, '')}\n\n"
        f"{validation_prompt}\n\n"
        f"Instructions:\n"
        f"1. Each question must start with a header: 'Qx: もんだい{question_format}'.\n"
        f"2. Provide exactly 4 options (1-4) in one line.\n"
        f"3. End each question with 'Answer: x'.\n"
        f"4. No extra text or formatting!\n\n"
        f"Example Format:\n"
        f"Q1: もんだい{question_format}\n"
        f"[Japanese Question Stem]\n"
        f"1. Option1 2. Option2 3. Option3 4. Option4\n"
        f"Answer: x\n"
    )
    return prompt



def generate_grammar_questions(knowledge_point: str, question_format: int, num_questions: int) -> str:
    """使用 LLM 生成语法题目"""
    prompt = generate_prompt(knowledge_point, question_format, num_questions)
    llm = ChatOpenAI(temperature=0.6, model='gpt-4o')
    chain = LLMChain(llm=llm, prompt=ChatPromptTemplate.from_template(prompt))
    try:
        return chain.run({'knowledge_point': knowledge_point})
    except Exception as e:
        print(f"Error generating questions: {e}")
        return ""

def split_sentences(text, question_counter):
    text = re.sub(r'Q\d+:\s*', '', text)
    problems = re.split(r'(もんだい\d+)', text)
    problems = [p.strip() for p in problems if p.strip()]
    result = []
    for part in problems:
        if part.startswith('もんだい'):
            result.append(f"Q{question_counter}: " + part)
            question_counter += 1
        else:
            result.append(part)
    return result, question_counter

def process_and_revise_document(doc_path: str):
    """调整文档中题目的格式"""
    doc = Document(doc_path)
    question_counter = 1
    for paragraph in doc.paragraphs:
        sentences, question_counter = split_sentences(paragraph.text, question_counter)
        p = paragraph._element
        for child in list(p):
            p.remove(child)
        for sentence in sentences:
            run = paragraph.add_run(sentence)
            if "Answer:" in sentence:
                paragraph.add_run("\n")
    doc.save(doc_path)

# def grammar_points_revise(num_list, grammar_list, output_dir, filepath):
#     """针对每个知识点生成题目并修订"""
#     filename = os.path.splitext(os.path.basename(filepath))[0]
#     for knowledge_point, question_number in zip(grammar_list, num_list):
#         print(f'Processing {knowledge_point} with number {question_number}...')
#         output_doc = Document()
#         for question_format in range(1, 9):
#             print(f"Generating questions for format {question_format}...")
#             questions_text = generate_grammar_questions(knowledge_point, question_format, 5)
#             sentences, _ = split_sentences(questions_text, 1)
#             output_doc.add_paragraph(f"### Format {question_format}")
#             for sentence in sentences:
#                 sentence = sentence.replace("**Answers:**", "**Answers**")
#                 output_doc.add_paragraph(sentence)
#         output_path = os.path.join(output_dir, f"{filename}_{question_number}_{knowledge_point}.docx")
#         output_doc.save(output_path)
#         process_and_revise_document(output_path)



# ---------------------------
# 第二部分：题目检查与修订相关函数
# ---------------------------
def api_call_with_retry(chain, input_data, max_retries=3, delay=1):
    retries = 0
    while retries < max_retries:
        try:
            return chain.run(input_data)
        except Exception as e:
            print(f"API call failed: {e}. Retrying in {delay} seconds...")
            retries += 1
            time.sleep(delay)
    print("Max retries reached. Giving up.")
    return None

def normalize_text(text):
    text = text.lower()
    text = text.translate(str.maketrans('', '', string.punctuation))
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def has_multiple_correct_answers(text, llm, knowledge_point, memory):
    prompt = PromptTemplate(
        input_variables = ["history", "input_data"],
        template = """
        You are an experienced and strict Japanese N4/N5 examiner reviewing the following multiple-choice questions:
        the review history is attached here: {history}.

        {input_data}
        """
    )
    input_data = f"""
        the questions are used to test {knowledge_point}
        Check if any question below has **more than one correct answer**. This means that multiple options are OK for the question given its context.
        An important notice: once the option is grammatically correct, regard it as a correct answer. In other words, never consider **tone** or **polite format**.

        Example:
        もしお金が（　　　　　）、旅行に行きます。
        1. あったら 2. あると 3. あれば 4. あった   

        Explanation: All 1,2,3 options are grammatically correct. 

        If at least one question has multiple correct answers, respond with 'True'. Otherwise, respond with 'False'.
        Your output must be exactly 'True' or 'False', nothing else.

        {text}
    """
    chain = LLMChain(llm=llm, prompt=prompt, memory=memory)
    result = api_call_with_retry(chain, input_data)
    if result is not None:
        result = result.strip().lower()
        return result == "true"
    return False

def has_stem_errors(text, llm, knowledge_point, memory):
    prompt = PromptTemplate(
        input_variables = ["history", "input_data"],
        template = f"""
            You are an experienced Japanese N4/N5 examiner reviewing the following multiple-choice questions:
            
            {{input_data}}

            {text}

            the review history is attached here: {{history}}.
        """
    )
    input_data = f'''
        the questions are used to test {knowledge_point}
        Check if any **question stem** (the main question part before the options) has errors, such as:
        - Grammatical mistakes
        - Unnatural sentence structures
        - Ambiguous wording
        If there is at least one issue in the stems, respond with 'True'. Otherwise, respond with 'False'.
        Your output must be exactly 'True' or 'False', nothing else.
        '''
    chain = LLMChain(llm=llm, prompt=prompt, memory=memory)
    result = api_call_with_retry(chain, input_data)
    if result is not None:
        result = result.strip().lower()
        return result == "true"
    return False

def has_duplicate_options(text):
    questions_with_options = re.findall(
        r'(\d+)\.\s*(.*?)\n(1\.\s*(.*?)\n)(2\.\s*(.*?)\n)(3\.\s*(.*?)\n)(4\.\s*(.*?)\n)',
        text, re.DOTALL
    )
    for question, _, opt1, _, opt2, _, opt3, _, opt4, _ in questions_with_options:
        options = {opt1.strip(), opt2.strip(), opt3.strip(), opt4.strip()}
        if len(options) < 4:
            print(f"Duplicate options detected in question {question}: {opt1.strip()}, {opt2.strip()}, {opt3.strip()}, {opt4.strip()}")
            return True
    return False

def has_duplicate_questions(text):
    questions = re.findall(
        r'(\d+)\.\s*(.*?)\n(1\.\s*(.*?)\n)(2\.\s*(.*?)\n)(3\.\s*(.*?)\n)(4\.\s*(.*?)\n)',
        text, re.DOTALL
    )
    seen_questions = set()
    for question, _, opt1, _, opt2, _, opt3, _, opt4, _ in questions:
        question_text = normalize_text(question.strip())
        options = {normalize_text(opt1.strip()), normalize_text(opt2.strip()),
                   normalize_text(opt3.strip()), normalize_text(opt4.strip())}
        normalized_question = f"{question_text} - {', '.join(sorted(options))}"
        if normalized_question in seen_questions:
            print(f"Duplicate question detected: {question_text} with options {options}")
            return True
        seen_questions.add(normalized_question)
    return False

def stem_options_error(text, llm, knowledge_point, memory):
    prompt = PromptTemplate(
        input_variables = ["history", "input_data"],
        template = """
            You are an experienced Japanese N4/N5 examiner reviewing the following multiple-choice questions:
            the review history is attached here: {history}.

            {input_data}
        """
    )
    input_data = f'''
        the questions are used to test {knowledge_point}
        Check if any question has the following problems:
        - There is repetition between options and the stem.
        - The sentence doesn't remain **natural and grammatically correct** after filling in the correct answer.

        Example:
        この薬を飲めば（　　　　　）、頭痛が治ります。
        1. 飲まなかったら 2. 飲まなければ 3. 飲めば 4. 飲んだら  

        Explanation: "飲めば" repetes twice after filling the blank which make no sense to the sentence.
        
        If at least one question has **stem-options problem**, respond with 'True'. Otherwise, respond with 'False'.
        Your output must be exactly 'True' or 'False', nothing else.

        {text}
        '''
    chain = LLMChain(llm=llm, prompt=prompt, memory=memory)
    result = api_call_with_retry(chain, input_data)
    if result is not None:
        result = result.strip().lower()
        return result == "true"
    return False

def question_revise_simple(rows, filename, output_dir, revised_newpaper_folder, knowledge_point, max_iterations=5, model='gpt-4o', temperature=0.6):
    """
    对新生成的日语练习题进行多轮修订和检查，确保题目质量。
    """
    revised_result = rows
    llm = ChatOpenAI(temperature=temperature, model=model)
    memory = ConversationSummaryMemory(
        llm = llm, memory_key="history", return_messages=True
    )
    prompt_revise = PromptTemplate(
        input_variables = ["history", "input_data"],
        template = """
**You are an experienced strict Japanese N4/N5 examiner tasked with reviewing and ensuring that all multiple-choice test questions are in high quality and meet the following criteria.**

some errors exist in the following question paper, please review and modify the questions to meet the following criteria.

1. No repetition between stem and any options. Ensure that the sentence is natural and grammatically correct after filling in the correct answer.

2. No duplicate correct answers: Ensure that only one option is grammatically correct for each question. **All three other options must be grammatically wrong**. Modify options that are not situable semantically but grammatically correct. Provide specific suggestions on how to make the answer clear and unambiguous.

3. No duplicate questions: Ensure that all questions are unique. If a question is repeated or too similar to another, please revise it to create a new question with a distinct structure or context. Provide specific suggestions on how to modify repeated questions.

4. No duplicate options: All options within a question should be unique, contextually meaningful, and grammatically correct. Avoid options that are too similar to each other. If necessary, suggest how to modify similar options to increase their clarity.

5. Grammatical correctness: The title and stem of each question must be grammatically correct. Review for influent sentence structures and revise them to ensure fluency and correctness. If you detect any grammatical errors, please explain how to fix them.

6. Pronunciation and Word Usage: If the question involves pronunciation, katakana, or hiragana forms, the Japanese word should be enclosed in brackets for clarity. For hiragana or katakana conversion questions, ensure that the word is written in the correct form, and the correct answer is not shown in the question stem. Also, check for spelling inconsistencies.

7. General guidance: Eliminate any ambiguity, revise unclear options, and avoid subjective or culturally biased phrasing. Ensure all questions are at an appropriate difficulty level for the target JLPT level (N4/N5). Avoid complex words or structures outside the typical N4/N5 range.

8. Output Format: Each question must keep the original format:
   - Each question must start with `Qx` (e.g., `Q1`, `Q2`...).
   - Each question must have exactly 4 options (`1` to `4`).
   - Each question must have an `Answer: x` at the end of it.
   - Do not include any other comments.
            
Here is the history of previous conversation: {history}

{input_data}
"""
    )

    chain = LLMChain(llm=llm, prompt=prompt_revise, memory = memory)

    for iteration in range(max_iterations):
        #revised_result = api_call_with_retry(chain, input_data, knowledge_point)
        if revised_result is None:
            print("Failed to get revised result. Stopping iteration.")
            break

        #for stem_error in range(max_iterations):
        try:
            if has_stem_errors(revised_result, llm, knowledge_point, memory):
                print(f"iteration - {iteration} , find stem error")

                input_data = f"""
                    **The questions below have **stem problems** that need to be addressed. Please detect and modify all possible errors.**
                    **For example: Grammatical mistakes, Unnatural sentence structures, Ambiguous wording.**

                    {revised_result}
                """
                revised_result = api_call_with_retry(chain, input_data)
                #input_data["new_paper"] = revised_result
            else:
                print(f"iteration - {iteration} , no stem error")
                #break
        except Exception as e:
            print(f"Error in check_for_error: {e}")

        #for duplicate_options in range(max_iterations):
        try:
            if has_duplicate_options(revised_result):
                print(f"iteration - {iteration} , find duplicate options")

                input_data = f"""
                    The questions below have **duplicate_options problem** that need to be addressed. Please detect and modify all possible errors.
                    For example: Two options in one questions are the same.

                    {revised_result}
                """

                revised_result = api_call_with_retry(chain, input_data)
                print(memory.load_memory_variables({})["history"])
                #input_data["new_paper"] = revised_result
            else:
                print(f"iteration - {iteration} , no duplicate options")
                #break
        except Exception as e:
            print(f"Error in check_for_error: {e}")

        #for stem_option_error in range(max_iterations):
        try:
            if stem_options_error(revised_result, llm, knowledge_point, memory):
                print(f"iteration - {iteration} , find stem_option_errors")

                input_data = f"""
                    The questions below have **stem-option-error** that need to be addressed. Please detect and modify all possible errors.
                    For example: After filling in the blank, the stem and the options have some part of overlap causing the overall sentence incorrect.

                    {revised_result}
                """

                revised_result = api_call_with_retry(chain, input_data)
                #print(memory_variables)
                #input_data["new_paper"] = revised_result
            else:
                print(f"iteration - {iteration} , no stem_option_error")
                #break
        except Exception as e:
            print(f"Error in check_for_error: {e}")

        #for multiple_correct_answers in range(max_iterations):
        try:
            if has_multiple_correct_answers(revised_result, llm, knowledge_point, memory):
                print(f"iteration - {iteration} , find multiple_correct_answers")

                input_data = f"""
                    The questions below have **multiple correct answers** that need to be addressed. Please detect and modify all possible errors.
                    Ensure that only one answer is correct for each question and all three othere options are definitely wrong on grammar.
                    
                    {revised_result}
                """

                revised_result = api_call_with_retry(chain, input_data)
                #print(memory_variables)
                #input_data["new_paper"] = revised_result
            else:
                print(f"iteration - {iteration} , no multiple_correct_answers")
                #break
        except Exception as e:
            print(f"Error in check_for_error: {e}")

        #for duplicate_questions in range(max_iterations):
        try:
            if has_duplicate_questions(revised_result):
                print(f"iteration - {iteration} , find duplicate_questions")

                input_data = f"""
                    The questions below have **duplicate_questions problem** that need to be addressed. Please detect and modify all possible errors.
                    For example: two questions are too similar or even the same in the following question paper.
                    
                    {revised_result}
                """

                revised_result = api_call_with_retry(chain, input_data)
                #print(memory_variables)
                #input_data["new_paper"] = revised_result
            else:
                print(f"iteration - {iteration} , no duplicate_questions")
                #break
        except Exception as e:
            print(f"Error in check_for_error: {e}")
        print(memory.load_memory_variables({})["history"])
        intermediate_path = os.path.join(output_dir, f"{filename}_iteration_{iteration + 1}.docx")
        output_doc = Document()
        sentences = split_into_sentences(revised_result)
        for sentence in sentences:
            output_doc.add_paragraph(sentence)
        output_doc.save(intermediate_path)
    else:
        print(f"Maximum iterations ({max_iterations}) reached. Errors may still exist.")
    
    output_path = os.path.join(revised_newpaper_folder, f"{filename}_revised.docx")
    output_doc = Document()
    sentences = split_into_sentences(revised_result)
    for sentence in sentences:
        output_doc.add_paragraph(sentence)
    output_doc.save(output_path)
    
    qa_list = parse_questions(revised_result)
    excel_filename = f"{filename}.xlsx"
    store_questions_to_excel(qa_list, output_dir, excel_filename)










# ---------------------------
# 整合工作流：生成 -> 检查 -> 存储
# ---------------------------
def generate_check_store_pipeline(grammar_list, num_list, output_dir, revised_newpaper_folder, base_filepath):
    """
    对每个语法知识点：
    1. 生成题目（按5种题型各生成一定数量的题目）
    2. 合并生成的题目文本
    3. 进行题目检查和多轮修订
    4. 存储最终修订结果（docx、excel）
    """
    filename = os.path.splitext(os.path.basename(base_filepath))[0]
    
    # 遍历每个知识点
    for knowledge_point, question_number in zip(grammar_list, num_list):
        print(f"Processing knowledge point: {knowledge_point}")
        all_questions = ""
        # 生成每种题型的题目并合并
        for question_format in range(1, 3):
            print(f"Generating questions for format {question_format}...")
            questions_text = generate_grammar_questions(knowledge_point, question_format, 10)
            all_questions += f"\n### Format {question_format}\n" + questions_text
        
        # 保存初步生成的题目到一个临时文件（可选）
        temp_path = os.path.join(output_dir, f"{filename}_{question_number}_{knowledge_point}_generated.docx")
        doc = Document()
        doc.add_paragraph(all_questions)
        doc.save(temp_path)
        
        # 调整格式（如需要）
        process_and_revise_document(temp_path)
        
        # 调用题目检查与修订流程
        question_revise_simple(all_questions, f"{filename}_{question_number}_{knowledge_point}", output_dir, revised_newpaper_folder, knowledge_point)
        
        print(f"Finished processing {knowledge_point}. Results stored in {revised_newpaper_folder}")




def main():
    # 文件路径定义
    #docx_file_grammar = "C:\\Users\\刘宇\\OneDrive - CUHK-Shenzhen\\桌面\\JAP_GPT\\N4N5 material\\N4 Notes 文法_numbered.docx"
    #docx_file_vocabulary = "C:\\Users\\刘宇\\OneDrive - CUHK-Shenzhen\\桌面\\JAP_GPT\\N4N5 material\\N4 Notes 語彙_numbered.docx"
    #test_knowledge_points = "C:\\Users\\刘宇\\OneDrive - CUHK-Shenzhen\\桌面\\JAP_GPT\\2025_new_db\\new_questions\\test_knowledge_points.docx"
    test_grammar_original = "D:\\JAP_GPT\\JAP_GPT\\2025_new_db\\new_questions\\test_grammar.docx"
    #test_vocabulary = "C:\\Users\\刘宇\\OneDrive - CUHK-Shenzhen\\桌面\\JAP_GPT\\2025_new_db\\new_questions\\test_vocabulary.docx"
    

    N4_grammar = "D:\\JAP_GPT\\JAP_GPT\\N4N5 material\\N4 Notes 文法_numbered.docx"
    #N4_vocabulary = "C:\\Users\\刘宇\\OneDrive - CUHK-Shenzhen\\桌面\\JAP_GPT\\N4N5 material\\N4 - Vocabulary・語彙.docx"
    N5_grammar = "D:\\JAP_GPT\\JAP_GPT\\N4N5 material\\N5 Notes 文法_numbered.docx"
    #N5_vocabulary = "C:\\Users\\刘宇\\OneDrive - CUHK-Shenzhen\\桌面\\JAP_GPT\\N4N5 material\\N5 - Vocabulary・語彙.docx"

    output_grammar_N4 = "D:\\JAP_GPT\\JAP_GPT\\2025_new_db\\new_questions\\N4 grammar"
    #output_vocabulary_N4 = "C:\\Users\\刘宇\\OneDrive - CUHK-Shenzhen\\桌面\\JAP_GPT\\2025_new_db\\new_questions\\N4 vocabulary"
    output_grammar_N5 = "D:\\JAP_GPT\\JAP_GPT\\2025_new_db\\new_questions\\N5 grammar"
    #output_vocabulary_N5 = "C:\\Users\\刘宇\\OneDrive - CUHK-Shenzhen\\桌面\\JAP_GPT\\2025_new_db\\new_questions\\N5 vocabulary"

    #revised_output_vocabualry = "C:\\Users\\刘宇\\OneDrive - CUHK-Shenzhen\\桌面\\JAP_GPT\\2025_new_db\\new_questions\\revised_vocabulary"
    revised_output_grammar = "D:\\JAP_GPT\\JAP_GPT\\2025_new_db\\new_questions\\语法问题测试\\revised_grammar"
    grammar_output = "D:\\JAP_GPT\\JAP_GPT\\2025_new_db\\new_questions\\语法问题测试\\grammar_original"

    # 提取和修订内容
    #vocabulary_N4_num = extract_numbered_content(N4_vocabulary, 689, 807)[0]
    #vocabulary_N4_content = extract_numbered_content(N4_vocabulary, 689, 807)[1]
    #vocabulary_N5_num = extract_numbered_content(N5_vocabulary, 1, 802)[0]
    #vocabulary_N5_content = extract_numbered_content(N5_vocabulary, 1, 802)[1]

    grammar_N4_num = extract_numbered_content(N4_grammar, 1, 92)[0]
    grammar_N4_content = extract_numbered_content(N4_grammar, 1, 92)[1]
    grammar_N5_num = extract_numbered_content(N5_grammar, 1, 77)[0]
    grammar_N5_content = extract_numbered_content(N5_grammar, 1, 77)[1]

    #vocabulary_num = extract_numbered_content(test_vocabulary, 1, 6)[0]
    #vocabulary_test = extract_numbered_content(test_vocabulary, 1, 6)[1]
    grammar_num = extract_numbered_content(test_grammar_original, 1, 4)[0]
    grammar_test = extract_numbered_content(test_grammar_original, 1, 4)[1]

    #print(vocabulary_test)
    #print(grammar_test)

    # 修订词汇和语法点
    '''N4 Vocabulary'''
    # vocabulary_points_revise(vocabulary_N4_num, vocabulary_N4_content, output_vocabulary_N4, N4_vocabulary)
    # process_word_to_excel(output_vocabulary_N4, output_vocabulary_N4)
    '''N5 Vocabulary'''
    # vocabulary_points_revise(vocabulary_N5_num, vocabulary_N5_content, output_vocabulary_N5, N5_vocabulary)
    # process_word_to_excel(output_vocabulary_N5, output_vocabulary_N5)


    #grammar_points_revise(grammar_num, grammar_test, revised_output_grammar, test_grammar)
    generate_check_store_pipeline(grammar_test, grammar_num, grammar_output, revised_output_grammar, test_grammar_original)
    process_word_to_excel(revised_output_grammar, revised_output_grammar)


if __name__ == "__main__":
    main()