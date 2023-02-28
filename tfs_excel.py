#!/usr/bin/python3
from tfs import TFSAPI
import xlsxwriter
import re
import argparse
import datetime
import subprocess
import sys
 
parser = argparse.ArgumentParser()
parser.add_argument('--pat', default="fmzzuj6opqc2yv2zspw2uoiz73k5iwa5q2v25nzcwyztg5oqtw3q" )
parser.add_argument('--from',
                    type=lambda d: datetime.datetime.strptime(d, '%d-%m-%Y').date().strftime("%d-%m-%Y"),
                    help='dd-mm-YYYY', required=True)
parser.add_argument('--to',
                    type=lambda d: datetime.datetime.strptime(d, '%d-%m-%Y').date().strftime("%d-%m-%Y"),
                    help='dd-mm-YYYY', required=True)
parser.add_argument("--out", default="time_report.xlsx", help="File to put results into")
parser.add_argument("--open", action='store_true', default=False, help="Tells if to open the resulting file immediately after creation")
args = parser.parse_args()

 #vars(args)["from"]
 #vars(args)["to"]
def get_items_from_project(project_name, date_start, date_end):

    client = TFSAPI("https://tfs.content.ai/", project=project_name, pat=args.pat) # Соединение с тфс
    # Запрос
    if (project_name == 'HQ/ContentAI'): 
        query = """SELECT [System.AssignedTo], [Tags]
    FROM workitems
    WHERE [System.State] = 'Done' AND [System.WorkItemType] = 'Task' AND ([Closed Date] >= ' """ + date_start + """ ' AND [Closed Date] <= ' """ + date_end + """ ')
    ORDER BY [System.AssignedTo]
    """
    elif (project_name == 'NLC/AIS'):
        query = """SELECT [System.AssignedTo], [Tags]
    FROM workitems
    WHERE [System.State] = 'Closed' AND ([System.WorkItemType] = 'Bug' OR [System.WorkItemType] = 'Task') AND ([Closed Date] >= ' """ + date_start + """ ' AND [Closed Date] <= ' """ + date_end + """ ')
    ORDER BY [System.AssignedTo]
    """
    elif (project_name == 'Lingvo/Lingvo X6'):
        query = """SELECT [System.AssignedTo], [Tags]
    FROM workitems
    WHERE [System.State] = 'Closed' AND ([System.WorkItemType] = 'Bug' OR [System.WorkItemType] = 'Feature')  AND ([Closed Date] >= ' """ + date_start + """ ' AND [Closed Date] <= ' """ + date_end + """ ')
    ORDER BY [System.AssignedTo]
    """
    wiql = client.run_wiql(query)
    return wiql


workitems = get_items_from_project("HQ/ContentAI", vars(args)["from"],vars(args)["to"]).workitems # Получаем объекты из запроса
workitems_1 = get_items_from_project("NLC/AIS", vars(args)["from"],vars(args)["to"]).workitems
workitems_2 = get_items_from_project("Lingvo/Lingvo X6", vars(args)["from"],vars(args)["to"]).workitems
workitems_all = workitems + workitems_1 + workitems_2

members = [] # Лист прикрепленных к задаче людей
tags = [] # Лист тегов
tasks_unassigned = [] # Лист unassigned тасков
id_unassigned = [] # Лист id unassigned тасков
tags_error = []
id_error = []
testers_names = []
testers_tags = []


def get_tag_from_parent(item): # Поиск тега таска через родителей
    if (item.parent):
        if (item.parent['Tags']):
            if(re.fullmatch(r'^[A-Z]+_\d+\.\d+\.\d+$', item.parent['Tags'])):
                return item.parent['Tags']
            else: return None
        else:
            return get_tag_from_parent(item.parent)
    else: return None

for x in workitems: # Выборка данных
    
    if (x['AssignedTo']):        
        members.append(x['AssignedTo'][:x['AssignedTo'].find(' <')]) 
        if (x['Tags']):
            if(re.search(r'\@[А-Яа-яё]+[_ ][А-Яа-яё]+', x['Tags']) != None):
                testers_names.append(re.search(r'\@[А-Яа-яё]+[_ ][А-Яа-яё]+', x['Tags']).group(0).replace('_',' ').replace('@',''))
                if(re.search(r'[A-Z]+_\d+\.\d+\.\d+', x['Tags']) != None):
                    tags.append(re.search(r'[A-Z]+_\d+\.\d+\.\d+', x['Tags']).group(0))
                    testers_tags.append(tags[-1])
                else:                
                    tags.append(get_tag_from_parent(x))
                    testers_tags.append(tags[-1])
            else:
                if(re.search(r'[A-Z]+_\d+\.\d+\.\d+', x['Tags']) != None):
                    tags.append(re.search(r'[A-Z]+_\d+\.\d+\.\d+', x['Tags']).group(0))                   
                else:                
                    tags.append(get_tag_from_parent(x))   
        else:
            tags.append(get_tag_from_parent(x))            
    else:
        tasks_unassigned.append(x['Title'])
        id_unassigned.append(x['Id'])
        
members += testers_names
tags += testers_tags
        
def sort_items_by_project(items, tag_sign):
    for item in items:
        if (item['AssignedTo']):        
            members.append(item['AssignedTo'][:item['AssignedTo'].find(' <')]) 
            if (re.search(r'\d+\.\d+\.\d+', item['system.iterationpath']) != None):
                tags.append(tag_sign+'_'+re.search(r'\d+\.\d+\.\d+', item['system.iterationpath']).group(0))
        else:
            tasks_unassigned.append(item['Title'])
            id_unassigned.append(item['Id'])   

sort_items_by_project(workitems_1, 'AIS')
sort_items_by_project(workitems_2, 'LX6')

# ============================Табличка======================================================

list_array = [[None]]  # Двумерный лист для заполнения
dict_tags = {} # Словарь тегов
dict_names = {} # Словарь имен

for i in range(len(tags)): # Заполнение словаря тегов и первой строчки листа
    if tags[i] not in list_array[0]:
        dict_tags[tags[i]] = len(list_array[0])
        list_array[0].append(tags[i])

dict_tags['Default'] = len(list_array[0]) # Добавляем в словарь и лист значения Default для задач без тегов и Sum для проверки
list_array[0].append('Default')
dict_tags['Sum'] = len(list_array[0])
list_array[0].append('Sum')

for i in range(len(members)): # Заполнение словаря имен и первого столбца листа
    if members[i] not in dict_names.keys():
        dict_names[members[i]] = len(list_array)
        list_array.append([members[i]])
        list_array[-1].extend([0]*(len(list_array[0])-1))

for i in range(len(members)): # Подсчет задач, к которым прикреплен конкретный человек
    if (dict_names.get(members[i])):
        if (dict_tags.get(tags[i])):
            list_array[dict_names.get(members[i])][dict_tags.get(tags[i])] += 1
            list_array[dict_names.get(members[i])][dict_tags.get('Sum')] += 1
        else:
            list_array[dict_names.get(members[i])][dict_tags.get('Default')] += 1
            list_array[dict_names.get(members[i])][dict_tags.get('Sum')] += 1

for i in range(1, len(list_array)): # Перезапись в процентной форме (0 значения заполняются ' ')
    for j in range(1, len(list_array[0])):
        if (list_array[i][j] > 0):
            list_array[i][j] = str(round((list_array[i][j]/list_array[i][dict_tags.get('Sum')])*100, 2)) + '%'
        else:
            list_array[i][j] = ' '

list_array[0][0] = ' '
list_array.sort(key = lambda x: x[0])

workbook = xlsxwriter.Workbook(args.out) # Создание excel файла
worksheet = workbook.add_worksheet() # Создание таблицы

def get_link_to_tfs(name, tag):
    result_string = ''
    if tag == 'Default':
        tag = None

    for x in workitems_all:        
        if (x['AssignedTo'][:x['AssignedTo'].find(' <')] == name):
            if (tag != None and tag.find("LX6") != -1 and x['TeamProject'] == 'Lingvo X6' and (re.search(r'\d+\.\d+\.\d+', tag).group(0) == re.search(r'\d+\.\d+\.\d+', x['system.iterationpath']).group(0))):
                result_string += x._links['html']['href'] +'\n'
            elif (tag != None and tag.find("AIS") != -1 and x['TeamProject'] == 'AIS' and (re.search(r'\d+\.\d+\.\d+', tag).group(0) == re.search(r'\d+\.\d+\.\d+', x['system.iterationpath']).group(0))):
                result_string += x._links['html']['href'] +'\n'
            elif (x['Tags']):
                if (tag == x['Tags'] or tag == get_tag_from_parent(x)):                    
                    result_string += x._links['html']['href'] +'\n'
            else:
                if (tag == get_tag_from_parent(x)):                    
                    result_string += x._links['html']['href'] +'\n'
        elif (x['Tags'] and re.search(r'\@[А-Яа-яё]+[_ ][А-Яа-яё]+', x['Tags']) != None and re.search(r'\@[А-Яа-яё]+[_ ][А-Яа-яё]+', x['Tags']).group(0).replace('_',' ').replace('@','') == name):
            if(tag != None and (x['Tags'].find(tag) != -1 or tag == get_tag_from_parent(x))):
                result_string += x._links['html']['href'] +'\n'
            

    return result_string


for i in range(len(list_array)): # Заполнение таблицы с помощью двумерного листа
    for j in range(len(list_array[0])):
        worksheet.write(i,j,list_array[i][j]) 

for i in range(1, len(list_array)): 
    for j in range(1, len(list_array[0])-1):
        if list_array[i][j] != ' ':
            worksheet.write_comment(i,j, get_link_to_tfs(list_array[i][0], list_array[0][j]), {'width': 200, 'height': 200})

max_range = len(list_array)+1 # Таблица для unassigned тасков
worksheet.write(max_range, 0, 'Unassigned таски')
worksheet.write(max_range, 1, "Tasks' Id")
worksheet.write(max_range, 3, 'Error Tags')
worksheet.write(max_range, 4, "Tags' Id")
max_range += 1
for i in range(len(tasks_unassigned)):
    worksheet.write(max_range+i,0,tasks_unassigned[i])
    worksheet.write(max_range+i,1,id_unassigned[i])

for i in range(len(tags_error)):
    worksheet.write(max_range+i,3,tags_error[i])
    worksheet.write(max_range+i,4,id_error[i])

workbook.close() # Сохраняем файл

if (args.open):
    if sys.platform in ("linux", "linux2"):
        subprocess.call(["xdg-open", args.out])
    else:
        print("--open works only on linux yet")
