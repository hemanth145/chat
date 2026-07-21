import asyncio
import sys

sys.stdout.reconfigure(encoding="utf-8")

from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage

llm = ChatOllama(model="gemma4:e2b", reasoning=True, num_predict=500, temperature=0.7) 

prompt_template = ChatPromptTemplate.from_messages([
    ("system", "You are a helpful, concise, and witty Travel assistant. "
    "***If users asks anything out of travelling deny with polite msg"
    " Your name is Ruby"),
    MessagesPlaceholder(variable_name="chat_history"),
    ("human", "{user_input}")
])

# 3. Create the LangChain Runnable Sequence (Chain)
chain = prompt_template | llm

async def main():
    # Local memory buffer to hold the session history
    chat_history = []
    tokens_spent = {
        "input": 0,
        "output": 0
    }
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
        reasoning_content = ""
        total_duration = 0
        total_tokens = ""
        
        # 4. Use astream to process the input concurrently
        async for chunk in chain.astream({
            "user_input": user_input,
            "chat_history": chat_history
        }):
            # Handle both string chunks (Ollama LLM) and message chunks (ChatOllama)
            # content = chunk.content if hasattr(chunk, 'content') else chunk
            
            # # Print the token immediately without buffering
            # print(content, end="", flush=True)
            # full_response += content
            if chunk.additional_kwargs.get('reasoning_content'):
                reasoning_content += chunk.additional_kwargs.get('reasoning_content') # type: ignore
                # print(chunk.additional_kwargs.get('reasoning_content'), end="")
            elif not chunk.response_metadata.get('created_at'):
                print(chunk.content, end="", flush=True)
                full_response += chunk.content
                # print(chunk.response_metadata)
            else:
                metadata = chunk.response_metadata
                usage = chunk.usage_metadata
                print("\n")
                seconds = metadata.get('total_duration') / 1000000000 
                total_duration += seconds
                total_tokens = f"{usage.get('output_tokens')} + {usage.get('input_tokens')}"
                tokens_spent["input"] += usage.get('input_tokens')
                tokens_spent["output"] += usage.get('output_tokens')
                print(f"Timetaken: {seconds} seconds, reason: {metadata.get('done_reason')}")
                print(f"Output tokens: {usage.get('output_tokens')}, input tokens: {usage.get('input_tokens')}")
                print(f"Total tokens spent so far: {tokens_spent['input']} input + {tokens_spent['output']} output = {tokens_spent['input'] + tokens_spent['output']} total")
            
        print() # Print a final newline after the full stream finishes
        
        # 5. Update history with both turns so the model remembers next time
        chat_history.append(HumanMessage(content=user_input))
        chat_history.append(AIMessage(content=full_response))

if __name__ == "__main__":
    # Run the async event loop for the CLI
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Session ended.")