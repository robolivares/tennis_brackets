import json
import os
import re
import argparse
import shutil

def parse_entrants(filepath="entrants.txt"):
    """
    Parses entrants.txt, reading headers like "Top Half (Day 1)" to determine
    the schedule for each half of the draw. Preserves player name capitalization.
    """
    if not os.path.exists(filepath):
        print(f"Error: Entrants file not found at '{filepath}'")
        return None

    parsed_data = {
        'mens': {'top': [], 'bottom': [], 'top_day': 0, 'bottom_day': 0},
        'womens': {'top': [], 'bottom': [], 'top_day': 0, 'bottom_day': 0}
    }
    current_category = None
    current_half = None
    header_regex = re.compile(r"(top|bottom)\s+half\s+\(day\s*([12])\)")
    player_regex = re.compile(r"\((.*?)\)\s*(.*)|(^[^\(]+)")

    def parse_player(p_str):
        match = player_regex.match(p_str.strip())
        if match:
            if match.group(1) is not None: return (match.group(1), match.group(2).strip())
            elif match.group(3) is not None: return ("", match.group(3).strip())
        return ("", p_str)

    with open(filepath, 'r', encoding='utf-8') as f:
        for original_line in f:
            line_stripped = original_line.strip()
            line_lower = line_stripped.lower()
            if not line_stripped: continue

            if line_lower == 'mens':
                current_category = 'mens'
                current_half = None
                continue
            elif line_lower == 'womens':
                current_category = 'womens'
                current_half = None
                continue

            header_match = header_regex.match(line_lower)
            if header_match and current_category:
                half, day = header_match.groups()
                current_half = half
                parsed_data[current_category][f'{half}_day'] = int(day)
                continue

            if 'vs' in line_lower and current_category and current_half:
                parts = re.split(r'\s+vs\s+', line_stripped, flags=re.IGNORECASE)
                if len(parts) == 2:
                    p1_str, p2_str = parts
                    player1 = parse_player(p1_str)
                    player2 = parse_player(p2_str)
                    parsed_data[current_category][current_half].append([player1, player2])

    return parsed_data

def generate_tournament_json(data, output_path):
    """
    Saves the parsed tournament data to a JSON file with a unified structure.
    Each R32 matchup is tagged with its play day.
    """
    def process_draw(category_data):
        top_matchups = [{'players': match, 'day': category_data['top_day']} for match in category_data['top']]
        bottom_matchups = [{'players': match, 'day': category_data['bottom_day']} for match in category_data['bottom']]
        return top_matchups + bottom_matchups

    tournament_config = {
        "mens_draw": process_draw(data['mens']),
        "womens_draw": process_draw(data['womens'])
    }

    # Ensure the output directory exists
    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(tournament_config, f, indent=4)
    print(f"Successfully generated primary tournament data at: {output_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate tournament_data.json from an entrants text file.")
    parser.add_argument('-e', '--entrants', default='entrants.txt', help="Path to the entrants text file.")
    parser.add_argument('-o', '--output', default='public/tournament_data.json', help="Path for the primary output JSON file for the website.")
    parser.add_argument('-s', '--storage_output', help="Optional path for the second output JSON file for Firebase Storage.")

    args = parser.parse_args()

    print("--- Tournament JSON Generator ---")
    parsed_data = parse_entrants(args.entrants)
    if parsed_data:
        placeholder_match = [['', 'TBD'], ['', 'TBD']]
        for category in ['mens', 'womens']:
            if not parsed_data[category]['top']:
                parsed_data[category]['top'] = [placeholder_match for _ in range(8)]
            if not parsed_data[category]['bottom']:
                parsed_data[category]['bottom'] = [placeholder_match for _ in range(8)]

        if len(parsed_data['mens']['top']) != 8 or len(parsed_data['mens']['bottom']) != 8 or \
           len(parsed_data['womens']['top']) != 8 or len(parsed_data['womens']['bottom']) != 8:
            print("\nError: A section in your entrants.txt has an incorrect number of matchups. Each half must have exactly 8 matches.")
        else:
            # Generate the primary file for the website
            generate_tournament_json(parsed_data, args.output)

            # If the storage_output path is provided, create a copy there
            if args.storage_output:
                try:
                    storage_dir = os.path.dirname(args.storage_output)
                    if storage_dir:
                        os.makedirs(storage_dir, exist_ok=True)

                    shutil.copy(args.output, args.storage_output)
                    print(f"Successfully created copy for Firebase Storage at: {args.storage_output}")
                except Exception as e:
                    print(f"\nError: Could not copy file to storage path: {e}")

            print("\nSetup complete!")

