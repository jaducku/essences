import uuid
import json
import os
from dotenv import load_dotenv
from supabase import create_client, Client
import pika  # RabbitMQ library
from langchain_core.tools import Tool
from langchain_openai import ChatOpenAI
from langchain.agents import initialize_agent, AgentType

# Load environment variables from .env file in another directory
load_dotenv("../../config/.env")

class DataExtractorMicroservice:
    def __init__(self):
        # Read configurations from environment variables
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")
        self.rabbitmq_host = os.getenv("RABBITMQ_HOST")
        self.rabbitmq_port = os.getenv("RABBITMQ_PORT")
        self.rabbitmq_id = os.getenv("RABBITMQ_ID")
        self.rabbitmq_pw = os.getenv("RABBITMQ_PW")
        self.queue_name = 'ev_info_save_queue'
        self.openai_api_key = os.getenv("OPENAI_API_KEY")

        # Initialize Supabase client
        self.supabase_client = create_client(supabase_url, supabase_key)
        self.tools = [
            Tool.from_function(self.save_to_db, name="save_to_db", description="충전을 한 경우에만 동작. 전기차 충전정보를 입력받으면 다른 내용 붙이지 말고 '충전량=, 손실량=, 충전가격=' 정보로만 정리하여 저장")
        ]

    def start_service(self):
        # Set up RabbitMQ connection and start consuming
        credentials = pika.PlainCredentials(self.rabbitmq_id, self.rabbitmq_pw)
        connection = pika.BlockingConnection(pika.ConnectionParameters(
            host=self.rabbitmq_host,
            port=self.rabbitmq_port,
            credentials=credentials
        ))
        channel = connection.channel()
        channel.queue_declare(queue=self.queue_name, durable=True)
        channel.basic_consume(queue=self.queue_name, on_message_callback=self.on_message, auto_ack=False)

        print("Waiting for messages...")
        channel.start_consuming()

    def on_message(self, channel, method, properties, body):
        # Decode and process the message
        message = body.decode()
        response = self.process_with_llm(message)
        print("Response:", response)
        channel.basic_ack(delivery_tag=method.delivery_tag)  # 메시지 처리 완료 후 ACK

    def save_to_db(self, datas: str):
        """충전을 한 경우에만 동작. 전기차 충전정보를 입력받으면 다른 내용 붙이지 말고 '충전량=, 손실량=, 충전가격=' 정보로만 정리하여 저장"""
        response = self.supabase_client.table("charge_info").insert({"datas":datas}).execute()
        return "데이터 등록" if response.data else "등록 실패"
    
    def process_with_llm(self, message: str) -> dict:
        # Initialize LLM with prompt
        llm = ChatOpenAI(model="gpt-3.5-turbo")

        # 에이전트 초기화
        agent_executor = initialize_agent(
            tools=self.tools,
            llm=llm,
            agent_type=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
            #max_iterations=1,
            verbose=True
        )
        
        # 에이전트 호출
        ai_response = agent_executor({"input": message})
        print("AI Response:", ai_response)
        return ai_response

# Instantiate and start the microservice
if __name__ == "__main__":
    microservice = DataExtractorMicroservice()
    microservice.start_service()