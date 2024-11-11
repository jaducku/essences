# Application Name
# essences
Multi Agent System(superviser)

# 구조
외부 참조

# 환경설정
RabbitMQ 설치 및 user/pw생성
.env파일을 config파일 폴더에 생성

RABBITMQ_ROBUST=amqp://essences:essences@localhost/
HF_TOKEN=
OPENAI_API_KEY=
SUPABASE_URL=
SUPABASE_KEY=

# Agent Info 스키마 정보
사용 DB





agent_id:uuid
is_superviser:bool
name:varchar
desc:text
is_active:bool
system_prompt:text
enhanced_prompt:text







AGENT_ID는 Supabase PostgreDB에 저장된 값 사용
접속정보는 별도 공유

구동순서
API - uvicorn app:app --host 0.0.0.0 --port 8000 --reload
Superviser
나머지 Agent

rabbitmq 로컬 환경 필요
