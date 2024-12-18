python ../../run.py \
<<<<<<< Updated upstream
    --backend gpt-3.5-turbo \
=======
    --backend gpt-4 \
>>>>>>> Stashed changes
    --task game24 \
    --task_start_index 1250 \
    --task_end_index 1362 \
    --method_generate propose \
    --method_evaluate value \
    --method_select greedy \
    --n_evaluate_sample 3 \
    --n_select_sample 5 \
    --n_generate_sample 5 \
    --threshold 0.5
