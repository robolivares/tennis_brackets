import firebase_admin
from firebase_admin import credentials, firestore
import json
import argparse # Import the argparse library to handle command-line arguments

# --- CONFIGURATION ---
# 1. Download your Firebase service account key JSON file and save it as 'serviceAccountKey.json'
#    in the SAME directory as THIS script.
# 2. Set your Tournament ID
TOURNAMENT_ID = 'usopen2024'
# ---------------------

# --- INITIALIZE FIREBASE ADMIN SDK ---
try:
    # The script will look for the key file in its own directory.
    cred = credentials.Certificate('serviceAccountKey.json')
    firebase_admin.initialize_app(cred)
    db = firestore.client()
    print("Successfully connected to Firebase.")
except Exception as e:
    print(f"Error connecting to Firebase: {e}")
    print("Please ensure 'serviceAccountKey.json' is in the same directory as this script.")
    exit()

# --- SCORING LOGIC ---
POINTS_PER_ROUND = {'r32': 2, 'r16': 3, 'qf': 5, 'sf': 8, 'f': 13}
ROUNDS = ["r32", "r16", "qf", "sf", "f"]

def get_all_participants():
    """Fetches all participant documents from Firestore."""
    participants_ref = db.collection('tournaments', TOURNAMENT_ID, 'participants')
    docs = participants_ref.stream()
    return [doc.to_dict() for doc in docs]

def get_actual_results():
    """Fetches the actual results document from Firestore."""
    results_ref = db.collection('tournaments', TOURNAMENT_ID, 'results').document('actualResults')
    doc = results_ref.get()
    if doc.exists:
        return doc.to_dict().get('winners', {})
    return {}

def get_eliminated_players(initial_entrants, actual_results):
    """Determines which players are out of the tournament."""
    all_players = set()
    for category in ['mens_draw', 'womens_draw']:
        for match_data in initial_entrants[category]:
            for player_info in match_data['players']:
                all_players.add(player_info[1])

    eliminated = set()
    for match_id, winner in actual_results.items():
        category_key = 'mens_draw' if 'mens' in match_id else 'womens_draw'
        round_key, match_idx_str = match_id.split('-')[1], match_id.split('-')[-1]
        match_idx = int(match_idx_str)

        p1, p2 = None, None
        if round_key == 'r32':
            p1 = initial_entrants[category_key][match_idx]['players'][0][1]
            p2 = initial_entrants[category_key][match_idx]['players'][1][1]
        else:
            prev_round_idx = ROUNDS.index(round_key) - 1
            prev_round_key = ROUNDS[prev_round_idx]
            p1_match_id = f"{match_id.split('-')[0]}-{prev_round_key}-match-{match_idx * 2}"
            p2_match_id = f"{match_id.split('-')[0]}-{prev_round_key}-match-{match_idx * 2 + 1}"
            p1 = actual_results.get(p1_match_id)
            p2 = actual_results.get(p2_match_id)

        if p1 and p2:
            if p1 == winner:
                eliminated.add(p2)
            elif p2 == winner:
                eliminated.add(p1)

    return list(eliminated)


def calculate_all_scores(tournament_data_path):
    """Main function to calculate and update scores."""
    print("Fetching data from Firestore...")
    participants = get_all_participants()
    actual_results = get_actual_results()

    # MODIFIED: Load tournament data from the path provided as an argument
    try:
        with open(tournament_data_path, 'r') as f:
            initial_entrants = json.load(f)
        print(f"Successfully loaded tournament data from: {tournament_data_path}")
    except FileNotFoundError:
        print(f"ERROR: The file was not found at the path you provided: {tournament_data_path}")
        exit()
    except json.JSONDecodeError:
        print(f"ERROR: The file at {tournament_data_path} is not a valid JSON file.")
        exit()

    # --- FIXED SECTION ---
    eliminated_players = get_eliminated_players(initial_entrants, actual_results)
    # First, create a set of all player names from the initial data.
    all_players_set = {
        player[1] for draw in initial_entrants.values()
        for match in draw
        for player in match['players']
    }
    # Then, determine active players by subtracting the eliminated ones.
    active_players = all_players_set - set(eliminated_players)
    # --- END FIXED SECTION ---

    leaderboard = []
    print(f"Calculating scores for {len(participants)} participants...")

    for p in participants:
        if not p.get('isLocked'):
            continue # Skip users who haven't submitted

        picks = p.get('picks', {})
        current_score = 0
        potential_score = 0

        for match_id, picked_winner_data in picks.items():
            picked_winner = picked_winner_data[1]
            round_key = match_id.split('-')[1]
            points = POINTS_PER_ROUND.get(round_key, 0)

            if match_id in actual_results:
                if picked_winner == actual_results[match_id]:
                    current_score += points
            elif picked_winner in active_players:
                potential_score += points

        leaderboard.append({
            "name": p.get('nickname', 'Unknown'),
            "fullName": p.get('fullName', 'Unknown'),
            "picks": picks,
            "score": current_score,
            "max_score": current_score + potential_score
        })

    leaderboard.sort(key=lambda x: x['score'], reverse=True)

    # Assign ranks
    rank = 0
    last_score = -1
    for i, p in enumerate(leaderboard):
        if p["score"] != last_score:
            rank = i + 1
            last_score = p["score"]
        p['rank'] = rank

    # Prepare data for viewer
    viewer_data = {
        "participants": leaderboard,
        "actual_results": actual_results,
        "eliminated_players": eliminated_players,
        "seed_map": { # Recreate seed map for the viewer
            'mens': {p[1]: p[0] for m in initial_entrants['mens_draw'] for p in m['players']},
            'womens': {p[1]: p[0] for m in initial_entrants['womens_draw'] for p in m['players']}
        }
    }

    # Save to Firestore
    print("Uploading calculated leaderboard to Firestore...")
    viewer_doc_ref = db.collection('tournaments', TOURNAMENT_ID, 'state').document('viewerData')
    viewer_doc_ref.set(viewer_data)
    print("Done. Leaderboard is now live.")


if __name__ == '__main__':
    # Set up the argument parser to accept the file path
    parser = argparse.ArgumentParser(description='Calculate scores for the tournament bracket challenge.')
    parser.add_argument('tournament_data_path', type=str, help='The full path to the tournament_data.json file.')

    args = parser.parse_args()

    # Call the main function with the path from the command-line argument
    calculate_all_scores(args.tournament_data_path)

