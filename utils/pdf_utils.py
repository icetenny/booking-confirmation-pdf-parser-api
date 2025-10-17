from typing import Any, Dict, List, Tuple


def count_common_header(page_words: List[List[Dict[str, Any]]]) -> int:
    """
    Find how many consecutive words at the start of each page
    are identical (common header).

    Args:
        page_words (List[List[Dict[str, Any]]]):
            Pages extracted with `pdfplumber.Page.extract_words()`.

    Returns:
        int: Number of the common header
    """
    # If only one page, no common header
    if len(page_words) == 1:
        return 0

    header_word_count = 0

    # Loop through words at the same position across all pages
    while True:
        try:
            # Collect the nth word from each page
            nth_header_words = [
                page_word[header_word_count]["text"] for page_word in page_words
            ]
        except IndexError:
            # Stop checking if any page run out of word
            break

        # If all pages share the same word at this position,
        # increment the header count; otherwise stop
        if len(set(nth_header_words)) == 1:
            header_word_count += 1
        else:
            break

    return header_word_count


def count_common_footer(page_words: List[List[Dict[str, Any]]]) -> int:
    """
    Find how many consecutive words at the end of each page
    are identical (common footer).

    Args:
        page_words (List[List[Dict[str, Any]]]):
            Pages extracted with `pdfplumber.Page.extract_words()`.

    Returns:
        int: Number of the common footer
    """
    # If only one page, no common footer
    if len(page_words) == 1:
        return 0

    footer_word_count = 0

    # Loop backwards from the end of each page
    while True:
        try:
            # Collect the nth word from the end across all pages
            nth_footer_words = [
                page_word[-1 - footer_word_count]["text"] for page_word in page_words
            ]
        except IndexError:
            # Stop checking if any page run out of word
            break

        # If all pages share the same word at this position,
        # increment the footer count; otherwise stop
        if len(set(nth_footer_words)) == 1:
            footer_word_count += 1
        else:
            break

    return footer_word_count


def combine_content(page_words: List[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    """
    Merge words from multiple pages into a single list.
    Adjusts each word's 'top' and 'bottom' coordinates so pages
    stack vertically.

    Args:
        page_words (List[List[Dict[str, Any]]]):
            Pages extracted with `pdfplumber.Page.extract_words()`.

    Returns:
        List[Dict[str, Any]]: Combined words with adjusted positions.
    """
    last_text_bottom = 0
    combined_page = []

    for page in page_words:
        for word in page:
            # Shift word position down by the offset of previous pages
            word["top"] += last_text_bottom
            word["bottom"] += last_text_bottom
            combined_page.append(word)

        # Update offset for the next page
        last_text_bottom = combined_page[-1]["bottom"]

    return combined_page


def merge_textbox(text, first_text, last_text):
    return {
        "text": text,
        "x0": first_text["x0"],
        "x1": last_text["x1"],
        "top": first_text["top"],
        "doctop": first_text["doctop"],
        "bottom": first_text["bottom"],
        "upright": True,
        "height": first_text["height"],
        "width": last_text["x1"] - first_text["x0"],
        "direction": "ltr",
        "center_x": (first_text["x0"] + last_text["x1"]) / 2,
    }


def horizontal_merge(
    text_list: List[Dict],
    merging_string: str = " ",
    space_tolerance_ratio: float = 0.5,
    height_tolerance_ratio: float = 0.1,
) -> List[Dict]:
    """
    Merge adjacent word dicts on the same line into sentences.

    Args:
        text_list: List of words in pdfplumber-style dicts.
        merging_string: String used to join word texts.
        space_tolerance_ratio: Max horizontal gap (in units of word height) to keep merging.
        height_tolerance_ratio: Max allowed diff for 'height' and 'top' of the word to be same-line.

    Returns:
        List of words in pdfplumber-style dicts.
    """
    sentence_list = []
    current_sentence = []

    for text in text_list:
        if len(current_sentence) == 0:
            current_sentence.append(text)
            continue

        prev_text = current_sentence[-1]

        # Condition to continue the sentence (font diff, y diff, and space)
        if (
            (
                abs(prev_text["height"] - text["height"])
                < text["height"] * height_tolerance_ratio
            )
            and (
                abs(prev_text["top"] - text["top"])
                < text["height"] * height_tolerance_ratio
            )
            and (text["x0"] - prev_text["x1"] < text["height"] * space_tolerance_ratio)
        ):
            # Continue Sentence
            current_sentence.append(text)
        else:
            # Break Sentence and create new textbox
            sentence_text = merging_string.join([i["text"] for i in current_sentence])

            first_text = current_sentence[0]
            last_text = current_sentence[-1]

            sentence_textbox = merge_textbox(sentence_text, first_text, last_text)
            sentence_list.append(sentence_textbox)

            current_sentence = [text]  # New sentence start with text

    # Flush out last sentence
    if len(current_sentence) > 0:
        sentence_text = merging_string.join([i["text"] for i in current_sentence])

        first_text = current_sentence[0]
        last_text = current_sentence[-1]

        sentence_textbox = merge_textbox(sentence_text, first_text, last_text)
        sentence_list.append(sentence_textbox)

    return sentence_list


# MULTI LINE
def vertical_merge(
    text_list: list[dict],
    merging_string=" ",
    vertical_space_tolerance_ratio=0.5,
    height_tolerance_ratio=0.1,
    x_start_tolerance_ratio=0.5,
) -> list[dict]:
    """
    Merge multi-line text boxes in one textbox.

    Args:
        text_list: List of words in pdfplumber-style dicts.
        merging_string: Joiner between line texts.
        vertical_space_tolerance_ratio: Max gap between lines (in word-height units).
        height_tolerance_ratio: Max diff for 'height' to consider same font/line family.
        x_start_tolerance_ratio: Max diff of left edges ('x0') to align vertically.

    Returns:
        List of words in pdfplumber-style dicts.
    """

    sentence_list = []
    current_sentence = []

    for text in text_list:
        if len(current_sentence) == 0:
            current_sentence.append(text)
            continue

        prev_text = current_sentence[-1]

        # Condition to continue the sentence (font diff, y diff, and space)
        if (
            (
                abs(prev_text["height"] - text["height"])
                < text["height"] * height_tolerance_ratio
            )
            and (
                abs(prev_text["bottom"] - text["top"])
                < text["height"] * vertical_space_tolerance_ratio
            )
            and (
                abs(text["x0"] - prev_text["x0"])
                < text["height"] * x_start_tolerance_ratio
            )
        ):
            # Continue Sentence
            current_sentence.append(text)
        else:
            # Break Sentence and create new textbox
            sentence_text = merging_string.join([i["text"] for i in current_sentence])

            first_text = current_sentence[0]
            last_text = current_sentence[-1]

            sentence_textbox = merge_textbox(sentence_text, first_text, last_text)
            sentence_list.append(sentence_textbox)

            current_sentence = [text]  # New sentence start with text

    # Flush out last sentence
    if len(current_sentence) > 0:
        sentence_text = merging_string.join([i["text"] for i in current_sentence])

        first_text = current_sentence[0]
        last_text = current_sentence[-1]

        sentence_textbox = merge_textbox(sentence_text, first_text, last_text)
        sentence_list.append(sentence_textbox)

    return sentence_list


# TABLE MERGE
def table_merge(
    text_list: list[dict],
    height_tolerance_ratio=0.1,
    vertical_space_tolerance_ratio=0.5,
    x_start_tolerance_ratio=0.5,
) -> list[dict]:
    table_list = []
    current_table = []
    current_row = []

    for text in text_list + [text_list[0]]:
        if len(current_row) == 0:
            current_row.append(text)
            continue

        prev_text = current_row[-1]

        # Condition to continue the row (font diff, y diff, and space), no space tolerance
        if (
            abs(prev_text["height"] - text["height"])
            < text["height"] * height_tolerance_ratio
        ) and (
            abs(prev_text["top"] - text["top"])
            < text["height"] * height_tolerance_ratio
        ):
            # Continue row
            current_row.append(text)
        else:
            # Complete 1 row
            if len(current_table) == 0:
                # Add the row to new table
                current_table.append(current_row.copy())
                current_row = [text]
            else:
                prev_table_row = current_table[-1]
                if len(prev_table_row) != len(
                    current_row
                ):  # Unequal number of column, break the table
                    table_list.append(current_table.copy())
                    current_table = []
                    current_row = [text]
                else:
                    for c1, c2 in zip(prev_table_row, current_row):
                        if not (
                            (
                                abs(c1["bottom"] - c2["top"])
                                < c2["height"] * vertical_space_tolerance_ratio
                            )
                            and (
                                abs(c2["x0"] - c1["x0"])
                                < text["height"] * x_start_tolerance_ratio
                            )
                        ):
                            # If even one column is not align, break the table
                            table_list.append(current_table.copy())
                            current_table = []
                            current_row = [text]
                            break
                    else:
                        # Add the row to table
                        current_table.append(current_row.copy())
                        current_row = [text]

    return table_list
