# Tennis Tournament Bracket Sweepstakes

This project is a complete system for creating, managing, and scoring tournament bracket sweepstakes for tennis events. It includes Python scripts to generate interactive HTML brackets (for both 32-player and 128-player draws), a command-line tool for scoring, and a master viewer generator for comparing all participants' brackets against the actual results.

## Core Features

* **Customizable Brackets:** Generate brackets for any tournament by simply editing a text file.
* **Interactive HTML Interface:** Participants can easily fill out their brackets in a clean, user-friendly web interface.
* **Automated Data Collection:** Seamlessly collect all predictions using a Google Form integration.
* **Flexible Scoring:** A command-line tool to calculate scores for individual brackets or generate a full leaderboard.
* **Master Results Viewer:** A single, shareable HTML file that displays a leaderboard and allows everyone to compare brackets visually.
* **Developer-Friendly:** Includes a hidden "Dev Mode" for rapid testing and debugging.

## Project Files

* `entrants.txt`: Data file for the **Round of 32** bracket. List 16 matchups per category here.
* `entrants_128.txt`: Data file for the **Round of 128** bracket. List 64 matchups per category here.
* `setup_bracket.py`: Python script to generate the interactive `bracket.html` for a **Round of 32** sweepstakes.
* `setup_bracket_128.py`: Python script to generate the interactive `bracket_128.html` for a full **Round of 128** sweepstakes. **(Note: This version is currently in development and may have bugs.)**
* `score_manager.py`: A command-line tool to score brackets individually or generate a scoreboard in the terminal (for Round of 32 brackets).
* `generate_viewer.py`: A command-line tool that reads all prediction files and generates a master `index.html` viewer page (for Round of 32 brackets).
* `LICENSE`: The MIT License file for the project.

---

## Full Workflow: From Setup to Sharing

### Step 1: Initial Setup (Admin)

1.  **Choose Your Bracket Size:** Decide if you are running a Round of 32 (5 rounds) or a full Round of 128 (7 rounds) tournament.

2.  **Prepare the Entrants File:**
    * For a R32 bracket, edit `entrants.txt`.
    * For a R128 bracket, edit `entrants_128.txt`.
    * List all the initial matchups under the `mens` and `womens` headers.
    * **Format:** `(SEED) Player One vs (SEED) Player Two`. The seed is optional.

3.  **Configure the Google Form (One-Time Setup):**
    * Create a Google Form with two "Short answer" questions (e.g., "Name" and "Prediction Data").
    * Get the pre-filled link and find the unique `entry.XXXXXXXXXX` IDs for each question.
    * Open the appropriate setup script (`setup_bracket.py` or `setup_bracket_128.py`) and update the `google_form_config` dictionary with your new IDs. **Ensure the `action_url` ends in `/formResponse`**.

4.  **Generate the Bracket HTML:**
    * Run the corresponding setup script from your terminal:
        * For R32: `python3 setup_bracket.py`
        * For R128: `python3 setup_bracket_128.py`
    * This will create the interactive HTML file (`bracket.html` or `bracket_128.html`).

5.  **Distribute to Participants:**
    * Send the generated HTML file to your friends. It's recommended they use a desktop browser for the best experience.

### Step 2: Collecting Predictions (Participants & Admin)

1.  **Participants Fill Out Bracket:** Each person opens the HTML file, fills out their entire bracket, and clicks **"Lock In & Review Bracket"**.
2.  **Participants Submit:** After reviewing their picks on the static "receipt" page, they click **"Submit My Bracket"**. This will automatically open and submit their data to your Google Form.
3.  **Admin Collects Data:**
    * Open the Google Sheet linked to your form.
    * For each submission, copy the text from the "Prediction Data" column.
    * Create a new `.csv` file for each person in a dedicated folder (e.g., `all_brackets/`).
    * Paste the data into the file and save it as `[participant_name]_predictions.csv`.
    * **Important:** Ensure the first line of each file is the header: `Category,Round,MatchID,PredictedWinner`.

### Step 3: Scoring and Viewing (Admin)

1.  **Create the "Actual Results" File:**
    * Fill out a bracket yourself with the real-world results of the tournament.
    * Submit it via the Google Form with the name `actual_results`.
    * Copy the data from the spreadsheet and save it as `actual_results_predictions.csv` inside your `all_brackets` folder. You can update this file as the tournament progresses.

2.  **Generate the Master Viewer:**
    * Run the viewer generator script, pointing it to your predictions folder and the correct entrants file.
        * For R32: `python3 generate_viewer.py -b ./all_brackets -e entrants.txt`
        * For R128: `python3 generate_viewer.py -b ./all_brackets -e entrants_128.txt`
    * This will create a single `index.html` file inside your `all_brackets` folder.

3.  **Share the Results:**
    * Go to **https://app.netlify.com/drop**.
    * Drag and drop your entire `all_brackets` folder onto the page.
    * Share the unique link Netlify provides with your group!

### Developer Mode (For Testing)

* To activate Dev Mode, add `?dev=true` to the end of the URL when you open `bracket.html` or `bracket_128.html` in your browser.
* This will display buttons that allow you to automatically and randomly fill the bracket round-by-round, which is extremely useful for testing the submission flow and scoring logic without having to click through every matchup manually.

