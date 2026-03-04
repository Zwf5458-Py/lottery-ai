with open(r"F:\CODE\六合彩\modules\statistics_engine.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

new_lines = []
skip = False
for index, line in enumerate(lines):
    if "'posterior': round(posterior_score, 1)" in line and "})" in lines[index+1]:
        # we found the point, skip lines[index+2:4] which contained duplicated ones
        new_lines.append(line)
        pass
    else:
        new_lines.append(line)

with open(r"F:\CODE\六合彩\modules\statistics_engine.py", "w", encoding="utf-8") as f:
    f.writelines(new_lines)
