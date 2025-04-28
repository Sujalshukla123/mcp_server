import os
from agents import Agent, Runner


with open("api.txt", "r") as f:
    api_key = f.read().strip()
os.environ["OPENAI_API_KEY"] = api_key


agent = Agent(
    name="Personal Agent",
    instructions="You are a helpful assistant. Use the realtime data",
    model="gpt-4o"
)
user_input = input("ask agent :")

result = Runner.run_sync(agent, user_input)


print("\nAgent Response:")
print(result.final_output)
