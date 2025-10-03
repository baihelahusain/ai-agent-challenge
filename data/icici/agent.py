import os
from dotenv import load_dotenv
import argparse
import subprocess
import importlib.util
import pandas as pd
from pathlib import Path
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import ChatPromptTemplate

# gemini setup
load_dotenv()
llm = ChatGoogleGenerativeAI(model="gemini-2.5-pro")  

# prompt
parser_prompt = ChatPromptTemplate.from_messages([
    ("system", "You are an AI coding agent that writes custom PDF parsers for bank statements."),
    ("user", """Write a Python file {parser_path} with a function:
    
def parse(pdf_path) -> pd.DataFrame

Requirements:
1. Use pdfplumber or PyPDF2 to extract text.
2. Parse transactions into columns matching {csv_path}.
3. Return a pandas DataFrame with the same schema as {csv_path}.
4. Include typing, docstrings, clean code.
""")
])