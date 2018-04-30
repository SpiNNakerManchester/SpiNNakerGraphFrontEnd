import pylab as plt

data_chip = dict()
data_size = dict()

# read in data
with open("results", "r") as reader:
    lines = reader.readlines()
    for line in lines[::2]:
        bits = line.split(":")
        bits[0] = bits[0].split(" ")[1]
        if (bits[0], bits[1]) not in data_chip:
            data_chip[bits[0], bits[1]] = dict()
        if int(bits[2]) not in data_chip[bits[0], bits[1]]:
            data_chip[bits[0], bits[1]][int(bits[2])] = set()
        data_chip[bits[0], bits[1]][int(bits[2])].add(float(bits[4]))

        if bits[2] not in data_size:
            data_size[bits[2]] = set()
        data_size[bits[2]].add(float(bits[4]))

    # print data_size
    # print data_chip


# sumemrise data
data_chip_summary = dict()
for x, y in data_chip:
    data_chip_summary[x, y] = dict()
    for mb in data_chip[x, y]:
        data_chip_summary[x, y][mb] = dict()
        data_chip_summary[x, y][mb]["average"] = 0
        data_chip_summary[x, y][mb]["high"] = 0
        data_chip_summary[x, y][mb]["low"] = 10000000
        for mbs in data_chip[x, y][mb]:
            data_chip_summary[x, y][mb]["average"] += mbs
            if mbs < data_chip_summary[x, y][mb]["low"]:
                data_chip_summary[x, y][mb]["low"] = mbs
            if mbs > data_chip_summary[x, y][mb]["high"]:
                data_chip_summary[x, y][mb]["high"] = mbs
        data_chip_summary[x, y][mb]["average"] = \
            data_chip_summary[x, y][mb]["average"] / len(data_chip[x, y][mb])
        print "{}:{}:{}:{}:{}:{}".format(
            x, y, mb, data_chip_summary[x, y][mb]["average"],
            data_chip_summary[x, y][mb]["low"],
            data_chip_summary[x, y][mb]["high"])

chip_keys = data_chip_summary
chip_keys = sorted(chip_keys)
for chip_x, chip_y in chip_keys:
    keys = data_chip[chip_x, chip_y]
    keys = sorted(keys)
    x = list()
    y = list()
    e_top = list()
    e_bottom = list()
    labels = list()
    index = 1
    for mb in keys:
        x.append(index)
        y.append(data_chip_summary[chip_x, chip_y][mb]["average"])
        e_top.append(data_chip_summary[chip_x, chip_y][mb]["high"] -
                     data_chip_summary[chip_x, chip_y][mb]["average"])
        e_bottom.append(data_chip_summary[chip_x, chip_y][mb]["average"] -
                        data_chip_summary[chip_x, chip_y][mb]["low"])
        index += 5
        labels.append("{}:{}:{}".format(chip_x, chip_y, mb))

    plt.errorbar(x, y, yerr=[e_bottom, e_top], fmt='o')
    plt.xticks(x, labels, rotation='vertical')
    plt.axis([0, 30, 0, 25])
    plt.ylabel("MBs performed")
    plt.xlabel("location and mb loaded")
    plt.show()
    plt.clf()
    plt.close()
