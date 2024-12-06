import re
import os
import sympy
import pandas as pd
from tot.tasks.base import Task, DATA_PATH
from tot.prompts.game24 import (
    standard_prompt,
    cot_prompt,
    propose_prompt,
    value_prompt,
    value_last_step_prompt,
    reflection_instruction  # Import reflection_instruction
)


def get_current_numbers(y: str) -> str:
    last_line = y.strip().split('\n')[-1]
    return last_line.split('left: ')[-1].split(')')[0]


class Game24Task(Task):
    """
    Input (x)   : a string of 4 numbers
    Output (y)  : a trajectory of 3 steps to reach 24
    Reward (r)  : 0 or 1, depending on whether the trajectory is correct
    Input Example: 
        1 2 3 4
    Output Example: 
        1 + 2 = 3 (left: 3 3 4)
        3 + 3 = 6 (left: 4 6)
        6 * 4 = 24 (left: 24)
        (1 + 2 + 3) * 4 = 24
    """
    def __init__(self, file='24.csv'):
        """
        file: a csv file (fixed)
        """
        super().__init__()
        path = os.path.join(DATA_PATH, '24', file)
        self.data = list(pd.read_csv(path)['Puzzles'])
        self.value_cache = {}
        self.steps = 4
        self.stops = ['\n'] * 4
        self.reflection_cache = {}
       
    def __len__(self) -> int:
        return len(self.data)
    
    def get_input(self, idx: int) -> str:
        return self.data[idx]

    def test_output(self, idx: int, output: str):
        expression = output.strip().split('\n')[-1].lower().replace('answer: ', '').split('=')[0]
        numbers = re.findall(r'\d+', expression)
        problem_numbers = re.findall(r'\d+', self.data[idx])
        if sorted(numbers) != sorted(problem_numbers):
            return {'r': 0}
        try:
            # print(sympy.simplify(expression))
            return {'r': int(sympy.simplify(expression) == 24)}
        except Exception as e:
            # print(e)
            return {'r': 0}
            
    @staticmethod
    def standard_prompt_wrap(x: str, y:str='') -> str:
        return standard_prompt.format(input=x) + y

    @staticmethod
    def cot_prompt_wrap(x: str, y:str='') -> str:
        return cot_prompt.format(input=x) + y
    
    @staticmethod
    def propose_prompt_wrap(x: str, y: str='') -> str:
        current_numbers = get_current_numbers(y if y else x)
        if current_numbers == '24':
            prompt = cot_prompt.format(input=x) + 'Steps:' + y
            # print([prompt])
        else:
            prompt = propose_prompt.format(input=current_numbers)
        return prompt
    
    @staticmethod
    def value_prompt_wrap(x: str, y: str) -> str:
        last_line = y.strip().split('\n')[-1]
        if 'left: ' not in last_line:  # last step
            ans = last_line.lower().replace('answer: ', '')
            # print([value_last_step_prompt.format(input=x, answer=ans)])
            return value_last_step_prompt.format(input=x, answer=ans)
        current_numbers = get_current_numbers(y)
        return value_prompt.format(input=current_numbers)
    
    @staticmethod
    def value_outputs_unwrap(x: str, y: str, value_outputs: list) -> float:
        if len(y.strip().split('\n')) == 4 and 'answer' not in y.lower():
            return 0
        value_names = [_.split('\n')[-1] for _ in value_outputs]
        value_map = {'impossible': 0.001, 'likely': 1, 'sure': 20}  # TODO: ad hoc
        value = sum(value * value_names.count(name) for name, value in value_map.items())
        return value
    
    @staticmethod
    def reflection_prompt_wrap(previous_attempt):
        """
        Constructs the reflection prompt using the previous attempt.
        """
        reflection_prompt = reflection_instruction.format(previous_attempt=previous_attempt)
        return reflection_prompt
    
    #add path to get_path
    def get_path(self, y):
        """
        Reconstructs the path leading to the candidate solution y, including value estimations.
        """
        steps_start = y.find('Steps:')
        answer_start = y.find('Answer:')
        if steps_start != -1 and answer_start != -1:
            steps_text = y[steps_start + len('Steps:'):answer_start].strip()
            steps_lines = steps_text.strip().split('\n')
            steps_with_values = []
            for line in steps_lines:
                if '(left:' in line:
                    step_part, left_part = line.split('(left:')
                    step = step_part.strip()
                    remaining = left_part.strip().rstrip(')')
                else:
                    step = line.strip()
                    remaining = 'Unknown'
                # Estimate the value after this step
                try:
                    # Extract the expression after '='
                    expr = step.split('=')[1].strip()
                    value = self.safe_eval(expr)
                except:
                    value = 'Unknown'
                steps_with_values.append(f"{step} (Value: {value}) (Remaining: {remaining})")
            attempt_result = 'Attempt **successfully** reached 24.' if self.is_goal(y) else 'Attempt **failed** to reach 24.'
            previous_attempt = 'Steps:\n' + '\n'.join(f"{i+1}. **{step}**" for i, step in enumerate(steps_with_values)) + f"\n{attempt_result}"
            return previous_attempt
        else:
            return ''
    def is_goal(self, y):
        """
        Determines if y is a goal state by checking if the final answer evaluates to 24.
        """
        import re
        match = re.search(r'Answer:\s*(.*)', y)
        if match:
            answer_expr = match.group(1).strip()
            try:
                result = self.safe_eval(answer_expr)
                return abs(result - 24) < 1e-6
            except:
                return False
        else:
            return False
    def safe_eval(self, expr):
        """
        Safely evaluates a mathematical expression.
        """
        import ast
        import operator as op

        # Supported operators
        operators = {ast.Add: op.add, ast.Sub: op.sub, ast.Mult: op.mul, ast.Div: op.truediv}

        def eval_(node):
            if isinstance(node, ast.Num):  # <number>
                return node.n
            elif isinstance(node, ast.BinOp):  # <left> <operator> <right>
                left = eval_(node.left)
                right = eval_(node.right)
                return operators[type(node.op)](left, right)
            else:
                raise TypeError(node)

        node = ast.parse(expr, mode='eval').body
        return eval_(node)

    @staticmethod
    def reflection_outputs_unwrap(reflection_outputs: list) -> str:
        """
        Processes and combines reflection outputs into a single string.
        
        Args:
            reflection_outputs: List of reflection responses from the model
            
        Returns:
            A processed string containing the combined reflections
        """
        # Combine all reflection outputs, assuming they're strings
        combined_reflections = "\n".join(reflection_outputs)
        return combined_reflections

