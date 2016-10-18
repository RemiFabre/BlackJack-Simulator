import sys

infile, outfile = sys.argv[1], sys.argv[2]
numbers = []
positives_ev = []
max_ev = 0.0
sum_positive_ev = 0.0
sum_ev = 0.0
key_string = "***Total EV : "
with open(infile) as inf, open(outfile,"w") as outf:
    for line in inf :
        line = line.strip()
        index1 = line.find(key_string)
        if (index1 == -1) :
            continue
        index1 = index1 + len(key_string)
        index2 = line.find(",", index1)
        ev_string = line[index1:index2]
        ev = float(ev_string)
        numbers.append(ev_string)
        sum_ev = sum_ev + ev
        if (ev > 0) :
            positives_ev.append(ev)
            sum_positive_ev = sum_positive_ev + ev
            if (ev > max_ev) :
                max_ev = ev

    for number in numbers :
        outf.writelines(number.strip() + '\n')

    positives_ev.sort()
    positives_ev_string = ""
    for ev in positives_ev :
        positives_ev_string = positives_ev_string + "{0:.3f}".format(ev) + ", "
    print ("positive evs : ", positives_ev_string)

    print("max_ev = ", max_ev)
    print("sum_positive_ev = ", sum_positive_ev)
    print("sum_ev = ", sum_ev)
