import argparse
import json
from difflib import get_close_matches

def get_players_from_json(filepath):
    """Extracts a set of player names from a tournament_data.json file."""
    players = set()
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            for draw in data.values():
                for match in draw:
                    for player_info in match['players']:
                        if player_info[1] and player_info[1] != 'TBD':
                            players.add(player_info[1])
    except (FileNotFoundError, json.JSONDecodeError, KeyError):
        return None
    return players

def get_players_from_entrants(filepath):
    """Extracts a set of player names from an entrants.txt file."""
    players = set()
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                if ' vs ' in line.lower():
                    parts = line.strip().split(' vs ')
                    for part in parts:
                        # Simple parsing, assuming name is after the seed if present
                        name = part.split(') ')[-1].strip()
                        if name and name.lower() != 'tbd':
                            players.add(name)
    except FileNotFoundError:
        return None
    return players

def compare_players(old_players, new_players):
    """Compares the two sets of players and prints a report."""
    if old_players is None or new_players is None:
        print("Could not compare files. One or both files might be missing or corrupted.")
        return

    added_players = new_players - old_players
    removed_players = old_players - new_players

    potential_changes = {}

    # Check for close matches to identify potential typos/renames
    for removed in list(removed_players):
        matches = get_close_matches(removed, added_players, n=1, cutoff=0.8)
        if matches:
            added = matches[0]
            potential_changes[removed] = added
            removed_players.remove(removed)
            added_players.remove(added)

    print("\n--- Data Validation Report ---")
    if not any([potential_changes, added_players, removed_players]):
        print("✅ No significant changes to player names found. Data is consistent.")
    else:
        if potential_changes:
            print("\n⚠️ Potential Name Changes Detected:")
            for old, new in potential_changes.items():
                print(f"  - '{old}'  ->  '{new}'")

        if added_players:
            print("\n➕ New Players Added:")
            for player in sorted(list(added_players)):
                print(f"  - {player}")

        if removed_players:
            print("\n➖ Players Removed:")
            for player in sorted(list(removed_players)):
                print(f"  - {player}")

    print("\nReview the changes above. If they are intentional, you can proceed to generate the new tournament file.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Validate player names between an entrants.txt file and an existing tournament_data.json file.")
    parser.add_argument('entrants_file', help="Path to the new entrants.txt file.")
    parser.add_argument('json_file', help="Path to the existing public/tournament_data.json file to compare against.")
    args = parser.parse_args()

    old_players = get_players_from_json(args.json_file)
    new_players = get_players_from_entrants(args.entrants_file)

    compare_players(old_players, new_players)

