# HtmlContentParse
解析网页文本，提取时间


使用：
```python
url = "https://bestyuan.fun/blog/2019-10/%E7%9F%A5%E4%B9%8E%E7%88%AC%E8%99%AB%E4%BA%8Cscrapy%E7%AF%87/"
response = requests.get(url)
response.encoding = 'utf-8'
text = response.text
htmlcontent =HtmlContentExtract(text ，delete_text_length=5) # 默认为5，可根据实际情况剔除相应长度的无关信息
#print(htmlcontent.title)
#print(htmlcontent.content)
time_parse = htmlcontent.time_parse()
format_date = htmlcontent.dateformat(time_parse)
print(format_date)
```
若提取不到时间会返回1970.01.01
