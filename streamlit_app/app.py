import streamlit as st
from groq import Groq

MODEL = "llama-3.3-70b-versatile"
SYSTEM_PROMPT = "You are a helpful, concise, and witty chat assistant. Your name is Ruby."

st.set_page_config(page_title="Chat with Ruby", page_icon="💬")
st.title("💬 Chat with Ruby")

client = Groq(api_key=st.secrets["GROQ_API_KEY"])

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if user_input := st.chat_input("Say something..."):
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        api_messages = [{"role": "system", "content": SYSTEM_PROMPT}] + st.session_state.messages
        stream = client.chat.completions.create(
            model=MODEL,
            messages=api_messages,
            temperature=0.7,
            stream=True,
        )

        def token_stream():
            for chunk in stream:
                yield chunk.choices[0].delta.content or ""

        full_response = st.write_stream(token_stream())

    st.session_state.messages.append({"role": "assistant", "content": full_response})
