import textgrad as tg
import os
from dotenv import load_dotenv
load_dotenv("../../config/.env")

os.environ['OPENAI_API_KEY'] # API 키 공란으로 올립니다
tg.set_backward_engine("gpt-4o")   # gpt-4 / gpt-4o 쓰시면 될 것 같아요

from supabase import create_client, Client

supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(supabase_url, supabase_key)

response = supabase.table('agent_info')\
    .select('agent_id','system_prompt','name')\
    .eq('is_active', True)\
    .execute()

agents = response.data

optimized_prompts = {}

for agent in agents:
    agent_id=agent["agent_id"]

    prompt_variable = tg.Variable(
        agent['system_prompt'],
        role_description=f"Multi-Agent 시스템의 {agent['name']} 프롬프트",
        requires_grad=True
    )

    # 손실 함수를 정의합니다. 여기서는 프롬프트의 품질을 평가하는 지시문을 사용합니다.
    evaluation_instruction = (
        "이 시스템 프롬프트를 평가하세요."
        "프롬프트가 명확하고, 구체적이며, 해당 작업에 적합한지 확인하세요."
    )
    loss_fn = tg.TextLoss(evaluation_instruction)

    # Optimizer 설정
    optimizer = tg.TGD(parameters=[prompt_variable])

    for step in range(1):  # 여러번 할수록 성능이 좋아질 수도??
        # 손실 계산.
        loss = loss_fn(prompt_variable)
        # print("loss: ", loss) => 여기 찍어봐도 의미있는 결과 나옵니다.

        loss.backward()
        optimizer.step()

    # 결과 저장
    optimized_prompts[agent['name']] = prompt_variable.value

    update_data = {
        "agent_id":agent_id,
        "enhanced_prompt": prompt_variable.value  # 업데이트할 컬럼과 값
    }

    # 조건에 맞는 데이터 업데이트
    response = (
        supabase
        .table("agent_info")  # 테이블 이름
        .update(update_data)  # 업데이트할 데이터
        .eq("agent_id", agent_id)  # 특정 조건, 예를 들어 id가 특정 값인 경우
        .execute()
    )

    



for agent_name, optimized_prompt in optimized_prompts.items():
    print(f"{agent_name}의 최적화된 프롬프트:\n{optimized_prompt}\n")
    print("=====================================================")

'''
# 시스템 프롬프트 정의
before_supervisor_prompt ="""세션 ID: {session_id}
사용자 문의: {user_input}
위 문의에서 사용자의 의도를 파악하고 다음 중 하나 또는 여러 개로 분류하세요:
{roles}
각 의도에 필요한 추가 정보를 추출하세요 (예: 날짜, 목적지 등).
결과를 JSON 형식으로 반환하세요. 예:
{{
  "intents": ["항공권", "호텔"],
  "정보": {{
    "항공권 예약": {{"날짜": "2023-10-20", "출발지": "서울", "도착지": "뉴욕"}},
    "호텔 예약": {{"체크인 날짜": "2023-10-21", "체크아웃 날짜": "2023-10-25", "위치": "뉴욕"}}
  }}
}}
Answer in the following language : Korean"""

before_agent1_prompt="""세션 ID: {session_id}
사용자 문의: {user_input}
위 요청에 대하여 사용자에게 엑티비티가 예약되었다는 메시지와 함께 예약된 엑티비티 정보를 전달해주세요.
Answer in the following language : Korean"""

before_agent2_prompt="""세션 ID: {session_id}
사용자 문의: {user_input}
위 요청에 대하여 사용자에게 항공권이 예약되었다는 메시지와 함께 탑승 정보를 전달해주세요.
Answer in the following language : Korean"""


### 효율화하고 싶은 프롬프트 선언
system_prompts = [
    {"name": "Supervisor", "prompt": before_supervisor_prompt},
    {"name": "Activity", "prompt": before_agent1_prompt},
    {"name": "AirlineTicket", "prompt": before_agent2_prompt}

]

optimized_prompts = {}

for prompt in system_prompts:
    prompt_variable = tg.Variable(
        prompt['prompt'],
        role_description=f"Multi-Agent 시스템의 {prompt['name']} 프롬프트",
        requires_grad=True
    )

    # 손실 함수를 정의합니다. 여기서는 프롬프트의 품질을 평가하는 지시문을 사용합니다.
    evaluation_instruction = (
        "이 시스템 프롬프트를 평가하세요."
        "프롬프트가 명확하고, 구체적이며, 해당 작업에 적합한지 확인하세요."
    )
    loss_fn = tg.TextLoss(evaluation_instruction)

    # Optimizer 설정
    optimizer = tg.TGD(parameters=[prompt_variable])

    for step in range(1):  # 여러번 할수록 성능이 좋아질 수도??
        # 손실 계산.
        loss = loss_fn(prompt_variable)
        # print("loss: ", loss) => 여기 찍어봐도 의미있는 결과 나옵니다.

        loss.backward()
        optimizer.step()

    # 결과 저장
    optimized_prompts[prompt['name']] = prompt_variable.value

for agent_name, optimized_prompt in optimized_prompts.items():
    print(f"{agent_name}의 최적화된 프롬프트:\n{optimized_prompt}\n")
    print("=====================================================")

    '''