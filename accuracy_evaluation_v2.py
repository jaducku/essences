# -*- coding: utf-8 -*-


'''
 1. Load Test data set
 2. Request to Multi-Agent
 3. Calculate Accuracy
'''

# 1. Load Test data set
import json, sys
import time

file = 'test.data'
with open(file, 'r', encoding='utf-8') as f:
    test_data_set = json.load(f)

#  1-1. test data meta info

agent_name = test_data_set['agent_name']          ## Multi-Agent 이름 == 결혼
agent_pool = test_data_set['agent_pool']          ## 전체 Agent List
agent_id_pool = list(agent_pool.values())
test_data_count = len(test_data_set['test_data']) ## Test data count

print(f'{agent_name} Agent Accuracy Test')
print(f'Agent Pool : {agent_pool}')


#  1-2. test data
test_data_list = test_data_set['test_data']

## 2. Request to Multi-Agent
import requests, uuid

url = "http://localhost:8000/request"
test_result_list = [] ## Test data 로 테스트 한 결과 (agnet_list, output..)가 담기는 list
response_times = []


for test_data in test_data_list:
    start_time = time.time()

    ## TODO: multi-agent 응답에서 'agent_list' key에 Supervisor Agent가 선택한 agent list 들어가야 함
    # # Request to Multi-Agent
    request_id = uuid.uuid4()
    data = {
        "request_id": str(request_id),
        "request": test_data['utterance']
    }
    res = requests.post(url, json=data)

    end_time = time.time()
    response_time = end_time-start_time
    response_times.append(response_time)

    '''
    <response.json()>
    {"agent_list": ["47cab7ce-1cdb-4745-bdd7-54c096481145", "22cab6a7-1783-4f43-8565-6678f16732ce", "758e8e24-5570-43a6-8859-d38ab726c7be"], "response": "1. 예산 5000만원 강남권 예식장 추천\n   - **그랜드 힐튼 서울**: 럭셔리 분위기와 고급 시설. 강남역 인근.\n   - **파크하얏트 서울**: 자연적인 모던 디자인. 삼성동 위치.\n   - **그랜드 인터컨티넨탈 서울 파르나스**: 세련된 인테리어, 멋진 전망. 코엑스 인근.\n\n2. 3억 원 이하 전세 아파트 추천 지역\n   - **강남구**: 교통과 상권 발달.\n   - **서초구**: 안전한 분위기, 자연환경.\n   - **마포구**: 예술과 문화가 풍부.\n\n3. 신혼여행 이탈리아 추천지\n   - **로마**: 역사적 명소, 로맨틱한 도시.\n   - **피렌체**: 르네상스 문화, 예술적 건축물.\n   - **아말피 해변**: 해안 마을, 아름다운 풍경.\n\n각 항목은 예산 및 선호도에 따라 선택 가능하며 추가 정보가 필요하면 언제든지 문의하세요."}
    '''
    if res.status_code == 200:
        test_result = {}
        test_result['agent_res'] = True  ## Agent 응답
        test_result['correct_agent_list'] = [agent_pool[agent_name] for agent_name in test_data['target_agents']]            ## 정답 Agent list
        test_result['selected_agent_list'] = json.loads(res.json())['agent_list']   ## 응답 Agent list

    else:
        test_result = {}
        test_result['agent_res'] = False

    
    # ## Temp - Code 수정 전까지 테스트용
    # test_result = {}
    # test_result['agent_res'] = True  ## Agent 응답
    # test_result['correct_agent_list'] = [agent_pool[agent_name] for agent_name in test_data['target_agents']]  ## 정답 Agent list
    # test_result['selected_agent_list'] = [agent_pool[agent_name] for agent_name in test_data['selected_agents']]

    test_result_list.append(test_result)
    '''
    [{'agent_res': True, 'correct_agent_list': [], 'selected_agent_list': ['22cab6a7-1783-4f43-8565-6678f16732ce', '47cab7ce-1cdb-4745-bdd7-54c096481145', '8de3de8c-a632-4f21-ac93-73b20e51c95b']}]
    '''

print(response_times)

## 3. Calculate Accuracy
from sklearn.metrics import confusion_matrix, accuracy_score, precision_score, recall_score


tn = []  # True Negative
fp = []  # False Positive
fn = []  # False Negative
tp = []  # True Positive

precision = [] # (= TP / TP + FP)
recall = []    # (= TP / TP + FN)
TPR = [] # True positive rate (= TP / TP + FN)
FPR = [] # False positive rate (= FP / FP + TN)

for cal_accuracy_target in test_result_list:
    correct_agent_list = cal_accuracy_target['correct_agent_list']    ## 정답 Agent list  e.g. ['weddinghall','invitation']
    selected_agent_list = cal_accuracy_target['selected_agent_list']  ## 응답 Agent list  e.g. ['invitation']

    correct_negative = [item for item in agent_id_pool if item not in correct_agent_list]   ## 정답 - 선택되지 않았어야 할 Agnet
    predict_negative = [item for item in agent_id_pool if item not in selected_agent_list]  ## 예측 - 선택되지 않은 Agent
    correct_positive = correct_agent_list  ## 정답 - 선택되었어야 할 Agent
    predict_positive = selected_agent_list ## 정답 - 선택한 Agent
    # print('correct_negative : {}'.format(correct_negative))
    # print('predict_negative : {}'.format(predict_negative))
    # print('correct_positive : {}'.format(correct_positive))
    # print('predict_positive : {}'.format(predict_positive))

    tn_list = list(set(correct_negative) & set(predict_negative))   ## 교집합 구하기
    print('tn_list : {}'.format(tn_list))
    tn.append(len(tn_list))

    fp_list = list(set(correct_negative) & set(predict_positive))   ## 교집합 구하기
    print('fp_list : {}'.format(fp_list))
    fp.append(len(fp_list))

    fn_list = list(set(correct_positive) & set(predict_negative))   ## 교집합 구하기
    print('fn_list : {}'.format(fn_list))
    fn.append(len(fn_list))

    tp_list = list(set(correct_positive) & set(predict_positive))   ## 교집합 구하기
    print('tp_list : {}'.format(tp_list))
    tp.append(len(tp_list))

    precision.append(len(tp_list) / (len(tp_list)+len(fp_list)) )  # (= TP / TP + FP)
    recall.append(len(tp_list) / (len(tp_list) + len(fn_list)))     # (= TP / TP + FN)
    TPR.append(len(tp_list) / (len(tp_list)+len(fn_list)) )        # True positive rate (= TP / TP + FN)
    FPR.append(len(fp_list) / (len(fp_list)+len(tn_list)) )        # False positive rate (= FP / FP + TN)

print('tn : {}'.format(tn))
print('fp : {}'.format(fp))
print('fn : {}'.format(fn))
print('tp : {}'.format(tp))


print('precision : {}'.format(precision))
print('recall : {}'.format(recall))
print('TPR : {}'.format(TPR))
print('FPR : {}'.format(FPR))


import matplotlib.pyplot as plt
import numpy as np

# Calculating average values for each metric across all instances
tp_value = np.mean(tp)
fp_value = np.mean(fp)
tn_value = np.mean(tn)
fn_value = np.mean(fn)

# Creating the confusion matrix with average values
confusion_matrix_avg = np.array([[tp_value, fn_value], [fp_value, tn_value]])

# Plotting the confusion matrix with average values
fig, ax = plt.subplots(figsize=(5, 5))
cax = ax.matshow(confusion_matrix_avg, cmap="Blues")
fig.colorbar(cax)

# Adding text annotations for each cell with formatted average values
for (i, j), value in np.ndenumerate(confusion_matrix_avg):
    ax.text(j, i, f'{value:.2f}', ha='center', va='center', color="black", fontsize=12)

# Labeling the axes
ax.set_xlabel('Predicted Labels')
ax.set_ylabel('Actual Labels')
ax.set_xticks([0, 1])
ax.set_yticks([0, 1])
ax.set_xticklabels(['Positive', 'Negative'])
ax.set_yticklabels(['Positive', 'Negative'])

# Setting title for clarity
plt.title("Average Confusion Matrix")

plt.show()
