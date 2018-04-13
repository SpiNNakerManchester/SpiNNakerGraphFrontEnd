from collections import OrderedDict

import pylab as plt

data_java_8_0 = list()
data_java_8_100 = list()
data_java_4_100 = list()
data_c_8_0 = list()
data_c_8_100 = list()
data_c_4_0 = list()
data_c_4_100 = list()

files = ["c_code_results_8_0_opt.txt", "c_code_results_8_100_opt.txt", 
         "java_results_8_0.txt", "java_results_8_100.txt",
         "c_code_results_4_0_opt.txt", "c_code_results_4_100_opt.txt",
         "java_results_4_100_opt.txt"]
data_stores = [data_c_8_0, data_c_8_100, data_java_8_0, data_java_8_100,
               data_c_4_0, data_c_4_100, data_java_4_100]
names= ["c code with 8 byte \n protocol, 0 timeout",
        "c code with 8 byte \n protocol, 100 timeout",
        "java code with 8 byte \n protocol, 0 timeout",
        "java code with 8 byte \n protocol, 100 timeout",
        "c code with 4 byte \n protocol, 0 timeout",
        "c code with 4 byte \n protocol, 100 timeout",
        "java code with 4 byte \n protocol, 100 timeout"]

# read in data
for file, data in zip(files, data_stores):
    with open(file, "r") as reader:
        lines = reader.readlines()
        for line in lines:
            bits = line.split(":")
            data.append(float(bits[1]))
    

# sumemrise data
data_chip_summary = OrderedDict()
for data, name in zip(data_stores, names):
    data_chip_summary[name] = dict()
    data_chip_summary[name]["average"] = 0
    data_chip_summary[name]["high"] = 0
    data_chip_summary[name]["low"] = 10000000
    for mbs in data:
        data_chip_summary[name]["average"] += mbs
        if mbs < data_chip_summary[name]["low"]:
            data_chip_summary[name]["low"] = mbs
        if mbs > data_chip_summary[name]["high"]:
            data_chip_summary[name]["high"] = mbs
    data_chip_summary[name]["average"] = \
        data_chip_summary[name]["average"] / len(data)
    print "{}:{}:{}:{}".format(
        name, data_chip_summary[name]["average"],
        data_chip_summary[name]["low"],
        data_chip_summary[name]["high"])

x = list()
y = list()
y_bottom = 20
y_top = 50
x_seperation = 25
x_bottom = 0
x_top = len(names) * 24
e_top = list()
e_bottom = list()
labels = list()
index = 1
for name in data_chip_summary:
    x.append(index)
    y.append(data_chip_summary[name]["average"])
    e_top.append(data_chip_summary[name]["high"] - data_chip_summary[name]["average"])
    e_bottom.append(data_chip_summary[name]["average"] - data_chip_summary[name]["low"])
    index += 25
    labels.append(name)

y_ticks = list()
for tick in range(y_bottom, y_top, 2):
    y_ticks.append(tick)

plt.errorbar(x, y, yerr=[e_bottom, e_top], fmt='o')
plt.xticks(x, labels, fontsize=8)
plt.yticks(y_ticks)
plt.axis([x_bottom, x_top, y_bottom, y_top])
plt.ylabel("MBs performed")
plt.xlabel("20 mb different host impls")
plt.show()
plt.clf()
plt.close()


