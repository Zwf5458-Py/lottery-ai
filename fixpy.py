lines = []
with open("modules/statistics_engine.py", "r", encoding="utf-8") as f:
    for line in f.readlines():
        if "'posterior': round(posterior_score, 1)" in line:
            # check the whole sequence
            pass
        lines.append(line)
        
with open("modules/statistics_engine.py", "w", encoding="utf-8") as f:
    f.writelines(lines)
