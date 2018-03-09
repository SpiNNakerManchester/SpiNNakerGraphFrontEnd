import pylab as plt

data_size = dict()

# read in data
with open("results", "r") as reader:
    lines = reader.readlines()
    index = 0
    for line in lines:
        if line != "\n" and len(line.split("running iteration")) != 2:
            bits = line.split(":")
            if int(bits[2]) not in data_size:
                data_size[int(bits[2])] = set()
            data_size[int(bits[2])].add(float(bits[3]))

    #print data_size


# sumemrise data
data_chip_summary = dict()
for mb in data_size:
    data_chip_summary[mb] = dict()
    data_chip_summary[mb]["average"] = 0
    data_chip_summary[mb]["high"] = 0
    data_chip_summary[mb]["low"] = 10000000
    for mbs in data_size[mb]:
        data_chip_summary[mb]["average"] += mbs
        if mbs < data_chip_summary[mb]["low"]:
            data_chip_summary[mb]["low"] = mbs
        if mbs > data_chip_summary[mb]["high"]:
            data_chip_summary[mb]["high"] = mbs
    data_chip_summary[mb]["average"] = \
        data_chip_summary[mb]["average"] / len(data_size[mb])
    print "{}:{}:{}:{}".format(
        mb, data_chip_summary[mb]["average"],
        data_chip_summary[mb]["low"],
        data_chip_summary[mb]["high"])

keys = data_chip_summary
keys = sorted(keys)
x = list()
y = list()
e_top = list()
e_bottom = list()
labels = list()
index = 1

for mb in keys:
    x.append(index)
    y.append(data_chip_summary[mb]["average"])
    e_top.append(data_chip_summary[mb]["high"] - data_chip_summary[mb]["average"])
    e_bottom.append(data_chip_summary[mb]["average"] - data_chip_summary[mb]["low"])
    index += 5
    labels.append("{}".format(mb))

plt.errorbar(x, y, yerr=[e_bottom, e_top], fmt='o')
plt.xticks(x, labels, rotation='vertical')
plt.axis([0, 30, 0, 25])
plt.ylabel("MBs performed")
plt.xlabel("mb loaded everywhere")
plt.show()
plt.clf()
plt.close()


