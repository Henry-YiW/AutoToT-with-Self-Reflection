python ../../run.py \
    --backend gpt-4 \
    --task game24 \
<<<<<<< Updated upstream
    --task_start_index 900 \
    --task_end_index 1000\
=======
    --task_start_index 1330 \
    --task_end_index 1362\
>>>>>>> Stashed changes
    --method_generate propose \
    --method_evaluate value \
    --method_select greedy \
    --n_generate_sample 5 \
    --n_evaluate_sample 3 \
    --n_select_sample 5 \
    --enable_reflection \
    --threshold 0.5


# python ../../run.py \
#     --backend gpt-4 \
#     --task game24 \
#     --task_start_index 1250 \
#     --task_end_index 1362\
#     --method_generate propose \
#     --method_evaluate value \
#     --method_select greedy \
#     --n_generate_sample 5 \
#     --n_evaluate_sample 3 \
#     --n_select_sample 5 \
#     --enable_reflection \
#     --threshold 0.5
