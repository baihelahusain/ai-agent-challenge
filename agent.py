import os
import re
import argparse
import subprocess
import pandas as pd
from pathlib import Path
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import ChatPromptTemplate
import pdfplumber
#gemini api
load_dotenv()
llm = ChatGoogleGenerativeAI(model="gemini-2.5-pro", temperature=0.1)

def extract_code(text: str) -> str:
    """Extract Python code from markdown blocks."""
    for pattern in [r"```python\n(.*?)```", r"```\n(.*?)```"]:
        match = re.findall(pattern, text, re.DOTALL)
        if match: return match[0].strip()
    return text.strip()

def create_csv(pdf_path: Path, csv_path: Path):
    if csv_path.exists(): 
        print(f" CSV already exists at {csv_path}")
        return
    
    transactions = []
    
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            lines = [line for line in text.split('\n') 
                    if line and 'ChatGPT' not in line and 'Karbon' not in line 
                    and not line.startswith('Date Description')]
            
            for line in lines:
                parts = line.split()
                # Match date pattern
                if len(parts) >= 3 and re.match(r'\d{2}-\d{2}-\d{4}', parts[0]):
                    date = parts[0]
                    
                    numbers = []
                    for p in parts[1:]:
                        if re.match(r'^-?\d+\.?\d*$', p):
                            numbers.append(p)
                    
                    if len(numbers) >= 2:
                        desc_parts = []
                        found_first_num = False
                        for p in parts[1:]:
                            if re.match(r'^-?\d+\.?\d*$', p):
                                found_first_num = True
                                break
                            desc_parts.append(p)
                        
                        desc = ' '.join(desc_parts)
                        
                        if len(numbers) == 2:
                            amt = float(numbers[0])
                            bal = float(numbers[1])
                            
                            credit_keywords = ['credit', 'salary', 'deposit', 'interest', 
                                             'transfer from', 'neft transfer from']
                            is_credit = any(kw in desc.lower() for kw in credit_keywords)
                            
                            if is_credit:
                                deb, cred = '', amt
                            else:
                                deb, cred = amt, ''
                        else:
                            deb = float(numbers[0]) if numbers[0] != '' else ''
                            cred = float(numbers[1]) if numbers[1] != '' else ''
                            bal = float(numbers[2])
                        
                        transactions.append({
                            'Date': date,
                            'Description': desc,
                            'Debit Amt': deb,
                            'Credit Amt': cred,
                            'Balance': bal
                        })
    
    df = pd.DataFrame(transactions)
    df.to_csv(csv_path, index=False)
    print(f" Created CSV with {len(transactions)} transactions")
#Test:
def run_tests(bank: str) -> tuple[int, str]:
    """Run pytest with environment variable for target bank."""
    env = os.environ.copy()
    env['TARGET_BANK'] = bank
    result = subprocess.run(
        ["pytest", "tests/test_parser.py", "-v", "--tb=short"],
        capture_output=True,
        text=True,
        env=env
    )
    return result.returncode, result.stdout + result.stderr
#Prompt:
def generate_code(parser_path: Path, csv_path: Path, prev_code: str = None, errors: str = None) -> str:
    """Generate or fix parser code using LLM."""
    if prev_code is None:
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are an expert Python developer. Write clean, typed code with docstrings."),
            ("user", """Create {parser_path} with function: def parse(pdf_path: str) -> pd.DataFrame

Requirements:
1. Use pdfplumber to extract PDF text
2. Parse bank statement transactions: Date, Description, Debit Amt, Credit Amt, Balance
3. Each transaction has EITHER debit OR credit (empty string '' for missing)
4. Match exact schema in {csv_path}
5. Handle negative balances (e.g., -566.45, -3183.95)
6. Skip header/footer lines containing 'ChatGPT', 'Karbon', 'Date Description'

Parsing rules:
- Date format: DD-MM-YYYY at start of line
- Balance can be negative (with minus sign)
- Numbers pattern: amount + balance (2 numbers) OR debit + credit + balance (3 numbers)
- Credit keywords: 'credit', 'salary', 'deposit', 'interest', 'transfer from'
- Description: all text between date and first number
- CRITICAL: Return DataFrame with columns exactly as: Date, Description, Debit Amt, Credit Amt, Balance

Write ONLY Python code, no explanations. Make sure to handle all edge cases.""")
        ])
        messages = prompt.format_messages(parser_path=str(parser_path), csv_path=str(csv_path))
    else:
        prompt = ChatPromptTemplate.from_messages([
            ("system", "Debug the parser and fix all errors."),
            ("user", """Parser failed with:\n{errors}\n\nPrevious code:\n```python\n{prev_code}\n```\n\nCommon issues to check:
1. Are you handling negative balances? (e.g., -566.45)
2. Are you skipping header/footer lines?
3. Is the DataFrame column order exactly: Date, Description, Debit Amt, Credit Amt, Balance?
4. Are empty debit/credit values set as empty string '' not 0 or NaN?
5. Are you parsing ALL transactions (should be 95 total)?

Fix and return complete corrected code only.""")
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
        print(f"X PDF not found: {pdf_path}")
        return
    
    parser_path.parent.mkdir(parents=True, exist_ok=True)
    Path("tests").mkdir(exist_ok=True)
    
    if csv_path.exists():
        print(f" Regenerating CSV to fix any issues...")
        csv_path.unlink()
    
    create_csv(pdf_path, csv_path)
    
    # Verify CSV row count
    expected_df = pd.read_csv(csv_path)
    print(f" Expected {len(expected_df)} transactions in CSV")
    print(f"\n{'='*60}")
    print(f" AI Agent: Parser Generator for {bank.upper()}")
    print(f"{'='*60}\n")
    
    # Agent loop: Generate → Test → Refine
    prev_code, errors = None, None
    for attempt in range(1, 4):
        print(f" Attempt {attempt}/3")
        
        # Generate
        print("Wait Generating code...")
        code = generate_code(parser_path, csv_path, prev_code, errors)
        parser_path.write_text(code)
        print(f" Saved to {parser_path}")
        
        # Test
        print(" Testing...")
        exit_code, logs = run_tests(bank)
        print(logs)
        
        if exit_code == 0:
            print(f"\n{'='*60}")
            print(" SUCCESS! Parser works.")
            print(f"{'='*60}")
            print(f" Parsed all {len(expected_df)} transactions correctly")
            print(f"Use: from custom_parsers.{bank}_parser import parse")
            return
        
        # Refine
        print(f"  Failed (exit {exit_code})")
        prev_code, errors = code, logs
        if attempt < 3:
            print("Wait Refining...\n")
    
    print(f"\n{'='*60}")
    print("XXX Failed after 3 attempts. Check logs above.")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
