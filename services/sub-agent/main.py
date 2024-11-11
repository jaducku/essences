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
        '''
        agent_info = self.supabase.table('agent_info')\
            .select('name', 'desc', 'system_prompt:enhanced_prompt')\
            .eq('agent_id', self.agent_id)\
            .execute()
        '''
        agent_info = self.supabase.table('agent_info')\
            .select('name', 'desc', 'system_prompt')\
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

class AgentManager:
    def __init__(self):
        self.rabbitmq_url = os.getenv("RABBITMQ_ROBUST")
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")

        self.supabase: Client = create_client(supabase_url, supabase_key)
        self.agents = {}  # Dictionary to store running agents

    async def start(self):
        # Load existing agents from the database
        await self.load_existing_agents()
        # Start consuming the agent_info queue to add new agents dynamically
        await self.consume_agent_info()

    async def load_existing_agents(self):
        print("[AgentManager] Loading existing agents from the database...")
        agent_infos = self.supabase.table('agent_info').select('agent_id').execute()
        agent_ids = [agent['agent_id'] for agent in agent_infos.data]

        for agent_id in agent_ids:
            if agent_id not in self.agents:
                print(f"[AgentManager] Creating agent with ID: {agent_id}")
                agent = Agent(
                    agent_id,
                    self.rabbitmq_url,
                    self.openai_api_key,
                    self.supabase
                )
                self.agents[agent_id] = agent
                # Start the agent in the background
                asyncio.create_task(agent.start())
            else:
                print(f"[AgentManager] Agent {agent_id} already exists.")

    async def consume_agent_info(self):
        print("[AgentManager] Starting to consume agent_info queue...")
        connection = await aio_pika.connect_robust(self.rabbitmq_url)
        channel = await connection.channel()
        agent_info_queue = await channel.declare_queue('agent_info', durable=True)

        async def on_message(message: aio_pika.IncomingMessage):
            async with message.process():
                agent_data = json.loads(message.body.decode())
                print(agent_data)
                agent_id = agent_data.get('agent_id')
                if agent_id:
                    if agent_id not in self.agents:
                        print(f"[AgentManager] Creating new agent with ID: {agent_id}")
                        agent = Agent(
                            agent_id,
                            self.rabbitmq_url,
                            self.openai_api_key,
                            self.supabase
                        )
                        self.agents[agent_id] = agent
                        # Start the agent in the background
                        asyncio.create_task(agent.start())
                    else:
                        print(f"[AgentManager] Agent {agent_id} already exists.")
                else:
                    print("[AgentManager] Invalid agent data received.")

        await agent_info_queue.consume(on_message)
        print("[AgentManager] Started consuming agent_info queue.")
        await asyncio.Future()  # Keep the coroutine running

if __name__ == "__main__":
    agent_manager = AgentManager()
    asyncio.run(agent_manager.start())