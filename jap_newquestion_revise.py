import re
import os
import glob
import time
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

from jap_paper_revise import return_revised_result
from jap_paper_revise import extract_student_id
from jap_paper_revise import read_docx_to_string
from db_util import drop_table_query ,create_table_query ,insert_query,show_fiverows_query,select_mistake_query,db




