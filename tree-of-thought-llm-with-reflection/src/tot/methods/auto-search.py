import itertools
import random
import numpy as np
from functools import partial
from tot.models import gpt
import heapq

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
    reflection_prompt = task.reflection_prompt_wrap(path)
    
    if cache_reflection and reflection_prompt in task.reflection_cache:
        return task.reflection_cache[reflection_prompt]
    
    reflections = gpt(reflection_prompt, n=n_reflection_sample, stop=None)
    processed_reflections = task.reflection_outputs_unwrap(reflections)
    
    if cache_reflection:
        task.reflection_cache[reflection_prompt] = processed_reflections
    
    return processed_reflections

def crossword_execute(env, action_info, other_params):
    action = action_info['action']
    if action_info['env_info'] is not None:
        board, status, steps = action_info['env_info']
        env.reset(env.idx, board=board.copy(), status=status.copy(), steps=steps)
    obs, r, done, info = env.step(action)
    r = info['r_word']
    if len(other_params['infos']) < other_params['time_limit'] and env.steps < 10 and not any(_ == 2 for _ in env.status):  # not violating any existing constraints
        
        cnt_per_state += 1
        if cnt_per_state > other_params['max_per_state']: return 'break'
        count = env.prompt_status()      
        actions = action_info['parent_actions'].copy() 
        actions.append(action)  

        print(len(other_params['infos']))
        print(actions)
        print(env.render_board())
        print(info)
        print(count)
        if other_params['infos']:
            best = max(other_params['infos'], key=lambda x: x['info']['r_word'])
            print('best', best)
        print('--------------')
        print()

        info = {'total_step': len(other_params['infos']), 'env_step': env.steps, 'actions': actions.copy(), 'info': info, 'count': count}
        other_params['infos'].append(info)
        if other_params['prune'] and count['impossible'] >= 1:  # only continue if the current status is possible
            return 'non-generate'
    return 'generate'

def crossword_generate(env, action_info, other_params):
    candidates_to_scores = get_candidates_to_scores(env)
    if len(candidates_to_scores) == 0: return []
    sorted_candidates = sorted(candidates_to_scores, key=candidates_to_scores.get, reverse=False)
    sorted_scores = [candidates_to_scores[candidate] for candidate in sorted_candidates]
    return { "result_list": sorted_candidates, "priority_list": sorted_scores }


def check_field_values_equal(elements, field):
    """
    Check if all elements in a list have the same value for a specific field.

    Args:
        elements (list): List of dictionaries.
        field (str): The key of the field to check.

    Returns:
        bool: True if all values are equal, False otherwise.
    """
    if not elements:
        return True  # Empty list is considered valid
    
    first_value = elements[0].get(field)
    return all(element.get(field) == first_value for element in elements)

def game24_queue_stack_valuate(env, queue_stack, other_params):
    task = env['task']
    x = task.get_input(other_params['idx'])  # Input
    new_ys = queue_stack
    if (not check_field_values_equal(queue_stack, 'level')):
        return
    ids = list(range(len(new_ys)))
    infos = other_params['infos']
    # Evaluation
    if other_params['method_evaluate'] == 'vote':
        values = get_votes(task, x, new_ys, other_params['n_evaluate_sample'])
    elif other_params['method_evaluate'] == 'value':
        values = get_values(task, x, new_ys, other_params['n_evaluate_sample'])

    # Selection
    if other_params['method_select'] == 'sample':
        ps = np.array(values) / sum(values)
        select_ids = np.random.choice(ids, size=other_params['n_select_sample'], p=ps).tolist()
    elif other_params['method_select'] == 'greedy':
        select_ids = sorted(ids, key=lambda x: values[x], reverse=True)[:other_params['n_select_sample']]
    select_new_ys = [new_ys[select_id] for select_id in select_ids]

    # Log
    if other_params['to_print']:
        sorted_new_ys, sorted_values = zip(*sorted(zip(new_ys, values), key=lambda x: x[1], reverse=True))
        print(f'-- new_ys --: {sorted_new_ys}\n-- sol values --: {sorted_values}\n-- choices --: {select_new_ys}\n')

    # Reflection Handling
    if other_params['enable_reflection']:
        for select_id in select_ids:
            selected_y = new_ys[select_id]
            print("To see whether the selected y is a path")
            print("FUCK SELECTED Y", selected_y)
            path = task.get_path(selected_y)
            if task.is_goal(selected_y):
                reflection = get_reflection(task, path)
                if isinstance(reflection, str):
                    if reflection not in env['Reflection_memory']:
                        env['Reflection_memory'].append(reflection)
                else:
                    for r in reflection:
                        if r not in env['Reflection_memory']:
                            env['Reflection_memory'].append(r)
            else:
                value = values[select_id]
                if value < other_params['threshold']:
                    reflection = get_reflection(task, path)
                    if isinstance(reflection, str):
                        if reflection not in env['Reflection_memory']:
                            env['Reflection_memory'].append(reflection)
                    else:
                        for r in reflection:
                            if r not in env['Reflection_memory']:
                                env['Reflection_memory'].append(r)
        # Optionally include reflection memory in infos
        infos.append({
            'step': step,
            'x': x,
            'ys': ys,
            'new_ys': new_ys,
            'values': values,
            'select_new_ys': select_new_ys,
            'Reflection_memory': list(env['Reflection_memory'])
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

    queue_stack[:] = select_new_ys

    if other_params['to_print']:
        print(queue_stack)

def game24_generate(env, action_info, other_params):
    task = env['task']
    x = task.get_input(env.idx)
    y = action_info['action']
    if action_info['level'] >= task.steps:
        return []
    # Generation
    if other_params['method_generate'] == 'sample':
        new_ys = get_samples(
                task, x, y, other_params['n_generate_sample'], 
                prompt_sample=other_params['prompt_sample'], stop=task.stops[action_info['level']]
            )
    elif other_params['method_generate'] == 'propose':
        new_ys = get_proposals(task, x, y)
    return new_ys

def auto_search(env, other_params, execute_func, generate_func, epsilon = 0.3, decay_rate = 0.9, sliding_window_size = None, heapify_queue_stack = False, queue_stack_valuate_func = None):
    queue_stack = [{'action': None, 'parent_actions': [], 'env_info': None, 'level': 0}]
    while queue_stack:
        if queue_stack_valuate_func is not None:
            queue_stack_valuate_func(env, queue_stack, other_params)
        random_number = random.random()
        if random_number < epsilon:
            sliding_window_indexes = (0, len(queue_stack) - 1) if sliding_window_size is None else sliding_window_size
            if heapify_queue_stack:
                queue_stack_copy = queue_stack.copy()
                heapq.heapify(queue_stack_copy)
                action_info = queue_stack_copy.pop(random.randint(sliding_window_indexes[0], sliding_window_indexes[1]))
                queue_stack.pop(queue_stack.index(action_info))
            else:
                action_info = queue_stack.pop(random.randint(sliding_window_indexes[0], sliding_window_indexes[1]))
        else:
            action_info = queue_stack.pop()
        actions = action_info['parent_actions']
        level = action_info['level']

        to_generate_thoughts = 'generate'

        if action_info['action'] is not None:
            to_generate_thoughts = execute_func(env, action_info, other_params)

        if to_generate_thoughts == 'generate':
            new_thoughts = generate_func(env, action_info, other_params)
            support_heapified = False
            if (type(new_thoughts) == dict) and 'priority_list' in new_thoughts and new_thoughts['priority_list'] is not None:
                support_heapified = True
                if len(new_thoughts['result_list']) == 0: continue
                for priority, action in zip(new_thoughts['priority_list'], new_thoughts['result_list']):
                    queue_stack.append((
                        priority, {
                            'action': action, 
                            'parent_actions': actions.copy(), 
                            'env_info': (env.board.copy(), env.status.copy(), env.steps),
                            'level': level + 1
                        }
                    ))
            else:
                if len(new_thoughts) == 0: continue
                for action in new_thoughts:
                    queue_stack.append({
                        'action': action, 'parent_actions': actions.copy(), 
                        'env_info': (env.board.copy(), env.status.copy(), env.steps),
                        'level': level + 1
                        })
        elif to_generate_thoughts == 'non-generate':
            continue
        elif to_generate_thoughts == 'break':
            break
        epsilon = epsilon * decay_rate



def dfs(env, actions, infos, time_limit, prune, max_per_state):
    # get candidate thoughts
    candidates_to_scores = get_candidates_to_scores(env)
    if len(candidates_to_scores) == 0: return 0, [], []
    print(sorted(candidates_to_scores.items(), key=lambda x: x[1], reverse=True))

    # back up current state
    board, status, steps = env.board.copy(), env.status.copy(), env.steps

    # try each candidate
    cnt_per_state = 0
    for action in sorted(candidates_to_scores, key=candidates_to_scores.get, reverse=True):
        obs, r, done, info = env.step(action)
        r = info['r_word']
        if len(infos) < time_limit and env.steps < 10 and not any(_ == 2 for _ in env.status):  # not violating any existing constraints
            cnt_per_state += 1
            if cnt_per_state > max_per_state: break
            count = env.prompt_status()       
            actions.append(action)  

            print(len(infos))
            print(actions)
            print(env.render_board())
            print(info)
            print(count)
            if infos:
                best = max(infos, key=lambda x: x['info']['r_word'])
                print('best', best)
            print('--------------')
            print()

            info = {'total_step': len(infos), 'env_step': env.steps, 'actions': actions.copy(), 'info': info, 'count': count}
            infos.append(info)
            if not prune or count['impossible'] < 1:  # only continue if the current status is possible
                dfs(env, actions, infos, time_limit, prune, max_per_state)
            actions.pop()
        env.reset(env.idx, board=board.copy(), status=status.copy(), steps=steps)

def solve(args, task, idx, to_print=True):
    global gpt
    gpt = partial(gpt, model=args.backend, temperature=args.temperature)
    print(gpt)
    
    x = task.get_input(idx)  # Input
    ys = ['']  # Initial candidates
    infos = []
    if args.enable_reflection:
        Reflection_memory = set()  # Initialize reflection memory
    
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
                path = task.get_path(selected_y)  # Implement get_path to retrieve the path leading to selected_y
                if task.is_goal(selected_y):
                    reflection = get_reflection(task, path)
                    Reflection_memory.update(reflection)
                else:
                    value = values[select_id]
                    if value < args.threshold:
                        reflection = get_reflection(task, path)
                        Reflection_memory.update(reflection)
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