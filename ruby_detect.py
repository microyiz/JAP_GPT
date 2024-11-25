# from zipfile import ZipFile
# from lxml import etree

# def extract_ruby_from_docx(docx_path):
#     try:
#         # 解压 Word 文件
#         with ZipFile(docx_path, 'r') as zip_ref:
#             # 读取 Word 主文档内容
#             xml_content = zip_ref.read('word/document.xml')
        
#         # 使用 lxml 解析 XML
#         root = etree.XML(xml_content)
#         namespace = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
        
#         ruby_texts = []
        
#         # 查找所有 ruby 标签
#         for ruby in root.xpath('//w:ruby', namespaces=namespace):
#             # 提取主文字（rubyBase）和假名注音（rt）
#             base_text = ruby.xpath('.//w:rubyBase//w:t', namespaces=namespace)  # 主文字
#             ruby_text = ruby.xpath('.//w:rt//w:t', namespaces=namespace)        # 假名注音
            
#             ruby_texts.append({
#                 'main_text': ''.join([t.text for t in base_text if t.text]),  # 组合所有文字
#                 'ruby_text': ''.join([t.text for t in ruby_text if t.text])   # 组合所有注音
#             })

#         return ruby_texts
    
#     except Exception as e:
#         print(f"发生错误: {e}")
#         return []

# # 使用示例
# docx_path = "C:\\Users\\刘宇\\OneDrive - CUHK-Shenzhen\\桌面\\JAP_GPT\\processed material\\N4 Notes 語彙.docx"  # 替换为你的文件路径
# ruby_data = extract_ruby_from_docx(docx_path)

# # 输出结果
# if ruby_data:
#     for item in ruby_data:
#         print(f"文字: {item['main_text']}, 注音: {item['ruby_text']}")
# else:
#     print("未找到 Ruby 数据或解析失败。")


import os
import glob
from docx import Document
from lxml import etree
from zipfile import ZipFile
from typing import Any
from langchain.document_loaders import UnstructuredWordDocumentLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter

class JapaneseCharacterTextSplitter(RecursiveCharacterTextSplitter):
    def __init__(self, **kwargs: Any):
        #separators = ["\n\n", "\n", "。", "、", " ", ""]
        separators = [
        "\n\n",
        "\n",
        "。",
        "、",
        " ",
        ".",
        ",",
        "?",
        "\u200B",  # Zero-width space
        "\uff0c",  # Fullwidth comma
        "\u3001",  # Ideographic comma
        "\uff0e",  # Fullwidth full stop
        "\u3002",  # Ideographic full stop
        "",
        ]

        question_separators = [f"Q.{i}" for i in range(1, 500)]
        separators.extend(question_separators)
        number_space_separators = [f"{str(i).zfill(2)}"for i in range(1, 100)]
        separators.extend(number_space_separators)
        super().__init__(separators=separators, **kwargs)


# 1. 读取普通文本并标记 ruby 的函数
def extract_ruby_and_modify_text(docx_path):
    with ZipFile(docx_path, 'r') as zip_ref:
        xml_content = zip_ref.read('word/document.xml')
    
    # 使用 lxml 解析 XML
    root = etree.XML(xml_content)
    namespace = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
    
    ruby_texts = []
    for ruby in root.xpath('//w:ruby', namespaces=namespace):
        # 提取 rubyBase 和 rt 信息
        base_text = ''.join([t.text for t in ruby.xpath('.//w:rubyBase//w:t', namespaces=namespace) if t.text])
        ruby_text = ''.join([t.text for t in ruby.xpath('.//w:rt//w:t', namespaces=namespace) if t.text])
        
        # 构造带标签的 ruby 标记
        ruby_tag = f'<ruby base="{base_text}" rt="{ruby_text}" />'
        ruby_texts.append({
            'main_text': base_text,
            'ruby_text': ruby_text,
            'ruby_tag': ruby_tag,
        })

    # 替换 XML 中的 ruby 标签为自定义标记
    ns = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
    for ruby in root.xpath('//w:ruby', namespaces=namespace):
        # 找到 rubyBase 的文字
        base_text = ''.join([t.text for t in ruby.xpath('.//w:rubyBase//w:t', namespaces=namespace) if t.text])
        ruby_tag = next((item['ruby_tag'] for item in ruby_texts if item['main_text'] == base_text), None)
        if ruby_tag:
            # 替换 ruby 的 XML 结构为带标签的内容
            ruby_element = etree.Element(f"{{{ns}}}t")  # 使用完整命名空间定义标签
            ruby_element.text = ruby_tag  # 设置文本为自定义 ruby 标记
            ruby.getparent().replace(ruby, ruby_element)

    # 提取标记替换后的完整文本
    modified_text = etree.tostring(root, encoding="unicode", method="text")
    return modified_text, ruby_texts


# 2. 分块处理文本
def split_document(text):
    splitter = JapaneseCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
    )
    return splitter.split_text(text)


# 3. 保存处理后的文档
def save_to_docx(splits, output_folder, filename):
    os.makedirs(output_folder, exist_ok=True)  # 确保文件夹存在
    output_path = os.path.join(output_folder, f"{filename}_processed.docx")
    doc = Document()
    for split in splits:
        doc.add_paragraph(split)
    doc.save(output_path)
    print(f"Saved processed document: {output_path}")


# 主函数
def main():
    processed_material = "C:\\Users\\刘宇\\OneDrive - CUHK-Shenzhen\\桌面\\JAP_GPT\\processed material"
    grammar = "C:\\Users\\刘宇\\OneDrive - CUHK-Shenzhen\\桌面\\JAP_GPT\\processed material\\N4 Notes 文法.docx"
    vocabulary = "C:\\Users\\刘宇\\OneDrive - CUHK-Shenzhen\\桌面\\JAP_GPT\\processed material\\N4 Notes 語彙.docx"
    N4N5_material = "C:\\Users\\刘宇\\OneDrive - CUHK-Shenzhen\\桌面\\JAP_GPT\\N4N5 material"
    
    # for filepath in [grammar, vocabulary]:
    for filepath in glob.glob(os.path.join(N4N5_material, "*.docx")):
        filename = os.path.splitext(os.path.basename(filepath))[0]
        print(f"Processing file: {filepath}")
        
        # 提取文本并标记 ruby 信息
        modified_text, ruby_texts = extract_ruby_and_modify_text(filepath)
        
        # 分块处理带标记的文本
        splits = split_document(modified_text)
        
        # 保存分块后的文档
        save_to_docx(splits, processed_material, filename)


if __name__ == "__main__":
    main()
