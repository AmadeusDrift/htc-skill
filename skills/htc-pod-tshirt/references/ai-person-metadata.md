# 写实AI人物的最终文件元数据

这是两条路线共用的上传准备步骤，适用实际渠道规则及用户授权。规则核对日期：2026-10-28；后续执行前核实当前站点/类目政策。不能把标记写入等同整套商品合规。

## 谁需要标签

Amazon官方公告要求全球站点Listing和A+中的写实AI生成人物素材在上传前披露；其帮助页给出XMP字段写法。按实际画面逐图分类，不能因为整套用了AI而全选：

- 含写实AI模特/人物：需要；不露脸、只有人体躯干也不能自动当作无人图。
- 无人物的布料、结构局部、平铺尺寸图：不因AI生成商品或环境而加此人物标签。
- 真实人物经AI修改、仅虚构作品角色等例外按当前官方定义判断，不臆造豁免。来源或人物性质不明先记录待核实。

## 写入和验证顺序

1. 记录每张最终文件的人物分类、目标格式和输出路径。用户要求先定稿再打标时，在定稿后执行；不会因此重新开启已经确认的授权。
2. 完成比例/裁切、景深、文字、印花和最终导出，再写入**实际上传图片文件内部**的XMP `dc:subject`，值为 `contains-synthetic-performer`。对应RDF结构为dc:subject → rdf:Bag → rdf:li。
3. 使用支持XMP的工具，保留其他关键词，避免重复添加。可用已安装ExifTool，或经当前文件格式验证的Photoshop元数据导出流程；不得假设已安装，也不把任意EXIF UserComment当等价字段。
4. 独立读取最终文件中的XMP/XML，核对精确字段和值、图片仍可打开及像素尺寸正确。写入命令返回成功、PSD内有关键词、文件名或旁置XMP都不能代替最终文件验证。
5. 无人图检查是否意外继承此关键词；在受控副本中移除误加的人物关键词、保留其他元数据后重验。PS跨图位导出前重置该图位人物关键词，防止上张模特标签泄漏到无人图。
6. 后续重新导出、压缩、裁切、替换或换格式可能丢元数据，必须对新最终文件重新检查并按需写入。记录文件哈希、分类和读取结果，不能沿用旧文件报告。

可执行工具示例（ExifTool已可用且检查尚未存在该值时）：

```powershell
exiftool -XMP-dc:Subject 'final-person.jpg'
exiftool '-XMP-dc:Subject+=contains-synthetic-performer' 'final-person.jpg'
exiftool -XMP-dc:Subject 'final-person.jpg'
```

实际文件路径按项目填写；工具默认可能生成备份，按项目交付范围保留到工作资料。不要对整目录盲写；重复运行前检查已有值。PNG/JPG分别验证本格式XMP是否可读，不因为JPG通过就声称所有格式通过。

## 主图用途与政策来源

无字节日场景封面和平台上传MAIN是不同用途；节日路线不覆盖渠道要求。Amazon普通服装MAIN的白底、完整正面、接近3:4及主体占比要求按具体站点与类目核实；低价商城另按该渠道规则。1800×2400不是官方唯一尺寸；场景封面不能冒称白底MAIN合规。

- [Amazon官方AI人物公告（全球站点Listing与A+）](https://sellercentral.amazon.com/seller-forums/discussions/t/aa0aee06-aff4-497a-a4b6-9b2ebe06f715)
- [Amazon官方XMP标记与验证说明（帮助页标注美国适用）](https://sellercentral.amazon.com/help/hub/reference/external/GFXHCHYZRGJRBZA5?locale=en_US)
- [Amazon服装图片指南（按实际站点核实）](https://sellercentral.amazon.com/help/hub/reference/external/G200498950?locale=en-US)

本次可读取官方公告和帮助页的搜索索引正文；直接打开部分帮助页会返回登录壳，不把它描述成完整阅读了登录后的规则。可访问性不足时明确核实范围，不能以用户截图或第三方摘要冒充官方全文。
