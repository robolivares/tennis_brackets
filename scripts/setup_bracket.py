import json
import os
import re
import argparse
import math

def parse_entrants(filepath="entrants.txt"):
    """
    Parses entrants.txt to collect matchups.
    Ignores deprecated Day/Half headers and focuses on 'Player vs Player'.
    """
    if not os.path.exists(filepath):
        print(f"Error: Entrants file not found at '{filepath}'")
        return None

    parsed_data = {'mens': [], 'womens': []}
    current_category = None
    player_regex = re.compile(r"(?:\((.*?)\))?\s*(.*)")

    def parse_player(p_str):
        p_str = p_str.strip()
        if not p_str or p_str.upper() == "TBD":
            return ["", "TBD"]
        match = player_regex.match(p_str)
        if match:
            seed = match.group(1) or ""
            name = match.group(2).strip() or "TBD"
            return [seed, name]
        return ["", p_str]

    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line: continue

            if line.lower() == 'mens':
                current_category = 'mens'
                continue
            elif line.lower() == 'womens':
                current_category = 'womens'
                continue

            if ' vs ' in line.lower() and current_category:
                parts = re.split(r'\s+vs\s+', line, flags=re.IGNORECASE)
                if len(parts) == 2:
                    p1 = parse_player(parts[0])
                    p2 = parse_player(parts[1])
                    parsed_data[current_category].append({"players": [p1, p2]})

    return parsed_data

def generate_tournament_json(data, output_path):
    """
    Calculates the target power of 2 for padding and generates the JSON.
    """
    # Valid match counts for common starting rounds
    # 8 (R16), 16 (R32), 32 (R64), 64 (R128)
    VALID_SIZES = [8, 16, 32, 64]

    # Determine the target size based on the largest draw provided
    max_found = max(len(data['mens']), len(data['womens']))

    # Find the smallest valid size that can hold all matches
    target_size = 16 # Default to R32
    for size in VALID_SIZES:
        if max_found <= size:
            target_size = size
            break

    print(f"Detected target draw size: {target_size} matches.")

    final_config = {}
    placeholder = {"players": [["", "TBD"], ["", "TBD"]]}

    for cat in ['mens', 'womens']:
        draw = data[cat]
        current_len = len(draw)

        if current_len < target_size:
            print(f"Padding {cat.title()} draw: {current_len}/{target_size} matches found.")
            draw.extend([placeholder] * (target_size - current_len))

        final_config[f"{cat}_draw"] = draw[:target_size]

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(final_config, f, indent=4)
    print(f"Successfully generated: {output_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-e', '--entrants', default='entrants.txt')
    parser.add_argument('-o', '--output', default='public/tournament_data.json')
    args = parser.parse_args()

    print("--- Dynamic Tournament Generator ---")
    tournament_data = parse_entrants(args.entrants)
    if tournament_data:
        generate_tournament_json(tournament_data, args.output)

