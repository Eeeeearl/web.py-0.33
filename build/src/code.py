import json
import web
import cx_Oracle
import datetime

# 前面是url地址，
# 前缀：http://localhost:8080
# 后面的 映射下面的class类，GET请求，则调用GET方法！
urls = (
    '/index', 'index',
)

render = web.template.render('../themes/')


class index:
    def GET(self):
        return render.index()

    def POST(self):
        print(datetime.datetime.now())
        data_chart = json.dumps(main(), ensure_ascii=False)
        print(datetime.datetime.now())
        return data_chart


# 封装所需数据，成对象
class DrawData:
    def __init__(self, stencil_id, stencil_code, used_count, location, update_time, cell_max, cell_min,
                 a_cell, b_cell, c_cell, d_cell, e_cell):
        # 第一次查询返回八个字段
        self.stencil_id = stencil_id
        self.stencil_code = stencil_code
        self.used_count = used_count
        self.location = location
        self.update_time = update_time
        self.cell_max = cell_max
        self.cell_min = cell_min
        self.A_CELL = a_cell
        self.B_CELL = b_cell
        self.C_CELL = c_cell
        self.D_CELL = d_cell
        self.E_CELL = e_cell

    # 总使用次数
    def set_total_used_count(self, total_used_count):
        self.total_used_count = total_used_count

    # 使用时间
    def set_used_time(self, used_time):
        self.used_time = used_time

    # terminal名称
    def set_terminal_name(self, terminal_name):
        self.terminal_name = terminal_name

    # pdline名称
    def set_pdline_name(self, pdline_name):
        self.pdline_name = pdline_name


# 连接数据库
def connect_db():
    try:
        conn = cx_Oracle.connect()
        return conn
    except BaseException:
        print("Connect Error!")
        return None


# 执行语句
def select_info(connect, sql):
    try:
        cursor = connect.cursor()
        all_data = cursor.execute(sql).fetchall()
        return all_data
    except BaseException:
        print("Select Error!")
        return None


# 关闭数据库
def close_db(connect):
    try:
        connect.close()
    except BaseException:
        print("Close Error!")


# 拼接sql语句
def connect_sql(sql, argument):
    sql = sql % argument
    return sql


# 主程序获取数据
def main():
    sql_1 = '''SELECT STENCIL_ID,  --钢网ID
                   STENCIL_CODE, --钢网编码
                   USED_COUNT,   --总使用次数
                   LOCATION,     --存放位置
                   UPDATE_TIME,  --时间
                   CELL_MAX,     --最大值
                   CELL_MIN,     --最小值
                   A_CELL,       --张力点A
                   B_CELL,       --张力点B
                   C_CELL,       --张力点C
                   D_CELL,       --张力点D
                   E_CELL       --张力点E
                   FROM SAJET.SYS_STENCIL
                   WHERE  ( STENCIL_CODE LIKE 'H16%' OR STENCIL_CODE LIKE 'H17%') AND
                   ENABLED = 'Y'
                   AND STATUS = 'L'  --上线
            '''
    sql_2 = '''SELECT PDLINE_ID,
                       TERMINAL_ID,
                       TOTAL_USED_COUNT
                    FROM (SELECT * FROM SAJET.G_HT_STENCIL_LOAD WHERE STENCIL_ID=%s ORDER BY UPDATE_TIME DESC)
                     T WHERE ROWNUM = 1
                '''
    sql_3 = 'SELECT TERMINAL_NAME FROM SAJET.SYS_TERMINAL WHERE TERMINAL_ID=%s'
    sql_4 = 'SELECT PDLINE_NAME FROM SAJET.SYS_PDLINE WHERE PDLINE_ID=%s'
    sql_7 = '''SELECT STENCIL_ID
                FROM SAJET.SYS_STENCIL
                WHERE ( STENCIL_CODE LIKE 'H16%' OR STENCIL_CODE LIKE 'H17%') AND
                ENABLED = 'Y'
                AND STATUS = 'I' --在库
            '''
    sql_8 = '''SELECT TOTAL_USED_COUNT
                FROM (SELECT * FROM SAJET.G_HT_STENCIL_LOAD WHERE STENCIL_ID=%s ORDER BY UPDATE_TIME DESC)
                 T WHERE ROWNUM = 1
            '''

    # 这个用来存放对象的list集合
    kanban_list = []
    # sql_2查询出来的两个id进行存储
    kanban_dict = {}

    conn = connect_db()
    result_1 = select_info(conn, sql_1)

    if result_1 is None:
        return
    # 往list里面存放对象  i对应的是一个二维元组
    for i in result_1:
        # 每个二维元组的各个元素 进行对象封装 然后list添加
        kanban_info = DrawData(i[0], i[1], i[2], i[3], i[4], i[5], i[6], i[7], i[8], i[9], i[10], i[11])
        kanban_info.set_used_time((datetime.datetime.now() - i[4]).seconds // 60)
        kanban_list.append(kanban_info)

    # 从list中弄出stencil_id
    num = 0
    for sid in kanban_list:
        sid_sql = connect_sql(sql_2, sid.stencil_id)
        # 第二条SQL的SELECT的结果，二位元组的格式
        result_2 = select_info(conn, sid_sql)
        # 填充使用总次数
        kanban_list[num].set_total_used_count(result_2[0][2])
        # 将两个id 对应的存进去 ter_id ==> k  pd_id ==> value
        kanban_dict[result_2[0][1]] = result_2[0][0]
        num += 1

    num2 = 0
    for ter_id, pd_id in kanban_dict.items():
        # 添加PDLINE_NAME属性
        pid_sql = connect_sql(sql_4, pd_id)
        result_4 = select_info(conn, pid_sql)
        kanban_list[num2].set_pdline_name(result_4[0][0])
        # 添加TERMINAL_NAME属性
        tid_sql = connect_sql(sql_3, ter_id)
        result_3 = select_info(conn, tid_sql)
        kanban_list[num2].set_terminal_name(result_3[0][0])
        if result_3[0][0][-2:] == "01":
            kanban_list[num2].set_terminal_name("左耳")
        if result_3[0][0][-2:] == "02":
            kanban_list[num2].set_terminal_name("右耳")
        num2 += 1

    # 画图数据 钢网 领用时间 使用总次数 使用时长
    data_stencil_code = []
    data_total_used_count = []
    data_used_time = []
    # 左右耳个数
    count_left = 0
    count_right = 0

    for i in kanban_list:
        data_stencil_code.append(i.stencil_code)
        data_total_used_count.append(i.total_used_count)
        data_used_time.append(i.used_time)
        if i.terminal_name == "左耳":
            count_left += 1
        if i.terminal_name == "右耳":
            count_right += 1

    x_data_pie = ["左耳", "右耳"]
    y_data_pie = [count_left, count_right]

    # 搜集在库钢网id和钢网已使用总次数
    result_unused_id = select_info(conn, sql_7)
    result_unused_y = []
    result_unused_x = []
    for unused_id in result_unused_id:
        count_sql = connect_sql(sql_8, unused_id)
        used_num = select_info(conn, count_sql)
        if used_num:
            if used_num[0][0] > 10000:
                result_unused_y.append(used_num[0][0])
                result_unused_x.append(unused_id)
        else:
            continue

    # 用于存储个图标需要的数据
    gw_data = []

    # 第一个图表 数据处理    0 1
    data_pair_1 = pair_sort(data_stencil_code, data_used_time)
    chart_one_x = []
    chart_one_y = []
    for i, j in data_pair_1:
        chart_one_x.append(i)
        chart_one_y.append(j)
    gw_data.append(chart_one_x)
    gw_data.append(chart_one_y)

    # 第二个图表 数据处理    2 3
    data_pair_2 = pair_sort(result_unused_x, result_unused_y)
    chart_two_x = []
    chart_two_y = []
    for i, j in data_pair_2:
        chart_two_x.append(i)
        chart_two_y.append(j)
    gw_data.append(chart_two_x)
    gw_data.append(chart_two_y)

    # 第三个图标 数据处理    4 5
    data_pair_3 = pair_sort(data_stencil_code, data_total_used_count)
    chart_three_x = []
    chart_three_y = []
    for i, j in data_pair_3:
        chart_three_x.append(i)
        chart_three_y.append(j)
    gw_data.append(chart_three_x)
    gw_data.append(chart_three_y)

    # 第四个图标 数据处理    6
    status_used = [0, 0, 0]
    for times in data_used_time:
        if times < 660:
            status_used[0] += 1
        elif times < 720:
            status_used[1] += 1
        else:
            status_used[2] += 1
    chart_four_x = ["正常", "预警", "下线"]
    chart_four_y = status_used
    chart_four = [list(z) for z in zip(chart_four_x, chart_four_y)]
    gw_data.append(chart_four)

    # 第六个图标 数据处理    7
    chart_six = [list(z) for z in zip(x_data_pie, y_data_pie)]
    gw_data.append(chart_six)

    # 第五个表格     8
    chart_five = []
    for kanban in kanban_list:
        kanban.update_time = ""
        chart_five.append(kanban.__dict__)
    gw_data.append(chart_five)

    return gw_data


def pair_sort(x, y):
    data_pair = [list(z) for z in zip(x, y)]
    data_pair.sort(key=lambda x: x[1], reverse=False)
    return data_pair


if __name__ == '__main__':
    app = web.application(urls, globals())
    app.run()
