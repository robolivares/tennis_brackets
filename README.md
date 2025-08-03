# Real-Time Tennis Bracket Sweepstakes

This project is a modern, fully-featured platform for running real-time tennis tournament bracket sweepstakes. It uses a web-based interface for both participants and administrators, with a serverless backend powered by Firebase for data storage and automated, real-time score calculation.

The old manual Python scripts have been deprecated in favor of this more robust and user-friendly system.

## Core Features

* **Real-Time Updates:** Scores and leaderboards update automatically for all users the moment an admin submits a new match result.
* **Dual-View Picking:** Participants can fill out their brackets using a classic visual **Bracket View** or a mobile-friendly **List View**.
* **Secure Authentication:** Each participant gets their own secure bracket, and anonymous login makes it easy to get started.
* **Automated Scoring:** A Firebase Cloud Function handles all score calculations in the background. No more manual scripts!
* **Admin Panel:** A simple, password-protected admin page for updating match results.
* **Interactive Viewer Mode:** A comprehensive viewer that includes a leaderboard, participant toggles, and a visual comparison of picks against actual results.
* **Scalable & Cost-Effective:** Built on the serverless, free-tier-friendly architecture of Firebase and Netlify.

## Project Structure

The repository is organized into three main directories:

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
    * Paste your `firebaseConfig` credentials into this new file.
    * **IMPORTANT:** The `.gitignore` file is already configured to ignore `app-config.js`, so your secrets will **not** be committed to GitHub.
3.  **Configure the Cloud Function:**
    * Follow the Firebase documentation to generate a `serviceAccountKey.json` file for your project.
    * Place this key file inside the `/functions` directory. The `.gitignore` will also keep this file private.
4.  **Update Tournament Data:**
    * Edit the `/public/tournament_data.json` file with the players and matchups for your tournament.
    * **Crucially, copy this same `tournament_data.json` file into the `/functions` directory**, as the Cloud Function needs it to calculate scores.

### Step 3: Deployment

1.  **Deploy the Website (Manual Drag and Drop):**
    * This method is simple and ensures your `app-config.js` with your private keys is included in the deployment without ever being exposed on GitHub.
    * Go to [**https://app.netlify.com/drop**](https://app.netlify.com/drop).
    * Drag and drop your entire local `/public` folder onto the page.
    * Netlify will upload the files and give you a unique, public URL to share.
    * **To update your site,** simply drag and drop the updated `/public` folder onto your site's deploy page in the Netlify dashboard.
2.  **Deploy the Cloud Function:**
    * Install the Firebase CLI (`npm install -g firebase-tools`).
    * Log in with `firebase login`.
    * From the **root of the `tennis_brackets` project folder**, run the deploy command:
        ```bash
        firebase deploy --only functions
        ```

### Step 4: Running the Sweepstakes

1.  **For Participants:** Share the public Netlify URL. They can visit the site, enter their name/nickname, and fill out their bracket.
2.  **For the Admin:**
    * Navigate to `your-netlify-url.netlify.app/admin.html`.
    * Enter the admin password (set inside `admin.html`).
    * As the tournament progresses, update match winners and click "Save All Results".
    * The Cloud Function will automatically trigger, and the leaderboard on the main `index.html` page will update for everyone in real-time.
