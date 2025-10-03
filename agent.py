import os
import re
import argparse
import subprocess
import pandas as pd
from pathlib import Path
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import ChatPromptTemplate

load_dotenv()
llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash-exp", temperature=0.1)

def extract_code(text: str) -> str:
    """Extract Python code from markdown blocks."""
    for pattern in [r"```python\n(.*?)```", r"```\n(.*?)```"]:
        match = re.findall(pattern, text, re.DOTALL)
        if match: return match[0].strip()
    return text.strip()

def create_csv(pdf_path: Path, csv_path: Path):
    """Generate CSV ground truth from PDF."""
    if csv_path.exists(): return
    
    import pdfplumber
    transactions = []
    
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            for line in page.extract_text().split('\n'):
                parts = line.split()
                if len(parts) >= 3 and re.match(r'\d{2}-\d{2}-\d{4}', parts[0]):
                    date = parts[0]
                    numbers = [p for p in parts if re.match(r'^\d+\.?\d*$', p)]
                    if len(numbers) >= 2:
                        desc = ' '.join(parts[1:-len(numbers)])
                        if len(numbers) == 2:
                            amt, bal = float(numbers[0]), float(numbers[1])
                            is_credit = any(w in desc.lower() for w in ['credit', 'salary', 'deposit', 'interest', 'transfer from'])
                            deb, cred = ('', amt) if is_credit else (amt, '')
                        else:
                            deb, cred, bal = float(numbers[0]), float(numbers[1]), float(numbers[2])
                        transactions.append({'Date': date, 'Description': desc, 'Debit Amt': deb, 'Credit Amt': cred, 'Balance': bal})
    
    pd.DataFrame(transactions).to_csv(csv_path, index=False)
    print(f"✓ Created CSV with {len(transactions)} transactions")

def run_tests() -> tuple[int, str]:
    """Run pytest and return exit code + output."""
    result = subprocess.run(["pytest", "test_parser.py", "-v"], capture_output=True, text=True)
    return result.returncode, result.stdout + result.stderr

def generate_code(parser_path: Path, csv_path: Path, prev_code: str = None, errors: str = None) -> str:
    """Generate or fix parser code using LLM."""
    if prev_code is None:
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are an expert Python developer. Write clean, typed code with docstrings."),
            ("user", """Create {parser_path} with function: def parse(pdf_path: str) -> pd.DataFrame

Requirements:
1. Use pdfplumber to extract PDF text
2. Parse transactions: Date, Description, Debit Amt, Credit Amt, Balance
3. Each transaction has EITHER debit OR credit (empty string for missing)
4. Match schema in {csv_path}
5. Handle edge cases

Parsing rules:
- Date: DD-MM-YYYY format
- Lines have 2-3 numbers at end (amount(s) + balance)
- Credit keywords: credit, salary, deposit, interest, transfer from
- Description: text between date and numbers

Write ONLY Python code, no explanations.""")
        ])
        messages = prompt.format_messages(parser_path=str(parser_path), csv_path=str(csv_path))
    else:
        prompt = ChatPromptTemplate.from_messages([
            ("system", "Debug the parser and fix all errors."),
            ("user", "Parser failed with:\n{errors}\n\nPrevious code:\n```python\n{prev_code}\n```\n\nFix and return complete corrected code only.")
        ])
        messages = prompt.format_messages(errors=errors, prev_code=prev_code)
    
    response = llm.invoke(messages)
    return extract_code(response.content if hasattr(response, 'content') else str(response))

def main():
    parser = argparse.ArgumentParser(description="AI agent for bank statement parsers")
    parser.add_argument("--target", required=True, help="Bank name (e.g., icici)")
    args = parser.parse_args()
    
    # Setup paths
    bank = args.target.lower()
    data_dir = Path(f"data/{bank}")
    parser_path = Path(f"custom_parsers/{bank}_parser.py")
    pdf_path = data_dir / f"{bank}_sample.pdf"
    csv_path = data_dir / f"{bank}_sample.csv"
    
    # Validate and prepare
    if not pdf_path.exists():
        print(f"❌ PDF not found: {pdf_path}")
        return
    
    parser_path.parent.mkdir(parents=True, exist_ok=True)
    create_csv(pdf_path, csv_path)
    
    print(f"\n{'='*60}")
    print(f"🤖 AI Agent: Parser Generator for {bank.upper()}")
    print(f"{'='*60}\n")
    
    # Agent loop: Plan → Generate → Test → Refine
    prev_code, errors = None, None
    for attempt in range(1, 4):
        print(f"🔄 Attempt {attempt}/3")
        
        # Generate
        print("📝 Generating code...")
        code = generate_code(parser_path, csv_path, prev_code, errors)
        parser_path.write_text(code)
        print(f"✓ Saved to {parser_path}")
        
        # Test
        print("🧪 Testing...")
        exit_code, logs = run_tests()
        print(logs)
        
        if exit_code == 0:
            print(f"\n{'='*60}")
            print("✅ SUCCESS! Parser works.")
            print(f"{'='*60}")
            print(f"Use: from custom_parsers.{bank}_parser import parse")
            return
        
        # Refine
        print(f"⚠️  Failed (exit {exit_code})")
        prev_code, errors = code, logs
        if attempt < 3:
            print("🔧 Refining...\n")
    
    print(f"\n{'='*60}")
    print("❌ Failed after 3 attempts. Check logs above.")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
