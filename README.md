# ai-agent-challenge
**Coding agent challenge which write custom parsers for Bank statement PDF.**

---

## 5-Step Run Instructions


```bash
1️. Create and activate a virtual environment
python -m venv venv
# Windows
venv\Scripts\activate

2️. Install project dependencies
pip install -r requirements.txt

3️. Set up your Gemini API key
# in a .env file or environment variable
GOOGLE_API_KEY=your_api_key_here

4️. Generate a parser for a bank
python agent.py --target icici

5️. Verify the generated parser
pytest tests/test_parser.py -v
```
---

## Architecture Diagram
![Agent Architecture](assets/flowchart.drawio.svg)
