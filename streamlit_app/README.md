# Chat with Ruby (Streamlit)

🔗 **Live app:** https://hemanth145-chat-streamlit-appapp-nbdvbl.streamlit.app

A witty AI chat assistant, powered by Groq's free hosted Llama 3.3 70B API. Deployed on Streamlit Community Cloud.

## Run locally

```
pip install -r requirements.txt
streamlit run app.py
```

Requires a `GROQ_API_KEY` secret (get one free at https://console.groq.com/keys). For local runs, put it in `.streamlit/secrets.toml`:

```toml
GROQ_API_KEY = "your-key-here"
```
