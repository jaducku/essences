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

class SupervisorAgent:
    def __init__(self):
        self.requests = {}  # request_id를 키로 하고, 남은 task 수와 응답을 저장
        self.rabbitmq_url = os.getenv("RABBITMQ_ROBUST")
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")
        supabase: Client = create_client(supabase_url, supabase_key)
        
        response = supabase.table('agent_info')\
            .select('agent_id','name','desc','system_prompt','is_superviser') \
            .eq('is_active', True)\
            .execute()

        superviser_data = [record for record in response.data if record.get('is_superviser') == True] if response.data else []
        self.prompt_template = superviser_data[0].get('system_prompt')
        #print(self.prompt_template)
        self.agent_list = json.loads(json.dumps([
            {
                'agent_id': record.get('agent_id'),
                'name': record.get('name'),
                'desc': record.get('desc')
            } 
            for record in response.data if record.get('is_superviser') == False]))
        print(self.agent_list)
    async def start(self):
        await asyncio.gather(
            self.consume_requests(),
            self.consume_task_responses()
        )

    async def consume_requests(self):
        connection = await aio_pika.connect_robust(self.rabbitmq_url)
        channel = await connection.channel()
        request_queue = await channel.declare_queue('request_queue', durable=True)

        async with request_queue.iterator() as queue_iter:
            async for message in queue_iter:
                async with message.process():
                    request_data = json.loads(message.body.decode())
                    #print(request_data)
                    request_id = request_data['request_id']
                    tasks = self.intent_analysis_and_split(request_data)
                    self.requests[request_id] = {"remain_task_cnt": len(tasks)}
                    
                    for task in tasks:
                        task_id = str(uuid.uuid4())
                        task['task_id'] = task_id
                        agent_id = task['agent_id']

                        await channel.default_exchange.publish(
                            aio_pika.Message(
                                body=json.dumps(task, ensure_ascii=False).encode('utf-8'),
                                message_id=request_id),
                            routing_key=agent_id
                        )

                        self.requests[request_id][task_id] = {
                            "agent_id": agent_id, "status": "process"
                        }

    async def consume_task_responses(self):
        connection = await aio_pika.connect_robust(self.rabbitmq_url)
        channel = await connection.channel()
        response_queue = await channel.declare_queue('task_response_queue')
        #큐를 컨슘하면서 request Dict에 Task 리턴정보 저정 및 cnt 갱신
        
        #request의 cnt를 체크라여 0인 것은 최종 답변으로 만든 후에 최종 response로 회신

        async def on_message(message: aio_pika.IncomingMessage):
            async with message.process():
                # 메시지 본문 디코딩
                
                response_data = json.loads(message.body.decode())
                request_id = response_data['request_id']
                task_id = response_data['task_id']
                task_result = response_data['response']  # 태스크 결과 데이터

                # 결과 추가 및 남은 태스크 개수 감소
                self.requests[request_id][task_id]["status"] = "finish"
                self.requests[request_id][task_id]["response"] = task_result
                self.requests[request_id]['remain_task_cnt'] -= 1
                
                # 남은 태스크가 0이면 최종 응답을 생성하여 응답 큐에 전송
                if self.requests[request_id]['remain_task_cnt'] == 0:
                    final_response = self.combine_responses(self.requests[request_id])
                    
                    await self.send_response_to_queue(final_response, request_id)

                    # 처리 완료된 요청은 딕셔너리에서 삭제
                    del self.requests[request_id]
                
            # 메시지 소비 시작
        await response_queue.consume(on_message)
        await asyncio.Future()
            
    async def send_response_to_queue(self, response_data, request_id):
        connection = await aio_pika.connect_robust(self.rabbitmq_url)
        channel = await connection.channel()

        await channel.default_exchange.publish(
            aio_pika.Message(
                body=json.dumps(response_data).encode('utf-8'),
                message_id=request_id
            ),
            routing_key='response_queue'
        )
        print(f"Sent combined response for request: {request_id}")

        await connection.close()

    def intent_analysis_and_split(self, request_data: json):
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
            return None

    def combine_responses(self, responses):
        # 여러 Task의 응답을 조합하는 로직

        # Collect agent IDs and responses
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
                    {"role": "system", "content": "너는 여러 Agent가 보낸 답변을 요약 하고 체계적으로 정리하는 agent야. 주어진 배열 데이터를 보고 깔끔하게 정리해줘. 불필요한 말은 삼가해"},
                    {"role": "user", "content": query}
                ]
            )
            result = completion.choices[0].message.content
        
            # Instead of loading, create a dictionary directly
            combined_response = {
                "agent_list": agent_list,
                "response": result
            }
            print(combined_response)
            return combined_response  # Return the dictionary directly

        except Exception as e:
            print(f"Error analyzing message: {e}")
            return None

if __name__ == "__main__":
    supervisor_agent = SupervisorAgent()
    asyncio.run(supervisor_agent.start())