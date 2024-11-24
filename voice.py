import streamlit as st
import speech_recognition as sr

def recognize_speech():
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        st.info("음성을 입력하세요...")
        audio_data = recognizer.listen(source)
        try:
            text = recognizer.recognize_google(audio_data, language="ko-KR")
            st.success("음성 인식 성공!")
            return text
        except sr.UnknownValueError:
            st.error("음성을 이해할 수 없습니다.")
        except sr.RequestError:
            st.error("음성 인식 서비스에 연결할 수 없습니다.")
    return ""

st.title("Streamlit 음성 인식 예제")
st.write("음성을 입력하면 텍스트로 변환합니다.")

if st.button("음성 입력"):
    result_text = recognize_speech()
    if result_text:
        st.write("인식된 텍스트:", result_text)