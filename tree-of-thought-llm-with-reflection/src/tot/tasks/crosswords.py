import re
import os
import json
from tot.tasks.base import Task, DATA_PATH
from tot.prompts.crosswords import * 
from tot.models import gpt

class MiniCrosswordsEnv:
    def __init__(self, file='mini0505.json'):
        self.file = os.path.join(DATA_PATH, 'crosswords', file)

        self.file = json.load(open(self.file))
        self.n = len(self.file)
        self.cache = {}
        self.idx = None
        self.times = 0
        self.prompt_status_cache = {}

    def __len__(self):
        return self.n
    
    def reset(self, idx, board=None, status=None, steps=None):
        self.idx = idx
        self.data, self.board_gt = self.file[idx]
        self.board = ['_'] * 25
        self.ans = ['_____'] * 10
        self.ans_gt = self.get_ans(self.board_gt)
        self.steps = 0
        self.status = [0] * 10  # 0: unfilled; 1: filled; 2: filled then changed
        if board is not None:
            self.board = board
            self.ans = self.get_ans(self.board)
        if status is not None:
            self.status = status
        if steps is not None:
            self.steps = steps
        return self.render()
    

    def prompt_status(self):
        count = {'sure': 0, 'maybe': 0, 'impossible': 0}
        for ans, data, status in zip(self.ans, self.data, self.status):
            # if status != 0: continue
            if ans.count('_') >= 4: continue
            ans = ' '.join(ans.lower())
            line = f'{data}: {ans}'
            prompt = value_prompt.format(input=line)
            if prompt in self.prompt_status_cache:
                res = self.prompt_status_cache[prompt]
            else:
                res = gpt(prompt)[0]
                self.prompt_status_cache[prompt] = res
            # print(line)
            # print(res)
            # print()
            res = res.split('\n')[-1].strip()
            if res in count: count[res] += 1
        # print(count)
        return count
    
    def render_gt_board(self):
        s = "GT Board:\n"
        for i in range(5):
            s += ' '.join(self.board_gt[i*5:(i+1)*5]) + '\n'
        return s
    
    def render_board(self):
        s = "Current Board:\n"
        for i in range(5):
            s += ''.join(self.board[i*5:(i+1)*5]) + '\n'
        return s

    def render_clues(self, status=None):
        s = ""
        # s += "Horizontal:\n"
        for i in range(5):
            if status is None or self.status[i] == status:
                s += 'h' + str(i+1) + '. ' + self.data[i] + '\n'
        # s += "Vertical:\n"
        for i in range(5, 10):
            if status is None or self.status[i] == status:
                s += 'v' + str(i-5+1) + '. ' + self.data[i] + '\n'
        return s
    
    def render_ans(self, status=None):
        s = ""
        # s += "Horizontal:\n"
        for i in range(5):
            if status is None or self.status[i] == status:
                s += 'h' + str(i+1) + '. ' + self.data[i] + ': ' + self.ans[i] + '\n'
        # s += "Vertical:\n"
        for i in range(5, 10):
            if status is None or self.status[i] == status:
                s += 'v' + str(i-5+1) + '. ' + self.data[i] + ': ' + self.ans[i] + '\n'
        return s
    
    def render_gt_ans(self, status=None):
        s = ""
        # s += "Horizontal:\n"
        for i in range(5):
            if status is None or self.status[i] == status:
                s += 'h' + str(i+1) + '. ' + self.data[i] + ': ' + self.ans_gt[i] + '\n'
        # s += "Vertical:\n"
        for i in range(5, 10):
            if status is None or self.status[i] == status:
                s += 'v' + str(i-5+1) + '. ' + self.data[i] + ': ' + self.ans_gt[i] + '\n'
        return s

    def render(self, status=True):
        if status:
            return self.render_board() + '\nUnfilled:\n' + self.render_ans(status=0) + '\nFilled:\n' + self.render_ans(status=1) + '\nChanged:\n' + self.render_ans(status=2)
        else:
            return self.render_board() + '\n' + self.render_ans()
    
    def get_ans(self, board):
        ans = [''] * 10
        for i in range(5):
            ans[i] = ''.join(board[i*5:(i+1)*5])
        for i in range(5):
            ans[i+5] = ''.join(board[i::5])
        return ans
    
    def step(self, action):
        self.steps += 1
        action = action.split('\n')[-1]
        action = action.split('. ')
        if len(action) != 2:
            return 'Invalid! Format should be like "h1. apple"', 0, False, {}
        pos, word = action

        if len(word) != 5:
            return 'Invalid! Word should have 5 letters.', 0, False, {}
        if pos.startswith('h'):
            idx = int(pos[1:]) - 1
            self.board[idx*5:(idx+1)*5] = list(word.upper())
        elif pos.startswith('v'):
            idx = int(pos[1:]) - 1
            self.board[idx::5] = list(word.upper())
            idx += 5  # for later status update
        else:
            return 'Invalid! Position should be h1-h5 or v1-v5', 0, False, {}
        
        self.new_ans = self.get_ans(self.board)
        # self.status = [2 if (status == 1 and ans != new_ans) else status for status, ans, new_ans in zip(self.status, self.ans, self.new_ans)]
        self.status = [2 if any(letter != new_letter and letter != '_' for letter, new_letter in zip(ans, new_ans)) else status for status, ans, new_ans in zip(self.status, self.ans, self.new_ans)]
        self.status[idx] = 1
        self.ans = self.new_ans
        r_all = (self.board == self.board_gt)
        r_letter = sum(a == b for a, b in zip(self.board, self.board_gt)) / 25
        r_word = sum(a == b for a, b in zip(self.ans, self.ans_gt)) / 10
        return self.render(), r_all, (r_all or self.steps >= 20), {'r_letter': r_letter, 'r_word': r_word, 'r_game': r_all}


class MiniCrosswordsTask(Task):
    """
    Input (x)   : Decription of a 5x5 mini crossword
    Output (y)  : List of 10 words to fill in the crossword
    Reward (r)  : word level and game level
    Input Example: 
    Output Example: 
    """
    def __init__(self, file='mini0505.json'):
        """
        file: a csv file (fixed)
        """
        super().__init__()
        self.env = MiniCrosswordsEnv(file)  # use it as a stateless tool
        self.xs = []
        for idx in range(len(self.env)):
            self.env.reset(idx)
            self.xs.append(self.env.render_clues())
        self.steps = 10  # TODO: variable steps??
        self.cache_proposals = {}

    def __len__(self) -> int:
        return len(self.env)
    
    def get_input(self, idx: int) -> str:
        self.env.reset(idx)
        return self.env.render_clues()
    
    # def test_output(self, idx: int, output: str):  # TODO: r_word for now
    #     self.env.reset(idx)
    #     info = {'r_word': 0}
    #     for line in output.split('\n'):
    #         if line.startswith('h') or line.startswith('v'):
    #             _, _, _, info = self.env.step(line)
    #     return info['r_word']
    
    def test_output(self, idx: int, output: str):
        self.env.reset(idx)
        output = output.split('Output:\n')[-1]
        info = {'r_word': 0, 'r_letter': 0, 'r_game': 0}
        for i, line in enumerate(output.strip().split('\n')[-5:], 1):
            letters = line.split(' ')[:5]
            word = ''.join(letters)
            word = word + '_' * (5 - len(word))
            action = f'h{i}. {word}'
            # print(action)
            _, _, _, info = self.env.step(action)
        info['r'] = info['r_word']
        return info

    def set_status(self, x: str, y: str):
        idx = self.xs.index(x)
        self.test_output(idx, y)  # update self.env
    
    @staticmethod
    def standard_prompt_wrap(x: str, y:str='') -> str:
        return standard_prompt.format(input=x) + y

    @staticmethod
    def cot_prompt_wrap(x: str, y:str='') -> str:
        return cot_prompt.format(input=x) + y
    
    def propose_prompt_wrap(self, x: str, y: str='') -> str:
        self.set_status(x, y)
        return propose_prompt.format(input=self.env.render())
    
    def propose_outputs_unwrap(self, x: str, y: str, outputs: list, n_max_propose: int) -> list:
        confidence_to_value = {'certain': 1, 'high': 0.5, 'medium': 0.2, 'low': 0.1}  # TODO: ad hoc
        proposals_to_scores = {}
        for output in outputs:
            lines = output.split('\n')
            pattern = r'^([hv][1-5])\. ([a-zA-Z]{5,5}) \((certain|high|medium|low)\).*$'
            for line in lines:
                match = re.match(pattern, line)
                if match:
                    parts = [match.group(1), match.group(2), match.group(3)]
                    proposal = parts[0].lower() + '. ' + parts[1].lower()
                    score = confidence_to_value.get(parts[2], 0)
                    proposals_to_scores[proposal] = proposals_to_scores.get(proposal, 0) + score
        
        proposals = sorted(proposals_to_scores.items(), key=lambda x: x[1], reverse=True)
        if n_max_propose != -1:
            proposals = proposals[:n_max_propose]
        proposals = [y + proposal[0] + '\n' for proposal in proposals]
        self.cache_proposals[(x, y, n_max_propose)] = proposals
        return proposals
    
    def evaluate(self, x: str, y: str, n_evaluate_sample: int) -> int:
        self.set_status(x, y)
        assert n_evaluate_sample == 1 # TODO: ad hoc
        count = {'sure': 0, 'maybe': 0, 'impossible': 0}
        for ans, data, status in zip(self.env.ans, self.env.data, self.env.status):
            if ans.count('_') >= 4: continue
            ans = ' '.join(ans.lower())
            line = f'{data}: {ans}'
            prompt = value_prompt.format(input=line)
            res = gpt(prompt)[0]
            print(line)
            print(res)
            print()
            res = res.split('\n')[-1].strip()
            if res in count: count[res] += 1
        print(count)
        return count

    @staticmethod
    def reflection_prompt_wrap(reasoning_path):
        """
        Constructs the reflection prompt using the previous attempt.
        """
        print("CROSSWORD REASONING PATH", reasoning_path)
        reflection_prompt = reflection_instruction.format(reasoning_path=reasoning_path)
        return reflection_prompt
    
    @staticmethod
    def add_reflections_to_prompt(original_prompt, local_reflections=None, global_reflections=None):
        """
        Add both local and global reflections to the prompt.
        Only use the most recent 20 global reflections to avoid prompt being too long.
        """
        reflection_text = ""
        
        if local_reflections:
            reflection_text += "\nLocal insights from current crossword attempts:\n"
            reflection_text += "\n".join(f"- {r}" for r in local_reflections)
        
        if global_reflections:
            reflection_text += "\nGlobal insights from previous crosswords:\n"
            recent_global_reflections = global_reflections[-20:]
            reflection_text += "\n".join(f"- {r}" for r in recent_global_reflections)
        
        if reflection_text:
            reflection_text += "\nPlease consider these insights when filling the crossword.\n"
            
        return original_prompt + reflection_text

    def get_path(self, y, father_dict=None):
        """
        Get the solution path with formatting and success/failure indication.
        """
        # Split into individual steps
        steps = [s.strip() for s in y.strip().split('\n') if s.strip()]
        
        # Determine success/failure
        attempt_result = 'Attempt **successfully** completed.' if self.is_goal(y) else 'Attempt **incomplete**.'
        
        # Format the output
        return 'Steps:\n' + '\n'.join(f"{i+1}. {step}" for i, step in enumerate(steps)) + f"\n\n{attempt_result}"

    def is_goal(self, y):
        """
        Determines if y is a complete solution by checking if all words are filled.
        """
        output = y.split('Output:\n')[-1]
        filled_words = [line for line in output.strip().split('\n')[-5:] if line.strip()]
        return len(filled_words) == 5 and all(len(word.split()) >= 5 for word in filled_words)

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
            word_analysis = re.search(r'Word Analysis:\s*([^\n]*)', reflection)
            constraint_analysis = re.search(r'Constraint Analysis:\s*([^\n]*)', reflection)
            next_step = re.search(r'Next Step:\s*([^\n]*)', reflection)
            
            if next_step:  # Only include if we have at least the next step suggestion
                reflection_text = f"Next step: {next_step.group(1)}"
                if word_analysis:
                    reflection_text += f" (based on: {word_analysis.group(1)})"
                processed_reflections.append(reflection_text)
        
        return processed_reflections
