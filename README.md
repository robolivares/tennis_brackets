# Real-Time Tennis Bracket Sweepstakes

This project is a modern, fully-featured platform for running real-time tennis tournament bracket sweepstakes. It uses a web-based interface for both participants and administrators, with a serverless backend powered by Firebase for data storage and automated, real-time score calculation.

## Core Features

* **Real-Time Updates:** Scores and leaderboards update automatically for all users the moment an admin submits a new match result.
* **Dual-View Picking:** Participants can fill out their brackets using a classic visual **Bracket View** or a mobile-friendly **List View**.
* **Secure Authentication:** Each participant gets their own secure bracket, and anonymous login makes it easy to get started.
* **Automated Scoring:** A Firebase Cloud Function handles all score calculations in the background. No more manual scripts!
* **Admin Panel:** A simple, password-protected admin page for updating match results.
* **Interactive Viewer Mode:** A comprehensive viewer that includes a leaderboard, participant toggles, and a visual comparison of picks against actual results.
* **Scalable & Cost-Effective:** Built on the serverless, free-tier-friendly architecture of Firebase and Netlify.

## Project Structure

* `/public/`: This is the root of your website. The contents of this folder will be deployed to Netlify.
* `/functions/`: Contains the backend Cloud Function code (`main.py`) responsible for automatic score calculation.
* `/scripts/`: Contains optional helper scripts, such as a manual score calculator (`calculate_scores.py`) for backup or testing purposes.

## Full Workflow: From Setup to Sharing

### Step 1: Firebase Setup (One-Time)

1.  **Create a Firebase Project:** Go to the [Firebase Console](https://console.firebase.google.com/) and create a new project.
2.  **Create a Firestore Database:** In your project, go to **Build > Firestore Database** and create a database in **Production mode**.
3.  **Get Web Credentials:**
    * In your project settings (gear icon), scroll down to "Your apps".
    * Create a new **Web app**.
    * Copy the `firebaseConfig` object containing your API keys.
4.  **Upgrade to Blaze Plan:** To use Cloud Functions, you must upgrade your project to the **Blaze (Pay-as-you-go)** plan. You still get a generous free tier, so costs for this project should be $0.
5.  **Set Up Security Rules:** In the Firestore Database section, go to the **Rules** tab and paste in the required security rules to allow users to write their own brackets and read results.

### Step 2: Local Project Setup

1.  **Clone the Repository:** Clone this project from GitHub to your local machine.
2.  **Configure the Website:**
    * In the `/public` directory, rename `app-config.js.template` to `app-config.js`.
    * Paste your `firebaseConfig` credentials into this new file and set your `TOURNAMENT_ID`.
    * **IMPORTANT:** The `.gitignore` file is already configured to ignore `app-config.js`, so your secrets will **not** be committed to GitHub.
3.  **Configure the Cloud Function:**
    * Follow the Firebase documentation to generate a `serviceAccountKey.json` file for your project.
    * Place this key file inside the `/functions` directory. The `.gitignore` will also keep this file private.
4.  **Generate Tournament Data:**
    * Create a file named `entrants.txt` in the root of your project.
    * Add the matchups in the following format, specifying the day for each half of the draw. The seed is optional.
        ```
        mens
        Top Half (Day 1)
        (1) Jannik Sinner vs Christopher O'Connell
        (17) Tommy Paul vs (16) Karen Khachanov
        ... (8 matchups total for the top half) ...

        Bottom Half (Day 2)
        (8) Casper Ruud vs Juncheng Shang
        ... (8 matchups total for the bottom half) ...

        womens
        Top Half (Day 2)
        (1) Iga Swiatek vs A. Pavlyuchenkova
        ... (etc.) ...
        ```
    * From the root of your project, run the setup script. Use the `-s` flag to specify the name for the Firebase Storage file, which **must match your `TOURNAMENT_ID`**.
        ```bash
        # Example for a tournament with ID 'usopen2024-v3'
        python scripts/setup_bracket.py -e entrants.txt -o public/tournament_data.json -s storage_files/usopen2024-v3.json
        ```
    * This command creates two files:
        1.  `public/tournament_data.json` (for the website)
        2.  `storage_files/usopen2024-v3.json` (for the backend)
5.  **Upload to Storage:** Manually upload the file from your `storage_files` directory (e.g., `usopen2024-v3.json`) to a `tournaments/` folder in your Firebase Storage bucket.

### Step 3: Deployment

1.  **Deploy the Website (Manual Drag and Drop):**
    * Go to [**https://app.netlify.com/drop**](https://app.netlify.com/drop).
    * Drag and drop your entire local `/public` folder onto the page.
2.  **Deploy the Cloud Function:**
    * From the **root of the `tennis_brackets` project folder**, run:
        ```bash
        firebase deploy --only functions
        ```

### Step 4: Running the Sweepstakes

1.  **For Participants:** Share the public Netlify URL.
2.  **For the Admin:** Navigate to `/admin.html` on your site to update results. The Cloud Function will handle scoring automatically.
