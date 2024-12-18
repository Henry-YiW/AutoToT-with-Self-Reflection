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
    reflection_instruction,  # Import reflection_instruction
    local_reflection_instruction
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
    def reflection_prompt_wrap(reasoning_path):
        """
        Constructs the reflection prompt using the previous attempt.
        """
        print("FUCK REASONING PATH", reasoning_path)
        reflection_prompt = reflection_instruction.format(reasoning_path=reasoning_path)
        return reflection_prompt
    
    @staticmethod
    def add_reflections_to_prompt(original_prompt, local_reflections=None, global_reflections=None):
        """
        Add both local and global reflections to the prompt.
        Only use the most recent 20 global reflections to avoid prompt being too long.
        
        Args:
            original_prompt: The base prompt
            local_reflections: List of local reflections for current run
            global_reflections: List of global reflections across runs
        """
        reflection_text = ""
        
        if local_reflections:
            reflection_text += "\nLocal insights from current attempts:\n"
            reflection_text += "\n".join(f"- {r}" for r in local_reflections)
        
        if global_reflections:
            reflection_text += "\nGlobal insights from previous experience:\n"
            # Take only the last 20 global reflections
            recent_global_reflections = global_reflections[-20:]
            reflection_text += "\n".join(f"- {r}" for r in recent_global_reflections)
        
        if reflection_text:
            reflection_text += "\nPlease consider these insights when generating your solution.\n"
            
        return original_prompt + reflection_text
    #add path to get_path
    def get_path(self, y, father_dict=None):
        """
        Get the solution path with formatting and success/failure indication.
        
        Args:
            y: The solution string containing all steps
            father_dict: Not used since solution path is already in y
            
        Returns:
            Formatted string containing steps and result indication
        """
        # Split into individual steps
        steps = [s.strip() for s in y.strip().split('\n') if s.strip()]
        
        # Determine success/failure
        attempt_result = 'Attempt **successfully** reached 24.' if self.is_goal(y) else 'Attempt **failed** to reach 24.'
        
        # Format the output
        return 'Steps:\n' + '\n'.join(f"{i+1}. {step}" for i, step in enumerate(steps)) + f"\n\n{attempt_result}"
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

    @staticmethod
    def local_reflection_prompt_wrap(path):
        """
        Generate a prompt for local reflection focused on immediate improvements.
        """
        return local_reflection_instruction.format(reasoning_path=path)

    @staticmethod
    def local_reflection_outputs_unwrap(reflections):
        """
        Process the local reflection outputs into structured tactical advice.
        """
        processed_reflections = []
        for reflection in reflections:
            # Extract sections using regex
            value_analysis = re.search(r'Value Analysis:\s*([^\n]*)', reflection)
            number_properties = re.search(r'Number Properties:\s*([^\n]*)', reflection)
            next_step = re.search(r'Next Step:\s*([^\n]*)', reflection)
            
            if next_step:  # Only include if we have at least the next step suggestion
                reflection_text = f"Next step: {next_step.group(1)}"
                if value_analysis:
                    reflection_text += f" (based on: {value_analysis.group(1)})"
                processed_reflections.append(reflection_text)
        
        return processed_reflections

