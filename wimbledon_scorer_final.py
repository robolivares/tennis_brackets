import csv
import os
from collections import defaultdict

def calculate_bracket_score(predictions_file, results_file):
    """
    Calculates a weighted score for a bracket by comparing predicted winners
    to actual winners from a results file, round by round.
    This logic correctly scores a bracket challenge.
    """
    # --- Points System (Feel free to adjust these values) ---
    points_per_round = {
        'r32': 1,       # Round of 32
        'r16': 2,       # Round of 16
        'qf': 4,        # Quarterfinals
        'sf': 8,        # Semifinals
        'f': 16         # Final
    }

    # --- Process the actual results file ---
    actual_winners = defaultdict(set)
    try:
        with open(results_file, 'r', newline='', encoding='utf-8') as file:
            reader = csv.reader(file)
            next(reader)  # Skip header
            for row in reader:
                # UPDATED: Now expects only category, round, winner
                category, round_key, winner = row
                actual_winners[f"{category}-{round_key}"].add(winner)
    except FileNotFoundError:
        print(f"\nERROR: The results file '{results_file}' was not found.")
        print("Please ensure 'actual_results.csv' is in the same folder.")
        return
    except ValueError:
        print(f"\nERROR: The results file '{results_file}' has the wrong format.")
        print("Please ensure it has exactly 3 columns: category,round,winner")
        return
    except Exception as e:
        print(f"\nAn error occurred while reading the results file: {e}")
        return

    # --- Process the user's predictions file ---
    predicted_winners = defaultdict(set)
    try:
        with open(predictions_file, 'r', newline='', encoding='utf-8') as file:
            reader = csv.reader(file)

            # Header validation to prevent using the wrong file
            header = [h.strip().lower() for h in next(reader)]
            expected_header = ['category', 'round', 'matchid', 'predictedwinner']
            if header != expected_header:
                print(f"\nERROR: The prediction file '{predictions_file}' has incorrect headers.")
                print(f"Expected: {expected_header}")
                print(f"Found:    {header}")
                print("\nIt looks like you might be using 'actual_results.csv' as the prediction file.")
                print("Please use a file exported from the 'bracket.html' page instead.")
                return # Exit the function

            # Process rows if header is correct
            for row in reader:
                # Expects: Category,Round,MatchID,PredictedWinner
                category, round_key, _, predicted_winner = row
                if predicted_winner != "NONE":
                    predicted_winners[f"{category}-{round_key}"].add(predicted_winner)
    except FileNotFoundError:
        print(f"\nERROR: The prediction file '{predictions_file}' was not found.")
        print("Please check the filename and try again.")
        return
    except Exception as e:
        print(f"\nAn error occurred while reading the prediction file: {e}")
        return

    # --- Calculate the score by comparing the sets ---
    total_score = 0
    report_data = {}
    round_keys = points_per_round.keys()

    for category in ["mens", "womens"]:
        for round_key in round_keys:
            round_id = f"{category}-{round_key}"

            correct_picks_set = actual_winners[round_id].intersection(predicted_winners[round_id])
            num_correct = len(correct_picks_set)

            points_for_round = num_correct * points_per_round.get(round_key, 0)
            total_score += points_for_round

            if round_key not in report_data:
                report_data[round_key] = {'correct': 0, 'points': 0}
            report_data[round_key]['correct'] += num_correct
            report_data[round_key]['points'] += points_for_round

    # --- Display the results in a formatted report ---
    print("\n" + "="*45)
    player_name = os.path.basename(predictions_file).replace('.csv', '').replace('_', ' ').title()
    print(f"  SCORE REPORT FOR: {player_name}")
    print("="*45)

    round_names = {
        'r32': 'Round of 32', 'r16': 'Round of 16', 'qf': 'Quarterfinals',
        'sf': 'Semifinals', 'f': 'Final'
    }

    for round_key, round_name in round_names.items():
        data = report_data.get(round_key, {'correct': 0, 'points': 0})
        print(f"{round_name+':':<16} {data['correct']} correct picks (+{data['points']} pts)")

    print("-"*45)
    print(f"{'TOTAL SCORE:':<16} {total_score} points")
    print("="*45)


if __name__ == "__main__":
    results_filename = "actual_results.csv"
    prediction_filename = input("Enter the CSV file name of a player's bracket (e.g., your_name.csv): ")

    calculate_bracket_score(prediction_filename, results_filename)

