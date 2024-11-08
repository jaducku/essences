import streamlit as st
import requests
import uuid


# 제목
st.title("Essences")

# 입력 필드
user_input = st.text_input("요청을 입력하세요:")

# 전송 버튼
if st.button("전송"):
    if user_input:
        # 여기에 호출하고자 하는 API의 URL을 입력하세요
        api_url = "http://localhost:8000/request"
        request_id = uuid.uuid4()

        data = {
            "request_id": str(request_id),
            "request": user_input
        }

        # API에 요청을 보낼 때 필요한 데이터나 파라미터를 설정합니다

        try:
            # API 요청 보내기
            response = requests.post(api_url, json=data)
            response.raise_for_status()  # 에러가 있으면 예외 발생

            # API 응답 가져오기
            data = response.json()

            # 화면에 응답 표시
            st.write("API 응답:")
            st.json(data)

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