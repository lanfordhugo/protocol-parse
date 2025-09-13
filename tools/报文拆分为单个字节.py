import textwrap

while True:
    print('')
    data = input("输入数据：")
    if(data == 'q'):
        exit()
    else:
        res = textwrap.fill(data, width=2)
        res_result = res.split()
        for i,data in enumerate(res_result):
            if((i % 25) == 0):
                print("")
            print(data, end=' ')