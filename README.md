# Application Name
essences - Multi Agent System(superviser)

# 구조
작성중

# 환경설정
rabbitmq 로컬 환경 필요
RabbitMQ 설치 및 user/pw생성
.env파일을 config파일 폴더에 생성

RABBITMQ_ROBUST=amqp://essences:essences@localhost/
HF_TOKEN=
OPENAI_API_KEY=
SUPABASE_URL=
SUPABASE_KEY=

# Agent Info 스키마 정보
사용 DB - supabase
스키마

agent_id:uuid
is_superviser:bool
name:varchar
desc:text
is_active:bool
system_prompt:text
enhanced_prompt:text


# Application 구동순서
API-Gateway - uvicorn app:app --host 0.0.0.0 --port 8000 --reload
Superviser - python ./superviser-agent/main.py
Agents - python ./sub-agents/main.py
PromptEnhancer - python ./prompt-enhancer/main.py
FrontEnd - python front.py

기타 agent들은 개별 특화 로직이 구성될 경우 범용 Agent로는 구성이 어려움(Tool Chain 등등)
이럴경우 별도로 Agent를 구성하여 Q로 연결해야 함
현재 Version은 producer/comsumer로 되어있으나 pub/sub구성도 함께 사용해야 함
