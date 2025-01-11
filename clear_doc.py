from docx import Document

def delete_keyword_lines(file_path, keyword, output_path):
    # 加载文档
    doc = Document(file_path)
    paragraphs = doc.paragraphs  # 获取所有段落

    # 找到所有包含关键词的段落并删除
    for paragraph in paragraphs:
        if keyword in paragraph.text:
            # 删除段落
            p = paragraph._element
            p.getparent().remove(p)

    # 保存修改后的文档
    doc.save(output_path)
    print(f"所有包含关键词 '{keyword}' 的段落已删除，文档已保存至 {output_path}")

# 示例调用
delete_keyword_lines("C:\\Users\\刘宇\\OneDrive - CUHK-Shenzhen\\桌面\\JAP_GPT\\N4N5 material\\N4N5 original\\N5 Notes 語彙.docx", 
                    "意味", 
                    "C:\\Users\\刘宇\\OneDrive - CUHK-Shenzhen\\桌面\\JAP_GPT\\processed material\\N5 Notes 語彙_processed.docx")
delete_keyword_lines("C:\\Users\\刘宇\\OneDrive - CUHK-Shenzhen\\桌面\\JAP_GPT\\N4N5 material\\N4N5 original\\N5 Notes 語彙.docx", 
                    "例", 
                    "C:\\Users\\刘宇\\OneDrive - CUHK-Shenzhen\\桌面\\JAP_GPT\\processed material\\N5 Notes 語彙_processed.docx")
delete_keyword_lines("C:\\Users\\刘宇\\OneDrive - CUHK-Shenzhen\\桌面\\JAP_GPT\\N4N5 material\\N4N5 original\\N5 Notes 語彙.docx", 
                    "辞書形", 
                    "C:\\Users\\刘宇\\OneDrive - CUHK-Shenzhen\\桌面\\JAP_GPT\\processed material\\N5 Notes 語彙_processed.docx")
