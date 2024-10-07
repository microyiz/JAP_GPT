## 10.7 Revise
### 1. jap_processor_v3.py
修改了question_revise()，降低了gpt temperature: 0.8->0.6 (improve probability), 加入for loop;
新增check_for_errors(), has_multiple_correct_answers()等functions用于检验new_paper中的重复、错误等问题；

### 2. Existing problems
关于如何检验存在多个正确答案、题干的语法等问题还未想好（详见jap_processor_v3.py）；
在loop中多次运行有助于减少错误，但可能无法完全消除错误，由于模型的输出是概率性的，因此重新运行修订过程可能会引入新的错误或无法正确识别现存问题；
更好的方法可能是通过添加约束或检查来优化提示，以针对特定的重复错误 (但新生成的题目中仍然有detect出，假装改了却未改的情况，如1155175928)
