known = set()
lines = []

removed = 0
file = "R2-C2-NM-gliders.db.txt"
with open(file, "r") as f:
    for line in f.readlines():
        tokens = line.split(":")
        if tuple(tokens[2:7]) in known:
            removed += 1
            continue

        known.add(tuple(tokens[2:7]))
        known.add(tuple(tokens[2:5] + [str(-int(line.split(":")[5]))] + [str(-int(line.split(":")[6]))]))
        known.add(tuple(tokens[2:7] + [str(int(line.split(":")[5]))] + [str(-int(line.split(":")[6]))]))
        known.add(tuple(tokens[2:7] + [str(-int(line.split(":")[5]))] + [str(int(line.split(":")[6]))]))
        lines.append(line)

with open(file, "w") as f:
    for line in lines:
        f.write(line)

print("Removed: " + str(removed))
