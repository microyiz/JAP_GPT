## Upload all changes now
数据库新建方面请见db_questions_results.py; insert_db.py; jap_paper_revise.py \n
数据库格式参考 new_db_test.docx

目前已实现大体框架上的建立，但仍然有一些问题；下一步需要使用ChatGPT生成题目后送人工检测（先和hk开会同步一下进度）

## 2/21更新：
1. 修改了vocabulary部分的prompt格式及部分代码逻辑，目前可以按要求生成多种不同题型的词汇题（见 jap_vocabulary_processor.py）；
2. 存储word文档进入excel的部分可见于 jap_excel_processor.py
3. 未完成的：grammar及revise部分还需要修改以提高鲁棒性
