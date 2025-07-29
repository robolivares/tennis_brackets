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
                    continue

                _, _, match_id, predicted_winner = row
                if predicted_winner and predicted_winner.strip() != "NONE":
                    picks[match_id.strip()] = predicted_winner.strip()
    except Exception as e:
        print(f"Warning: Could not read or process file {filepath}. Error: {e}")
        return None
    return picks

def get_active_and_eliminated_players(initial_entrants, actual_results, debug=False):
    """
    Determines which players are still in the tournament and which are out.
    This new logic correctly identifies losers from each match.
    """
    all_players_in_draw = set()
    for category in ['mens', 'womens']:
        for matchup in initial_entrants[category]:
            all_players_in_draw.add(matchup[0][1])
            all_players_in_draw.add(matchup[1][1])

    # First, reconstruct the actual matchups that have been played
    actual_matchups = {}
    for category in ['mens', 'womens']:
        for round_index, round_info in enumerate(ROUNDS):
            num_matches = 16 // (2**round_index)
            for match_idx in range(num_matches):
                match_id = f"{category}-{round_info['key']}-match-{match_idx}"
                if match_id in actual_results:
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

    # NEW, CORRECTED LOGIC: Explicitly find the loser of each match
    eliminated = set()
    for match_id, players in actual_matchups.items():
        p1, p2 = players
        winner = actual_results.get(match_id)
        # Add the player who is NOT the winner to the eliminated set
        if p1 == winner:
            eliminated.add(p2)
        elif p2 == winner:
            eliminated.add(p1)

    active = all_players_in_draw - eliminated

    return active, list(eliminated)

def calculate_scores(picks, actual_results, points_per_round):
    """Calculates the current score for a set of picks."""
    current_score = 0
    for match_id, predicted_winner in picks.items():
        if match_id in actual_results and predicted_winner == actual_results.get(match_id):
            round_key = match_id.split('-')[1]
            current_score += points_per_round.get(round_key, 0)
    return current_score

def calculate_max_score(picks, current_score, active_players, points_per_round, actual_results):
    """Calculates the maximum possible score for a set of picks."""
    potential_points = 0
    for match_id, predicted_winner in picks.items():
        if match_id not in actual_results:
            if predicted_winner in active_players:
                round_key = match_id.split('-')[1]
                potential_points += points_per_round.get(round_key, 0)
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
        "participants": [],
        "eliminated_players": []
    }

    master_filepath = os.path.join(predictions_dir, master_filename)
    if not os.path.exists(master_filepath):
        print(f"Error: The master results file '{master_filename}' was not found in '{predictions_dir}'.")
        return None

    viewer_data["actual_results"] = read_prediction_file(master_filepath)
    if viewer_data["actual_results"] is None:
        return None

    active_players, eliminated_players = get_active_and_eliminated_players(initial_entrants, viewer_data["actual_results"], debug)
    viewer_data["eliminated_players"] = eliminated_players

    for filename in sorted(os.listdir(predictions_dir)):
        if filename.endswith("_predictions.csv") and filename != master_filename:
            filepath = os.path.join(predictions_dir, filename)
            player_name = filename.replace("_predictions.csv", "").replace("_", " ").title()
            picks = read_prediction_file(filepath)
            if picks:
                current_score = calculate_scores(picks, viewer_data["actual_results"], points_per_round)
                max_score = calculate_max_score(picks, current_score, active_players, points_per_round, viewer_data["actual_results"])

                viewer_data["participants"].append({
                    "name": player_name,
                    "picks": picks,
                    "score": current_score,
                    "max_score": max_score
                })

    viewer_data["participants"].sort(key=lambda p: p["score"], reverse=True)

    # Assign ranks, handling ties (e.g., 1, 2, 2, 4)
    rank = 0
    last_score = -1
    for i, p in enumerate(viewer_data["participants"]):
        # Check if the score is different from the last participant's score
        if p["score"] != last_score:
            rank = i + 1  # Update rank to the current position (1-based index)
            last_score = p["score"]
        p['rank'] = rank # Assign the calculated rank

    return viewer_data

def generate_leaderboard_html(participants):
    """Generates the HTML table for the leaderboard."""
    if not participants: return ""

    return f"""
    <div class="leaderboard-container">
        <h3>Leaderboard</h3>
        <table>
            <thead>
                <tr>
                    <th>Rank</th>
                    <th>Name</th>
                    <th onclick="sortTable('score')" style="cursor: pointer;">Current Score &#x2195;</th>
                    <th onclick="sortTable('max_score')" style="cursor: pointer;">Max Possible &#x2195;</th>
                </tr>
            </thead>
            <tbody id="leaderboard-body">
            </tbody>
        </table>
    </div>
    """

def generate_viewer_html(viewer_data, output_path):
    """Generates the master viewer HTML file with all data embedded."""

    leaderboard_html = generate_leaderboard_html(viewer_data["participants"])

    # Break the HTML into parts to avoid f-string parsing issues with JS/CSS.
    html_part1 = f"""
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
        thead th {{ cursor: pointer; white-space: nowrap; }}
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
        .bracket-container {{
            position: relative;
            display: flex;
            align-items: stretch;
            justify-content: flex-start;
            overflow-x: auto;
            padding: 20px;
            -webkit-overflow-scrolling: touch;
        }}
        .round {{ display: flex; flex-direction: column; flex-shrink: 0; margin: 0 15px; }}
        .round-title {{ font-size: 1.2em; font-weight: bold; text-align: center; margin-bottom: 30px; color: #4A0072; min-width: 270px; transition: color 0.2s; }}
        .round-title:hover {{ color: #005A31; text-decoration: underline; }}
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
        .player-name.eliminated-player {{ text-decoration: line-through; color: #999; }}
        .actual-winner-note {{ font-size: 0.8em; color: #005A31; margin-left: 5px; padding-top: 5px; }}
        .champion-container {{ display: flex; align-items: center; justify-content: center; }}
        .champion-box {{ display: flex; flex-direction: column; align-items: center; justify-content: center; }}
        .champion-trophy {{ font-size: 4em; color: #d4af37; line-height: 1; }}
        .champion-name {{ font-size: 1.5em; font-weight: bold; color: #005A31; background-color: #fff; padding: 10px 20px; border-radius: 8px; box-shadow: 0 4px 8px rgba(0,0,0,0.1); min-height: 30px; text-align: center; }}
        footer {{
            text-align: center;
            margin-top: 3em;
            padding-top: 1.5em;
            border-top: 1px solid #ccc;
            font-size: 1em;
            font-weight: bold;
            color: #555;
        }}
    </style>
</head>
<body>
    <h1>Tournament Results Viewer</h1>
    <h3>Scoring System: R32 (2pts), R16 (3pts), QF (5pts), SF (8pts), Final (13pts)</h3>
    {leaderboard_html}
    <div id="tab-navigation" class="tab-nav"></div>
    <div id="tab-contents"></div>
    <div id="tab-navigation-bottom" class="tab-nav" style="margin-top: 2em; border-top: 2px solid #ddd; padding-top: 1em;"></div>

    <footer>
        This bracket was served up by Rob Olivares.
    </footer>

    <script>
        const viewerData =
"""

    html_part2 = """
        const ROUNDS = [
            { "name": "Round of 32", "key": "r32" },
            { "name": "Round of 16", "key": "r16" },
            { "name": "Quarterfinals", "key": "qf" },
            { "name": "Semifinals", "key": "sf" },
            { "name": "Final", "key": "f" }
        ];

        function createBracketDisplay(container, category, participantPicks) {
            container.innerHTML = '';

            ROUNDS.forEach((round, roundIndex) => {
                const roundDiv = document.createElement('div');
                roundDiv.classList.add('round');
                const roundTitle = document.createElement('div');
                roundTitle.classList.add('round-title');
                roundTitle.textContent = round.name;
                roundTitle.style.cursor = 'pointer';
                roundTitle.onclick = () => {
                    container.scrollTo({
                        left: roundDiv.offsetLeft,
                        behavior: 'smooth'
                    });
                };
                roundDiv.appendChild(roundTitle);
                const matchupWrapper = document.createElement('div');
                matchupWrapper.classList.add('matchup-wrapper');

                const numMatches = 16 / Math.pow(2, roundIndex);
                for (let i = 0; i < numMatches; i++) {
                    const matchupId = `${category}-${round.key}-match-${i}`;
                    const matchupDiv = document.createElement('div');
                    matchupDiv.classList.add('matchup');

                    let player1, player2;

                    if (roundIndex === 0) {
                        player1 = viewerData.initial_entrants[category][i][0];
                        player2 = viewerData.initial_entrants[category][i][1];
                    } else {
                        const prevRoundKey = ROUNDS[roundIndex - 1].key;
                        const p1MatchupId = `${category}-${prevRoundKey}-match-${i * 2}`;
                        const p2MatchupId = `${category}-${prevRoundKey}-match-${i * 2 + 1}`;

                        const p1Name = participantPicks[p1MatchupId] || "TBD";
                        const p2Name = participantPicks[p2MatchupId] || "TBD";

                        const p1Seed = viewerData.seed_map[category][p1Name] || "";
                        const p2Seed = viewerData.seed_map[category][p2Name] || "";

                        player1 = [p1Seed, p1Name];
                        player2 = [p2Seed, p2Name];
                    }

                    const predictedWinner = participantPicks[matchupId];
                    const actualWinner = viewerData.actual_results[matchupId];

                    const p1Classes = ['player-name'];
                    if (predictedWinner === player1[1]) p1Classes.push('winner');
                    if (viewerData.eliminated_players.includes(player1[1])) {
                        p1Classes.push('eliminated-player');
                    }

                    const p2Classes = ['player-name'];
                    if (predictedWinner === player2[1]) p2Classes.push('winner');
                    if (viewerData.eliminated_players.includes(player2[1])) {
                        p2Classes.push('eliminated-player');
                    }

                    if (participantPicks !== viewerData.actual_results && predictedWinner && actualWinner) {
                        const winnerSpanClasses = (predictedWinner === player1[1]) ? p1Classes : p2Classes;
                        if (predictedWinner === actualWinner) {
                            winnerSpanClasses.push('correct-pick');
                        } else {
                            winnerSpanClasses.push('incorrect-pick');
                        }
                    }

                    matchupDiv.innerHTML = `
                        <div class="player"><span class="player-seed">${player1[0]}</span><span class="${p1Classes.join(' ')}">${player1[1]}</span></div>
                        <div class="player"><span class="player-seed">${player2[0]}</span><span class="${p2Classes.join(' ')}">${player2[1]}</span></div>
                    `;

                    if (participantPicks !== viewerData.actual_results && predictedWinner && actualWinner && predictedWinner !== actualWinner) {
                        const note = document.createElement('div');
                        note.className = 'actual-winner-note';
                        note.textContent = `Actual: ${actualWinner}`;
                        matchupDiv.appendChild(note);
                    }
                    matchupWrapper.appendChild(matchupDiv);
                }
                roundDiv.appendChild(matchupWrapper);
                container.appendChild(roundDiv);
            });

            const championContainer = document.createElement('div');
            championContainer.classList.add('champion-container');
            const finalWinner = participantPicks[`${category}-f-match-0`] || "";
            championContainer.innerHTML = `<div class="champion-box"><div class="champion-trophy">&#127942;</div><div class="champion-name">${finalWinner}</div></div>`;
            container.appendChild(championContainer);
        }

        function goToTab(tabId) {
            const button = document.querySelector(`.tab-button[data-tab-id='${tabId}']`);
            if (button) {
                openTab(tabId);
                button.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
            }
        }

        function setDefaultScrollView(container) {
            const roundToView = container.querySelectorAll('.round')[2];
            if (roundToView) {
                setTimeout(() => {
                    container.scrollTo({ left: roundToView.offsetLeft, behavior: 'auto' });
                }, 0);
            }
        }

        function openTab(tabId) {
            document.querySelectorAll('.tab-content').forEach(tab => tab.style.display = 'none');
            document.querySelectorAll('.tab-button').forEach(btn => btn.classList.remove('active'));

            const tabToShow = document.getElementById(tabId);
            if (tabToShow) {
                tabToShow.style.display = 'block';
                const bracketContainers = tabToShow.querySelectorAll('.bracket-container');
                bracketContainers.forEach(container => setDefaultScrollView(container));
            }

            document.querySelectorAll(`[data-tab-id="${tabId}"]`).forEach(b => b.classList.add('active'));
        }

        function sortTable(sortBy) {
            const sortedParticipants = [...viewerData.participants].sort((a, b) => b[sortBy] - a[sortBy]);
            renderLeaderboard(sortedParticipants);
        }

        function renderLeaderboard(participants) {
            const tbody = document.getElementById('leaderboard-body');
            tbody.innerHTML = '';
            participants.forEach(p => {
                const nameKey = p.name.replace(/\\s+/g, '-');
                const tabId = `${nameKey}-tab`;
                const row = document.createElement('tr');
                row.style.cursor = 'pointer';
                row.onclick = () => goToTab(tabId);
                row.innerHTML = `
                    <td>${p.rank}</td>
                    <td>${p.name}</td>
                    <td>${p.score}</td>
                    <td>${p.max_score}</td>
                `;
                tbody.appendChild(row);
            });
        }

        function setupViewer() {
            const navContainer = document.getElementById('tab-navigation');
            const contentContainer = document.getElementById('tab-contents');
            let firstTabId = '';

            renderLeaderboard(viewerData.participants);

            const allParticipants = [{"name": "Actual Results", "picks": viewerData.actual_results, "score": null}, ...viewerData.participants];

            allParticipants.forEach((p, index) => {
                const nameKey = p.name.replace(/\\s+/g, '-');
                const tabId = `${nameKey}-tab`;

                if (index === 0) {
                    firstTabId = tabId;
                }

                const btn = document.createElement('button');
                btn.className = 'tab-button';
                btn.textContent = p.name;
                btn.dataset.tabId = tabId;
                btn.onclick = () => openTab(tabId);
                navContainer.appendChild(btn);

                const tab = document.createElement('div');
                tab.id = tabId;
                tab.className = 'tab-content';

                let scoreHtml = p.name !== "Actual Results" ? `<h3>Total Score: ${p.score} pts | Max Possible: ${p.max_score} pts</h3>` : '';

                tab.innerHTML = scoreHtml + `
                    <h2>Men's Singles</h2><div id="${nameKey}-mens-bracket" class="bracket-container"></div>
                    <h2>Women's Singles</h2><div id="${nameKey}-womens-bracket" class="bracket-container"></div>`;
                contentContainer.appendChild(tab);

                const mensBracketContainer = tab.querySelector(`#${nameKey}-mens-bracket`);
                const womensBracketContainer = tab.querySelector(`#${nameKey}-womens-bracket`);

                createBracketDisplay(mensBracketContainer, 'mens', p.picks);
                createBracketDisplay(womensBracketContainer, 'womens', p.picks);
            });

            const bottomNavContainer = document.getElementById('tab-navigation-bottom');
            bottomNavContainer.innerHTML = navContainer.innerHTML;
            bottomNavContainer.querySelectorAll('.tab-button').forEach(btn => {
                const tabId = btn.dataset.tabId;
                btn.onclick = () => openTab(tabId);
            });

            if (firstTabId) {
                openTab(firstTabId);
            }
        }

        setupViewer();
    </script>
</body>
</html>
"""
    html_template = html_part1 + json.dumps(viewer_data, indent=4) + ";" + html_part2

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_template)
    print(f"Successfully generated viewer HTML at: {output_path}")

def export_scores_to_csv(participants, output_path):
    """
    Exports the participant scores to a CSV file, sorted alphabetically by name.
    """
    if not participants:
        print("No participant data to export.")
        return

    # Sort participants alphabetically by name
    sorted_participants = sorted(participants, key=lambda p: p['name'])

    try:
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            # Write the header row
            writer.writerow(['Name', 'Current Score'])
            # Write the data for each participant
            for p in sorted_participants:
                writer.writerow([p['name'], p['score']])
        print(f"Successfully exported scores to: {output_path}")
    except Exception as e:
        print(f"Error exporting scores to CSV: {e}")


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
    # New argument for CSV output
    parser.add_argument(
        '--output',
        metavar='FILENAME.CSV',
        help="Optional: Export scores to a CSV file, sorted alphabetically."
    )
    args = parser.parse_args()

    if not os.path.isdir(args.board):
        print(f"Error: Directory '{args.board}' not found.")
    else:
        viewer_data = create_viewer_data(args.board, args.entrants, args.debug)
        if viewer_data:
            # Generate the HTML viewer file
            output_filename = "index.html"
            output_filepath = os.path.join(args.board, output_filename)
            generate_viewer_html(viewer_data, output_filepath)

            # Check if the --output flag was used and export to CSV if so
            if args.output:
                export_scores_to_csv(viewer_data['participants'], args.output)

