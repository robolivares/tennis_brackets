# Welcome to Cloud Functions for Firebase for Python!
# To learn more about Cloud Functions, see the documentation:
# https://firebase.google.com/docs/functions/beta

from firebase_functions import firestore_fn, options
from firebase_admin import initialize_app, firestore
import json

# It's recommended to initialize the app once at the top level
initialize_app()

# --- SCORING LOGIC (Adapted from calculate_scores.py) ---
POINTS_PER_ROUND = {'r32': 2, 'r16': 3, 'qf': 5, 'sf': 8, 'f': 13}
ROUNDS = ["r32", "r16", "qf", "sf", "f"]

@firestore_fn.on_document_written(document="tournaments/{tournId}/results/actualResults")
def on_results_update(event: firestore_fn.Event[firestore_fn.Change]) -> None:
    """
    When results are updated, recalculate all scores and update the viewerData document.
    """
    # *** FIX: Changed event.resource to event.source ***
    print(f"Triggered by update to: {event.source}")

    tourn_id = event.params["tournId"]
    print(f"Processing scores for tournament: {tourn_id}")

    db = firestore.client()

    # --- Fetch all necessary data ---
    participants_ref = db.collection('tournaments', tourn_id, 'participants')
    participants_docs = participants_ref.stream()
    participants = [doc.to_dict() for doc in participants_docs]

    actual_results_data = event.data.after.to_dict()
    actual_results = actual_results_data.get('winners', {})

    try:
        with open('tournament_data.json', 'r') as f:
            initial_entrants = json.load(f)
    except FileNotFoundError:
        print("ERROR: tournament_data.json not found. Make sure it's in the functions directory.")
        return

    # --- Start Calculation Logic ---
    eliminated_players = get_eliminated_players(initial_entrants, actual_results)

    all_players_set = {
        player[1] for draw in initial_entrants.values()
        for match in draw
        for player in match['players']
    }
    active_players = all_players_set - set(eliminated_players)

    leaderboard = []
    print(f"Calculating scores for {len(participants)} participants...")

    for p in participants:
        if not p.get('isLocked'):
            continue

        picks = p.get('picks', {})
        current_score = 0
        potential_score = 0

        for match_id, picked_winner_data in picks.items():
            # Handle both list format ['seed', 'name'] and old string format
            picked_winner = picked_winner_data[1] if isinstance(picked_winner_data, list) else picked_winner_data
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
            "score": current_score,
            "max_score": current_score + potential_score,
            "picks": p.get('picks', {}) # Pass picks through for viewer
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
        "eliminated_players": list(eliminated_players),
        "seed_map": {
            'mens': {p[1]: p[0] for m in initial_entrants['mens_draw'] for p in m['players']},
            'womens': {p[1]: p[0] for m in initial_entrants['womens_draw'] for p in m['players']}
        }
    }

    print("Uploading calculated leaderboard to Firestore...")
    viewer_doc_ref = db.collection('tournaments', tourn_id, 'state').document('viewerData')
    viewer_doc_ref.set(viewer_data)
    print("Done. Leaderboard is now live.")

def get_eliminated_players(initial_entrants, actual_results):
    eliminated = set()
    for match_id, winner in actual_results.items():
        category_key = 'mens_draw' if 'mens' in match_id else 'womens_draw'
        parts = match_id.split('-')
        round_key, match_idx = parts[1], int(parts[-1])

        p1, p2 = None, None
        if round_key == 'r32':
            p1 = initial_entrants[category_key][match_idx]['players'][0][1]
            p2 = initial_entrants[category_key][match_idx]['players'][1][1]
        else:
            prev_round_idx = ROUNDS.index(round_key) - 1
            prev_round_key = ROUNDS[prev_round_idx]
            p1_match_id = f"{parts[0]}-{prev_round_key}-match-{match_idx * 2}"
            p2_match_id = f"{parts[0]}-{prev_round_key}-match-{match_idx * 2 + 1}"
            p1 = actual_results.get(p1_match_id)
            p2 = actual_results.get(p2_match_id)

        if p1 and p2:
            if p1 == winner: eliminated.add(p2)
            elif p2 == winner: eliminated.add(p1)
    return eliminated
