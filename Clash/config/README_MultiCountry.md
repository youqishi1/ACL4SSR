# 全国家／地区节点分组

适用文件：`ACL4SSR_Online_MultiCountry.ini`。

继续使用原来的配置地址，重新进行订阅转换并更新客户端订阅即可：

<https://raw.githubusercontent.com/youqishi1/ACL4SSR/refs/heads/main/Clash/config/ACL4SSR_Online_MultiCountry.ini>

## 如何识别

- 覆盖 ISO 3166-1 的 249 个国家／地区。香港、澳门、台湾等各有独立分组。
- 按节点名称中的中文、繁体中文、英文名、国旗、两位或三位国家代码归组，英文忽略大小写。包含部分常见旧称、简称及城市名称，不承诺识别所有城市。
- 名称中的明确国旗优先。例如 `🇸🇬 香港中转 日本专线` 归入新加坡。
- 代码限制字母边界，支持 `HK01`、`[us]-02`；`AUS` 不会进入美国，`CACHE` 不会进入加拿大，`500GB` 不会进入英国。
- 对南苏丹／苏丹、几内亚比绍／几内亚、新墨西哥／墨西哥等名称做排除处理，避免较长名称误入短名称的分组。
- 每个国家组使用 `url-test`，每 300 秒测速，容差 150 毫秒。全部节点仍可从“手动切换”和“自动选择”访问，未识别的节点不会丢失。
- 保留原来的分流规则、美国优先顺序和原有九组的中文名称；修正美国、新加坡的国旗。新增组使用“国旗 国家名节点”。

## 使用限制

这是名称匹配，不查询服务器 IP 或实际出口国家。无地区信息、命名错误、代码用于其他含义、无国旗且包含多个地区、包含多面国旗等名称仍可能无法识别或进入多个组。建议使用 `🇯🇵 日本 01` 或 `JP01` 这类明确名称。

所有国家组都是预先定义的。标准 subconverter 在没有匹配节点时，会给该组填入 `DIRECT`，不会自动隐藏。**空国家组代表没有匹配节点，选择它会直连。** 如果需要“只显示订阅中实际存在的国家”，还需要转换端动态生成或客户端脚本支持。

配置默认关闭转换器自动添加／移除国旗，避免其内置 Emoji 规则先改变地区。转换请求若显式设置 `emoji`、`add_emoji`、`remove_emoji` 等参数，可能覆盖这些默认设置；仅依赖国旗命名的节点应保留原旗帜。

## 维护和检查

分组由仓库内的标准库 Python 脚本生成，无需联网或额外依赖：

```sh
python scripts/generate_multicountry.py
python scripts/generate_multicountry.py --check
python scripts/test_multicountry.py -v
```

国家名称和代码保存在 `scripts/data/countries.json`；额外简称、城市别名和匹配逻辑在 `scripts/generate_multicountry.py`。修改后重新生成 INI。其他配置模板不受影响。

目录数据取自 [pycountry 的 ISO 3166-1 数据](https://github.com/pycountry/pycountry/blob/main/src/pycountry/databases/iso3166-1.json)，中英文及繁体地区名称来自 Node.js `Intl.DisplayNames` 的 Unicode CLDR 数据，已固定保存在仓库中。

可选真实转换测试：安装 PyYAML，将 `SUBCONVERTER_DIR` 指向官方 subconverter 解压目录，再运行相同测试。测试会使用独立临时目录和本机回环端口，核对全部国家组及少量节点订阅的空组行为，并在结束时关闭测试进程。已使用官方 subconverter v0.9.0 验证。
