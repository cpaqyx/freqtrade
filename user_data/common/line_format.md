
kline_tool.py 中实现以下功能，输入的参数为close_prices，见line_format.py中的kline_trend_description中的close_prices参数，即输入是一样的

程序实现功能的描述：
得到一组k线的轮廓图，示例如下：
[{'end_price': 92.34,
  'k_cnt': 23,
  'line': 'down',
  'max_price': 112.1,
  'min_price': 92.34,
  'start_price': 112.1},
 {'end_price': 118.5,
  'k_cnt': 26,
  'line': 'up',
  'max_price': 118.5,
  'min_price': 95.6,
  'start_price': 95.6},....]
即把一组k线生成几条直线段，总体思路是：
从数组中的最后一根k线，开始向前推移，只做一次遍历，在推移过程中会记录很多信息，主要有当前趋势段与下一个趋势段，当下一个反转的趋势段没有形成，如中间可能方向相反，但很快后续的同向k线掩盖，则不会形成反相趋势，即一直会强化当前趋势段，趋势段的k线数量会越来越多，但当出现大量相反段的k线时，并已经足够形成一个反向趋势时，把当前段存入到列表中，相反段变为当前段，相反段重置，然后继续执行统计，直到再次出现相反段趋势才把当前段存入到列表中，相反段变为当前段，直到遍历完成，并存入当前段和最后一个相反段到列表中，详细的程序掩码如下：


part_list = [] 用于存放段, 示例如下：

阈值定义：
part_cnt: 可确认方向k线数量，即达到这些k线数量，可以确定为一段；
part_percnt: 达到多少时涨跌幅度时，可以确定为一段；
first_part_cnt: 第一段允许的最小k线数量;
first_part_percnt: 第一段达到多少时涨跌幅度时，可以确定为一段；
part_diff_cnt: 允许反方向的k线数量，超过，说明需要回退；
part_diff_percnt: 允许反方向的涨跌帐度是多少,即达到反方向的幅度，说明需要回退；


定义如下变量：
fix_index: 已可确认的元素序号，默认为1；
index: 当前序号；
cur_part_direct: 当前段的方向，有up|down，默认为空; 
cur_part_index: 当前段的序号；
cur_part_percnt: 当前段的累计涨跌幅度;
cur_part_cnt: 当前段的累计k线数量；
next_part_diff_cnt：当前段遇到的反向k线数量；
next_part_diff_percnt: 当前段遇到的反向百分比；
cur_part_same_percnt: 当前段遇到的正向百分比；

极值变量（下方并没有显示说明，需要考虑并实现）：
cur_part_max_price：当前段的最高价，最高收盘价
cur_part_min_price：当前段的最低价，最低收盘价
cur_part_start_price：当前段的起始价，该段的第一根k线收盘价
cur_part_end_price：当前段的的终止价，最后一根k线收盘价
next_part_max_price：相反段的最高价，最高收盘价
next_part_min_price：相反段的最低价，最低收盘价
next_part_start_price：相反段的起始价，该段的第一根k线收盘价
next_part_end_price：当相反段的的终止价，最后一根k线收盘价

从数组的最后1根k线向前推，即时间最近的向时间早的方向推移，遍历每个k线时的逻辑如下：
第1根线的赋值逻辑：

赋值操作：
（1）记录当前的序号为index；获当前的涨跌幅度percent；
（2）cur_part_direct为空，则当前k线为涨则为up, 跌则为down, 否则为flat;

判断赋值操作：
（1）如果当前涨跌幅度percent > 0,即为上涨, cur_part_direct为up则：
cur_part_cnt+1;
cur_part_same_percnt+percent;
cur_part_same_percnt+1;

（2）如果当前涨跌幅度percent > 0,即为上涨, cur_part_direct为down则：
cur_part_same_percnt=0;
next_part_diff_percnt+percent;
next_part_diff_cnt+1;


（3）如果当前涨跌幅度percent < 0,即为上涨, cur_part_direct为up则：
cur_part_same_percnt=0;
next_part_diff_percnt+percent;
next_part_diff_cnt+1;


（4）如果当前涨跌幅度percent < 0,即为上涨, cur_part_direct为down则：
cur_part_cnt+1;
cur_part_same_percnt+percent;
cur_part_same_percnt+1;

判断逻辑：
（1）cur_part_same_percnt > next_part_diff_percnt 则：
cur_part_same_percnt=0;
next_part_diff_percnt=0;
cur_part_cnt+next_part_diff_cnt;
next_part_diff_cnt=0;
fix_index = index;
cur_part_index = index;

（2）cur_part_cnt >= part_kcnt 则：
fix_index = index;
cur_part_index = index;

（3）如果相反方向没有形成，则继续遍历
next_part_diff_percnt - cur_part_same_percnt > part_percnt ||  next_part_diff_percnt+ cur_part_same_percnt >  part_cnt:
continue;

添加段逻辑：
（1）如果是第一段, 即len(part_list) = 0
（1.1）cur_part_cnt > first_part_cnt || cur_part_percnt > first_part_percnt 则：
 加入段到part_list，重置段，详细逻辑见子处理定义addAndReset
（1.2）否则：
 第一段合并到相反段中，此时不添加到part_list中，设置好段的切换后,执行swap子处理方法，执行continue;

 (2) 如果不是第一段，即len(part_list) > 0，则:
 cur_part_cnt > part_cnt || cur_part_percnt > part_percnt:
 加入段到part_list，重置段，详细逻辑见子处理定义addAndReset


addAndReset逻辑：
（1）将当前段加入到列表中；
（2）把相反段变赋值给当前段，相反段重置；


swap逻辑：
（1）改变当前段的方向为相反段的方向；
（2）把相反段变赋值给当前段，相反段重置；



kline_tool.py程序实现功能的描述：
得到一组k线的轮廓图，示例如下：
[{'end_price': 92.34,
  'k_cnt': 23,
  'line': 'down',
  'max_price': 112.1,
  'min_price': 92.34,
  'start_price': 112.1},
 {'end_price': 118.5,
  'k_cnt': 26,
  'line': 'up',
  'max_price': 118.5,
  'min_price': 95.6,
  'start_price': 95.6},....]
即把一组k线生成几条直线段，总体思路是：
从数组中的最后一根k线，开始向前推移，只做一次遍历，在推移过程中会记录很多信息，主要有当前趋势段与下一个趋势段，当下一个反转的趋势段没有形成，如中间可能方向相反，但很快后续的同向k线掩盖，则不会形成反相趋势，即一直会强化当前趋势段，趋势段的k线数量会越来越多，但当出现大量相反段的k线时，并已经足够形成一个反向趋势时，把当前段存入到列表中，相反段变为当前段，相反段重置，然后继续执行统计，直到再次出现相反段趋势才把当前段存入到列表中，相反段变为当前段，直到遍历完成，并存入当前段和最后一个相反段到列表中



### 添加最大最小值，涨跌幅度
kline_tool.py 设置最大最小值，该值直接用起始值来赋值即可，然后依据起始与终目值计算出涨跌幅度


