# essences
rabbitMQ기반으로 구성

.env파일을 config파일 폴더에 생성

RABBITMQ_ROBUST=amqp://essences:essences@localhost/
HF_TOKEN=
OPENAI_API_KEY=
SUPABASE_URL=
SUPABASE_KEY=
AGENT_ID_RESIDENCE=22cab6a7-1783-4f43-8565-6678f16732ce
AGENT_ID_INVITATION=f80541ed-7dcc-4548-a80b-90cd8b64ed82
AGENT_ID_TRAVEL=758e8e24-5570-43a6-8859-d38ab726c7be
AGENT_ID_WEDDINGHALL=47cab7ce-1cdb-4745-bdd7-54c096481145


AGENT_ID는 Supabase PostgreDB에 저장된 값 사용
접속정보는 별도 공유

구동순서
API - uvicorn app:app --host 0.0.0.0 --port 8000 --reload
Superviser
나머지 Agent

rabbitmq 로컬 환경 필요
