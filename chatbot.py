import asyncio
import sys

# Must run before anything prints so emoji output works on Windows consoles
sys.stdout.reconfigure(encoding="utf-8")

from langchain_ollama import ChatOllama  # noqa: E402
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder  # noqa: E402
from langchain_core.messages import HumanMessage, AIMessage  # noqa: E402

llm = ChatOllama(model="gemma3:1b", num_predict=50, temperature=0.7) 

# Set to True to send past turns to the model so it remembers the conversation
USE_MEMORY = False

prompt_template = ChatPromptTemplate.from_messages([
    ("system", "You are a helpful, concise, and witty CLI assistant. Your name is Ruby"),
    MessagesPlaceholder(variable_name="chat_history"),
    ("human", "{user_input}")
])

# Create the LangChain Runnable Sequence (Chain)
chain = prompt_template | llm

async def main():
    # Local memory buffer to hold the session history
    chat_history = []
    
    print("=" * 60)
    print("🤖 CLI CHATBOT INITIALIZED (Type 'exit' or 'quit' to stop)")
    print("=" * 60)
    
    while True:
        # Get user input synchronously from the console
        try:
            user_input = input("\n👤 You: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n👋 Goodbye!")
            break
            
        if not user_input:
            continue
            
        if user_input.lower() in ['exit', 'quit']:
            print("🤖 Assistant: Goodbye! Have a great day.")
            break
        
        print("🤖 Assistant: ", end="", flush=True)
        
        # Track the streaming response tokens to rebuild the full text later
        full_response = ""
        
        # Stream the reply token by token as it is generated
        try:
            async for chunk in chain.astream({
                "user_input": user_input,
                "chat_history": chat_history if USE_MEMORY else []
            }):
                content = chunk.content
                # Print the token immediately without buffering
                print(content, end="", flush=True)
                full_response += content
        except Exception as e:
            print(f"\n⚠️ Error talking to Ollama (is `ollama serve` running and `gemma3:1b` pulled?): {e}")
            continue
            
        print() # Print a final newline after the full stream finishes
        
        # Update history with both turns (sent to the model when USE_MEMORY is True)
        chat_history.append(HumanMessage(content=user_input))
        chat_history.append(AIMessage(content=full_response))

if __name__ == "__main__":
    # Run the async event loop for the CLI
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Session ended.")