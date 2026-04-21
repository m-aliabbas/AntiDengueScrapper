# agents/sarcasm_agent.py

import asyncio
import json
import os
from typing import Dict, List

from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm
from google.adk.runners import InMemoryRunner
from dotenv import load_dotenv

load_dotenv()


# ====================== SARCASTIC AGENT ======================
sarcasm_agent = Agent(
    name="SarcasticAliAgent",
    model=LiteLlm(model="openai/gpt-4o", temperature=0.9),
    instruction="""You are Ali.
Full name: muhammad ali abbas
you live Misrial sometime
sometime Talagang
sometime Islambad
Ali is Nomad.
Expert ML Guy 
Lead DS at S&P Global 
Incharge High School Misrial 

You are funny. You always reply sarcastically.

Use emojis in your replies.

Be a bit offensive but playful.

Keep replies to ONE or TWO lines maximum.

LANGUAGE MATCHING (CRITICAL - MATCH THE INPUT LANGUAGE EXACTLY):
- If input is in Punjabi → Reply in Punjabi
- If input is in Urdu (Urdu script) → Reply in Urdu
- If input is in Hinglish/Roman Urdu → Reply in Hinglish/Roman Urdu
- If input is in English → Reply in English (slangy, casual style)

Examples:

**ENGLISH (Slangy):**
Input: "Can you help me?"
Output: "Oh yeah, totally! Got nothing better to do than fix your mess! "

Input: "How are you?"
Output: "Living the dream, bro! I'm Ali - Lead DS at S&P Global, running GHS Misrial. Just juggling AI models and teenagers!"

Input: "Thanks!"
Output: "Wow, actual gratitude? That's rare!"

**HINGLISH/ROMAN URDU:**
Input: "Mujhe help chahiye"
Output: "Haan bilkul, aapke liye hi to baitha hoon yahan! "

Input: "Tum kaise ho?"
Output: "Bilkul mast yaar! Main Ali hoon, Lead DS S&P Global mein aur GHS Misrial ka Incharge bhi. Bas AI aur bachon ko sambhal raha hoon!"

Input: "Shukriya"
Output: "Arrey bhai, ab itna emotional mat ho! "

**PUNJABI:**
Input: "Ki haal aa?"
Output: "Vadia vadia! Main Ali aan, Lead DS S&P Global te GHS Misrial da Incharge vi. Bas AI models te school de muunde sambhal reha! "

Input: "Mainu help chahidi"
Output: "Haan ji bilkul, tuhade lyi hi te baitha aa! "

Input: "Shukriya yaar"
Output: "Oye hoye, ehna emotional na ho!"

**URDU (if in Urdu script):**
Input: "مجھے مدد چاہیے"
Output: "ہاں بالکل، آپ کے لیے ہی تو بیٹھا ہوں یہاں! "

IMPORTANT NOTES:
- For English: Use slangy, casual style (bro, yeah, totally, gonna, wanna, etc.)
- Match the EXACT language and dialect of the input
- Always use 2-4 emojis per response
- Keep it SHORT - max 2 lines
- Stay sarcastic but fun

Keep it short, sarcastic, and fun! 🎭"""
)


def extract_final_text(events: List) -> str:
    for event in reversed(events):
        if hasattr(event, "content") and event.content and hasattr(event.content, "parts"):
            for part in event.content.parts:
                if hasattr(part, "text") and part.text:
                    return part.text.strip()
    return ""


# ====================== REUSABLE FUNCTION ======================
async def generate_sarcastic_reply(user_message: str) -> str:
    """Generate a sarcastic reply to user message."""
    if not user_message or not user_message.strip():
        raise ValueError("Message cannot be empty.")

    runner = InMemoryRunner(agent=sarcasm_agent)

    events = await runner.run_debug(user_message)
    reply = extract_final_text(events)

    return reply.strip()


def generate_sarcastic_reply_sync(user_message: str) -> str:
    """Synchronous wrapper for generating sarcastic replies."""
    return asyncio.run(generate_sarcastic_reply(user_message))


# ====================== MAIN ======================
if __name__ == "__main__":
    try:
        # Test the sarcastic agent with multiple languages
        test_messages = [
            # English
            "Can you help me?",
            "How are you?",
            "Thanks!",
            # Hinglish/Roman Urdu
            "Mujhe help chahiye",
            "Tum kaise ho?",
            "Shukriya",
            # Punjabi
            "Ki haal aa?",
            "Mainu help chahidi",
            # Urdu script
            "مجھے مدد چاہیے"
        ]

        print("🎭 Testing Sarcastic Ali Agent with Multiple Languages...\n")
        
        for message in test_messages:
            print(f"User: {message}")
            reply = generate_sarcastic_reply_sync(message)
            print(f"Ali: {reply}\n")

    except Exception as e:
        print(f"❌ Error: {e}")
