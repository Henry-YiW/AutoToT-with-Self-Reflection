import json
import os

def analyze_failed_crossword(data, output_file):
    """Identify failed crossword attempts and save to file"""
    
    failed_cases = []
    
    # Analyze each episode (first level of the list)
    for episode_idx, episode_list in enumerate(data):
        # Get final state from the episode's attempts (last dictionary in the inner list)
        final_state = episode_list[-1]
        
        # Check if this is a failed case (r_letter < 1.0 means not all letters are correct)
        if final_state['info']['r_letter'] < 1.0:
            failed_case = {
                'episode': episode_idx,
                'final_attempt': final_state['actions']
            }
            failed_cases.append(failed_case)
    
    # If we found any failed cases, write them to file
    if failed_cases:
        # Create output directory if it doesn't exist
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        with open(output_file, 'w') as f:
            f.write(f"Failed Crossword Cases:\n")
            f.write(f"Total failed cases: {len(failed_cases)}\n\n")
            
            for case in failed_cases:
                f.write(f"Episode {case['episode']}:\n")
                f.write("Final word configuration:\n")
                for word in case['final_attempt']:
                    f.write(f"  {word}\n")
                f.write("\n")
        
        print(f"Failed cases saved to {output_file}")
        return True
    
    return False

def main():
    input_file = "/scratch/bdes/haorany7/self-reflection-ToT/AutoToT-with-Self-Reflection/tree-of-thought-llm-with-reflection/logs/crosswords/infoss_dfs_no_prune.json"
    base_name = os.path.basename(input_file).replace('.json', '')
    output_file = f"tree-of-thought-llm-with-reflection/logs/crosswords/failed_cases/{base_name}_failed.txt"
    
    try:
        with open(input_file, 'r') as f:
            data = json.load(f)
            analyze_failed_crossword(data, output_file)
    except Exception as e:
        print(f"Error processing file: {str(e)}")

if __name__ == "__main__":
    main()