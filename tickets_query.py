#coding: utf-8

"""命令行火车票查看器

Usage:
    tickets.py <type> <start> <end> <date>

Options:
    -h,--help   显示帮助菜单

Example:
    g          高铁
    d          动车
    t          特快
    k          快速
    z          直达
    e`         其他
    a          显示全部结果
    tickets 北京 上海 2016-10-10        #查询北京到上海，出发日期为2016-10-10的火车票
    tickets gd 成都 南京 2016-10-10    #查询成都到南京，出发日期为2016-10-10的高铁、动车票
"""
import re
import requests
from docopt import docopt
from prettytable import PrettyTable


def get_mapping():
    #本函数用于获取火车站名与火车站名代码之间的映射关系
    url = 'https://kyfw.12306.cn/otn/resources/js/framework/station_name.js?station_version=1.9053'
    response = requests.get(url)
    stations = re.findall('[\u4e00-\u9fa5]+\|[A-Z]+', response.text)
    stations_codes = [line.split('|') for line in stations]
    mapping_to_name = {code: name for (name, code) in stations_codes}
    mapping_to_code = {name: code for (name, code) in stations_codes}

    return mapping_to_code, mapping_to_name

def trans_console(arguments,mapping_to_code):
    #本函数用于把命令行中的参数转化为有效信息
    type_code_dict = {
        'a':'全部',
        'g':'高铁',
        'd':'动车',
        't':'特快',
        'k':'快速',
        'z':'直达',
        'e':'其他'
    }
    type_code = '.'.join(arguments['<type>']).split('.')
    type_trans = [type_code_dict[i] for i in type_code]     #把车次类型指令转化为中文
    start_code = mapping_to_code[arguments['<start>']]      #出发站名编码
    end_code = mapping_to_code[arguments['<end>']]          #终点站名编码
    date = arguments['<date>']                              #出发时间
    trans_list = [type_trans, start_code, end_code, date]
    return trans_list, type_code_dict

def trains_info(mapping_to_name, trans_list, type_code_dict):
    url_tickets_info = ('https://kyfw.12306.cn/otn/leftTicket/query?' \
          'leftTicketDTO.train_date={}' \
          '&leftTicketDTO.from_station={}&leftTicketDTO.to_station={}&purpose_codes=ADULT').format(
        trans_list[3], trans_list[1], trans_list[2]
    )
    #提取列车查询页面信息
    response_tickets_info = requests.get(url_tickets_info)
    result = [line.split('|') for line in response_tickets_info.json()['data']['result']]
    #由于返回的数据格式为非结构化数据所以此处先进行分割处理
    trains_info = []
    count = 0
    for trains_available in result:
        count += 1
        if count % 10 == 0:
            print ('正在为您查询信息，请稍等...已获取 %d 趟列车数据' % count)  # 计数器显示查询进度
        url_type_info = 'https://kyfw.12306.cn/otn/czxx/queryByTrainNo?' \
                        'train_no={}' \
                        '&from_station_telecode={}' \
                        '&to_station_telecode={}' \
                        '&depart_date={}'.format(
            trains_available[2], trans_list[1], trans_list[2], trans_list[3]
        )
        train_pass_info = requests.get(url_type_info).json()['data']['data']
        train_type = train_pass_info[0]['train_class_name']
        if trans_list[0][0] != '全部':
            if train_type not in trans_list[0]:
                if '其他' in trans_list[0]:
                    if train_type in type_code_dict.values():
                        continue
                else:
                    continue
        url_price_info = 'https://kyfw.12306.cn/otn/leftTicket/queryTicketPrice?' \
                         'train_no={}' \
                         '&from_station_no={}' \
                         '&to_station_no={}' \
                         '&seat_types={}' \
                         '&train_date={}'.format(
            trains_available[2], trains_available[16], trains_available[17], trains_available[-2], trans_list[3]
        )
        #提取票价查询页面

        response_price_info = requests.get(url_price_info).json()['data']
        keys_list = response_price_info.keys()

        trains_info_values = [
            trains_available[3], #车次
            '\n'.join([mapping_to_name[trains_available[6]], mapping_to_name[trains_available[7]]]), #出发及到达车站
            '\n'.join([trains_available[8], trains_available[9]]),                                   #出发及到达时间
            trains_available[10],                                                                    #历时
            trains_available[-5] or trains_available[25],                                            #商务座/特等座剩余数量
            trains_available[-6],                                                                    #一等座剩余数量
            trains_available[-7],                                                                    #二等座剩余数量
            trains_available[21],                                                                    #高级软卧剩余数量
            trains_available[23],                                                                    #软卧剩余数量
            trains_available[-4],                                                                    #动卧剩余数量
            trains_available[28],                                                                    #硬卧剩余数量
            trains_available[24],                                                                    #软座剩余数量
            trains_available[29],                                                                    #硬座剩余数量
            trains_available[26],                                                                    #无座剩余数量
            trains_available[22],                                                                    #其它剩余数量
            train_type                                                                               #车次类型
        ]

        for i in range(len(trains_info_values)):
            if trains_info_values[i] == '':
                trains_info_values[i] = '--'
        if 'P' in keys_list and not 'A9' in keys_list:
            trains_info_values[4] = '\n'.join([trains_info_values[4],  response_price_info['P']])
        elif 'A9' in keys_list and not 'P' in keys_list:
            trains_info_values[4] = '\n'.join([trains_info_values[4],  response_price_info['A9']])

        trains_info.append([
            trains_info_values[0],
            trains_info_values[1],
            trains_info_values[2],
            trains_info_values[3],
            trains_info_values[4],
            #以下分别为不同座位对应的票价
            '\n'.join([trains_info_values[5],  response_price_info['M']]) if 'M' in keys_list else trains_info_values[5],
            '\n'.join([trains_info_values[6],  response_price_info['O']]) if 'O' in keys_list else trains_info_values[6],
            '\n'.join([trains_info_values[7],  response_price_info['A6']]) if 'A6' in keys_list else trains_info_values[7],
            '\n'.join([trains_info_values[8],  response_price_info['A4']]) if 'A4' in keys_list else trains_info_values[8],
            '\n'.join([trains_info_values[9],  response_price_info['F']]) if 'F' in keys_list else trains_info_values[9],
            '\n'.join([trains_info_values[10],  response_price_info['A3']]) if 'A3' in keys_list else trains_info_values[10],
            '\n'.join([trains_info_values[11],  response_price_info['A2']]) if 'A2' in keys_list else trains_info_values[11],
            '\n'.join([trains_info_values[12],  response_price_info['A1']]) if 'A1' in keys_list else trains_info_values[12],
            '\n'.join([trains_info_values[13],  response_price_info['WZ']]) if 'WZ' in keys_list else trains_info_values[13],
            '\n'.join([trains_info_values[14],  ''.join(response_price_info['OT'])]) if 'OT' in keys_list else trains_info_values[14],
            train_type
        ])
        #更新价格信息后的车次信息


    return trains_info

def pretty_print(trains_info, header):
    #打印函数
    pt = PrettyTable()
    pt._set_field_names(header)
    for train in trains_info:
        pt.add_row(train)
        pt.add_row(' ' * 16)
    print(pt)

def main():
    arguments = docopt(__doc__)
    header = '车次 车站 时间 历时 商务/特等 一等 二等 高级软卧 软卧 动卧 硬卧 软座 硬座 无座 其他 车次类型'.split()
    mapping_to_code, mapping_to_name = get_mapping()
    trans_list,type_code_dict = trans_console(arguments,mapping_to_code)
    trains = trains_info(mapping_to_name, trans_list,type_code_dict)
    print('共计符合搜索条件 %d 个车次' % len(trains))
    pretty_print(trains, header)

if __name__ == '__main__':
    main()