# 5-shot
standard_prompt = '''Use numbers and basic arithmetic operations (+ - * /) to obtain 24.
Input: 4 4 6 8
Answer: (4 + 8) * (6 - 4) = 24
Input: 2 9 10 12
Answer: 2 * 12 * (10 - 9) = 24
Input: 4 9 10 13
Answer: (13 - 9) * (10 - 4) = 24
Input: 1 4 8 8
Answer: (8 / 4 + 1) * 8 = 24
Input: 5 5 5 9
Answer: 5 + 5 + 5 + 9 = 24
Input: {input}
'''

# 5-shot
cot_prompt = '''Use numbers and basic arithmetic operations (+ - * /) to obtain 24. Each step, you are only allowed to choose two of the remaining numbers to obtain a new number.
Input: 4 4 6 8
Steps:
4 + 8 = 12 (left: 4 6 12)
6 - 4 = 2 (left: 2 12)
2 * 12 = 24 (left: 24)
Answer: (6 - 4) * (4 + 8) = 24
Input: 2 9 10 12
Steps:
12 * 2 = 24 (left: 9 10 24)
10 - 9 = 1 (left: 1 24)
24 * 1 = 24 (left: 24)
Answer: (12 * 2) * (10 - 9) = 24
Input: 4 9 10 13
Steps:
13 - 10 = 3 (left: 3 4 9)
9 - 3 = 6 (left: 4 6)
4 * 6 = 24 (left: 24)
Answer: 4 * (9 - (13 - 10)) = 24
Input: 1 4 8 8
Steps:
8 / 4 = 2 (left: 1 2 8)
1 + 2 = 3 (left: 3 8)
3 * 8 = 24 (left: 24)
Answer: (1 + 8 / 4) * 8 = 24
Input: 5 5 5 9
Steps:
5 + 5 = 10 (left: 5 9 10)
10 + 5 = 15 (left: 9 15)
15 + 9 = 24 (left: 24)
Answer: ((5 + 5) + 5) + 9 = 24
Input: {input}
'''


# 1-shot
propose_prompt = '''Input: 2 8 8 14
Possible next steps:
2 + 8 = 10 (left: 8 10 14)
8 / 2 = 4 (left: 4 8 14)
14 + 2 = 16 (left: 8 8 16)
2 * 8 = 16 (left: 8 14 16)
8 - 2 = 6 (left: 6 8 14)
14 - 8 = 6 (left: 2 6 8)
14 /  2 = 7 (left: 7 8 8)
14 - 2 = 12 (left: 8 8 12)
Input: {input}
Possible next steps:
'''

auto_thought_generation_selection_prompt_with_cot = '''
Given the task described previously, select a thought generation method (proposition/sampling).
proposition is a method that proposes several new thoughts at the same time by quering LLM using a single prompt (it queries the LLM once using a single prompt to get several thoughts),
this method works better for tasks with a limited thought space that could easily generate the same or similar thoughts. For example, a single number or sentence is a type thought with limited thought space.
sampling is a method that samples a new thought independently and identically from LLM (it queries the LLM independently several times to get several thoughts),
this method works better for tasks with a rich thought space that could easily generate diverse thoughts. For example, a paragraph is a type thought with rich thought space.
Please give your choice in the following format in a single word and please reach the answer step by step:
Thought generation method: proposition/sampling
'''

auto_thought_generation_method_selection_prompt_with_cot_and_few_shot = '''


Given the task described previously, select a thought generation method (proposition/sampling).
proposition is a method that proposes several new thoughts at the same time by quering LLM using a single prompt (it queries the LLM once using a single prompt to get several thoughts),
this method works better for tasks with a limited thought space that could easily generate the same or similar thoughts. For example, a single number or sentence is a type thought with limited thought space.
sampling is a method that samples a new thought independently and identically from LLM (it queries the LLM independently several times to get several thoughts),
this method works better for tasks with a rich thought space that could easily generate diverse thoughts. For example, a paragraph is a type thought with rich thought space.
Please give your choice in the following format in a single word and please reach the answer step by step:
Thought generation method: proposition/sampling
'''

auto_state_evaluation_method_selection_prompt_with_cot = '''
Given the task described previously and interaction history, select a thought/state evaluation method (value/vote).
value is a method that evaluates the current state by directly and independently scoring the current state based on how likely it is to reach the goal from the current state 
(normaly the possible scores are sure/likely/impossible where sure means the current state is guaranteed to reach the goal and impossible means the current state is guaranteed not to reach the goal),
this method works well for cases where the prospect of a thought/state to reach the goal is easy to be independently determined.
vote is a method that evaluates the current state by voting across the thoughts/states under the current parent thought/state and then selects the one with the highest votes,
this method works well for cases where the prospect of a thought/state to reach the goal is hard to be determined.
Please give your choice in the following format in a single word and please reach the answer step by step:
Thought/state evaluation method: value/vote
'''

auto_state_evaluation_method_selection_prompt_with_cot_and_few_shot = '''


Given the task described previously and interaction history, select a thought/state evaluation method (value/vote).
value is a method that evaluates the current state by directly and independently scoring the current state based on how likely it is to reach the goal from the current state 
(normaly the possible scores are sure/likely/impossible where sure means the current state is guaranteed to reach the goal and impossible means the current state is guaranteed not to reach the goal),
this method works well for cases where the prospect of a thought/state to reach the goal is easy to be independently determined.
vote is a method that evaluates the current state by voting across the thoughts/states under the current parent thought/state and then selects the one with the highest votes,
this method works well for cases where the prospect of a thought/state to reach the goal is hard to be determined.
Please give your choice in the following format in a single word and please reach the answer step by step:
Thought/state evaluation method: value/vote
'''
auto_search_method_selection_prompt_with_cot_and_few_shot = '''
Given the task described previously and interaction history, select a search method (DFS/BFS).
DFS is a method that traverse over the thought tree in a depth-first manner.
BFS is a method that traverse over the thought tree in a breadth-first manner.
Please give your choice in the following format in a single word and please reach the answer step by step:
Search method: DFS/BFS
'''

value_prompt = '''Evaluate if given numbers can reach 24 (sure/likely/impossible)
10 14
10 + 14 = 24
sure
11 12
11 + 12 = 23
12 - 11 = 1
11 * 12 = 132
11 / 12 = 0.91
impossible
4 4 10
4 + 4 + 10 = 8 + 10 = 18
4 * 10 - 4 = 40 - 4 = 36
(10 - 4) * 4 = 6 * 4 = 24
sure
4 9 11
9 + 11 + 4 = 20 + 4 = 24
sure
5 7 8
5 + 7 + 8 = 12 + 8 = 20
(8 - 5) * 7 = 3 * 7 = 21
I cannot obtain 24 now, but numbers are within a reasonable range
likely
5 6 6
5 + 6 + 6 = 17
(6 - 5) * 6 = 1 * 6 = 6
I cannot obtain 24 now, but numbers are within a reasonable range
likely
10 10 11
10 + 10 + 11 = 31
(11 - 10) * 10 = 10
10 10 10 are all too big
impossible
1 3 3
1 * 3 * 3 = 9
(1 + 3) * 3 = 12
1 3 3 are all too small
impossible
{input}
'''

value_last_step_prompt = '''Use numbers and basic arithmetic operations (+ - * /) to obtain 24. Given an input and an answer, give a judgement (sure/impossible) if the answer is correct, i.e. it uses each input exactly once and no other numbers, and reach 24.
Input: 4 4 6 8
Answer: (4 + 8) * (6 - 4) = 24
Judge: 
sure
Input: 2 9 10 12
Answer: 2 * 12 * (10 - 9) = 24
Judge: 
sure
Input: 4 9 10 13
Answer: (13 - 9) * (10 - 4) = 24
Judge: 
sure
Input: 4 4 6 8
Answer: (4 + 8) * (6 - 4) + 1 = 25
Judge: 
impossible
Input: 2 9 10 12
Answer: 2 * (12 - 10) = 24
Judge: 
impossible
Input: 4 9 10 13
Answer: (13 - 4) * (10 - 9) = 24
Judge: 
impossible
Input: {input}
Answer: {answer}
Judge:'''