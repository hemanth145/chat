import os

import gradio as gr
from groq import Groq

client = Groq(api_key=os.environ["GROQ_API_KEY"])

MODEL = "llama-3.3-70b-versatile"

SYSTEM_PROMPT = "You are a helpful, concise, and witty chat assistant. Your name is Ruby."


def respond(message, history):
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for user_msg, bot_msg in history:
        messages.append({"role": "user", "content": user_msg})
        if bot_msg:
            messages.append({"role": "assistant", "content": bot_msg})
    messages.append({"role": "user", "content": message})

    stream = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        temperature=0.7,
        stream=True,
    )

    partial = ""
    for chunk in stream:
        delta = chunk.choices[0].delta.content or ""
        partial += delta
        yield partial


demo = gr.ChatInterface(
    fn=respond,
    title="Chat with Ruby",
    description="A witty AI assistant powered by Groq (Llama 3.3 70B).",
)

if __name__ == "__main__":
    demo.launch()
