# Import necessary modules
import streamlit as st
import requests
import uuid
import json
import os
from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment variables
load_dotenv("./config/.env")
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(supabase_url, supabase_key)

# Fetch agent information from Supabase
try:
    agent_get = supabase.table('agent_info')\
        .select('agent_id', 'name')\
        .eq('is_superviser', False)\
        .execute()

    agents = agent_get.data if agent_get.data else []  # Use .data instead of .get("data")
    
except Exception as e:
    st.error(f"Error fetching agents: {e}")
    agents = []

# Title
st.title("Essences")

# Input field for user requests
user_input = st.text_input("요청을 입력하세요:")

# Send button
if st.button("전송"):
    if user_input:
        # Define API URL and create unique request ID
        api_url = "http://localhost:8000/request"
        request_id = uuid.uuid4()

        payload = {
            "request_id": str(request_id),
            "request": user_input
        }

        # Send request to the API
        try:
            response = requests.post(api_url, json=payload)
            res = {}
            try:
                res = response.json()  # Attempt to parse the response as JSON
            except ValueError:
                st.error("응답을 JSON으로 파싱하는 중에 문제가 발생했습니다.")
                st.write("응답 내용:", response.text)  # Show raw response content for debugging

            if isinstance(res, str):
                res = json.loads(res)

            agent_list = res.get("agent_list", [])
            response_text = res.get("response", "")

            st.subheader("응답한 Agent")

            for agent in agent_list:
                for ag in agents:
                    if (ag.get("agent_id", "") == agent):
                        st.markdown(f"""
                            <span style='font-size:24px; color:red;'>{ag.get("name", "")}</span>
                        """, unsafe_allow_html=True)

            # Display response as Markdown
            st.subheader("Response")
            st.markdown(res.get("response", ""), unsafe_allow_html=True)
            
        except requests.exceptions.HTTPError as errh:
            st.error(f"HTTP 에러가 발생했습니다: {errh}")
        except requests.exceptions.ConnectionError as errc:
            st.error(f"연결 에러가 발생했습니다: {errc}")
        except requests.exceptions.Timeout as errt:
            st.error(f"타임아웃 에러가 발생했습니다: {errt}")
        except requests.exceptions.RequestException as err:
            st.error(f"요청 에러가 발생했습니다: {err}")
    else:
        st.warning("요청을 입력해주세요.")

# Display available agents
st.markdown("<hr>", unsafe_allow_html=True)
st.subheader("사용 가능한 Agent List")
for agent in agents:
    agent_id = agent.get("agent_id", "")
    name = agent.get("name", "")
    st.markdown(f"""
        - **Name:** <span style='font-size:20px;'>{name}</span>, **Agent ID:** <span style='font-size:20px;'>{agent_id}</span>
    """, unsafe_allow_html=True)