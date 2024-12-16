import os
import json
import argparse

from tot.tasks import get_task
from tot.methods.bfs import solve, naive_solve
from tot.models import gpt_usage

def run(args):
    task = get_task(args.task)
    logs, cnt_avg, cnt_any = [], 0, 0
    
    # File paths
    if args.naive_run:
        log_file = f'./logs/{args.task}/{args.backend}_{args.temperature}_naive_{args.prompt_sample}_sample_{args.n_generate_sample}_start{args.task_start_index}_end{args.task_end_index}.json'
        reflection_file = f'./logs/{args.task}/{args.backend}_{args.temperature}_naive_reflection_start{args.task_start_index}_end{args.task_end_index}.json'
    else:
        reflection_suffix = "_reflection" if args.enable_reflection else ""
        log_file = f'./logs/{args.task}/{args.backend}_{args.temperature}_{args.method_generate}{args.n_generate_sample}_{args.method_evaluate}{args.n_evaluate_sample}_{args.method_select}{args.n_select_sample}{reflection_suffix}_start{args.task_start_index}_end{args.task_end_index}.json'
        reflection_file = f'./logs/{args.task}/{args.backend}_{args.temperature}_reflection_{args.method_generate}{args.n_generate_sample}_start{args.task_start_index}_end{args.task_end_index}.json'

    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    
    # Initialize global reflection memory (list)
    # Try loading existing reflections if you want to accumulate across multiple runs
    global_reflection_memory = []
    if args.enable_reflection and os.path.isfile(reflection_file):
        with open(reflection_file, 'r') as rf:
            try:
                existing_data = json.load(rf)
                if 'global_reflection_memory' in existing_data:
                    global_reflection_memory = existing_data['global_reflection_memory']
            except json.JSONDecodeError:
                pass
    
    print("FUCK GLOBAL REFLECTION MEMORY", global_reflection_memory)
    for i in range(args.task_start_index, args.task_end_index):
        # solve
        if args.naive_run:
            ys, info = naive_solve(args, task, i)
        else:
            ys, info = solve(args, task, i, global_reflection_memory)

        # Update global reflection memory from the latest solve
        
        if args.enable_reflection and "steps" in info:
            for step_info in info["steps"]:
                if "Reflection_memory" in step_info:
                    for reflection in step_info["Reflection_memory"]:
                        if reflection not in global_reflection_memory:
                            global_reflection_memory.append(reflection)

        # log task info
        infos = [task.test_output(i, y) for y in ys]
        info.update({
            'idx': i, 
            'ys': ys, 
            'infos': infos, 
            'usage_so_far': gpt_usage(args.backend),
            'global_reflection_memory': global_reflection_memory
        })
        logs.append(info)
        
        # Write to log file incrementally
        with open(log_file, 'w') as f:
            json.dump(logs, f, indent=4)

        # Update metrics
        accs = [inf['r'] for inf in infos]
        cnt_avg += sum(accs) / len(accs)
        cnt_any += any(accs)
        print(i, 'sum(accs)', sum(accs), 'cnt_avg', cnt_avg, 'cnt_any', cnt_any, '\n')
    
    # After the loop ends, write the entire reflection memory once
    if args.enable_reflection:
        with open(reflection_file, 'w') as rf:
            json.dump({
                'global_reflection_memory': global_reflection_memory,
                'last_index': args.task_end_index - 1
            }, rf, indent=4)

    n = args.task_end_index - args.task_start_index
    print(cnt_avg / n, cnt_any / n)
    print('usage_so_far', gpt_usage(args.backend))


def parse_args():
    args = argparse.ArgumentParser()
    args.add_argument('--backend', type=str, choices=['gpt-4', 'gpt-3.5-turbo'], default='gpt-4')
    args.add_argument('--temperature', type=float, default=0.7)

    args.add_argument('--task', type=str, required=True, choices=['game24', 'text', 'crosswords'])
    args.add_argument('--task_start_index', type=int, default=900)
    args.add_argument('--task_end_index', type=int, default=1000)

    args.add_argument('--naive_run', action='store_true')
    args.add_argument('--prompt_sample', type=str, choices=['standard', 'cot'])  # only used when method_generate = sample, or naive_run

    args.add_argument('--method_generate', type=str, choices=['sample', 'propose'])
    args.add_argument('--method_evaluate', type=str, choices=['value', 'vote'])
    args.add_argument('--method_select', type=str, choices=['sample', 'greedy'], default='greedy')
    args.add_argument('--n_generate_sample', type=int, default=1)  # only thing needed if naive_run
    args.add_argument('--n_evaluate_sample', type=int, default=1)
    args.add_argument('--n_select_sample', type=int, default=1)
    args.add_argument('--enable_reflection', action='store_true', help='Enable reflection in Tree of Thought')
    args.add_argument('--threshold', type=float, default=0.5,
                       help='Threshold value for BFS method')
    # Add any additional arguments you need

    args = args.parse_args()
    return args


if __name__ == '__main__':
    args = parse_args()
    print(args)
    run(args)
