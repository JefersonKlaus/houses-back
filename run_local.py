import json
import os
import sys
from pathlib import Path


# Preencha apenas os valores necessários para o evento escolhido.
ENVIRONMENT = {
    "GROQ_API_KEY": "",
    "GROQ_MODEL": "meta-llama/llama-4-scout-17b-16e-instruct",
    "TWILIO_ACCOUNT_SID": "",
    "TWILIO_AUTH_TOKEN": "",
    "GOOGLE_SHEET_ID": "",
    "GOOGLE_CREDENTIALS_JSON": "",
    "GOOGLE_SHEET_WORKSHEET": "",
}


ROOT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT_DIR / "src"))

for name, value in ENVIRONMENT.items():
    if value:
        os.environ[name] = value

import function


def main() -> None:
    event_path = ROOT_DIR / "tests" / "local_event.json"
    with event_path.open(encoding="utf-8") as event_file:
        event = json.load(event_file)

    result = function.lambda_handler(event, None)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
