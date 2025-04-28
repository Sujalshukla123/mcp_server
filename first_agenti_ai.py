# main.py
import openai
import asyncio
import os

# Load your OpenAI key from a file (or use an environment variable)
with open("api.txt") as f:
    openai.api_key = f.read().strip()

async def writer_agent(topic):
    """Simulates the writer agent generating content."""
    response = await openai.ChatCompletion.acreate(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are a helpful writing assistant."},
            {"role": "user", "content": f"Write a short email on: {topic}"}
        ]
    )
    return response.choices[0].message.content.strip()

async def critic_agent(text):
    """Simulates the critic agent reviewing the content."""
    response = await openai.ChatCompletion.acreate(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are a helpful writing critic. Score grammar, style, and content from 0 to 10 and suggest improvements."},
            {"role": "user", "content": f"Please review the following email:\n\n{text}"}
        ]
    )
    return response.choices[0].message.content.strip()

async def main():
    prompt = "Write an email to my professor Jon asking to see my exam paper."
    
    # Writer creates first draft
    draft = await writer_agent(prompt)
    print("\n📄 Writer's Draft:\n", draft)
    
    # Critic reviews it
    feedback = await critic_agent(draft)
    print("\n📝 Critic's Feedback:\n", feedback)

if __name__ == "__main__":
    asyncio.run(main())
