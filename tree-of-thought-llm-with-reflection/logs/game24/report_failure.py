import json
import os

def analyze_failed_game24(game_data, index, failed_games):
    """Analyze failed attempts in Game24 and collect the initial numbers with test case index"""
    
    # Extract the initial numbers from the first step
    if "steps" in game_data and len(game_data["steps"]) > 0:
        initial_numbers = game_data["steps"][0]["x"]
    else:
        return False
    
    # Check if the game reached 24
    reached_24 = False
    
    # Look through all steps for solutions that reached 24
    for step in game_data["steps"]:
        for y in step.get("select_new_ys", []):
            if "(left: 24)" in y or "Answer:" in y and "= 24" in y:
                reached_24 = True
                break
        if reached_24:
            break
    
    # If game didn't reach 24, add to failed games list with index
    if not reached_24:
        failed_games.append((index, initial_numbers))
    
    return not reached_24

def analyze_game24_log(log_data, output_file):
    failed_games = []
    
    # Pass the index along with the game data
    for i, game in enumerate(log_data):
        analyze_failed_game24(game, i + 900, failed_games)  # Adding 900 as per filename range
    
    # Create output directory if it doesn't exist
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    # Write failed games to file with test case numbers
    with open(output_file, 'w') as f:
        for index, numbers in failed_games:
            f.write(f"Test case {index}: {numbers}\n")
    
    print(f"Found {len(failed_games)} failed games. Saved to {output_file}")

def main():
    # Define the input and output paths
    input_file = "/scratch/bdes/haorany7/self-reflection-ToT/AutoToT-with-Self-Reflection/tree-of-thought-llm-with-reflection/logs/game24/gpt-4_0.7_propose1_value3_greedy5_start900_end1000.json"
    
    # Create output filename based on input filename
    base_name = os.path.basename(input_file).replace('.json', '')
    output_file = f"/scratch/bdes/haorany7/self-reflection-ToT/AutoToT-with-Self-Reflection/tree-of-thought-llm-with-reflection/logs/game24/failed_games/{base_name}_failed.txt"
    
    try:
        with open(input_file, 'r') as f:
            log_data = json.load(f)
            print(f"\nAnalyzing {os.path.basename(input_file)}...")
            analyze_game24_log(log_data, output_file)
    except Exception as e:
        print(f"Error processing file: {str(e)}")

if __name__ == "__main__":
    main()