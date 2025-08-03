# Welcome to Cloud Functions for Firebase for Python!
# To learn more about Cloud Functions, see the documentation:
# https://firebase.google.com/docs/functions/beta

from firebase_functions import firestore_fn, options
from firebase_admin import initialize_app, firestore, storage
import json

# Initialize the app once at the top level
initialize_app()

# --- SCORING LOGIC ---
POINTS_PER_ROUND = {'r32': 2, 'r16': 3, 'qf': 5, 'sf': 8, 'f': 13}
ROUNDS = ["r32", "r16", "qf", "sf", "f"]

@firestore_fn.on_document_written(document="tournaments/{tournId}/results/actualResults")
def on_results_update(event: firestore_fn.Event[firestore_fn.Change]) -> None:
    """
    When results are updated, dynamically fetch the correct tournament data from
    Firebase Storage, recalculate all scores, and update the viewerData document.
    This version is backwards-compatible and handles mixed data formats.
    """
    print(f"Triggered by update to: {event.source}")

    tourn_id = event.params["tournId"]
    print(f"Processing scores for tournament: {tourn_id}")

    db = firestore.client()

    # --- Download tournament data from Firebase Storage ---
    try:
        bucket = storage.bucket()
        file_name = f"tournaments/{tourn_id}.json"
        blob = bucket.blob(file_name)

        print(f"Attempting to download data from: {file_name}")
        json_data = blob.download_as_string()
        initial_entrants = json.loads(json_data)
        print("Successfully downloaded and parsed tournament data.")

    except Exception as e:
        print(f"FATAL ERROR: Could not download or parse '{file_name}' from Firebase Storage.")
        print(f"Error details: {e}")
        return

    # --- Fetch other necessary data ---
    participants_ref = db.collection('tournaments', tourn_id, 'participants')
    participants_docs = participants_ref.stream()
    participants = [doc.to_dict() for doc in participants_docs]

    actual_results_data = event.data.after.to_dict()
    actual_results = actual_results_data.get('winners', {})

    # --- Calculation Logic ---
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
            # *** FIX: Reliably get the player NAME, regardless of data format ***
            picked_winner_name = (picked_winner_data[1] if isinstance(picked_winner_data, list) else picked_winner_data).strip()

            round_key = match_id.split('-')[1]
            points = POINTS_PER_ROUND.get(round_key, 0)

            actual_winner_data = actual_results.get(match_id)
            if actual_winner_data:
                # *** FIX: Reliably get the player NAME, regardless of data format ***
                actual_winner_name = (actual_winner_data[1] if isinstance(actual_winner_data, list) else actual_winner_data).strip()

                if picked_winner_name == actual_winner_name:
                    current_score += points
            elif picked_winner_name in active_players:
                potential_score += points

        leaderboard.append({
            "name": p.get('nickname', 'Unknown'),
            "fullName": p.get('fullName', 'Unknown'),
            "score": current_score,
            "max_score": current_score + potential_score,
            "picks": p.get('picks', {})
        })

    leaderboard.sort(key=lambda x: x['score'], reverse=True)

    rank = 0
    last_score = -1
    for i, p in enumerate(leaderboard):
        if p["score"] != last_score:
            rank = i + 1
            last_score = p["score"]
        p['rank'] = rank

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
    for match_id, winner_data in actual_results.items():
        # *** FIX: Reliably get the player NAME, regardless of data format ***
        winner_name = (winner_data[1] if isinstance(winner_data, list) else winner_data).strip()

        category_key = 'mens_draw' if 'mens' in match_id else 'womens_draw'
        parts = match_id.split('-')
        round_key, match_idx = parts[1], int(parts[-1])

        p1_name, p2_name = None, None
        if round_key == 'r32':
            p1_name = initial_entrants[category_key][match_idx]['players'][0][1]
            p2_name = initial_entrants[category_key][match_idx]['players'][1][1]
        else:
            prev_round_idx = ROUNDS.index(round_key) - 1
            prev_round_key = ROUNDS[prev_round_idx]
            p1_match_id = f"{parts[0]}-{prev_round_key}-match-{match_idx * 2}"
            p2_match_id = f"{parts[0]}-{prev_round_key}-match-{match_idx * 2 + 1}"

            p1_data = actual_results.get(p1_match_id)
            if p1_data:
                p1_name = (p1_data[1] if isinstance(p1_data, list) else p1_data).strip()

            p2_data = actual_results.get(p2_match_id)
            if p2_data:
                p2_name = (p2_data[1] if isinstance(p2_data, list) else p2_data).strip()

        if p1_name and p2_name:
            if p1_name == winner_name: eliminated.add(p2_name)
            elif p2_name == winner_name: eliminated.add(p1_name)
    return eliminated

