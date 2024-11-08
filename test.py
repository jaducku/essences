import requests
import uuid
url = "http://localhost:8000/request"

request_id = uuid.uuid4()

data = {
    "request_id": str(request_id),
    "request": "결혼을 할 예정이야. 5000만원으로 하객 200명 정도를 초대할 수 있는 강남권 예식장을 추천해줘. 신혼집은 3억정도하는 서울 아파트 전세에 살고 싶어. 신혼여행은 이탈리아로 갈꺼고 예산은 2000만원이야."
}

response = requests.post(url, json=data)
print(response.json())

