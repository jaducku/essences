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
    def __init__(self, agent_id, rabbitmq_url, openai_api_key, supabase_client):
        self.rabbitmq_url = rabbitmq_url
        self.openai_api_key = openai_api_key
        self.agent_id = agent_id
        self.supabase = supabase_client

        agent_info = self.supabase.table('agent_info')\
            .select('name', 'desc', 'system_prompt:enhanced_prompt')\
            .eq('agent_id', self.agent_id)\
            .execute()

        if agent_info.data:
            self.system_prompt = agent_info.data[0]['system_prompt']
        else:
            self.system_prompt = "You are an AI assistant."

    async def start(self):
        await self.consume_requests()

    async def consume_requests(self):
        connection = await aio_pika.connect_robust(self.rabbitmq_url)
        channel = await connection.channel()
        request_queue = await channel.declare_queue(self.agent_id, durable=True)

        async def on_message(message: aio_pika.IncomingMessage):
            async with message.process():
                request_id = message.message_id
                my_task = json.loads(message.body.decode())
                task_id = my_task["task_id"]
                task_content = my_task["task"]

                print(f"[Agent {self.agent_id}] Received task: {task_content}")

                response = self.generate_response(task_content)
                print(f"[Agent {self.agent_id}] Response: {response}")

                res = {
                    "request_id": request_id,
                    "task_id": task_id,
                    "response": response,
                }

                await self.send_response_to_queue(res)

        await request_queue.consume(on_message)
        await asyncio.Future()  # Keeps the coroutine running

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
            print(f"[Agent {self.agent_id}] Error: {e}")
            return "An error occurred while processing your request."

if __name__ == "__main__":
    load_dotenv("../../config/.env")
    rabbitmq_url = os.getenv("RABBITMQ_ROBUST")
    openai_api_key = os.getenv("OPENAI_API_KEY")
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")

    supabase: Client = create_client(supabase_url, supabase_key)

    # Retrieve all agent IDs from the database
    agent_infos = supabase.table('agent_info').select('agent_id').eq('is_superviser',False).execute()
    agent_ids = [agent['agent_id'] for agent in agent_infos.data]

    async def main():
        agents = []
        for agent_id in agent_ids:
            agent = Agent(agent_id, rabbitmq_url, openai_api_key, supabase)
            agents.append(agent)

        # Start all agents concurrently
        await asyncio.gather(*(agent.start() for agent in agents))

    asyncio.run(main())