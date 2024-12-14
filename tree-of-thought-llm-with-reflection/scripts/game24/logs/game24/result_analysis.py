import json

# Load data from the file
#file_name = "/scratch/bdes/haorany7/self-reflection-ToT/AutoToT-with-Self-Reflection/tree-of-thought-llm-with-reflection/logs/game24/gpt-4_0.7_propose1_value3_greedy5_start900_end1000.json"
file_name = "gpt-3.5-turbo_0.7_propose5_value3_greedy5_reflection_start805_end810.json"
try:
    with open(file_name, "r") as file:
        data = json.load(file)
except FileNotFoundError:
    print(f"Error: File '{file_name}' not found.")
    exit(1)
except json.JSONDecodeError:
    print(f"Error: Failed to decode JSON from the file '{file_name}'.")
    exit(1)

# Initialize counters
total_problems = len(data)
successful_problems = 0
total_steps = 0

# Extract the last usage statistics (already summed up)
if total_problems > 0:
    last_usage = data[-1].get("usage_so_far", {})
    total_completion_tokens = last_usage.get("completion_tokens", 0)
    total_prompt_tokens = last_usage.get("prompt_tokens", 0)
    total_cost = last_usage.get("cost", 0)
else:
    total_completion_tokens = total_prompt_tokens = total_cost = 0

# Process data
for problem in data:
    steps = len(problem["steps"])
    total_steps += steps

    # Check if the problem was solved successfully
    if any(info["r"] == 1 for info in problem["infos"]):
        successful_problems += 1

# Calculate averages
average_steps = total_steps / total_problems if total_problems > 0 else 0
success_rate = (successful_problems / total_problems) * 100 if total_problems > 0 else 0
avg_completion_tokens = total_completion_tokens / total_problems if total_problems > 0 else 0
avg_prompt_tokens = total_prompt_tokens / total_problems if total_problems > 0 else 0
avg_cost = total_cost / total_problems if total_problems > 0 else 0

# Display results
print(f"Average Steps: {average_steps:.2f}")
print(f"Success Rate: {success_rate:.2f}%")
print(f"Average Completion Tokens: {avg_completion_tokens:.2f}")
print(f"Average Prompt Tokens: {avg_prompt_tokens:.2f}")
print(f"Average Cost: {avg_cost:.2f}")
