import textgrad as tg
import os
import json
import asyncio
from dotenv import load_dotenv
from supabase import create_client, Client
import aio_pika

class AgentUpdater:
    def __init__(self):
        # 환경 변수 로드
        load_dotenv("../../config/.env")
        self.rabbitmq_host = os.getenv("RABBITMQ_ROBUST")
        # Supabase 클라이언트 설정
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_key = os.getenv("SUPABASE_KEY")
        self.supabase: Client = create_client(self.supabase_url, self.supabase_key)

        # Textgrad 최적화 엔진 설정
        tg.set_backward_engine("gpt-4o")  # gpt-4 / gpt-4o 사용 가능

    async def optimize_and_update_agent(self, agent):
        print('start enhancing prompt...')
        agent_id = agent["agent_id"]

        prompt_variable = tg.Variable(
            agent['system_prompt'],
            role_description=f"Multi-Agent 시스템의 {agent['name']} 프롬프트",
            requires_grad=True
        )

        # 손실 함수 정의
        evaluation_instruction = (
            "이 시스템 프롬프트를 평가하세요. "
            "프롬프트가 명확하고, 구체적이며, 해당 작업에 적합한지 확인하세요."
        )
        loss_fn = tg.TextLoss(evaluation_instruction)

        # Optimizer 설정
        optimizer = tg.TGD(parameters=[prompt_variable])

        for step in range(1):  # 반복 횟수 조정 가능
            loss = loss_fn(prompt_variable)
            loss.backward()
            optimizer.step()

        # 최적화된 프롬프트 결과 저장
        optimized_prompt = prompt_variable.value
        update_data = {
            "enhanced_prompt": optimized_prompt
        }

        # Supabase에 업데이트
        response = (
            self.supabase
            .table("agent_info")
            .update(update_data)
            .eq("agent_id", agent_id)
            .execute()
        )
        print('Enhancing prompt complate...')
        return response

    async def process_message(self, message: aio_pika.IncomingMessage):
        async with message.process():
            # 메시지 가져오기
            agent_info = json.loads(message.body.decode())
            print(agent_info)

            # 비동기 최적화 및 업데이트 수행
            await self.optimize_and_update_agent(agent_info)

    async def consume_queue(self):
        connection = await aio_pika.connect_robust(self.rabbitmq_host)
        async with connection:
            channel = await connection.channel()
            queue = await channel.declare_queue("agent_insert")

            # 메시지 소비
            await queue.consume(self.process_message)
            print("Consuming messages from 'agent_insert' queue")

            await asyncio.Future()  # 큐 소비를 계속 유지

if __name__ == "__main__":
    agent_updater = AgentUpdater()
    asyncio.run(agent_updater.consume_queue())