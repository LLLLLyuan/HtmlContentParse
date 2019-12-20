# -*- coding: utf-8 -*-
import re
from copy import deepcopy
from datetime import datetime
import requests
from lxml import etree


class HtmlContentExtract:
    def __init__(self, htmltext):
        """
        :param htmltext:html文本
        抽取正文的 标题：self.title 文章详情:self.content 发布日期：self.time_parse()
        :return
        """
        tree = etree.HTML(htmltext)
        scripts = tree.xpath('//script/text()')
        styles = tree.xpath('//style/text()')
        contents = tree.xpath('//*/text() | //br/following::text()[1]')
        copyrights = tree.xpath('//*/text()[contains(.,"©")]')
        self.title = tree.xpath('//title/text()')[0] if tree.xpath('//title/text()') else None
        # 剔除 meta的title
        try: contents.remove(self.title)
        except: pass
        # 剔除超链接文本，若正文中有超链接的文字，也会被剔除掉
        for pattern in tree.xpath('//*'):
            if pattern.xpath('./@href'):
                text = pattern.xpath('./text()')
                if text: contents.remove(text[0])
        # 剔除 script 文本
        for i in scripts:
            try: contents.remove(i)
            except: pass
        # 剔除 css样式
        for i in styles:
            try: contents.remove(i)
            except: pass
        # 剔除 copyright
        for i in copyrights:
            try: contents.remove(i)
            except: pass
        self.text = contents
        self.meta_date = self.get_meta_time(tree)
        self.content = '\n'.join([i[1]['NowElement'] for i in self.exclude()])

    def countwrap(self):
        """
        统计不同段落间的换行数，值为当前元素与下个元素的距离
        给文本从上到下，编号，排序
        根据不同段落间的换行数（间距）和排序位置 确定段落性质
        该算法会漏掉最后一个文本的计数（文本之间丢弃），
        需注意字典的键有可能重复
        :return
        """
        # 对\n 进行计数
        num = 0
        # 文本与\n之间的状态,0代表上一个元素为空
        start = 0
        end = 0
        # 记录元素的位置
        position = 0
        # 缓存当前比对区间第一个文本
        NowElement = None
        # 保存统计结果
        result_dict = {'data': {}}
        rp = lambda x: x.replace('\n', '').replace('\r', '').replace('\u3000', '').replace('\t', '').replace('\xa0', '')
        # 替换掉空白字符
        for i in self.text:
            # print(num,start,end,position,i)
            realcontent = rp(i).strip()
            if start == 0:
                if len(realcontent) > 5:
                    start = 1
                    # 将原始元素（文本）赋值给变量
                    NowElement = i
                    position += 1
            else:
                # 中间空置计数
                if not realcontent:
                    num += 1
                # 下一个有文本，end = 1
                else:
                    end = 1
                    # 一个统计区间结束
                    if start and end:
                        result_dict['data'][position] = {'NowElement': NowElement, 'num': num}
                        # 复位
                        num = 0
                        # 复位, 将下一个比对区间的第一文本替换为上一个比对区间的后一个文本
                        position += 1
                        NowElement = i
        # 添加最后一个文本
        result_dict['data'][position] = {'NowElement': NowElement, 'num': num}
        return result_dict

    def combination(self):
        data = self.countwrap()
        datacopy = deepcopy(data['data'])
        rp = lambda x: x.replace('\n', '').replace('\r', '').replace('\u3000', '').replace('\t', '').replace('\xa0', '')
        for index, value in data['data'].items():
            NewElement = rp(value['NowElement']).strip()
            # 剔除掉长度为 1 的文本
            if len(NewElement) == 1:
                datacopy.pop(index)
                continue
        return datacopy

    def exclude(self):
        """
        剔除长度小于5的垃圾文本
        剔除离散的文本（长度小于10，并且前后的换行数大于3）
        :return(list): [(1, {'NowElement': 'str', 'num': 0}), (2, {'NowElement': 'str', 'num': 1})]
        """
        data = self.combination()
        datacopy = deepcopy(data)
        # 上一个元素的num值
        upelement = 0
        # 上一个元素的index
        upindex = 0
        for i in data:
            # 其他文本长度的计算也剔除空格的影响
            content_statistics = data[i]['NowElement'].strip()
            # 剔除长度小于5的垃圾文本
            if len(content_statistics) < 5:
                datacopy.pop(i)
                # 在剔除该元素之后把该元素的换行添加到上一个元素上
                if upindex != 0:
                    datacopy[upindex]['num'] = datacopy[upindex]['num'] + data[i]['num']
                continue
            # 剔除离散的文本（长度小于10，并且前后的换行数大于3）
            if len(content_statistics) < 10:
                # 第一个元素
                if upelement == 0:
                    datacopy.pop(i)
                    continue
                else:
                    if (upelement > 3) and (data[i]['num'] > 3):
                        datacopy.pop(i)
                        upelement = data[i]['num']
                        # 在剔除该元素之后把该元素的换行添加到上一个元素上
                        if upindex != 0:
                            datacopy[upindex]['num'] = datacopy[upindex]['num'] + data[i]['num']
                        continue
            # 只有当当前文本是正常值的时候才修改
            upindex = i
        # 按key排序
        s = sorted(datacopy.items(), key=lambda x: x[0])
        return s

    def get_meta_time(self, htmltree):
        """
        从html的 meta 标签中获取提取时间
        :param htmltree:
        :return:
        """
        tree = htmltree
        meta_list = tree.xpath(
            '//meta[contains(@name|@Name|@property|@Property|itemprop|prop|Prop,"time") '
            'or contains(@name|@Name|@property|@Property|itemprop|prop|Prop,"Time") '
            'or contains(@name|@Name|@property|@Property|itemprop|prop|Prop,"data") '
            'or contains(@name|@Name|@property|@Property|itemprop|prop|Prop,"Data") '
            'or contains(@name|@Name|@property|@Property|itemprop|prop|Prop,"publish") '
            'or contains(@name|@Name|@property|@Property|itemprop|prop|Prop,"Publish") '
            'or contains(@name|@Name|@property|@Property|itemprop|prop|Prop,"creat") '
            'or contains(@name|@Name|@property|@Property|itemprop|prop|Prop,"Creat") '
            'or contains(@name|@Name|@property|@Property|itemprop|prop|Prop,"Date") '
            'or contains(@name|@Name|@property|@Property|itemprop|prop|Prop,"date")]'
            '/@content')
        if len(meta_list) == 0: return None
        meta_str = " ".join(meta_list)
        # 去除meta中的url链接,避免链接中 2019/01/01的误提取
        meta_str = re.sub(r"((https?|ftp|file)://[-\wA-Za-z0-9+&@#/%?=~_|!:,.;]+[-A-Za-z0-9+&@#/%=~_|])", "", meta_str)
        pattern = re.compile(r'(20\d{2}[./\-年]\d{1,2}[./\-月]\d{1,2}[.\-日T\s])(\d{2}:\d{2}[:\d]{0,3}){0,1}|'
                             r'(19\d{2}[./\-年]\d{1,2}[./\-月]\d{1,2}[.\-日T\s])(\d{2}:\d{2}[:\d]{0,3}){0,1}')
        date_match = re.findall(pattern=pattern, string=meta_str)
        date_list = [''.join(date_tuple) for date_tuple in date_match]

        if len(date_list) == 0:
            return None
        elif len(date_list) == 1:
            date_str = date_list[0]
            if len(date_str.split(':')) == 4: date_str = ":".join(date_str.split(':')[0:-1])
            return date_str
        else:
            lastdate = date_str = None
            for i in date_list:
                if lastdate:
                    if i != lastdate:
                        if len(i) > len(lastdate):
                            date_str = i
                        else:
                            continue
                lastdate = i
            if not date_str: date_str = date_list[0]
            if len(date_str.split(':')) == 4: date_str = ":".join(date_str.split(':')[0:-1])
            return date_str

    def get_en_time(self, content):
        """
        英文因字母长度不一样，无法判断，只返回匹配到的第一个
        :param content:
        :return:
        """
        pattern = re.compile(
            "(\d{1,2}(st|th|nd|rd)?[\./\s](January|February|March|April|May|June|July|August|September|October|November|December)[\./\s]\d{4})|"
            "((Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[,\.\s]{1,2}(\d{1,2}(st|th|nd|rd)?[,\s\.]{1,2}\d{4}[,\s]{0,2})(\d{1,2}:\d{2}[:\d]{0,3}){0,1})|"
            "((\d{2}[/\.]\d{2}[/\.]\d{4}[,\s]{0,1})(\s{0,1}\d{1,2}:\d{2}[:\d]{0,3}){0,1})|"
            "((January|February|March|April|May|June|July|August|September|October|November|December)[,\.\s]{1,2}(\d{1,2}(st|th|nd|rd)?[,\s\.]{1,2}\d{4}[,\s]{0,2})(\d{1,2}:\d{2}[:\d]{0,3}){0,1})"
        )
        date_match = re.search(pattern=pattern, string=content)
        # print(re.findall(pattern,content))
        return [date_match.group()] if date_match else []

    def time_parse(self):
        """
        提取详情页的时间并且解析
        :param :
        :return:
        """
        if self.meta_date:
            return self.meta_date
        text = self.content
        # print("\n".join([i.get("NowElement") for i in self.combination().values()]))
        pattern = re.compile(
            r'(20\d{2}[_,/,\-,年]\d{1,2}[/,_,\-,月]\d{1,2}[/,_,\-,日\s]{0,1})(\s{0,1}\d{1,2}:\d{2}:\d{2}){0,1}|'
            r'(19\d{2}[_,/,\-,年]\d{1,2}[/,_,\-,月]\d{1,2}[/,_,\-,日\s]{0,1})(\s{0,1}\d{1,2}:\d{2}:\d{2}){0,1}')
        date_match = re.findall(pattern, text)
        # print(date_match)
        # 将元组转化为字符串
        date_list = [''.join(date_tuple) for date_tuple in date_match] if date_match else self.get_en_time(text)
        if not date_list:
            # 若从处理过的文本中提取不到时间，则从原始的文本中再找一次
            text = "\n".join([i.get("NowElement") for i in self.combination().values()])
            date_match = re.findall(pattern, text)
            date_list = [''.join(date_tuple) for date_tuple in date_match] if date_match else self.get_en_time(text)
        # print(date_list)
        if len(date_list) == 0:
            return datetime(1970, 1, 1)
        elif len(date_list) == 1:
            date_str = date_list[0]
            if len(date_str.split(':')) == 4: date_str = ":".join(date_str.split(':')[0:-1])
            return date_str
        else:
            # 当列表中时间长度不同时：列表从前往后迭代，两两对比不同的时间的长度，返回最大的
            lastdate = date_str = None
            for i in date_list:
                if lastdate:
                    if i != lastdate:
                        if len(i) > len(lastdate):
                            date_str = i
                        else:
                            continue
                lastdate = i
            # 如果列表内所有字符串长度相同那么返回index 0
            if not date_str: date_str = date_list[0]
            if len(date_str.split(':')) == 4: date_str = ":".join(date_str.split(':')[0:-1])
            return date_str

    def dateformat(self, date_string):
        dateformat_list = [
            "%Y/%m/%d",
            "%Y %m %d",
            "%Y-%m-%d",
            "%Y.%m.%d",
            "%Y年%m月%d日",
            "%Y年%m月%d",
            "%Y年%m月%d日 %H:%M",
            "%Y年%m月%d日 %H:%M:%S",
            "%Y年%m月%d %H:%M:%S",
            "%Y-%m-%dT%H:%M:%S",
            "%Y/%m/%d %H:%M:%S",
            "%Y/%m/%d %H:%M",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M",

            # 英文时间格式 美式时间一般为 月-日-年  英式时间一般为 日-月-年
            "%dst %B %Y",
            "%dst %B %Y %H:%M",
            "%dst %B %Y %H:%M:%S",
            "%dnd %B %Y",
            "%dnd %B %Y %H:%M",
            "%dnd %B %Y %H:%M:%S",
            "%drd %B %Y",
            "%drd %B %Y %H:%M",
            "%drd %B %Y %H:%M:%S",
            "%dth %B %Y",
            "%dth %B %Y %H:%M",
            "%dth %B %Y %H:%M:%S",
            "%d %b %Y",
            "%d %B %Y",
            "%d.%m.%Y",
            "%d.%m.%Y %H:%M",
            "%d.%m.%Y %H:%M:%S",
            "%d/%m/%Y",
            "%d/%m/%Y %H:%M",
            "%d/%m/%Y %H:%M:%S",

            "%m.%d.%Y",
            "%m.%d.%Y %H:%M",
            "%m.%d.%Y %H:%M:%S",
            "%m/%d/%Y",
            "%m/%d/%Y %H:%M",
            "%m/%d/%Y %H:%M:%S",
            "%b %dst %Y",
            "%b %dst %Y %H:%M",
            "%b %dst %Y %H:%M:%S",
            "%b %dnd %Y",
            "%b %dnd %Y %H:%M",
            "%b %dnd %Y %H:%M:%S",
            "%b %drd %Y",
            "%b %drd %Y %H:%M",
            "%b %drd %Y %H:%M:%S",
            "%b %dth %Y",
            "%b %dth %Y %H:%M",
            "%b %dth %Y %H:%M:%S",
            "%b %d, %Y",
            "%b %d, %Y %H:%M",
            "%b %d, %Y %H:%M:%S",
            "%b. %d, %Y",
            "%b. %d, %Y,",
            "%b. %d, %Y %H:%M",
            "%b. %d, %Y %H:%M:%S",
            "%b. %d, %Y",
            "%b. %d, %Y, %H:%M",
            "%b. %d, %Y, %H:%M:%S",
            "%B %dst %Y",
            "%B %dst %Y %H:%M",
            "%B %dst %Y %H:%M:%S",
            "%B %dnd %Y",
            "%B %dnd %Y %H:%M",
            "%B %dnd %Y %H:%M:%S",
            "%B %drd %Y",
            "%B %drd %Y %H:%M",
            "%B %drd %Y %H:%M:%S",
            "%B %dth %Y",
            "%B %dth %Y %H:%M",
            "%B %dth %Y %H:%M:%S",
            "%B %d, %Y",
            "%B %d, %Y %H:%M",
            "%B %d, %Y %H:%M:%S",
            "%B. %d, %Y",
            "%B. %d, %Y %H:%M",
            "%B. %d, %Y %H:%M:%S",
        ]
        if not date_string: return datetime(1970, 1, 1)
        if isinstance(date_string, datetime): return date_string
        result = datetime(1970, 1, 1)
        for date_format in dateformat_list:
            try:
                result = datetime.strptime(date_string.strip(), date_format)
                break
            except ValueError:
                pass
        return result


if __name__ == '__main__':
    headers = {
        'accept': "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*"
                  "/*;q=0.8,application/signed-exchange",
        'accept-encoding': "gzip, deflate",
        'accept-language': "zh,en;q=0.9,zh-TW;q=0.8,zh-CN;q=0.7",
        'cache-control': "max-age=0,no-cache",
        'user-agent': "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_6) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/77.0.3865.120 Safari/537.36",
        'Connection': "keep-alive"
    }

    url = "https://bestyuan.fun/blog/2019-10/%E7%9F%A5%E4%B9%8E%E7%88%AC%E8%99%AB%E4%BA%8Cscrapy%E7%AF%87/"
    response = requests.get(url, headers=headers)
#     response.encoding = response.apparent_encoding
    response.encoding = 'utf-8'
    text = response.text
    # text = "".join(open('../test.html', 'r', encoding="utf-8").readlines())
    htmlcontent =HtmlContentExtract(text)
    print(htmlcontent.content)
    time_parse = htmlcontent.time_parse()
    print(f"meta_date: {htmlcontent.meta_date}")
    print("提取时间为: ", time_parse.strip())
    sss = htmlcontent.dateformat(time_parse)
    print("格式化时间为: ", sss)

    em_time = [
        ("Nov 14th 2019 at 9:20AM"),
        ("11.26.2019"),
        ("November 26, 2019"),
        ("12/01/2019 11:03"),
        ("Dec. 2, 2019, 6:50"),
        ("December 02, 2019"),
        ("Dec. 3, 2019, 9:18"),
        ("Dec. 2, 2019, at 9:00 a.m."),
        ("1st December 2019"),
        ("3 December 2019")
    ]

    # for one in em_time:
    #     time = get_en_time(str(one))
    #     print(time, dataformat(time[0]))
