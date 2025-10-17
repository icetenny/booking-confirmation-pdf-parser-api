import argparse
import json
import os
import re
from pathlib import Path

import pdfplumber

from utils import key_utils, pdf_utils


def main(args):
    if not os.path.exists(args.filename):
        print("File path does not exist")
        return

    # Read PDF
    pdf = pdfplumber.open(args.filename)

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

    # Print output_dict
    for k, v in output_dict["normal"].items():
        print(f"{k}   {v}")
    print("\n")

    for table in output_dict["table"]:
        print(table["header"])
        print()
        for content_row in table["content"]:
            print(content_row)

    if args.write_json:
        # make new filename with .json extension
        file_path = Path(args.filename)
        output_filename = os.path.join(
            "output", file_path.stem + ".json"
        )  # "BookingConfirm-SE.json"

        with open(output_filename, "w", encoding="utf-8") as f:
            json.dump(output_dict, f, indent=4, ensure_ascii=False)

        print(f"Write JSON Output to: {output_filename}")


if __name__ == "__main__":
    # Parse Filename
    parser = argparse.ArgumentParser(description="Process a file name.")
    parser.add_argument(
        "filename",
        nargs="?",
        help="The name of the file to process",
        default="pdfs/BookingConfirm-SE.pdf",
    )
    parser.add_argument("--write-json", action="store_true", help="Write JSON output")
    args = parser.parse_args()

    main(args=args)
