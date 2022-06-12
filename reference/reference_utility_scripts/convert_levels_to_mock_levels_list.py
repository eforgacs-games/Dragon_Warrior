import os
import re

raw_files_dir = "C:\\Users\\eddie\\PycharmProjects\\DragonWarrior\\reference\\raw_levels_lists"
for filename in os.listdir(raw_files_dir):
    with open(os.path.join(raw_files_dir, filename), "r") as input_raw_levels_file:
        level = os.path.basename(input_raw_levels_file.name).split(".txt")[0]
        output_file = open(f"C:\\Users\\eddie\\PycharmProjects\\DragonWarrior\\reference\\converted_levels_lists\\{level}.py", "w")
        output_file.write(f"mock_levels_list_{level} = {{")
        output_file.write("\n")
        for line in input_raw_levels_file:
            line = line.replace('=', '')
            line = line.replace(',', '')
            line = re.sub('\u2212', '\u002D', line)

            line = re.sub("\t([A-Z]+)", r'\t"\1"', line)
            line = re.sub("\t-", "\tNone", line)
            line = re.sub("(\d+)\t(\d+)\t(\d+)\t(\d+.*)\t(\d+.*)\t(\d+.*)\t(\d+.*)\t(.*)",
                          r"\1: {'total_exp': \2, 'strength': \3, 'agility': \4, 'max_hp': \5, 'max_mp': \6, 'spell': \7},",
                          line)
            line = line.replace('"None"', "None")
            output_file.write(line)
        output_file.write("\n}")
