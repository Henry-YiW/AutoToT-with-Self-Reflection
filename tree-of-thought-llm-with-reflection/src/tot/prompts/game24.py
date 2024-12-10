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

reflection_instruction = """You are an advanced reasoning agent that improves based on self-reflection. You will be given a previous reasoning trial where you attempted to solve a Game24 puzzle. Each step includes the operation performed, the resulting value, and the remaining numbers. The attempt may or may not have successfully reached 24.

In your reflection, please:

1. Determine whether the previous attempt successfully reached 24.
2. Analyze each step, focusing on the reasoning, operations used, and value estimations.
3. Identify any mistakes, inefficiencies, or mathematical properties that were overlooked.
4. Suggest specific strategies or improvements for the next attempt.
5. Summarize common patterns or insights useful for future puzzles, such as:
   - Common factors of 24 (e.g., 8×3, 6×4, 12×2)
   - Useful intermediate numbers (e.g., creating 12 or 8 first)
   - Operation priorities (e.g., handling larger numbers first)
   - Number combinations that often work together

**Examples:**

**Example 1:**
Previous attempt:
Steps:
1. **1 + 1 = 2** (Value: 2) (Remaining: 2, 3, 8)
2. **2 * 3 = 6** (Value: 6) (Remaining: 6, 8)
3. **6 * 8 = 48** (Value: 48) (Remaining: 48)
Attempt **failed** to reach 24.

**Reflection:**
1. The attempt failed because the final result was 48, exceeding 24.
2. Multiplying 6 by 8 resulted in a value too high. Earlier steps didn't consider the end goal.
3. Overlooked that **8 * 3 = 24** could be achieved directly.
4. Next time, consider using **8 and 3** first to reach 24 efficiently.
5. Pattern: Combining larger numbers early can lead to better results.

**Example 2:**
Previous attempt:
Steps:
1. **6 * 4 = 24** (Value: 24) (Remaining: 1, 1, 24)
2. **1 + 1 = 2** (Value: 2) (Remaining: 2, 24)
3. **24 - 2 = 22** (Value: 22) (Remaining: 22)
Attempt **failed** to reach 24.

**Reflection:**
1. The attempt failed because after reaching 24, further operations moved away from the goal.
2. Subtracting 2 from 24 reduced the result unnecessarily.
3. Should have stopped after reaching 24 in the first step.
4. Next time, recognize when the goal is achieved and avoid extra steps.
5. Pattern: Avoid unnecessary operations after reaching 24.

**Example 3:**
Previous attempt:
Steps:
1. **5 + 5 = 10** (Value: 10) (Remaining: 5, 9, 10)
2. **10 + 5 = 15** (Value: 15) (Remaining: 9, 15)
3. **15 + 9 = 24** (Value: 24) (Remaining: 24)
Attempt **successfully** reached 24.

**Reflection:**
1. The attempt successfully reached 24 in three steps.
2. Addition was effectively used to combine smaller numbers to reach 24.
3. Efficient use of all numbers with simple operations.
4. This strategy worked well; similar approaches can be used in future puzzles.
5. Pattern: Summing numbers incrementally can be effective when numbers are suitable.

**Example 4:**
Previous attempt:
Steps:
1. **8 / 4 = 2** (Value: 2.0) (Remaining: 1, 2, 8)
2. **1 + 2 = 3** (Value: 3) (Remaining: 3, 8)
3. **3 * 8 = 24** (Value: 24) (Remaining: 24)
Attempt **successfully** reached 24.

**Reflection:**
1. Successfully reached 24 using division and multiplication.
2. Clever use of division to reduce a number and multiplication to reach the goal.
3. Efficient operations and good number pairing.
4. Continue using a mix of operations to find optimal solutions.
5. Pattern: Using division to create smaller numbers that can be multiplied to 24.

**Example 5:**
Previous attempt:
Steps:
1. **7 - 3 = 4** (Value: 4) (Remaining: 4, 8, 4)
2. **4 + 4 = 8** (Value: 8) (Remaining: 8, 8)
3. **8 * 8 = 64** (Value: 64) (Remaining: 64)
Attempt **failed** to reach 24.

**Reflection:**
1. The attempt failed because the final result was 64, exceeding 24.
2. Multiplying two 8s led to too high a number.
3. Overlooked that **8 * 3 = 24**; could have used 8 and the original 3.
4. Next time, consider keeping numbers that can directly lead to 24.
5. Pattern: Be cautious when multiplying large numbers; focus on combinations that produce 24.

**Example 6:**
Previous attempt:
Steps:
1. **9 + 3 = 12** (Value: 12) (Remaining: 2, 4, 12)
2. **12 * 2 = 24** (Value: 24) (Remaining: 4, 24)
3. **24 / 4 = 6** (Value: 6.0) (Remaining: 6)
Attempt **failed** to reach 24.

**Reflection:**
1. The attempt failed by performing an unnecessary operation after reaching 24.
2. Dividing 24 by 4 moved away from the goal.
3. Should have stopped after obtaining 24 in step 2.
4. In future attempts, recognize when 24 is achieved and avoid extra steps.
5. Pattern: Stop the calculation upon reaching 24 to prevent overcomplicating.

**Example 7:**
Previous attempt:
Steps:
1. **5 * 5 = 25** (Value: 25) (Remaining: 2, 7, 25)
2. **25 - 2 = 23** (Value: 23) (Remaining: 7, 23)
3. **23 + 7 = 30** (Value: 30) (Remaining: 30)
Attempt **failed** to reach 24.

**Reflection:**
1. The attempt failed as it moved further away from 24 with each step.
2. Multiplying 5 * 5 overshot the target early on.
3. Overlooked using subtraction earlier to control the total value.
4. Next time, consider using **5 * (7 - 5) = 10** and building up from there.
5. Pattern: Be cautious with multiplication that produces large numbers; consider operations that keep results within range.

**Example 8:**
Previous attempt:
Steps:
1. **6 / 2 = 3** (Value: 3.0) (Remaining: 3, 7, 8)
2. **7 + 3 = 10** (Value: 10.0) (Remaining: 8, 10)
3. **10 + 8 = 18** (Value: 18) (Remaining: 18)
Attempt **failed** to reach 24.

**Reflection:**
1. The attempt failed with a final result of 18.
2. Operations didn't focus on reaching key factors of 24.
3. Overlooked that **8 * 3 = 24** could be achieved from the numbers.
4. Next time, aim to create or use numbers that multiply to 24.
5. Pattern: Utilize multiplication of suitable numbers to reach 24 efficiently.

**Example 9:**
Previous attempt:
Steps:
1. **9 - 5 = 4** (Value: 4) (Remaining: 4, 6, 4)
2. **4 + 4 = 8** (Value: 8) (Remaining: 6, 8)
3. **6 * 8 = 48** (Value: 48) (Remaining: 48)
Attempt **failed** to reach 24.

**Reflection:**
1. The attempt failed as it resulted in 48, overshooting 24.
2. Multiplying 6 and 8 led to too large a number.
3. Could have considered **6 * 4 = 24** in earlier steps.
4. Next time, identify pairs that multiply to 24 before performing operations.
5. Pattern: Focus on creating or preserving numbers that can directly reach 24.

**Example 10:**
Previous attempt:
Steps:
1. **3 * 8 = 24** (Value: 24) (Remaining: 4, 7, 24)
Attempt **successfully** reached 24.

**Reflection:**
1. Successfully reached 24 in a single step.
2. Efficient use of multiplication with key numbers.
3. Minimal steps used, making it an optimal solution.
4. Continue identifying opportunities to reach 24 quickly.
5. Pattern: Recognize key number pairs (e.g., 3 and 8) that multiply to 24.

**Previous trial:**
{reasoning_path}

**The newly generated reflection based on the reasoning path is as follows:**"""