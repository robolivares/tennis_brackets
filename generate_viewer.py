import os
import csv
import json
import argparse
import re
from collections import defaultdict

# Define ROUNDS globally so it's accessible to all functions
ROUNDS = [
    { "name": "Round of 32", "key": "r32" }, { "name": "Round of 16", "key": "r16" },
    { "name": "Quarterfinals", "key": "qf" }, { "name": "Semifinals", "key": "sf" },
    { "name": "Final", "key": "f" }
]

def parse_entrants(filepath="entrants.txt"):
    """
    Parses the entrants.txt file to get initial matchups, including seeding.
    This is needed to know the original R32 matchups.
    """
    if not os.path.exists(filepath):
        print(f"Error: {filepath} not found. It's needed to build the viewer.")
        return None, None

    mens_matchups = []
    womens_matchups = []
    current_category = None
    player_regex = re.compile(r"\((.*?)\)\s*(.*)|(^[^\(]+)")

    def parse_player(p_str):
        match = player_regex.match(p_str.strip())
        if match:
            if match.group(1) is not None:
                return (match.group(1), match.group(2).strip())
            elif match.group(3) is not None:
                return ("", match.group(3).strip())
        return ("", p_str)

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

            if 'vs' in line and current_category:
                p1_str, p2_str = [p.strip() for p in line.split('vs')]
                player1 = parse_player(p1_str)
                player2 = parse_player(p2_str)

                if current_category == 'mens':
                    mens_matchups.append([player1, player2])
                elif current_category == 'womens':
                    womens_matchups.append([player1, player2])

    return mens_matchups, womens_matchups

def read_prediction_file(filepath):
    """
    Reads a single prediction CSV and returns a dictionary of picks.
    Safely skips blank or malformed rows.
    """
    picks = {}
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            try:
                next(reader)  # Skip header
            except StopIteration:
                return {} # Handle empty file

            for i, row in enumerate(reader):
                if not row:  # Skips blank lines
                    continue

                if len(row) != 4:
                    print(f"Warning: Skipping malformed row #{i+2} in {os.path.basename(filepath)}: {row}")
                    continue

                _, _, match_id, predicted_winner = row
                if predicted_winner and predicted_winner.strip() != "NONE":
                    picks[match_id.strip()] = predicted_winner.strip()
    except Exception as e:
        print(f"Warning: Could not read or process file {filepath}. Error: {e}")
        return None
    return picks

def get_active_players(initial_entrants, actual_results, debug=False):
    """Determines which players are still in the tournament."""
    all_players = set()
    for category in ['mens', 'womens']:
        for matchup in initial_entrants[category]:
            all_players.add(matchup[0][1])
            all_players.add(matchup[1][1])

    eliminated = set()
    actual_matchups = {}

    if debug: print("\n--- DEBUG: Building Actual Matchups Map ---")
    for category in ['mens', 'womens']:
        for round_index, round_info in enumerate(ROUNDS):
            num_matches = 16 // (2**round_index)
            for match_idx in range(num_matches):
                match_id = f"{category}-{round_info['key']}-match-{match_idx}"
                p1, p2 = None, None
                if round_index == 0:
                    entrants_list = initial_entrants[category]
                    if match_idx < len(entrants_list):
                        p1 = entrants_list[match_idx][0][1]
                        p2 = entrants_list[match_idx][1][1]
                else:
                    prev_round_key = ROUNDS[round_index - 1]['key']
                    p1_match_id = f"{category}-{prev_round_key}-match-{match_idx * 2}"
                    p2_match_id = f"{category}-{prev_round_key}-match-{match_idx * 2 + 1}"
                    p1 = actual_results.get(p1_match_id)
                    p2 = actual_results.get(p2_match_id)

                if p1 and p2:
                    actual_matchups[match_id] = (p1, p2)
                    if debug: print(f"  Mapping {match_id}: {p1} vs {p2}")

    if debug: print("\n--- DEBUG: Determining Eliminated Players ---")
    for match_id, winner in actual_results.items():
        if match_id in actual_matchups:
            p1, p2 = actual_matchups[match_id]
            loser = p2 if winner == p1 else p1
            eliminated.add(loser)
            if debug: print(f"  Match {match_id}: {winner} def. {loser}. Adding {loser} to eliminated set.")

    active = all_players - eliminated
    if debug:
        print("\n--- DEBUG: Final Active Players List ---")
        print(sorted(list(active)))
        print("-----------------------------------------")
    return active

def calculate_scores(picks, actual_results, points_per_round):
    """Calculates the current score for a set of picks."""
    current_score = 0
    for match_id, predicted_winner in picks.items():
        if match_id in actual_results and predicted_winner == actual_results.get(match_id):
            round_key = match_id.split('-')[1]
            current_score += points_per_round.get(round_key, 0)
    return current_score

def calculate_max_score(picks, current_score, active_players, points_per_round, actual_results, debug=False):
    """Calculates the maximum possible score for a set of picks."""
    potential_points = 0
    if debug: print(f"\n--- Calculating Max Score (Starting with Current Score: {current_score}) ---")

    for match_id, predicted_winner in sorted(picks.items()):
        if match_id not in actual_results:
            is_alive = predicted_winner in active_players
            round_key = match_id.split('-')[1]
            points = points_per_round.get(round_key, 0)

            if debug:
                status = "ALIVE" if is_alive else "ELIMINATED"
                print(f"  - Checking future match '{match_id}': Pick = {predicted_winner} ({status})")

            if is_alive:
                potential_points += points
                if debug: print(f"    > Player is active. Adding {points} potential points.")
            elif debug:
                print(f"    > Player is eliminated. No points added.")

    if debug: print(f"  >>> Final Calculation: {current_score} (current) + {potential_points} (potential)")
    return current_score + potential_points

def create_viewer_data(predictions_dir, entrants_file, debug=False):
    """Reads all prediction files, calculates scores, and structures data."""
    master_filename = "actual_results_predictions.csv"
    points_per_round = {'r32': 2, 'r16': 3, 'qf': 5, 'sf': 8, 'f': 13}

    mens_entrants, womens_entrants = parse_entrants(entrants_file)
    if mens_entrants is None:
        return None

    initial_entrants = {"mens": mens_entrants, "womens": womens_entrants}
    mens_seed_map = {name: seed for seed, name in [player for matchup in mens_entrants for player in matchup]}
    womens_seed_map = {name: seed for seed, name in [player for matchup in womens_entrants for player in matchup]}

    viewer_data = {
        "initial_entrants": initial_entrants,
        "seed_map": { "mens": mens_seed_map, "womens": womens_seed_map },
        "actual_results": None,
        "participants": []
    }

    master_filepath = os.path.join(predictions_dir, master_filename)
    if not os.path.exists(master_filepath):
        print(f"Error: The master results file '{master_filename}' was not found in '{predictions_dir}'.")
        return None

    viewer_data["actual_results"] = read_prediction_file(master_filepath)
    if viewer_data["actual_results"] is None:
        return None

    active_players = get_active_players(initial_entrants, viewer_data["actual_results"], debug)

    for filename in sorted(os.listdir(predictions_dir)):
        if filename.endswith("_predictions.csv") and filename != master_filename:
            filepath = os.path.join(predictions_dir, filename)
            player_name = filename.replace("_predictions.csv", "").replace("_", " ").title()
            picks = read_prediction_file(filepath)
            if picks:
                if debug: print(f"\n--- Processing: {player_name} ---")
                current_score = calculate_scores(picks, viewer_data["actual_results"], points_per_round)
                if debug: print(f"  Current Score: {current_score}")
                max_score = calculate_max_score(picks, current_score, active_players, points_per_round, viewer_data["actual_results"], debug)
                if debug: print(f"  >>> Final Max Score for {player_name}: {max_score}")

                viewer_data["participants"].append({
                    "name": player_name,
                    "picks": picks,
                    "score": current_score,
                    "max_score": max_score
                })

    viewer_data["participants"].sort(key=lambda p: p["score"], reverse=True)
    return viewer_data

def generate_leaderboard_html(participants):
    """Generates the HTML table for the leaderboard."""
    if not participants: return ""

    table_rows = ""
    for i, p in enumerate(participants):
        name_key = p['name'].replace(' ', '-')
        tab_id = f"{name_key}-tab"
        table_rows += f"""
        <tr onclick="goToTab('{tab_id}')" style="cursor: pointer;">
            <td>{i + 1}</td>
            <td>{p['name']}</td>
            <td>{p['score']}</td>
            <td>{p['max_score']}</td>
        </tr>
        """

    return f"""
    <div class="leaderboard-container">
        <h3>Leaderboard</h3>
        <table>
            <thead>
                <tr>
                    <th>Rank</th>
                    <th>Name</th>
                    <th>Current Score</th>
                    <th>Max Possible</th>
                </tr>
            </thead>
            <tbody>
                {table_rows}
            </tbody>
        </table>
    </div>
    """

def generate_viewer_html(viewer_data, output_path):
    """Generates the master viewer HTML file with all data embedded."""

    leaderboard_html = generate_leaderboard_html(viewer_data["participants"])

    html_template = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Tournament Bracket Viewer</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;700&display=swap" rel="stylesheet">
    <style>
        body {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            margin: 0; padding: 2em;
            background-color: #f0f4f7; color: #333;
        }}
        h1, h2, h3 {{ text-align: center; color: #005A31; }}
        h1 {{ font-size: 2.5em; margin-bottom: 0.25em; }}
        h2 {{ font-size: 2em; margin-top: 1.5em; border-bottom: 3px solid #4A0072; padding-bottom: 0.5em; }}
        h3 {{ font-size: 1.2em; margin-bottom: 1em; color: #4A0072; }}

        .leaderboard-container {{ max-width: 600px; margin: 2em auto; }}
        table {{ width: 100%; border-collapse: collapse; background-color: #fff; box-shadow: 0 4px 8px rgba(0,0,0,0.1); border-radius: 8px; overflow: hidden; }}
        th, td {{ padding: 12px 15px; text-align: left; }}
        thead tr {{ background-color: #4A0072; color: #fff; font-size: 1.1em; }}
        tbody tr:nth-of-type(even) {{ background-color: #f8f9fa; }}
        tbody tr {{ border-bottom: 1px solid #ddd; }}
        tbody tr:hover {{ background-color: #f0e6f6; }}
        td:first-child {{ font-weight: bold; }}

        .tab-nav {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 10px; margin: 2em auto; max-width: 1200px; }}
        .tab-button {{ padding: 0.8em 1.5em; font-size: 1em; font-weight: bold; border: 2px solid #4A0072; background-color: #fff; color: #4A0072; border-radius: 8px; cursor: pointer; transition: background-color 0.2s, color 0.2s; text-align: center; }}
        .tab-button:hover {{ background-color: #f0e6f6; }}
        .tab-button.active {{ background-color: #4A0072; color: #fff; }}

        .tab-content {{ display: none; }}
        .tab-content.active {{ display: block; }}

        .bracket-container {{ display: flex; align-items: stretch; justify-content: flex-start; overflow-x: auto; padding: 20px; -webkit-overflow-scrolling: touch; }}
        .round {{ display: flex; flex-direction: column; flex-shrink: 0; margin: 0 15px; }}
        .round-title {{ font-size: 1.2em; font-weight: bold; text-align: center; margin-bottom: 30px; color: #4A0072; min-width: 270px; }}
        .matchup-wrapper {{ display: flex; flex-direction: column; justify-content: space-around; flex-grow: 1; }}

        .matchup {{ background-color: #fff; padding: 10px 15px; border-radius: 8px; box-shadow: 0 4px 8px rgba(0,0,0,0.1); width: 270px; position: relative; }}
        .matchup-wrapper > .matchup:not(:last-child) {{ margin-bottom: 28px; }}

        .player {{ display: flex; align-items: center; margin: 8px 0; border-radius: 5px; }}
        .player-seed {{ font-size: 0.8em; color: #888; width: 30px; text-align: center; font-weight: 700; }}
        .player-name {{ flex-grow: 1; font-size: 1em; color: #333; }}
        .player-name.winner {{ font-weight: bold; color: #005A31; }}
        .tbd {{ font-style: italic; color: #999; }}

        .player-name.correct-pick {{ background-color: #d4edda; border-radius: 3px; padding: 2px 4px; }}
        .player-name.incorrect-pick {{ background-color: #f8d7da; text-decoration: line-through; border-radius: 3px; padding: 2px 4px; }}
        .actual-winner-note {{ font-size: 0.8em; color: #005A31; margin-left: 5px; padding-top: 5px; }}

        .champion-container {{ display: flex; align-items: center; justify-content: center; }}
        .champion-box {{ display: flex; flex-direction: column; align-items: center; justify-content: center; }}
        .champion-trophy {{ font-size: 4em; color: #d4af37; line-height: 1; }}
        .champion-name {{ font-size: 1.5em; font-weight: bold; color: #005A31; background-color: #fff; padding: 10px 20px; border-radius: 8px; box-shadow: 0 4px 8px rgba(0,0,0,0.1); min-height: 30px; text-align: center; }}
    </style>
</head>
<body>
    <h1>Tournament Results Viewer</h1>
    <h3>Scoring System: R32 (2pts), R16 (3pts), QF (5pts), SF (8pts), Final (13pts)</h3>
    {leaderboard_html}
    <div id="tab-navigation" class="tab-nav"></div>
    <div id="tab-contents"></div>
    <div id="tab-navigation-bottom" class="tab-nav" style="margin-top: 2em; border-top: 2px solid #ddd; padding-top: 1em;"></div>

    <script>
        const viewerData = {json.dumps(viewer_data, indent=4)};

        const ROUNDS = [
            {{ "name": "Round of 32", "key": "r32" }},
            {{ "name": "Round of 16", "key": "r16" }},
            {{ "name": "Quarterfinals", "key": "qf" }},
            {{ "name": "Semifinals", "key": "sf" }},
            {{ "name": "Final", "key": "f" }}
        ];

        function createBracketDisplay(container, category, participantPicks) {{
            container.innerHTML = '';

            ROUNDS.forEach((round, roundIndex) => {{
                const roundDiv = document.createElement('div');
                roundDiv.classList.add('round');
                const roundTitle = document.createElement('div');
                roundTitle.classList.add('round-title');
                roundTitle.textContent = round.name;
                roundDiv.appendChild(roundTitle);
                const matchupWrapper = document.createElement('div');
                matchupWrapper.classList.add('matchup-wrapper');

                const numMatches = 16 / Math.pow(2, roundIndex);
                for (let i = 0; i < numMatches; i++) {{
                    const matchupId = `${{category}}-${{round.key}}-match-${{i}}`;
                    const matchupDiv = document.createElement('div');
                    matchupDiv.classList.add('matchup');

                    let player1, player2;

                    if (roundIndex === 0) {{
                        player1 = viewerData.initial_entrants[category][i][0];
                        player2 = viewerData.initial_entrants[category][i][1];
                    }} else {{
                        const prevRoundKey = ROUNDS[roundIndex - 1].key;
                        const p1MatchupId = `${{category}}-${{prevRoundKey}}-match-${{i * 2}}`;
                        const p2MatchupId = `${{category}}-${{prevRoundKey}}-match-${{i * 2 + 1}}`;

                        const p1Name = participantPicks[p1MatchupId] || "TBD";
                        const p2Name = participantPicks[p2MatchupId] || "TBD";

                        const p1Seed = viewerData.seed_map[category][p1Name] || "";
                        const p2Seed = viewerData.seed_map[category][p2Name] || "";

                        player1 = [p1Seed, p1Name];
                        player2 = [p2Seed, p2Name];
                    }}

                    const predictedWinner = participantPicks[matchupId];
                    const actualWinner = viewerData.actual_results[matchupId];

                    const p1Classes = ['player-name'];
                    if (predictedWinner === player1[1]) p1Classes.push('winner');

                    const p2Classes = ['player-name'];
                    if (predictedWinner === player2[1]) p2Classes.push('winner');

                    if (participantPicks !== viewerData.actual_results && predictedWinner && actualWinner) {{
                        const winnerSpanClasses = (predictedWinner === player1[1]) ? p1Classes : p2Classes;
                        if (predictedWinner === actualWinner) {{
                            winnerSpanClasses.push('correct-pick');
                        }} else {{
                            winnerSpanClasses.push('incorrect-pick');
                        }}
                    }}

                    matchupDiv.innerHTML = `
                        <div class="player"><span class="player-seed">${{player1[0]}}</span><span class="${{p1Classes.join(' ')}}">${{player1[1]}}</span></div>
                        <div class="player"><span class="player-seed">${{player2[0]}}</span><span class="${{p2Classes.join(' ')}}">${{player2[1]}}</span></div>
                    `;

                    if (participantPicks !== viewerData.actual_results && predictedWinner && actualWinner && predictedWinner !== actualWinner) {{
                        const note = document.createElement('div');
                        note.className = 'actual-winner-note';
                        note.textContent = `Actual: ${{actualWinner}}`;
                        matchupDiv.appendChild(note);
                    }}
                    matchupWrapper.appendChild(matchupDiv);
                }}
                roundDiv.appendChild(matchupWrapper);
                container.appendChild(roundDiv);
            }});

            const championContainer = document.createElement('div');
            championContainer.classList.add('champion-container');
            const finalWinner = participantPicks[`${{category}}-f-match-0`] || "";
            championContainer.innerHTML = `<div class="champion-box"><div class="champion-trophy">&#127942;</div><div class="champion-name">${{finalWinner}}</div></div>`;
            container.appendChild(championContainer);
        }}

        function goToTab(tabId) {{
            const button = document.querySelector(`.tab-button[data-tab-id='${{tabId}}']`);
            if (button) {{
                openTab(tabId);
                button.scrollIntoView({{ behavior: 'smooth', block: 'nearest' }});
            }}
        }}

        function openTab(tabId) {{
            document.querySelectorAll('.tab-content').forEach(tab => tab.style.display = 'none');
            document.querySelectorAll('.tab-button').forEach(btn => btn.classList.remove('active'));

            document.getElementById(tabId).style.display = 'block';
            document.querySelectorAll(`[data-tab-id="${{tabId}}"]`).forEach(b => b.classList.add('active'));
        }}

        function setupViewer() {{
            const navContainer = document.getElementById('tab-navigation');
            const contentContainer = document.getElementById('tab-contents');

            const allParticipants = [{{"name": "Actual Results", "picks": viewerData.actual_results, "score": null}}, ...viewerData.participants];

            allParticipants.forEach((p, index) => {{
                const nameKey = p.name.replace(/\\s+/g, '-');
                const tabId = `${{nameKey}}-tab`;

                const btn = document.createElement('button');
                btn.className = 'tab-button';
                btn.textContent = p.name;
                btn.dataset.tabId = tabId;
                btn.onclick = () => openTab(tabId);
                navContainer.appendChild(btn);

                const tab = document.createElement('div');
                tab.id = tabId;
                tab.className = 'tab-content';

                let scoreHtml = p.name !== "Actual Results" ? `<h3>Total Score: ${{p.score}} pts | Max Possible: ${{p.max_score}} pts</h3>` : '';

                tab.innerHTML = scoreHtml + `
                    <h2>Men's Singles</h2><div id="${{nameKey}}-mens-bracket" class="bracket-container"></div>
                    <h2>Women's Singles</h2><div id="${{nameKey}}-womens-bracket" class="bracket-container"></div>`;
                contentContainer.appendChild(tab);

                createBracketDisplay(tab.querySelector(`#${{nameKey}}-mens-bracket`), 'mens', p.picks);
                createBracketDisplay(tab.querySelector(`#${{nameKey}}-womens-bracket`), 'womens', p.picks);

                if (index === 0) {{
                    btn.classList.add('active');
                    tab.style.display = 'block';
                }}
            }});

            const bottomNavContainer = document.getElementById('tab-navigation-bottom');
            bottomNavContainer.innerHTML = navContainer.innerHTML;
            bottomNavContainer.querySelectorAll('.tab-button').forEach(btn => {{
                const tabId = btn.dataset.tabId;
                btn.onclick = () => openTab(tabId);
            }});
        }}

        setupViewer();
    </script>
</body>
</html>
    """
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_template)
    print(f"Successfully generated viewer HTML at: {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate a master viewer HTML for tournament brackets.")
    parser.add_argument(
        '-b', '--board',
        required=True,
        metavar='DIRECTORY',
        help="Directory containing all prediction files."
    )
    parser.add_argument(
        '-e', '--entrants',
        default='entrants.txt',
        help="Path to the entrants.txt file (default: entrants.txt)."
    )
    parser.add_argument(
        '--debug',
        action='store_true',
        help="Enable debug printing to the console."
    )
    args = parser.parse_args()

    if not os.path.isdir(args.board):
        print(f"Error: Directory '{args.board}' not found.")
    else:
        viewer_data = create_viewer_data(args.board, args.entrants, args.debug)
        if viewer_data:
            output_filename = "index.html"
            output_filepath = os.path.join(args.board, output_filename)
            generate_viewer_html(viewer_data, output_filepath)

