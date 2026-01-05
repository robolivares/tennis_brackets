import firebase_admin
from firebase_admin import credentials, firestore
import json
import argparse
import os

def download_participant_entries(tournament_id, nickname, output_dir):
    """
    Finds all participants by nickname within a specific tournament and saves their
    picks to uniquely named JSON files.
    """
    try:
        # --- INITIALIZE FIREBASE ADMIN SDK ---
        cred = credentials.Certificate('serviceAccountKey.json')
        try:
            # Check if the app is already initialized
            firebase_admin.get_app()
        except ValueError:
            # Initialize the app if it's not
            firebase_admin.initialize_app(cred)
        db = firestore.client()
        print("Successfully connected to Firebase.")
    except Exception as e:
        print(f"Error connecting to Firebase: {e}")
        print("Please ensure 'serviceAccountKey.json' is in the project root directory.")
        return

    # --- QUERY FIRESTORE ---
    print(f"Searching for all participants with nickname '{nickname}' in tournament '{tournament_id}'...")

    participants_ref = db.collection('tournaments', tournament_id, 'participants')
    # Query for all documents with the matching nickname
    query = participants_ref.where('nickname', '==', nickname)
    docs = query.stream()

    download_count = 0
    # Loop through all documents found by the query
    for i, doc in enumerate(docs):
        download_count += 1
        participant_data = doc.to_dict()

        full_name = participant_data.get('fullName', 'Unknown_Name')
        picks = participant_data.get('picks', {})

        # --- SAVE FILE ---
        # Sanitize nickname for a safe filename
        safe_filename = "".join(x for x in nickname if x.isalnum())

        # Append a number to the filename to handle duplicates
        output_filename = f"{safe_filename}_{i+1}_picks.json"
        output_path = os.path.join(output_dir, output_filename)

        # Create the output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(picks, f, indent=4, sort_keys=True)

        print(f"\nSuccess! Downloaded entry for '{nickname}' ({full_name}).")
        print(f"File saved to: {output_path}")

    if download_count == 0:
        print(f"\nError: Could not find any participant with the nickname '{nickname}' in this tournament.")
        print("Please check the nickname for typos and capitalization.")
    else:
        print(f"\nFinished. Downloaded a total of {download_count} entries for nickname '{nickname}'.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download participant bracket entries from Firebase.")
    parser.add_argument('tournament_id', help="The ID of the tournament (e.g., 'usopen2024-demo').")
    parser.add_argument('nickname', help="The nickname of the participant(s) whose entries you want to download.")
    parser.add_argument('-o', '--output_dir', default='downloads', help="The directory where the entry file(s) will be saved.")

    args = parser.parse_args()

    download_participant_entries(args.tournament_id, args.nickname, args.output_dir)


