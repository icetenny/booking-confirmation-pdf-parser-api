import json
from typing import Any, Dict, List, Tuple

from rapidfuzz import fuzz, process, utils


def create_key_map(
    json_file: str = "label.json", key_type: str = "normal"
) -> Tuple[Dict[str, str], List[str], List[str]]:
    """
    Load a key mapping from a JSON label file.

    Args:
        json_file: Path to the label file (default: "label.json").
        key_type: Section to read, {"normal" or "table"}.

    Returns:
        tuple:
            - key_map: Maps each key variant → canonical key.
            - all_keys: Canonical keys.
            - all_keys_variance: All key variants across keys.
    """
    with open(json_file, "r", encoding="utf-8") as f:
        label_dict = json.load(f)[key_type]

    # Create a dict to map all variance to each key
    key_map = dict()

    for key, key_variances in label_dict.items():
        for key_variance in key_variances:
            key_map[key_variance] = key

    all_keys_variance = list(key_map.keys())
    all_keys = list(label_dict.keys())

    return key_map, all_keys, all_keys_variance


def match_key(
    text: str, key_list: list[str], matching_threhold: int = 90
) -> tuple[str, float]:
    best_match_key, score, _ = process.extractOne(
        text,
        key_list,
        scorer=fuzz.token_sort_ratio,
        processor=utils.default_process,
    )
    if score > matching_threhold:
        return best_match_key, score
    else:
        return None, 0.0


def key_split(
    text: str, key_list: list[str], sep: str = " ", matching_threhold: int = 90
) -> list[str]:
    text_list = text.split(sep)

    best_match_score, best_match_key, best_match_value = 0, None, None

    for i in range(3):
        key_substring = " ".join(text_list[: i + 1])
        value_substring = " ".join(text_list[i + 1 :])

        best_match_key_substring, score = match_key(
            key_substring, key_list, matching_threhold=matching_threhold
        )

        if best_match_key_substring is None:
            continue

        if score >= best_match_score:
            best_match_key = best_match_key_substring
            best_match_score = score
            best_match_value = value_substring

    return [best_match_key, best_match_value]


def tab_split(
    text: str, key_list: list[str], sep: str = "|", matching_threhold: int = 90
) -> list[str]:

    input_sentences = text.split(sep)
    output_sentences = []
    current_sentence = ""

    for sentence in input_sentences:
        k, _ = key_split(sentence, key_list, matching_threhold=matching_threhold)

        if k is not None:  # The sentence start with key
            if current_sentence != "":
                # Add previous sentence to output
                output_sentences.append(current_sentence)
            # Start new setence
            current_sentence = sentence

        else:  # The sentence do not start with a key
            # Concat the sentence to current sentence
            current_sentence = f"{current_sentence} {sentence}"

    # Add last sentence
    if current_sentence != "":
        output_sentences.append(current_sentence)

    return output_sentences