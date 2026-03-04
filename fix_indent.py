result_text = []
drop_mode = False
with open("modules/statistics_engine.py", "r", encoding="utf-8") as f:
    orig = f.readlines()

for idx, lin in enumerate(orig):
    if "'posterior': round(posterior_score, 1)" in lin and orig[idx+1].strip() == "})" and orig[idx+2].strip() == "'posterior': round(posterior_score, 1)":
        new_lin = lin
        result_text.append(new_lin)
        drop_mode = 2  # Drop next 2 lines
    elif drop_mode > 0:
        drop_mode -= 1
        pass
    else:
        result_text.append(lin)
        
with open("modules/statistics_engine.py", "w", encoding="utf-8") as f:
    f.writelines(result_text)
