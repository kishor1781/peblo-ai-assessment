import os
import json
os.environ['GEMINI_API_KEY'] = 'AIzaSyDl8Fpw34PsZqWEnkWYheMCv-eWZ1Nv6Yo'
from google import genai
from google.genai import types

client = genai.Client()

prompt = """You are an educational content expert generating quiz questions for students.
Given the following educational text, generate exactly 3 quiz questions.
RULES:
- Generate a MIX of the following types: MCQ, TrueFalse, FillBlank
- MCQ: 4 answer options (A, B, C, D), exactly one correct
- TrueFalse: options must be ["True", "False"]
- FillBlank: the question contains a blank represented by "___", answer is the missing word/phrase
- Difficulty: easy
- Questions MUST be based ONLY on the provided text
- Keep questions appropriate for the educational level indicated
- Answer must be the exact text of the correct option

EDUCATIONAL TEXT:
A triangle has three sides.

RESPOND WITH VALID JSON ONLY - an array of objects with this exact structure:
[
  {
    "question": "...",
    "type": "MCQ",
    "options": ["A. ...", "B. ...", "C. ...", "D. ..."],
    "answer": "B. ...",
    "difficulty": "easy"
  }
]
Return ONLY the JSON array. No markdown, no explanation."""

try:
    response = client.models.generate_content(
        model='gemini-2.0-flash',
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.4,
            top_p=0.9,
            max_output_tokens=2048,
        ),
    )
    print("RAW RESPONSE START")
    print(response.text)
    print("RAW RESPONSE END")
except Exception as e:
    print('ERROR:', e)
