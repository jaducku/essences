import asyncio
import aio_pika
from aio_pika import connect, Message
import json
import uuid
from dotenv import load_dotenv
import os
import openai
from openai import OpenAI
from supabase import create_client, Client

load_dotenv("../../config/.env")

class SupervisorAgent:
    def __init__(self):
        self.requests = {}  # request_id를 키로 하고, 남은 task 수와 응답을 저장
        self.rabbitmq_url = os.getenv("RABBITMQ_ROBUST")
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")
        self.supabase: Client = create_client(supabase_url, supabase_key)
        response = self.supabase.table('agent_info')\
            .select('agent_id', 'name', 'desc', 'system_prompt:enhanced_prompt', 'is_superviser')\
            .eq('is_active', True)\
            .execute()

        superviser_data = [record for record in response.data if record.get('is_superviser') == True] if response.data else []
        self.prompt_template = superviser_data[0].get('system_prompt')
        self.agent_list = [
            {
                'agent_id': record.get('agent_id'),
                'name': record.get('name'),
                'desc': record.get('desc')
            }
            for record in response.data if record.get('is_superviser') == False
        ]

    async def start(self):
        await asyncio.gather(
            self.consume_requests(),
            self.consume_task_responses()#
            #self.periodic_agent_checker()
        )

    async def consume_requests(self):
        connection = await aio_pika.connect_robust(self.rabbitmq_url)
        channel = await connection.channel()
        request_queue = await channel.declare_queue('request_queue', durable=True)

        async with request_queue.iterator() as queue_iter:
            async for message in queue_iter:
                async with message.process():
                    try:
                        request_data = json.loads(message.body.decode())
                        print(request_data)
                        if not isinstance(request_data, dict):
                            print("Invalid request data format, skipping message.")
                            continue
                        
                        request_id = request_data.get('request_id')
                        if not request_id:
                            print("Request ID missing in request data.")
                            continue

                        tasks = self.intent_analysis_and_split(request_data)
                        self.requests[request_id] = {"remain_task_cnt": len(tasks)}
                        
                        for task in tasks:
                            task_id = str(uuid.uuid4())
                            task['task_id'] = task_id
                            agent_id = task.get('agent_id')

                            await channel.default_exchange.publish(
                                aio_pika.Message(
                                    body=json.dumps(task, ensure_ascii=False).encode('utf-8'),
                                    message_id=request_id
                                ),
                                routing_key=agent_id
                            )

                            self.requests[request_id][task_id] = {
                                "agent_id": agent_id, "status": "process"
                            }
                    except json.JSONDecodeError:
                        print("Failed to decode request message, skipping.")

    async def consume_task_responses(self):
        connection = await aio_pika.connect_robust(self.rabbitmq_url)
        channel = await connection.channel()
        response_queue = await channel.declare_queue('task_response_queue')

        async def on_message(message: aio_pika.IncomingMessage):
            async with message.process():
                try:
                    response_data = json.loads(message.body.decode())
                    if not isinstance(response_data, dict):
                        print("Invalid response data format, skipping message.")
                        return

                    request_id = response_data.get('request_id')
                    task_id = response_data.get('task_id')
                    task_result = response_data.get('response')
                    response_queue_name = f'response_{request_id}'
                    if request_id and task_id and task_result:
                        self.requests[request_id][task_id]["status"] = "finish"
                        self.requests[request_id][task_id]["response"] = task_result
                        self.requests[request_id]['remain_task_cnt'] -= 1

                        if self.requests[request_id]['remain_task_cnt'] == 0:
                            final_response = self.combine_responses(self.requests[request_id])
                            await self.send_response_to_queue(final_response, request_id, response_queue_name)
                            del self.requests[request_id]
                except json.JSONDecodeError:
                    print("Failed to decode response message, skipping.")
                except KeyError as e:
                    print(f"Key error: {e}, skipping message.")

        await response_queue.consume(on_message)
        await asyncio.Future()

    async def send_response_to_queue(self, response_data, request_id, queue_name):
        connection = await aio_pika.connect_robust(self.rabbitmq_url)
        channel = await connection.channel()

        await channel.default_exchange.publish(
            aio_pika.Message(
                body=json.dumps(response_data, ensure_ascii=False).encode('utf-8'),
                message_id=request_id
            ),
            routing_key=queue_name
        )
        print(f"Sent combined response for request: {request_id}")
        await connection.close()

    def intent_analysis_and_split(self, request_data: dict):
        try:
            client = OpenAI(api_key=self.openai_api_key)
            query = f"""
                사용자 입력 : {request_data['request']}
                Agent List : {self.agent_list}
                위의 사용자 입력과 Agent 리스트를 참고하여 답변.
            """

            completion = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": self.prompt_template},
                    {"role": "user", "content": query}
                ]
            )
            result = completion.choices[0].message.content
            return json.loads(result)

        except Exception as e:
            print(f"Error analyzing message: {e}")
            return []

    def combine_responses(self, responses):
        agent_list = [entry['agent_id'] for key, entry in responses.items() if isinstance(entry, dict) and 'agent_id' in entry]
        response_list = [entry['response'] for key, entry in responses.items() if isinstance(entry, dict) and 'response' in entry]

        try:
            client = OpenAI(api_key=self.openai_api_key)
            query = f"""
              사용자 입력 : {response_list}
              위의 사용자 입력을 정리해주세요.
            """

            completion = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "너는 여러 Agent가 보낸 답변을 요약하고 체계적으로 정리하는 agent야. 주어진 배열 데이터를 보고 깔끔하게 정리해줘. 불필요한 말은 삼가해"},
                    {"role": "user", "content": query}
                ]
            )
            result = completion.choices[0].message.content
            return {"agent_list": agent_list, "response": result}

        except Exception as e:
            print(f"Error analyzing message: {e}")
            return {}

    async def periodic_agent_checker(self):
        while True:
            await self.agent_checker()
            await asyncio.sleep(10)

    async def agent_checker(self):
        print("update agents")
        response = self.supabase.table('agent_info')\
            .select('agent_id', 'name', 'desc', 'system_prompt:enhanced_prompt', 'is_superviser')\
            .eq('is_active', True)\
            .execute()

        superviser_data = [record for record in response.data if record.get('is_superviser') == True] if response.data else []
        self.prompt_template = superviser_data[0].get('system_prompt')
        self.agent_list = [
            {
                'agent_id': record.get('agent_id'),
                'name': record.get('name'),
                'desc': record.get('desc')
            }
            for record in response.data if record.get('is_superviser') == False
        ]

if __name__ == "__main__":
    supervisor_agent = SupervisorAgent()
    asyncio.run(supervisor_agent.start())
    