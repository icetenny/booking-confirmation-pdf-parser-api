import base64
import json
import os
from pathlib import Path

import requests

BASE = "http://127.0.0.1:8000"

def send_pdf(path: str):
    p = Path(path)
    data = p.read_bytes()
    payload = {
        "filename": p.name,
        "data_base64": base64.b64encode(data).decode("ascii")
    }
    r = requests.post(f"{BASE}/pdf/run", json=payload, timeout=20)
    r.raise_for_status()
    print(r.json())
    return r.json()

def save_json(json_dict, filename="output.json"):
        output_filename = os.path.join(
            "output", filename
        )
        with open(output_filename, "w", encoding="utf-8") as f:
            json.dump(json_dict, f, indent=4, ensure_ascii=False)

        print(f"Write JSON Output to: {output_filename}")

if __name__ == "__main__":
    # replace with your PDF path
    output_json = send_pdf("pdfs/BookingConfirm-SE.pdf")

    save_json(output_json)
