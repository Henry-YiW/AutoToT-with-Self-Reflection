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

def get_proposals(task, x, y): 
    propose_prompt = task.propose_prompt_wrap(x, y)
    proposals = gpt(propose_prompt, n=1, stop=None)[0].split('\n')
    return [y + _ + '\n' for _ in proposals]

def get_samples(task, x, y, n_generate_sample, prompt_sample, stop):
    if prompt_sample == 'standard':
        prompt = task.standard_prompt_wrap(x, y)
    elif prompt_sample == 'cot':
        prompt = task.cot_prompt_wrap(x, y)
    else:
        raise ValueError(f'prompt_sample {prompt_sample} not recognized')
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


def solve(args, task, idx, global_reflection_memory=None, to_print=True):
    global gpt
    gpt = partial(gpt, model=args.backend, temperature=args.temperature)
    print(gpt)
    
    x = task.get_input(idx)  # Input
    ys = ['']  # Initial candidates
    infos = []
    
    # Use global reflection memory if provided, otherwise create new list
    Reflection_memory = global_reflection_memory.copy() if global_reflection_memory is not None else []
    
    for step in range(task.steps):
        # Generation
        if args.method_generate == 'sample':
            new_ys = [
                get_samples(
                    task, x, y, args.n_generate_sample, 
                    prompt_sample=args.prompt_sample, stop=task.stops[step]
                ) for y in ys
            ]
        elif args.method_generate == 'propose':
            new_ys = [get_proposals(task, x, y) for y in ys]
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

        # Log
        if to_print:
            sorted_new_ys, sorted_values = zip(*sorted(zip(new_ys, values), key=lambda x: x[1], reverse=True))
            print(f'-- new_ys --: {sorted_new_ys}\n-- sol values --: {sorted_values}\n-- choices --: {select_new_ys}\n')

        # Reflection Handling
        if args.enable_reflection:
            for select_id in select_ids:
                selected_y = new_ys[select_id]
                print("To see whether the selected y is a path")
                print("FUCK SELECTED Y", selected_y)
                path = task.get_path(selected_y)
                if task.is_goal(selected_y):
                    reflection = get_reflection(task, path)
                    if isinstance(reflection, str):
                        if reflection not in Reflection_memory:
                            Reflection_memory.append(reflection)
                    else:
                        for r in reflection:
                            if r not in Reflection_memory:
                                Reflection_memory.append(r)
                else:
                    value = values[select_id]
                    if value < args.threshold:
                        reflection = get_reflection(task, path)
                        if isinstance(reflection, str):
                            if reflection not in Reflection_memory:
                                Reflection_memory.append(reflection)
                        else:
                            for r in reflection:
                                if r not in Reflection_memory:
                                    Reflection_memory.append(r)
            # Optionally include reflection memory in infos
            infos.append({
                'step': step,
                'x': x,
                'ys': ys,
                'new_ys': new_ys,
                'values': values,
                'select_new_ys': select_new_ys,
                'Reflection_memory': list(Reflection_memory)
            })
        else:
            infos.append({
                'step': step,
                'x': x,
                'ys': ys,
                'new_ys': new_ys,
                'values': values,
                'select_new_ys': select_new_ys
            })

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