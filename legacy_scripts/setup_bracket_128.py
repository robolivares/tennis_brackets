import json
import os
import csv
import re

def parse_entrants(filepath="entrants_128.txt"):
    """
    Parses the entrants_128.txt file to get initial matchups for a 128-player draw.
    Expects 64 matchups per category.
    """
    if not os.path.exists(filepath):
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

def generate_html(mens_matchups, womens_matchups, output_path="bracket_128.html"):
    """
    Generates the full 128-player interactive HTML bracket file with a linear layout,
    review screen, and dev mode.
    """
    js_matchups = {"mens": mens_matchups, "womens": womens_matchups}

    google_form_config = {
        "action_url": "https://docs.google.com/forms/d/e/1FAIpQLScZYp9PTDpzzOUJD7tXRG8hzMy3Lah_h1bERTQozYz65eD-4g/formResponse",
        "name_entry": "entry.2093168041",
        "data_entry": "entry.1061406125"
    }

    html_template = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Full Tournament Bracket Challenge</title>
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
        .instructions {{ max-width: 600px; margin: 0 auto 2em auto; padding: 1em; background-color: #e6f3ff; border: 1px solid #b3d9ff; border-radius: 8px; text-align: left; }}
        .instructions ol {{ padding-left: 25px; margin: 0; }}

        .bracket-container {{ display: flex; align-items: stretch; justify-content: flex-start; overflow-x: auto; padding: 20px; -webkit-overflow-scrolling: touch; background-color: #e9ecef; border-radius: 8px; margin-top: 1em;}}
        .round {{ display: flex; flex-direction: column; flex-shrink: 0; margin: 0 15px; }}
        .round-title {{ font-size: 1.2em; font-weight: bold; text-align: center; margin-bottom: 30px; color: #4A0072; min-width: 270px; }}
        .matchup-wrapper {{ display: flex; flex-direction: column; justify-content: space-around; flex-grow: 1; }}

        .matchup {{
            background-color: #fff; padding: 10px 15px; border-radius: 8px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);
            width: 270px; position: relative;
        }}
        .matchup-wrapper > .matchup:not(:last-child) {{ margin-bottom: 28px; }}

        .matchup-title {{
            font-size: 0.7em;
            font-weight: bold;
            color: #aaa;
            text-align: center;
            border-bottom: 1px solid #eee;
            margin: -10px -15px 8px -15px;
            padding: 4px 0;
            text-transform: uppercase;
        }}

        .player {{ display: flex; align-items: center; margin: 8px 0; border-radius: 5px; transition: background-color 0.2s; }}
        .interactive .player {{ cursor: pointer; }}
        .interactive .player:hover {{ background-color: #f0f8ff; }}
        .static .player {{ cursor: default; }}

        .player-seed {{ font-size: 0.8em; color: #888; width: 30px; text-align: center; font-weight: 700; }}
        .player-name {{ flex-grow: 1; font-size: 1em; color: #333; }}
        .player-name.winner {{ font-weight: bold; color: #005A31; }}
        .tbd {{ font-style: italic; color: #999; }}

        .action-button {{ display: block; width: 300px; margin: 1em auto; padding: 1em; font-size: 1.2em; font-weight: bold; color: #fff; background-color: #4A0072; border: none; border-radius: 8px; cursor: pointer; transition: background-color 0.3s, transform 0.2s; }}
        .action-button:hover {{ background-color: #005A31; transform: scale(1.05); }}

        .button-container {{ display: flex; justify-content: center; gap: 20px; margin: 2em auto; }}
        .button-container .action-button {{ margin: 0; width: auto; padding: 0.8em 1.5em; font-size: 1em; }}

        #interactive-view {{ display: block; }}
        #static-view {{ display: none; }}

        #dev-controls {{ display: none; justify-content: center; flex-wrap: wrap; gap: 10px; margin-bottom: 2em; padding: 1em; background-color: #fff3cd; border: 1px solid #ffeeba; border-radius: 8px; }}
        .dev-button {{ background-color: #c82333; font-size: 0.9em; padding: 0.5em 1em; width: auto; margin: 0; }}
    </style>
</head>
<body>
    <div id="interactive-view">
        <h1>Full Tournament Bracket Challenge</h1>
        <div id="dev-controls"></div>
        <div class="instructions">
          <ol>
            <li>Fill out the bracket completely from left to right. Scroll to see all rounds.</li>
            <li>Once finished, click the "Lock In & Review" button to see a summary of your picks.</li>
          </ol>
        </div>

        <h2>Men's Singles Draw</h2>
        <div id="mens-bracket" class="bracket-container"></div>

        <h2>Women's Singles Draw</h2>
        <div id="womens-bracket" class="bracket-container"></div>

        <button id="lock-in-btn" class="action-button" onclick="lockInBracket()">Lock In & Review Bracket</button>
    </div>

    <div id="static-view">
        <!-- Static content will be generated here -->
    </div>

    <script>
        let participantName = '';
        const initialMatchups = {json.dumps(js_matchups, indent=4)};
        const googleFormConfig = {json.dumps(google_form_config)};

        const rounds = [
            {{ "name": "Round of 128", "key": "r128" }},
            {{ "name": "Round of 64",  "key": "r64" }},
            {{ "name": "Round of 32",  "key": "r32" }},
            {{ "name": "Round of 16",  "key": "r16" }},
            {{ "name": "Quarterfinals","key": "qf" }},
            {{ "name": "Semifinals",   "key": "sf" }},
            {{ "name": "Final",        "key": "f" }}
        ];

        function createBracket(containerId, initialData, category) {{
            const bracketContainer = document.getElementById(containerId);
            bracketContainer.classList.add('interactive');
            rounds.forEach((round, roundIndex) => {{
                const roundDiv = document.createElement('div');
                roundDiv.classList.add('round');
                const roundTitle = document.createElement('div');
                roundTitle.classList.add('round-title');
                roundTitle.textContent = round.name;
                roundDiv.appendChild(roundTitle);
                const matchupWrapper = document.createElement('div');
                matchupWrapper.classList.add('matchup-wrapper');

                const numMatches = 64 / Math.pow(2, roundIndex);
                for (let i = 0; i < numMatches; i++) {{
                    const matchupId = `${{category}}-${{round.key}}-match-${{i}}`;
                    const matchupDiv = document.createElement('div');
                    matchupDiv.classList.add('matchup');
                    matchupDiv.id = matchupId;

                    const roundName = round.name.replace('Round of ', 'R');
                    let innerHTML = `<div class="matchup-title">${{roundName}}</div>`;

                    if (roundIndex === 0) {{
                        const [p1, p2] = initialData[i];
                        innerHTML += `<label class="player"><input type="radio" name="${{matchupId}}" value="${{p1[1]}}"><span class="player-seed">${{p1[0]}}</span><span class="player-name">${{p1[1]}}</span></label><label class="player"><input type="radio" name="${{matchupId}}" value="${{p2[1]}}"><span class="player-seed">${{p2[0]}}</span><span class="player-name">${{p2[1]}}</span></label>`;
                    }} else {{
                        innerHTML += `<label class="player"><input type="radio" name="${{matchupId}}" value=""><span class="player-seed"></span><span class="player-name tbd">To Be Decided</span></label><label class="player"><input type="radio" name="${{matchupId}}" value=""><span class="player-seed"></span><span class="player-name tbd">To Be Decided</span></label>`;
                    }}
                    matchupDiv.innerHTML = innerHTML;
                    matchupWrapper.appendChild(matchupDiv);
                }}
                roundDiv.appendChild(matchupWrapper);
                bracketContainer.appendChild(roundDiv);
            }});
            addEventListeners(containerId);
        }}

        function addEventListeners(containerId) {{
            document.getElementById(containerId).addEventListener('change', (event) => {{
                if (event.target.type === 'radio') {{
                    const selectedLabel = event.target.closest('.player');
                    selectedLabel.parentElement.querySelectorAll('.player-name').forEach(el => el.classList.remove('winner'));
                    selectedLabel.querySelector('.player-name').classList.add('winner');
                    updateNextRound(event.target.name, {{
                        seed: selectedLabel.querySelector('.player-seed').textContent,
                        name: event.target.value
                    }});
                }}
            }});
        }}

        function updateNextRound(matchupId, winner) {{
            const parts = matchupId.split('-');
            const category = parts[0];
            const roundKey = parts[1];
            const matchIndex = parseInt(parts[3], 10);

            const currentRoundIndex = rounds.findIndex(r => r.key === roundKey);
            if (currentRoundIndex >= rounds.length - 1) return;

            const nextRound = rounds[currentRoundIndex + 1];
            const nextMatchIndex = Math.floor(matchIndex / 2);
            const playerSlot = matchIndex % 2;
            const nextMatchupId = `${{category}}-${{nextRound.key}}-match-${{nextMatchIndex}}`;
            const nextMatchupDiv = document.getElementById(nextMatchupId);

            if (nextMatchupDiv) {{
                const playerLabel = nextMatchupDiv.querySelectorAll('.player')[playerSlot];
                if (nextMatchupDiv.querySelector('input:checked')?.value === playerLabel.querySelector('input').value) {{
                     updateNextRound(nextMatchupId, {{seed:'', name:'To Be Decided'}});
                }}
                playerLabel.querySelector('input').value = winner.name;
                playerLabel.querySelector('.player-name').textContent = winner.name;
                playerLabel.querySelector('.player-seed').textContent = winner.seed;
                playerLabel.querySelector('.player-name').classList.toggle('tbd', winner.name === 'To Be Decided');

                nextMatchupDiv.querySelectorAll('input').forEach(i => i.checked = false);
                nextMatchupDiv.querySelectorAll('.player-name').forEach(el => el.classList.remove('winner'));
            }}
        }}

        function lockInBracket() {{
            let allPicksMade = true;
            document.querySelectorAll('#interactive-view .matchup').forEach(matchup => {{
                const firstPlayer = matchup.querySelector('.player:first-child .player-name');
                if (firstPlayer && firstPlayer.textContent !== 'To Be Decided' && !matchup.querySelector('input:checked')) {{
                    allPicksMade = false;
                }}
            }});
            if (!allPicksMade) {{ alert("Please complete the entire bracket before continuing!"); return; }}

            if (!participantName) {{
                const name = prompt("Please enter your name:", "your_name");
                if (name === null || name.trim() === "") return;
                participantName = name;
            }}

            const interactiveView = document.getElementById('interactive-view');
            const staticViewContent = interactiveView.cloneNode(true);

            staticViewContent.id = 'static-view-content';
            const staticH1 = staticViewContent.querySelector('h1');
            staticH1.textContent = `Tournament Bracket - ${{participantName}}'s Picks`;

            staticViewContent.querySelector('.instructions').remove();
            staticViewContent.querySelector('#lock-in-btn').remove();
            const devControlsInClone = staticViewContent.querySelector('#dev-controls');
            if(devControlsInClone) devControlsInClone.remove();

            const staticBrackets = staticViewContent.querySelectorAll('.bracket-container');
            staticBrackets.forEach(bracket => {{
                bracket.classList.remove('interactive');
                bracket.classList.add('static');
                bracket.querySelectorAll('input[type="radio"]').forEach(radio => radio.remove());
            }});

            const staticViewContainer = document.getElementById('static-view');
            staticViewContainer.innerHTML = '';

            const buttonContainer = document.createElement('div');
            buttonContainer.className = 'button-container';
            const submitButton = document.createElement('button');
            submitButton.className = 'action-button';
            submitButton.textContent = 'Submit My Bracket';
            submitButton.onclick = submitToGoogleForm;
            buttonContainer.appendChild(submitButton);

            const editButton = document.createElement('button');
            editButton.className = 'action-button';
            editButton.textContent = 'Edit My Bracket';
            editButton.style.backgroundColor = '#6c757d';
            editButton.onclick = goBackToEdit;
            buttonContainer.appendChild(editButton);

            staticViewContainer.appendChild(staticH1);
            staticViewContainer.appendChild(buttonContainer);

            staticViewContent.querySelectorAll('.bracket-container, h2').forEach(el => {{
                 staticViewContainer.appendChild(el);
            }});

            document.getElementById('interactive-view').style.display = 'none';
            document.getElementById('static-view').style.display = 'block';
            window.scrollTo(0, 0);
        }}

        function goBackToEdit() {{
            document.getElementById('static-view').style.display = 'none';
            document.getElementById('interactive-view').style.display = 'block';
        }}

        function submitToGoogleForm() {{
            let csvData = "Category,Round,MatchID,PredictedWinner\\n";
            document.querySelectorAll('#interactive-view .matchup input:checked').forEach(radio => {{
                 const [category, roundKey] = radio.name.split('-');
                 csvData += `${{category}},${{roundKey}},${{radio.name}},${{radio.value}}\\n`;
            }});

            const hiddenForm = document.createElement('form');
            hiddenForm.action = googleFormConfig.action_url;
            hiddenForm.method = 'POST';
            hiddenForm.target = '_blank';
            const nameInput = document.createElement('input');
            nameInput.type = 'hidden';
            nameInput.name = googleFormConfig.name_entry;
            nameInput.value = participantName;
            hiddenForm.appendChild(nameInput);
            const dataInput = document.createElement('input');
            dataInput.type = 'hidden';
            dataInput.name = googleFormConfig.data_entry;
            dataInput.value = csvData;
            hiddenForm.appendChild(dataInput);
            document.body.appendChild(hiddenForm);
            hiddenForm.submit();
            document.body.removeChild(hiddenForm);
        }}

        function autoFillRound(roundKey) {{
            ['mens', 'womens'].forEach(category => {{
                document.querySelectorAll(`#${{category}}-bracket [id*="-${{roundKey}}-"]`).forEach(matchup => {{
                    if (matchup.querySelector('input:checked')) return;
                    const players = matchup.querySelectorAll('.player input');
                    if (players.length === 2 && players[0].value) {{
                        const radioToClick = players[Math.floor(Math.random() * 2)];
                        radioToClick.dispatchEvent(new Event('change', {{ bubbles: true }}));
                    }}
                }});
            }});
        }}

        // --- Initial Setup ---
        createBracket('mens-bracket', initialMatchups.mens, 'mens');
        createBracket('womens-bracket', initialMatchups.womens, 'womens');

        const urlParams = new URLSearchParams(window.location.search);
        if (urlParams.get('dev') === 'true') {{
            const devControlsContainer = document.getElementById('dev-controls');
            devControlsContainer.style.display = 'flex';

            rounds.forEach(round => {{
                const btn = document.createElement('button');
                btn.className = 'action-button dev-button';
                btn.textContent = `Fill ${{round.name}}`;
                btn.onclick = () => autoFillRound(round.key);
                devControlsContainer.appendChild(btn);
            }});
        }}
    </script>
</body>
</html>
"""
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_template)
    print(f"Successfully generated HTML bracket at: {output_path}")

def generate_results_template(output_path="actual_results.csv"):
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['category', 'round', 'winner'])
    print(f"Successfully generated results template at: {output_path}")


if __name__ == "__main__":
    print("--- 128-Player Bracket Generator ---")
    mens_data, womens_data = parse_entrants()

    if not mens_data or not womens_data:
        print(f"\nError: Could not find 'entrants_128.txt' or the file is empty.")
    elif len(mens_data) != 64 or len(womens_data) != 64:
        print(f"\nError: Incorrect number of matchups found in entrants_128.txt.")
        print(f"Expected 64 for each category, but found {len(mens_data)} for men and {len(womens_data)} for women.")
    else:
        print("\nFound 64 matchups for Men and 64 for Women. Generating files...")
        generate_html(mens_data, womens_data)
        generate_results_template()
        print("\nSetup complete! You can now send 'bracket_128.html' to your friends.")


