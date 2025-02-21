import re
import os
from docx import Document
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate  
from langchain.chains import LLMChain   
from typing import Any



def split_into_sentences(text):
    sentence_endings = re.compile(r'(?<=[。！？])\s*')
    sentences = sentence_endings.split(text)
    return sentences

"""
Main Processor for Vocabulary
"""

def vocabulary_points_revise(num, vocabulary_list, output, filepath):
    filename = os.path.splitext(os.path.basename(filepath))[0]
    llm = ChatOpenAI(
        temperature=0.6,
        model='gpt-4o'
    )

    # Define a function to handle the generation of questions for each format
    def generate_questions_for_format(knowledge_point, question_format, num_questions):
        # Descriptions for each question format
        format_descriptions = {
            1: '''**How to write in hiragana:**  
                Test the ability to convert kanji into hiragana in a variety of sentence structures. Avoid directly showing the hiragana word in the stem.
                Example:  
                もんだい1 ＿＿＿の　ことばは　ひらがなで　どう　かきますか。   
                あそこに　かわいい　[鳥]が　います。  
                1. いぬ  2. とり  3. ねこ  4. むし  
                Answer: 2''', 

            2: '''**Kanji recognition:**  
                Test the ability to recognize the kanji form of a word written in hiragana. Provide different verbs, adjectives, or nouns in hiragana and test their kanji recognition.
                Example:  
                もんだい2 ＿＿＿の　ことばは　どう　かきますか。  
                [おっと]は　今、出かけています。  
                1. 大  2. 犬  3. 太  4. 夫  
                Answer: 4''', 

            3: '''**Filling in the blanks:**  
                Focus on testing the correct usage of verbs, nouns, or grammar by filling in blanks. Introduce different sentence structures or subtle grammatical conditions, such as honorifics or formal vs. informal tone. 
                Example:  
                もんだい3 (   　  ) に　なにを　いれますか。  
                これから　ひこうきに　（  　　　　　 ）。  
                1. おります  2. のります  3. あがります  4. のぼります  
                Answer: 2''', 

            4: '''**Sentence meaning comparison:**  
                Test the ability to recognize sentences with similar meanings, but using different vocabulary or grammatical structures. Make sure there are subtle differences in meaning that only one answer fits the context. 
                Example:  
                もんだい4 ＿＿＿の　ぶんと　だいたい　おなじ　いみの　ぶんが　あります。  
                [ギターは　ちちに　ならいました。]  
                1. ギターは　ちちに　もらいました。  
                2. ギターは　ちちに　えらんでもらいました。  
                3. ギターは　ちちに　おしえてもらいました。  
                4. ギターは　ちちに　かってもらいました。  
                Answer: 3''', 

            5: '''**Usage of vocabulary:**  
                Test vocabulary usage in different contexts. Include variations in sentence patterns and test how vocabulary can change meaning in different scenarios. For example, one option might test for transitive vs. intransitive usage.
                Example:  
                もんだい5 つぎの　ことばの　つかいかたで　いちばん　いい　ものを　1・2・3・4から　ひとつ　えらんで　ください。  
                [ずいぶん]  
                1　てんきが　わるいですね。　あしたは　[ずいぶん]　あめでしょう。  
                2　プレゼントを　もらって、　[ずいぶん]　うれしかったです。  
                3　まいにち　れんしゅうして　いますが、　[ずいぶん]　じょうずに　なりません。  
                4　この　ホテルは　駅から　[ずいぶん]　とおいですね。  
                Answer: 4'''
        }

        # Ensure that we have a description for the given format
        format_description = format_descriptions.get(question_format, "")

        # The revised prompt now includes the explanation for each question format
        prompt_vocabulary = ChatPromptTemplate.from_template(
            f'''
            You are an experienced Japanese examiner, well-versed in the N4 and N5 levels of the Japanese Language Proficiency Test (JLPT). Your task is to create exactly {num_questions} multiple-choice questions based on the following vocabulary knowledge point: **{knowledge_point}**.

            ### Requirements:
            1. Each question should have **4 options**, with only **one correct answer**.
            2. The correct answer must strictly match the meaning or usage of the vocabulary word, ensuring no ambiguity.
            3. The incorrect options should deviate from the correct one but be contextually plausible.
            4. Introduce logical conditions or context into the stem that restricts the possible answers, ensuring only one option fits.
            5. The options should be meaningful, with the incorrect ones being close to the correct answer, yet still clearly wrong in context.
            6. After generating the question, apply a check to ensure that only one answer is clearly correct, and the other options are incorrect.
            7. Each question must have an `Answer: x` at the end.

            ### Diversified test question setting methods: 
            The following **Question Format** is {question_format}. Here's what this format means:
            {format_description}

            ### Additional Notes:
            - The generated questions must maintain high linguistic and contextual accuracy.
            - Avoid using cultural or subjective biases that could confuse learners.
            - Ensure that each question format has diversity in context, grammatical structure, and vocabulary usage.

            ### Before finalizing, check your output against these rules:
            1. Each question must start with `もんだい{question_format}` for format indication.
            2. Each question must have exactly 4 options (`1` to `4`).
            3. Each question must have an `Answer: x` at the end.
            4. Do not include any additional instruction in the output except the questions and their content.
            '''
        )

        # Create chain to run the model
        chain_one = LLMChain(llm=llm, prompt=prompt_vocabulary)

        # Input data for generation
        input_data = {
            'knowledge_point': knowledge_point,
        }

        # Generate the questions
        return chain_one.run(input_data)
    

    def split_sentences(text, question_counter):
        # 使用 'もんだい' 切分文本，确保每个问题独立
        problems = re.split(r'(もんだい\d+)', text)
    
        # 去除切分后为空的元素
        problems = [p.strip() for p in problems if p.strip()]
    
        # 为每个问题加上 Qx 序号
        result = []
        for i in range(len(problems)):
            if problems[i].startswith('もんだい'):
                result.append(f"Q{question_counter}: " + problems[i])
                question_counter += 1  # 增加问题计数器
            else:
                result.append(problems[i])

        return result, question_counter

    def process_and_revise_document(output_path):
        # 读取已保存的文档
        doc = Document(output_path)
    
        question_counter = 1  # 从1开始计数
    
        # 遍历文档中的每个段落
        for paragraph in doc.paragraphs:
            # 使用 split_into_sentences 来处理每个段落
            sentences, question_counter = split_sentences(paragraph.text, question_counter)
        
            # 清空原段落文本
            paragraph.clear()

            # 添加每个切分后的句子到段落中，并在 Answer 后添加换行
            for sentence in sentences:
                # 如果句子包含 Answer: x，在后面加一个换行
                if "Answer:" in sentence:
                    paragraph.add_run(sentence)
                    paragraph.add_run("\n")  # 添加换行
                else:
                    paragraph.add_run(sentence)
    
        # 保存修改后的文档，覆盖原文件
        doc.save(output_path)


    # Iterate over each knowledge point and process each one separately
    for knowledge_point, question_number in zip(vocabulary_list, num):
        print(f'Processing vocabulary {knowledge_point} with number {question_number}...')

        # Create a new document for this knowledge point
        output_doc = Document()

        # Generate 20 questions for each format (1 to 5)
        for question_format in range(1, 6):  # Iterate over formats 1 to 5
            print(f"Generating questions for format {question_format}...")

            # Generate the questions for this format
            revise_result = generate_questions_for_format(knowledge_point, question_format, 20)

            # Process the generated questions and add them to the output document
            sentences = split_into_sentences(revise_result)

            # Add format heading to the document for each format
            output_doc.add_paragraph(f"### Format {question_format}")

            # Add sentences (questions) to the document
            for sentence in sentences:
                sentence = sentence.replace("**Answers:**", "**Answers**")
                sentence = sentence.replace("＿＿＿", "[ ]")  # 替换空格部分
                output_doc.add_paragraph(sentence)

        # Save the generated questions for this knowledge point into a Word document
        output_path = os.path.join(output, f"{filename}_{question_number}_{knowledge_point}.docx")
        output_doc.save(output_path)

        # Process and revise the document after saving
        process_and_revise_document(output_path)
        