import copy

v = 50
p = 0.52
q = 1 - p
N = 2500
values = {v:1.0}

for i in range(N) :
    old_values = copy.deepcopy(values) 
    values = {}
    if (0 in old_values) :
        values[0] = old_values[0]
    for key in old_values :
        if (key == 0) :
            continue
        current_value = key
        current_p = old_values[key]
        win_value = current_value + 1
        lose_value = current_value - 1 
        #p probability of wining 1
        if (win_value in values) :
            values[win_value] = values[win_value] + current_p*p
        else :
            values[win_value] = current_p*p

        #q probability of losing 1
        if (lose_value in values) :
            values[lose_value] = values[lose_value] + current_p*q
        else :
            values[lose_value] = current_p*q

    
    #print(values)
    #test = input("go")
total = 0.0
for i in range(v) :
    if (i in values) :
        print ("values[i] = ", values[i])
        total = values[i] + total

grand_total = 0.0
for i in values :
    grand_total = values[i] + grand_total
        
print("Proba of losing : ", values[0])
print("Proba of less than initial : ", total)
print("1 : ", grand_total)
