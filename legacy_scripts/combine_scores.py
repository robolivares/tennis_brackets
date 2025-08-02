import os
import glob
import pandas as pd

def combine_daily_scores(directory="."):
    """
    Finds all 'day_XX.csv' files in a directory, combines them into a single
    dataset, and renames the score columns to reflect the day.

    Args:
        directory (str): The path to the directory containing the CSV files.
                         Defaults to the current directory.
    """
    # Use glob to find all files matching the pattern 'day_*.csv'
    # The sorting ensures they are processed in order (day_01, day_02, etc.)
    file_pattern = os.path.join(directory, 'day_*.csv')
    csv_files = sorted(glob.glob(file_pattern))

    if not csv_files:
        print(f"No files found matching the pattern 'day_*.csv' in '{directory}'")
        return

    print(f"Found files: {', '.join(os.path.basename(f) for f in csv_files)}")

    # List to hold each day's DataFrame
    data_frames = []

    for file_path in csv_files:
        try:
            # Read the CSV file into a pandas DataFrame
            df = pd.read_csv(file_path)

            # --- Data Cleaning and Renaming ---
            # Extract the day number from the filename (e.g., '01' from 'day_01.csv')
            base_name = os.path.basename(file_path)
            day_number_str = base_name.replace('day_', '').replace('.csv', '')

            # Format the new column name, e.g., "Day 01"
            new_column_name = f"Day {day_number_str}"

            # Check if 'Current Score' column exists and rename it
            if 'Current Score' in df.columns:
                df.rename(columns={'Current Score': new_column_name}, inplace=True)
            else:
                print(f"Warning: 'Current Score' column not found in {base_name}. Skipping file.")
                continue

            # Ensure the 'Name' column is the index for easy merging
            df.set_index('Name', inplace=True)

            data_frames.append(df)

        except Exception as e:
            print(f"Error processing file {file_path}: {e}")

    if not data_frames:
        print("No data was processed. Exiting.")
        return

    # --- Merging the Data ---
    # Merge all DataFrames together on the 'Name' index.
    # 'outer' join ensures that all players from all files are included.
    combined_df = pd.concat(data_frames, axis=1, join='outer')

    # Fill any missing values with 0 (for players who might not be in every file)
    combined_df.fillna(0, inplace=True)

    # Convert float scores to integers
    for col in combined_df.columns:
        combined_df[col] = combined_df[col].astype(int)

    # Reset the index so 'Name' becomes a column again
    combined_df.reset_index(inplace=True)


    # --- Output ---

    # 1. Convert the final DataFrame to a list of dictionaries and print
    final_list = combined_df.to_dict(orient='records')
    print("\n--- Combined Scores (List Format) ---")
    # Pretty print the JSON-like list
    import json
    print(json.dumps(final_list, indent=4))

    # 2. Save the combined DataFrame to a new CSV file
    output_filename = os.path.join(directory, 'combined_scores.csv')
    try:
        combined_df.to_csv(output_filename, index=False)
        print(f"\nSuccessfully saved combined data to '{output_filename}'")
    except Exception as e:
        print(f"\nError saving combined CSV file: {e}")


if __name__ == "__main__":
    # You can optionally pass a directory path as a command-line argument
    # For now, it just runs in the current directory.
    combine_daily_scores()

