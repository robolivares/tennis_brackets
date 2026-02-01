from firebase_functions import firestore_fn, options
from firebase_admin import initialize_app, firestore, storage
import json

# Initialize the app once at the top level
initialize_app()

# --- SCORING CONFIGURATION ---
BASE_POINTS = {
    'r128': 1,
    'r64': 1,
    'r32': 2,
    'r16': 3,
    'qf': 5,
    'sf': 8,
    'f': 13
}

ROUNDS = ["r128", "r64", "r32", "r16", "qf", "sf", "f"]

@firestore_fn.on_document_written(document="tournaments/{tournId}/results/actualResults")
def on_results_update(event: firestore_fn.Event[firestore_fn.Change]) -> None:
    tourn_id = event.params["tournId"]
    db = firestore.client()

    try:
        bucket = storage.bucket()
        blob = bucket.blob(f"tournaments/{tourn_id}.json")
        initial_entrants = json.loads(blob.download_as_string())
    except Exception as e:
        print(f"Error loading tournament file: {e}")
        return

    match_count = len(initial_entrants.get('mens_draw', []))
    match_to_round = {64: 'r128', 32: 'r64', 16: 'r32', 8: 'r16'}
    start_round = match_to_round.get(match_count, 'r128')

    actual_results_data = event.data.after.to_dict()
    actual_results = actual_results_data.get('winners', {})

    participants_docs = db.collection('tournaments', tourn_id, 'participants').stream()
    participants = [doc.to_dict() for doc in participants_docs]

    seed_map = {
        'mens': {p[1]: p[0] for m in initial_entrants['mens_draw'] for p in m['players']},
        'womens': {p[1]: p[0] for m in initial_entrants['womens_draw'] for p in m['players']}
    }

    def get_seed_num(name, category):
        seed_str = seed_map.get(category, {}).get(name, "")
        if not seed_str or seed_str in ["Q", "WC", "LL"]: return 0
        return int(''.join(filter(str.isdigit, seed_str)))

    eliminated_players = get_eliminated_players(initial_entrants, actual_results, start_round)
    all_players_set = {p[1] for draw in initial_entrants.values() if isinstance(draw, list) for match in draw for p in match['players']}
    active_players = all_players_set - set(eliminated_players)

    leaderboard = []

    for p in participants:
        if not p.get('isLocked'): continue

        picks = p.get('picks', {})
        current_score = 0
        potential_score = 0

        for match_id, picked_winner_data in picks.items():
            picked_name = (picked_winner_data[1] if isinstance(picked_winner_data, list) else picked_winner_data).strip()

            # FIX: Use startswith to avoid substring collision (e.g., 'womens' containing 'mens')
            category = 'mens' if match_id.startswith('mens') else 'womens'
            round_key = match_id.split('-')[1]
            base_points = BASE_POINTS.get(round_key, 0)

            actual_winner_data = actual_results.get(match_id)

            if actual_winner_data:
                actual_name = (actual_winner_data[1] if isinstance(actual_winner_data, list) else actual_winner_data).strip()

                if picked_name == actual_name:
                    bonus = 0
                    is_week_1 = round_key in ["r128", "r64", "r32"]
                    opp_name = get_opponent_name(match_id, actual_name, initial_entrants, actual_results, start_round)
                    w_seed = get_seed_num(actual_name, category)
                    o_seed = get_seed_num(opp_name, category) if opp_name else 0

                    if w_seed == 0 and o_seed > 0:
                        bonus = 6 if not is_week_1 else 2
                    elif 17 <= w_seed <= 33 and 1 <= o_seed <= 16:
                        bonus = 3 if not is_week_1 else 1

                    current_score += (base_points + bonus)

            elif picked_name in active_players:
                # IMPROVEMENT: Calculate potential based on specific pick's upset potential
                potential_bonus = 0
                is_week_1_pot = round_key in ["r128", "r64", "r32"]
                w_seed_pot = get_seed_num(picked_name, category)

                # Assume "best case" for the user's specific pick
                if w_seed_pot == 0:
                    potential_bonus = 6 if not is_week_1_pot else 2
                elif 17 <= w_seed_pot <= 33:
                    potential_bonus = 3 if not is_week_1_pot else 1

                potential_score += (base_points + potential_bonus)

        leaderboard.append({
            "name": p.get('nickname', 'Unknown'),
            "fullName": p.get('fullName', 'Unknown'),
            "score": current_score,
            "max_score": current_score + potential_score,
            "picks": picks
        })

    leaderboard.sort(key=lambda x: x['score'], reverse=True)
    viewer_data = {
        "participants": leaderboard,
        "actual_results": actual_results,
        "eliminated_players": list(eliminated_players),
        "seed_map": seed_map
    }

    db.collection('tournaments', tourn_id, 'state').document('viewerData').set(viewer_data)

def get_opponent_name(match_id, winner_name, initial_entrants, actual_results, start_round):
    parts = match_id.split('-')

    # FIX: Use startswith for accurate draw selection
    category_key = 'mens_draw' if match_id.startswith('mens') else 'womens_draw'
    round_key, match_idx = parts[1], int(parts[-1])

    if round_key == start_round:
        players = initial_entrants[category_key][match_idx]['players']
        p1, p2 = players[0][1], players[1][1]
        return p2 if p1 == winner_name else p1

    # For later rounds, look at the winners of the previous feeder matches
    prev_round_idx = ROUNDS.index(round_key) - 1
    prev_round_key = ROUNDS[prev_round_idx]
    m1_id = f"{parts[0]}-{prev_round_key}-match-{match_idx * 2}"
    m2_id = f"{parts[0]}-{prev_round_key}-match-{match_idx * 2 + 1}"

    p1_data = actual_results.get(m1_id)
    p2_data = actual_results.get(m2_id)
    p1 = (p1_data[1] if isinstance(p1_data, list) else p1_data) if p1_data else None
    p2 = (p2_data[1] if isinstance(p2_data, list) else p2_data) if p2_data else None

    if p1 and p2:
        return p2 if p1 == winner_name else p1
    return None

def get_eliminated_players(initial_entrants, actual_results, start_round):
    eliminated = set()
    for match_id, winner_data in actual_results.items():
        winner_name = (winner_data[1] if isinstance(winner_data, list) else winner_data).strip()
        parts = match_id.split('-')

        # FIX: Use startswith for accurate draw selection
        category_key = 'mens_draw' if match_id.startswith('mens') else 'womens_draw'
        round_key, match_idx = parts[1], int(parts[-1])

        p1_name, p2_name = None, None
        if round_key == start_round:
            p1_name = initial_entrants[category_key][match_idx]['players'][0][1]
            p2_name = initial_entrants[category_key][match_idx]['players'][1][1]
        else:
            prev_round_idx = ROUNDS.index(round_key) - 1
            prev_round_key = ROUNDS[prev_round_idx]
            p1_data = actual_results.get(f"{parts[0]}-{prev_round_key}-match-{match_idx * 2}")
            p2_data = actual_results.get(f"{parts[0]}-{prev_round_key}-match-{match_idx * 2 + 1}")
            if p1_data: p1_name = (p1_data[1] if isinstance(p1_data, list) else p1_data).strip()
            if p2_data: p2_name = (p2_data[1] if isinstance(p2_data, list) else p2_data).strip()

        if p1_name and p2_name:
            if p1_name == winner_name: eliminated.add(p2_name)
            elif p2_name == winner_name: eliminated.add(p1_name)
    return eliminated
