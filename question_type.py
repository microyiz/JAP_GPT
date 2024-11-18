import re
import os
import glob
import time
import warnings
import docx
import mysql.connector
from docx import Document
from jap_paper_revise import read_docx_to_string_with_format
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate  
from langchain.chains import LLMChain   
from typing import Any


def split_into_sentences(text):
        """
        Splits text into sentences based on common Japanese sentence endings.
        
        :param text: Text to split.
        :return: List of sentences.
        """
        sentence_endings = re.compile(r'(?<=[。！？])\s*')
        sentences = sentence_endings.split(text)
        return sentences

def knowledge_point_analysis(paper, question_type):
    """
    Revises a list using a language model and saves the results.

    :param rows: Loaded list data to revise.
    :param filename: Path to save the revised document.
    """
    llm = ChatOpenAI(
        temperature=0.8,
        model="gpt-4o"
    ) 
    prompt_two = ChatPromptTemplate.from_template(
        "I have provided a sample of questions Japanese Language Proficiency Test N4 level: {question_paper}.\
        Now base on these questions, detailed analyze the types of questions"
    )
    
    chain_one = LLMChain(llm=llm, prompt=prompt_two)


    inputs_two = {'question_paper': paper}
    revise_result = chain_one.run(inputs_two)
    output_doc = Document()
    sentences = split_into_sentences(revise_result)
    for sentence in sentences:
        output_doc.add_paragraph(sentence)

    output_path = os.path.join(question_type, f"question_type.docx")
    output_doc.save(output_path)

def process_material(meterial_folder):
    material_doc = []
    for filepath in glob.glob(os.path.join(meterial_folder, "*.docx")):
        material_doc.append(read_docx_to_string_with_format(filepath))
    return material_doc

def knowledge_points_match(self, rows, meterial_paper, filename):
        llm = ChatOpenAI(
            temperature=0.8,
            model="gpt-4o"
        )
        prompt_four = ChatPromptTemplate.from_template(
            "Now here are the knowledge points of Japanese language test :{material}, it includes vocabulary and grammar knowledge of Japanese.\
            Please use it as a reference to matching this list of incorrect answers provided by Japanese language students: {error_report}.\
            You need to find the corresponding knowledge point for each incorrect answer.\
            Given the content of the original questions and all the options, attach the corresponding knowledge points with them. ")
        
        chain_four = LLMChain(llm=llm, prompt = prompt_four)
        input_four = {'material': meterial_paper,
                      'error_report': rows}
        
        matching_result = chain_four.run(input_four)

        output_doc = Document()
        sentences = self.split_into_sentences(matching_result)
        
        for sentence in sentences:
            output_doc.add_paragraph(sentence)
            

        # 路径修改
        output_path = os.path.join(self.matched_knowledge_points_folder, f"{filename}_knowledge_points.docx")
        output_doc.save(output_path)

        return matching_result
def main():
    material_folder = "C:\\Users\\30998\\Desktop\\JAP_GPT\\template paper from CUHK\\Jap_GPT_hk\\test 1 paper\\Test 1 Question Paper.docx"
    # paper = "C:\\Users\\30998\\Desktop\\JAP_GPT\\template paper from CUHK\\Test1\\test 1 paper\\Test 1 Question Paper.docx"
    # question_type = "C:\\Users\\30998\\Desktop\\JAP_GPT\\template paper from CUHK\\Test1\\test 1 paper"
    # document = Document(paper)
    # text = ""
    # for paragraph in document.paragraphs:
    #     text += paragraph.text
    # result = knowledge_point_analysis(text,question_type)
    


if __name__ == "__main__":
    main()