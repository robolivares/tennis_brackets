import os
import pandas as pd
import matplotlib.pyplot as plt
import imageio.v2 as imageio
import numpy as np

def generate_scoreboard_gif(csv_path='combined_scores.csv', output_gif='scoreboard_evolution.gif', output_png='final_rankings.png', total_gif_duration=20):
    """
    Reads a combined scores CSV, converts scores to ranks, generates a line chart
    animation with custom axis labels, and saves a final static PNG.

    Args:
        csv_path (str): The path to the 'combined_scores.csv' file.
        output_gif (str): The filename for the output GIF.
        output_png (str): The filename for the final static PNG image.
        total_gif_duration (int): The total desired duration of the animated GIF in seconds.
    """
    # --- 1. Load and Prepare the Data ---
    try:
        df = pd.read_csv(csv_path).set_index('Name')
    except FileNotFoundError:
        print(f"Error: The file '{csv_path}' was not found.")
        print("Please run the 'combine_scores.py' script first to generate it.")
        return

    day_columns = sorted([col for col in df.columns if col.startswith('Day')])
    if not day_columns:
        print("Error: No 'Day XX' columns found in the CSV file.")
        return

    # --- 2. Define Custom Label Mapping and Apply It ---
    day_label_mapping = {
        'Day 01': 'R32 D1', 'Day 02': 'R32 D2', 'Day 03': 'R16 D1',
        'Day 04': 'R16 D2', 'Day 05': 'QF D1', 'Day 06': 'QF D2',
        'Day 07': 'SF W', 'Day 08': 'SF M', 'Day 09': 'F W', 'Day 10': 'F M'
    }
    plot_labels = [day_label_mapping.get(day, day) for day in day_columns]


    # --- 3. Convert Scores to Ranks ---
    df_ranks = pd.DataFrame(index=df.index)
    for col in day_columns:
        df_ranks[col] = df[col].rank(method='min', ascending=False).astype(int)

    # --- 4. Determine Final Rank for Legend Ordering ---
    last_day_col = day_columns[-1]
    final_rank_order = df_ranks.sort_values(by=last_day_col).index

    df_plot = df_ranks.T[final_rank_order]
    df_plot.index = plot_labels

    # --- 5. Generate a Line Chart Plot for Each Day (for the GIF) ---
    image_files = []
    temp_dir = "temp_frames"
    os.makedirs(temp_dir, exist_ok=True)

    print(f"Generating {len(plot_labels)} frames for the GIF...")

    colors1 = plt.cm.get_cmap('tab20', 20)
    colors2 = plt.cm.get_cmap('tab20b', 20)
    colors = np.vstack((colors1.colors, colors2.colors))
    markers = ['o', 's', 'X', 'P', '*', 'D', 'v', '^', '<', '>']

    all_days_custom_labels = df_plot.index
    x_axis_ticks = range(len(all_days_custom_labels))

    for i in range(len(all_days_custom_labels)):
        current_day_index = i + 1
        current_df = df_plot.iloc[:current_day_index]
        day_label = all_days_custom_labels[i]

        plt.style.use('seaborn-v0_8-whitegrid')
        fig, ax = plt.subplots(figsize=(14, 8))

        for j, player in enumerate(current_df.columns):
            color = colors[j % len(colors)]
            marker = markers[j % len(markers)]

            ax.plot(range(len(current_df)), current_df[player], marker=marker, markersize=6, color=color, linewidth=2.5, alpha=0.8, label=player)
            ax.plot(i, current_df.loc[day_label, player], marker=marker, markersize=12, color=color, markeredgecolor='black', markeredgewidth=0.5)

        ax.set_title(f'Rank Evolution: {day_label}', fontsize=22, fontweight='bold')
        ax.set_ylabel('Rank', fontsize=16)
        ax.set_xlabel('Day / Round', fontsize=16)
        ax.invert_yaxis()

        max_rank = df_ranks.max().max()
        ax.set_yticks(np.arange(1, max_rank + 1))
        ax.set_ylim(max_rank + 1, 0)

        ax.set_xticks(x_axis_ticks)
        ax.set_xticklabels(all_days_custom_labels, rotation=45, ha="right")
        ax.set_xlim(-0.5, len(all_days_custom_labels) - 0.5)

        plt.yticks(fontsize=12)
        ax.legend(title='Participants (by Final Rank)', bbox_to_anchor=(1.04, 1), loc="upper left", borderaxespad=0)
        fig.tight_layout(rect=[0, 0, 0.85, 1])

        filename = os.path.join(temp_dir, f"frame_{i:02d}.png")
        plt.savefig(filename, dpi=150)
        plt.close(fig)
        image_files.append(filename)
        print(f"  - Saved frame for {day_label}")

    # --- 6. Generate Final Static PNG ---
    print("\nGenerating final static PNG of all results...")
    fig, ax = plt.subplots(figsize=(14, 8))
    for j, player in enumerate(df_plot.columns):
        color = colors[j % len(colors)]
        marker = markers[j % len(markers)]
        ax.plot(x_axis_ticks, df_plot[player], marker=marker, markersize=6, color=color, linewidth=2.5, alpha=0.8, label=player)

    ax.set_title('Final Rank Evolution', fontsize=22, fontweight='bold')
    ax.set_ylabel('Rank', fontsize=16)
    ax.set_xlabel('Day / Round', fontsize=16)
    ax.invert_yaxis()
    max_rank = df_ranks.max().max()
    ax.set_yticks(np.arange(1, max_rank + 1))
    ax.set_ylim(max_rank + 1, 0)
    ax.set_xticks(x_axis_ticks)
    ax.set_xticklabels(all_days_custom_labels, rotation=45, ha="right")
    ax.set_xlim(-0.5, len(all_days_custom_labels) - 0.5)
    plt.yticks(fontsize=12)
    ax.legend(title='Participants (by Final Rank)', bbox_to_anchor=(1.04, 1), loc="upper left", borderaxespad=0)
    fig.tight_layout(rect=[0, 0, 0.85, 1])

    try:
        plt.savefig(output_png, dpi=150)
        plt.close(fig)
        print(f"Successfully saved final results chart to '{output_png}'")
    except Exception as e:
        print(f"\nError saving final PNG: {e}")


    # --- 7. Compile Images into a GIF ---
    print("\nCompiling frames into a GIF...")
    try:
        num_frames = len(image_files)
        # Calculate duration per frame based on the total desired duration
        duration_per_frame = total_gif_duration / num_frames if num_frames > 0 else 2.0

        with imageio.get_writer(output_gif, mode='I', duration=duration_per_frame, loop=0) as writer:
            for filename in image_files:
                image = imageio.imread(filename)
                writer.append_data(image)
        print(f"\nSuccess! Animated scoreboard saved as '{output_gif}'")
    except Exception as e:
        print(f"\nError creating GIF: {e}")
    finally:
        # --- 8. Clean up temporary image files ---
        print("Cleaning up temporary frame files...")
        for filename in image_files:
            os.remove(filename)
        os.rmdir(temp_dir)


if __name__ == "__main__":
    # You can easily change the total duration of the GIF (in seconds) here
    generate_scoreboard_gif(total_gif_duration=10)

