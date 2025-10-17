import argparse
import base64
import io
import json
import os
import re
from pathlib import Path

import pdfplumber
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from utils import key_utils, pdf_utils

app = FastAPI(title="Booking Confirmation PDF Parser API")

class PDFPayload(BaseModel):
    filename: str = Field(..., description="Original filename (for logging)")
    data_base64: str = Field(..., description="Base64-encoded PDF bytes")

def _is_pdf(data: bytes) -> bool:
    # PDF files start with "%PDF-" magic header
    return data.startswith(b"%PDF-")


def run(pdf_raw):
    # Open with pdfplumber (use BytesIO wrapper)
    pdf = pdfplumber.open(io.BytesIO(pdf_raw))

    # Use pdfplumber to extract the word in every pages
    page_words = [page.extract_words(use_text_flow=True) for page in pdf.pages]

    print(f"Reading PDF with {len(page_words)} page(s).")

    # Find common header and footer
    header_word_count = pdf_utils.count_common_header(page_words)
    footer_word_count = pdf_utils.count_common_footer(page_words)

    # Remove Header and footer, only content
    page_words_content = [
        page[header_word_count : len(page) - footer_word_count] for page in page_words
    ]

    # Commind all page content
    combined_content = pdf_utils.combine_content(page_words_content)

    # First merge: Merge by spacebar
    sentence_list_temp1 = pdf_utils.horizontal_merge(
        combined_content, space_tolerance_ratio=0.5, height_tolerance_ratio=0.75
    )

    # Second merge: Multi line Merge
    sentence_list_temp2 = pdf_utils.vertical_merge(
        sentence_list_temp1, height_tolerance_ratio=0.1, x_start_tolerance_ratio=5
    )

    # Table Merge
    sentence_list_table = pdf_utils.table_merge(sentence_list_temp2)

    # Third merge: Non-spacebar merge
    sentence_list_merged = pdf_utils.horizontal_merge(
        sentence_list_temp2,
        merging_string="|",
        space_tolerance_ratio=8,
        height_tolerance_ratio=0.75,
    )

    # Translate
    # create key map from json file
    key_map, all_keys, all_keys_variance = key_utils.create_key_map(
        "label.json", key_type="normal"
    )
    table_key_map, all_table_keys, all_table_keys_variance = key_utils.create_key_map(
        "label.json", key_type="table"
    )

    # Init normal_dict (all keys with value = empty list)
    normal_dict = dict([(k, []) for k in all_keys])

    for sentence in sentence_list_merged:

        # Split each line based on the keys
        tab_split_data = key_utils.tab_split(sentence["text"], all_keys_variance)

        for t in tab_split_data:
            key_variance, value = key_utils.key_split(t, all_keys_variance)

            if key_variance is not None and len(value) > 0:
                normal_dict[key_map[key_variance]].append(value)

    all_table_list = []
    for tb in sentence_list_table:
        if len(tb) <= 1:
            continue

        header_row = tb[0]

        # Check if all header is in desired key
        header_matched_keys = [
            key_utils.match_key(
                header_col["text"],
                key_list=all_table_keys_variance,
                matching_threhold=90,
            )[0]
            for header_col in header_row
        ]

        if any(h is None for h in header_matched_keys):
            # If any is not in table key, skip
            continue
        header_keys = [table_key_map[hk] for hk in header_matched_keys]

        table_content_rows = tb[1:]
        table_content_texts = []
        for table_content_row in table_content_rows:
            table_content_texts.append([c["text"] for c in table_content_row])

        table_dict = {"header": header_keys, "content": table_content_texts}
        all_table_list.append(table_dict)

    # Init output_dict
    output_dict = dict([("normal", normal_dict), ("table", all_table_list)])
    return output_dict


@app.post("/pdf/run")
def pdf_size(payload: PDFPayload):
    # 1) decode
    try:
        raw = base64.b64decode(payload.data_base64, validate=True)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid base64 data")

    # 2) basic validation
    if not _is_pdf(raw):
        raise HTTPException(status_code=400, detail="Decoded data is not a PDF (missing %PDF- header)")

    # 3) Run
    size_bytes = len(raw)
    size_kb = round(size_bytes / 1024, 2)
    size_mb = round(size_bytes / (1024 * 1024), 2)

    output  = run(pdf_raw=raw)
    output['format'] = payload.filename

    return output