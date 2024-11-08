import asyncio
import aio_pika
from aio_pika import connect, Message, ExchangeType
import json
import uuid
from dotenv import load_dotenv
import os
import openai
from openai import OpenAI
from supabase import create_client, Client

load_dotenv("../../config/.env")

class Agent:
    def __init__(self):
        self.rabbitmq_url = os.getenv("RABBITMQ_ROBUST")
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.agent_id = os.getenv("AGENT_ID_RESIDENCE")
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")
        
        supabase: Client = create_client(supabase_url, supabase_key)
        
        agent_info = supabase.table('agent_info')\
            .select('name','desc','system_prompt') \
            .eq('agent_id', self.agent_id)\
            .execute()

        self.system_prompt = agent_info.data[0]['system_prompt']

    async def start(self):
        await asyncio.gather(
            self.consume_requests()
        )

    async def consume_requests(self):
        # RabbitMQ 연결 및 채널 생성
        connection = await aio_pika.connect_robust(self.rabbitmq_url)
        channel = await connection.channel()
        # 큐 선언
        request_queue = await channel.declare_queue(self.agent_id, durable=True)

        # 메시지 처리 콜백 함수
        async def on_message(message: aio_pika.IncomingMessage):
            async with message.process():
                # 메시지 본문 디코딩
                request_id = message.message_id
                my_task = json.loads(message.body.decode())
                task_id = my_task["task_id"]
                task_content = my_task["task"]
                
                print(f"Received task: {task_content}")
                
                # 응답 생성
                response = self.generate_response(task_content)
                print(f"Response: {response}")
                
                res = {
                    "request_id":request_id,
                    "task_id":task_id,
                    "response":response,
                }

                # 응답을 큐에 전송
                await self.send_response_to_queue(res)
        # 메시지 소비 시작
        await request_queue.consume(on_message)
        await asyncio.Future()
        
    async def send_response_to_queue(self, res):
        connection = await aio_pika.connect_robust(self.rabbitmq_url)
        channel = await connection.channel()
        await channel.default_exchange.publish(
            aio_pika.Message(
                body=json.dumps(res, ensure_ascii=False).encode('utf-8')
            ),
            routing_key='task_response_queue'
        )
        await connection.close()

    def generate_response(self, query: str):
        try:
            client = OpenAI(api_key=self.openai_api_key)

            completion = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": query}
                ]
            )
            
            result = completion.choices[0].message.content
            return result

        except Exception as e:
            print(f"Error analyzing message: {e}")
            return None

    def combine_responses(self, responses):
        # 여러 Task의 응답을 조합하는 로직
        combined = {'combined_responses': responses}
        return combined


if __name__ == "__main__":
    agent = Agent()
    asyncio.run(agent.start())