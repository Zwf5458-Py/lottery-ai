result_text = []
skip_next = 0
with open("modules/statistics_engine.py", "r", encoding="utf-8") as f:
    for line in f.readlines():
        if skip_next > 0:
            skip_next -= 1
            continue
        if "results.append({" in line:
            result_text.append(line)
        elif "'posterior': round(posterior_score, 1)" in line:
            result_text.append("            'posterior': round(posterior_score, 1)\n        })\n        \n")
            skip_next = 2  # skip the incorrectly remaining duplicated format lines
        else:
            result_text.append(line)
            
with open("modules/statistics_engine.py", "w", encoding="utf-8") as f:
    f.writelines(result_text)
