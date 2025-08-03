import csv
import os
import argparse
from collections import defaultdict

# --- Configuration ---
# You can adjust these values
#POINTS_PER_ROUND = {
#    'r32': 1, 'r16': 2, 'qf': 4, 'sf': 8, 'f': 16
#}
POINTS_PER_ROUND = {
    'r128':1, 'r64':1, 'r32': 2, 'r16': 3, 'qf': 5, 'sf': 8, 'f': 13
}
ROUND_NAMES = {
    'r32': 'Round of 32', 'r16': 'Round of 16', 'qf': 'Quarterfinals',
    'sf': 'Semifinals', 'f': 'Final'
}
RESULTS_FILENAME = "actual_results.csv"
PREDICTION_SUFFIX = "_predictions.csv"

# --- Core Logic ---

def load_actual_winners(results_file):
    """Loads the actual tournament winners from the results CSV file."""
    actual_winners = defaultdict(set)
    try:
        with open(results_file, 'r', newline='', encoding='utf-8') as file:
            reader = csv.reader(file)
            next(reader)  # Skip header
            for row in reader:
                category, round_key, winner = row
                actual_winners[f"{category}-{round_key}"].add(winner.strip())
    except FileNotFoundError:
        print(f"\nERROR: The results file '{results_file}' was not found.")
        return None
    except Exception as e:
        print(f"\nAn error occurred while reading the results file: {e}")
        return None
    return actual_winners

def calculate_score_data(prediction_file, actual_winners):
    """Calculates the score data for a single prediction file."""
    predicted_winners = defaultdict(set)
    try:
        with open(prediction_file, 'r', newline='', encoding='utf-8') as file:
            reader = csv.reader(file)
            header = [h.strip().lower() for h in next(reader)]
            expected_header = ['category', 'round', 'matchid', 'predictedwinner']
            if header != expected_header:
                # Silently skip files that don't match the prediction format
                return None

            for row in reader:
                category, round_key, _, predicted_winner = row
                if predicted_winner != "NONE":
                    predicted_winners[f"{category}-{round_key}"].add(predicted_winner.strip())
    except Exception:
        # Ignore files that can't be read
        return None

    # Calculate score
    score_data = {}
    total_score = 0
    for round_key in POINTS_PER_ROUND.keys():
        round_points = 0
        for category in ["mens", "womens"]:
            round_id = f"{category}-{round_key}"
            correct_picks_set = actual_winners[round_id].intersection(predicted_winners[round_id])
            num_correct = len(correct_picks_set)
            round_points += num_correct * POINTS_PER_ROUND.get(round_key, 0)

        score_data[round_key] = round_points
        total_score += round_points

    score_data['total'] = total_score
    return score_data

# --- Display Functions ---

def display_single_report(score_data, player_name):
    """Formats and prints a detailed report for a single player."""
    print("\n" + "="*45)
    print(f"  SCORE REPORT FOR: {player_name.title()}")
    print("="*45)

    for round_key, round_name in ROUND_NAMES.items():
        points = score_data.get(round_key, 0)
        print(f"{round_name+':':<16} {points} pts")

    print("-"*45)
    print(f"{'TOTAL SCORE:':<16} {score_data.get('total', 0)} pts")
    print("="*45)

def display_scoreboard(all_scores):
    """Formats and prints a leaderboard table for all players."""
    player_names = sorted(all_scores.keys())

    # Determine column widths
    col_width = max(len(name) for name in player_names) + 2 if player_names else 10

    # Print header
    header = f"{'ROUND':<16}|" + "".join(f"{name.upper():<{col_width}}" for name in player_names)
    print("\n" + "--- Tournament Scoreboard ---")
    print(header)
    print("-" * len(header))

    # Print scores for each round
    for round_key, round_name in ROUND_NAMES.items():
        row_str = f"{round_name:<16}|"
        for name in player_names:
            points = all_scores[name].get(round_key, 0)
            row_str += f"{str(points) + ' pts':<{col_width}}"
        print(row_str)

    # Print total
    print("-" * len(header))
    total_str = f"{'TOTAL SCORE':<16}|"
    for name in player_names:
        total_points = all_scores[name].get('total', 0)
        total_str += f"{str(total_points):<{col_width}}"
    print(total_str)
    print("-" * len(header))

# --- Main Execution ---

def main():
    """Main function to parse arguments and run the correct mode."""
    parser = argparse.ArgumentParser(
        description="A tool to score tournament bracket predictions.",
        epilog="Example usage: python score_manager.py -b ./predictions"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        '-s', '--single',
        metavar='FILENAME',
        help="Score a single prediction file."
    )
    group.add_argument(
        '-b', '--board',
        nargs='?',
        const='.',
        metavar='DIRECTORY',
        help="Generate a scoreboard for all prediction files in a directory (default: current directory)."
    )

    args = parser.parse_args()

    actual_winners = load_actual_winners(RESULTS_FILENAME)
    if actual_winners is None:
        return # Stop if results can't be loaded

    if args.single:
        player_name = os.path.basename(args.single).replace(PREDICTION_SUFFIX, '')
        score_data = calculate_score_data(args.single, actual_winners)
        if score_data:
            display_single_report(score_data, player_name)
        else:
            print(f"Could not process the file: {args.single}. Ensure it is a valid prediction file.")

    elif args.board is not None:
        directory = args.board
        if not os.path.isdir(directory):
            print(f"Error: Directory not found at '{directory}'")
            return

        all_scores = {}
        for filename in os.listdir(directory):
            if filename.endswith(PREDICTION_SUFFIX):
                filepath = os.path.join(directory, filename)
                player_name = filename.replace(PREDICTION_SUFFIX, '')
                score_data = calculate_score_data(filepath, actual_winners)
                if score_data:
                    all_scores[player_name] = score_data

        if not all_scores:
            print(f"No valid prediction files found in '{directory}'.")
            print(f"Files must end with '{PREDICTION_SUFFIX}'.")
            return

        display_scoreboard(all_scores)

if __name__ == "__main__":
    main()

