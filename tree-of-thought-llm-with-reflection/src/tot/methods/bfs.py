import itertools
import numpy as np
from functools import partial
from tot.models import gpt

def get_value(task, x, y, n_evaluate_sample, cache_value=True):
    value_prompt = task.value_prompt_wrap(x, y)
    if cache_value and value_prompt in task.value_cache:
        return task.value_cache[value_prompt]
    value_outputs = gpt(value_prompt, n=n_evaluate_sample, stop=None)
    value = task.value_outputs_unwrap(x, y, value_outputs)
    if cache_value:
        task.value_cache[value_prompt] = value
    return value

def get_values(task, x, ys, n_evaluate_sample, cache_value=True):
    values = []
    local_value_cache = {}
    for y in ys:  # each partial output
        if y in local_value_cache:  # avoid duplicate candidates
            value = 0
        else:    
            value = get_value(task, x, y, n_evaluate_sample, cache_value=cache_value)
            local_value_cache[y] = value
        values.append(value)
    return values

def get_votes(task, x, ys, n_evaluate_sample):
    vote_prompt = task.vote_prompt_wrap(x, ys)
    vote_outputs = gpt(vote_prompt, n=n_evaluate_sample, stop=None)
    values = task.vote_outputs_unwrap(vote_outputs, len(ys))
    return values

def get_proposals(task, x, y, local_reflections=None, global_reflections=None): 
    """
    Generate proposals considering both local and global reflections.
    
    Args:
        task: The task object
        x: Input
        y: Current partial output
        local_reflections: List of local reflections for current run
        global_reflections: List of global reflections across runs
    """
    propose_prompt = task.propose_prompt_wrap(x, y)
    
    # # Add reflections to the prompt if available
    # if local_reflections or global_reflections:
    #     propose_prompt = task.add_reflections_to_prompt(
    #         propose_prompt,
    #         local_reflections=local_reflections,
    #         global_reflections=global_reflections
    #     )
    print("------------------------FUCK PROPOSE PROMPT--------------------------", propose_prompt)
    proposals = gpt(propose_prompt, n=1, stop=None)[0].split('\n')
    return [y + _ + '\n' for _ in proposals]

def get_samples(task, x, y, n_generate_sample, prompt_sample, stop, local_reflections=None, global_reflections=None):
    """
    Generate samples considering both local and global reflections.
    
    Args:
        task: The task object
        x: Input
        y: Current partial output
        n_generate_sample: Number of samples to generate
        prompt_sample: Type of prompt ('standard' or 'cot')
        stop: Stop tokens
        local_reflections: List of local reflections for current run
        global_reflections: List of global reflections across runs
    """
    if prompt_sample == 'standard':
        prompt = task.standard_prompt_wrap(x, y)
    elif prompt_sample == 'cot':
        prompt = task.cot_prompt_wrap(x, y)
    else:
        raise ValueError(f'prompt_sample {prompt_sample} not recognized')
    
    # Add reflections to the prompt if available
    if local_reflections or global_reflections:
        prompt = task.add_reflections_to_prompt(
            prompt,
            local_reflections=local_reflections,
            global_reflections=global_reflections
        )
    print("------------------------FUCK PROMPT--------------------------", prompt)
    samples = gpt(prompt, n=n_generate_sample, stop=stop)
    return [y + _ for _ in samples]

#For the ToT with self-reflection.
def get_reflection(task, path, n_reflection_sample=1, cache_reflection=True):
    print("FUCK PATH", path)
    reflection_prompt = task.reflection_prompt_wrap(path)
    #print("FUCK REFLECTION PROMPT", reflection_prompt)
    if cache_reflection and reflection_prompt in task.reflection_cache:
        return task.reflection_cache[reflection_prompt]
    
    reflections = gpt(reflection_prompt, n=n_reflection_sample, stop=None)
    print("FUCK REFLECTION", reflections)
    processed_reflections = task.reflection_outputs_unwrap(reflections)
    print("FUCK PROCESSED REFLECTION", processed_reflections)
    
    if cache_reflection:
        task.reflection_cache[reflection_prompt] = processed_reflections
    
    return processed_reflections

def get_local_reflection(task, path, n_reflection_sample=1):
    local_reflection_prompt = task.local_reflection_prompt_wrap(path)
    reflections = gpt(local_reflection_prompt, n=n_reflection_sample, stop=None)
    processed_reflections = task.local_reflection_outputs_unwrap(reflections)
    return processed_reflections


def solve_with_reflection(args, task, idx, global_reflection_memory=None, to_print=True):
    global gpt
    gpt = partial(gpt, model=args.backend, temperature=args.temperature)
    
    x = task.get_input(idx)  # Input
    ys = ['']  # Initial candidates
    infos = []
    
    # Initialize reflection memories
    global_reflection_memory = global_reflection_memory.copy() if global_reflection_memory is not None else []
    local_reflection_memory = []

    for step in range(task.steps):
        # Generation step
        if args.method_generate == 'sample':
            # Include local reflections in the prompt
            new_ys = [
                get_samples(
                    task, x, y, args.n_generate_sample, 
                    prompt_sample=args.prompt_sample, 
                    stop=task.stops[step],
                    local_reflections=local_reflection_memory if args.enable_local_reflection else None,
                    global_reflections=global_reflection_memory if args.enable_global_reflection else None
                ) for y in ys
            ]
        elif args.method_generate == 'propose':
            new_ys = [
                get_proposals(
                    task, x, y,
                    local_reflections=local_reflection_memory if args.enable_local_reflection else None,
                    global_reflections=global_reflection_memory if args.enable_global_reflection else None
                ) for y in ys
            ]
        new_ys = list(itertools.chain(*new_ys))
        ids = list(range(len(new_ys)))

        # Evaluation
        if args.method_evaluate == 'vote':
            values = get_votes(task, x, new_ys, args.n_evaluate_sample)
        elif args.method_evaluate == 'value':
            values = get_values(task, x, new_ys, args.n_evaluate_sample)

        # Selection
        if args.method_select == 'sample':
            ps = np.array(values) / sum(values)
            select_ids = np.random.choice(ids, size=args.n_select_sample, p=ps).tolist()
        elif args.method_select == 'greedy':
            select_ids = sorted(ids, key=lambda x: values[x], reverse=True)[:args.n_select_sample]
        select_new_ys = [new_ys[select_id] for select_id in select_ids]

        # Log intermediate results
        if to_print:
            sorted_new_ys, sorted_values = zip(*sorted(zip(new_ys, values), key=lambda x: x[1], reverse=True))
            print(f'-- new_ys --: {sorted_new_ys}\n-- sol values --: {sorted_values}\n-- choices --: {select_new_ys}\n')

        # Handle Reflections
        for select_id in select_ids:
            selected_y = new_ys[select_id]
            path = task.get_path(selected_y)
            value = values[select_id]
            
            # Local reflection handling
            if args.enable_local_reflection and value < args.threshold:
                local_reflection = get_local_reflection(task, path)
                if isinstance(local_reflection, str):
                    local_reflection_memory.append(local_reflection)
                else:
                    local_reflection_memory.extend(local_reflection)
            
            # Global reflection handling
            if args.enable_global_reflection and (task.is_goal(selected_y) or value < args.threshold):
                reflection = get_reflection(task, path)
                if isinstance(reflection, str):
                    global_reflection_memory.append(reflection)
                else:
                    global_reflection_memory.extend(reflection)

        # Store step information
        step_info = {
            'step': step,
            'x': x,
            'ys': ys,
            'new_ys': new_ys,
            'values': values,
            'select_new_ys': select_new_ys
        }
        
        # Add reflection information if enabled
        if args.enable_local_reflection:
            step_info['local_reflections'] = list(local_reflection_memory)
        if args.enable_global_reflection:
            step_info['global_reflections'] = list(global_reflection_memory)
            
        infos.append(step_info)
        ys = select_new_ys

    if to_print:
        print(ys)
    return ys, {'steps': infos}

def solve_without_reflection(args, task, idx, to_print=True):
    global gpt
    gpt = partial(gpt, model=args.backend, temperature=args.temperature)
    print(gpt)
    x = task.get_input(idx)  # input
    ys = ['']  # current output candidates
    infos = []
    for step in range(task.steps):
        # generation
        if args.method_generate == 'sample':
            new_ys = [get_samples(task, x, y, args.n_generate_sample, prompt_sample=args.prompt_sample, stop=task.stops[step]) for y in ys]
        elif args.method_generate == 'propose':
            new_ys = [get_proposals(task, x, y) for y in ys]
        new_ys = list(itertools.chain(*new_ys))
        ids = list(range(len(new_ys)))
        # evaluation
        if args.method_evaluate == 'vote':
            values = get_votes(task, x, new_ys, args.n_evaluate_sample)
        elif args.method_evaluate == 'value':
            values = get_values(task, x, new_ys, args.n_evaluate_sample)

        # selection
        if args.method_select == 'sample':
            ps = np.array(values) / sum(values)
            select_ids = np.random.choice(ids, size=args.n_select_sample, p=ps).tolist()
        elif args.method_select == 'greedy':
            select_ids = sorted(ids, key=lambda x: values[x], reverse=True)[:args.n_select_sample]
        select_new_ys = [new_ys[select_id] for select_id in select_ids]

        # log
        if to_print: 
            sorted_new_ys, sorted_values = zip(*sorted(zip(new_ys, values), key=lambda x: x[1], reverse=True))
            print(f'-- new_ys --: {sorted_new_ys}\n-- sol values --: {sorted_values}\n-- choices --: {select_new_ys}\n')
        
        infos.append({'step': step, 'x': x, 'ys': ys, 'new_ys': new_ys, 'values': values, 'select_new_ys': select_new_ys})
        ys = select_new_ys
    
    if to_print: 
        print(ys)
    return ys, {'steps': infos}


def naive_solve(args, task, idx, to_print=True):
    global gpt
    gpt = partial(gpt, model=args.backend, temperature=args.temperature)
    print(gpt)
    x = task.get_input(idx)  # input
    ys = get_samples(task, x, '', args.n_generate_sample, args.prompt_sample, stop=None)
    return ys, {}