from fastapi import FastAPI, HTTPException
import asyncio
import aio_pika
import json
import uuid
from dotenv import load_dotenv
import os

load_dotenv("../../config/.env")

class QueueProcessor:
    def __init__(self):
        self.rabbitmq_url = os.getenv("RABBITMQ_ROBUST")
        self.response_queue ={}
    async def send_task_to_queue(self, data: str, request_id: str):
        connection = await aio_pika.connect_robust(self.rabbitmq_url)
        channel = await connection.channel()
        self.response_queue = await channel.declare_queue(name=f"response_{request_id}", exclusive=True)
        await channel.default_exchange.publish(
            aio_pika.Message(body=data.encode('utf-8'), message_id=request_id),
            routing_key='request_queue'
        )
        await connection.close()

    async def receive_response_from_queue(self, request_id: str):
        connection = await aio_pika.connect_robust(self.rabbitmq_url)
        channel = await connection.channel()
        queue = await channel.declare_queue(f"response_{request_id}")
        
        future = asyncio.get_event_loop().create_future()

        async def message_handler(message: aio_pika.IncomingMessage):
            async with message.process():
                if message.message_id == request_id:
                    future.set_result(message.body.decode())
                    await queue.cancel()  # 특정 메시지를 받은 후 반복을 중지합니다.

        # 큐에 컨슈머를 추가합니다.
        await queue.consume(message_handler)

        # future에서 특정 메시지를 기다립니다.
        response = await future

        # 응답을 받은 후 채널과 연결을 닫습니다.
        await channel.close()
        await connection.close()
    
        return response

app = FastAPI()
queue_processor = QueueProcessor()

@app.post("/request")
async def process_request(request_data: dict):
    try:
        request_id = request_data['request_id']
        request = request_data['request']

        await queue_processor.send_task_to_queue(json.dumps(request_data, ensure_ascii=False), request_id)
        
        # 큐에서 응답 받기
        response = await queue_processor.receive_response_from_queue(request_id)
        return response
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))