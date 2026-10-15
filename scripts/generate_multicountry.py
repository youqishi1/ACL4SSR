"""Generate name-based country groups; Python 3, no third-party dependencies."""

import argparse
import json
import re
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "Clash/config/ACL4SSR_Online_MultiCountry.ini"
DATA = Path(__file__).with_name("data") / "countries.json"
TEST_URL = "http://www.gstatic.com/generate_204"
PRIORITY = "US CA BR MX GB RU DE HK SG JP TW KR MO AU FR NL IN TR TH VN MY ID PH AE".split()
LEGACY_NAMES = {
    "US": "美国节点", "CA": "加拿大小组", "BR": "巴西小组",
    "MX": "墨西哥小组", "GB": "英国小组", "RU": "俄罗斯小组",
    "DE": "德国小组", "HK": "香港小组", "SG": "新加坡小组",
}
DISPLAY_NAMES = {"HK": "香港", "MO": "澳门", "PS": "巴勒斯坦"}
EXTRA_ALIASES = {
    "US": ["波特兰", "波特蘭", "达拉斯", "達拉斯", "俄勒冈", "俄勒岡",
           "凤凰城", "鳳凰城", "费利蒙", "費利蒙", "硅谷", "矽谷",
           "拉斯维加斯", "拉斯維加斯", "洛杉矶", "洛杉磯", "圣克拉拉",
           "聖克拉拉", "西雅图", "西雅圖", "芝加哥", "新墨西哥", "New Mexico",
           "Los Angeles", "Seattle", "Chicago", "Dallas", "Portland",
           "Las Vegas", "Silicon Valley", "San Francisco", "旧金山", "舊金山",
           "ATL", "BUF", "DFW", "EWR", "IAD", "LAX", "MCI", "MIA", "ORD",
           "PHX", "PDX", "SEA", "SJC"],
    "HK": ["香港", "HongKong"],
    "MO": ["澳门", "澳門", "Macau"],
    "TW": ["臺灣", "台北", "臺北", "新北", "高雄", "Taipei"],
    "JP": ["东京", "東京", "大阪", "Tokyo", "Osaka"],
    "SG": ["狮城", "獅城", "Singapore"],
    "KR": ["南韩", "韓國", "首尔", "首爾", "Seoul"],
    "KP": ["北韩", "朝鮮"],
    "GB": ["UK", "Britain", "Great Britain", "伦敦", "倫敦", "London"],
    "RU": ["俄罗斯", "俄羅斯", "莫斯科", "Moscow"],
    "DE": ["法兰克福", "法蘭克福", "Frankfurt"],
    "CA": ["多伦多", "多倫多", "温哥华", "溫哥華", "Toronto", "Vancouver"],
    "AU": ["澳大利亞", "悉尼", "雪梨", "墨尔本", "墨爾本", "Sydney", "Melbourne"],
    "NL": ["阿姆斯特丹", "Amsterdam"],
    "AE": ["阿联酋", "阿聯酋", "阿拉伯聯合酋長國", "UAE", "迪拜", "杜拜", "Dubai"],
    "TR": ["土耳其", "土耳其共和国", "Turkiye", "Turkey"],
    "PS": ["巴勒斯坦", "Palestine"],
    "CD": ["刚果金", "剛果金", "刚果民主共和国", "剛果民主共和國",
           "Democratic Republic of the Congo", "DR Congo", "Congo-Kinshasa", "DRC"],
    "CG": ["刚果布", "剛果布", "刚果共和国", "剛果共和國", "Congo-Brazzaville"],
    "CI": ["科特迪瓦", "象牙海岸", "Ivory Coast", "Cote d'Ivoire"],
    "SZ": ["斯威士兰", "史瓦帝尼", "Swaziland"],
    "CZ": ["捷克", "Czech Republic"],
    "CV": ["Cape Verde"],
    "TL": ["East Timor"],
    "VA": ["梵蒂冈", "梵蒂岡", "Vatican", "Vatican City"],
    "BN": ["文莱", "汶萊", "Brunei"],
    "LA": ["老挝", "寮國", "Laos"],
    "VN": ["越南", "Vietnam"],
    "BO": ["玻利维亚", "玻利維亞", "Bolivia"],
    "VE": ["委内瑞拉", "委內瑞拉", "Venezuela"],
    "IR": ["伊朗", "Iran"],
    "SY": ["叙利亚", "敘利亞", "Syria"],
    "MD": ["摩尔多瓦", "摩爾多瓦", "Moldova"],
    "TZ": ["坦桑尼亚", "坦尚尼亞", "Tanzania"],
}


def flag(code):
    return "".join(chr(0x1F1E6 + ord(c) - ord("A")) for c in code)


def literal_pattern(value):
    """ASCII word boundaries prevent US/AUS, CA/Canada and IN/Singapore overlap.

    A code cannot follow a digit (500GB is a quota); HK01 and [us]-02 work.
    """
    result = re.escape(value)
    if value[0].isascii() and value[0].isalpha():
        left = r"(?<![A-Za-z0-9])" if re.fullmatch(r"[A-Z]{2,3}", value) else r"(?<![A-Za-z])"
        result = left + result
    if value[-1].isascii() and value[-1].isalpha():
        result += r"(?![A-Za-z])"
    return result


def load_countries():
    countries = json.loads(DATA.read_text(encoding="utf-8"))
    for country in countries:
        values = [country["name"], *country["aliases"], *EXTRA_ALIASES.get(country["code"], [])]
        # Accept ASCII spellings of names such as Türkiye and Réunion as well.
        values += ["".join(c for c in unicodedata.normalize("NFKD", v)
                           if not unicodedata.combining(c)) for v in values]
        country["aliases"] = list(dict.fromkeys(values))
    return sorted(countries, key=lambda c: (
        PRIORITY.index(c["code"]) if c["code"] in PRIORITY else len(PRIORITY), c["code"]))


def group_name(country):
    code = country["code"]
    label = LEGACY_NAMES.get(code, DISPLAY_NAMES.get(code, country["name"]) + "节点")
    return f"{flag(code)} {label}"


def build_patterns(countries):
    patterns = {}
    for country in countries:
        terms = [country["code"], country["alpha3"], *country["aliases"]]
        identity = "(?:" + "|".join(literal_pattern(t) for t in dict.fromkeys(terms)) + ")"
        matcher = re.compile(identity, re.I)
        # Longer country names must not leak into a shorter country name/code:
        # South Sudan/Sudan, New Mexico/Mexico, Guinea-Bissau/Guinea, etc.
        blockers = sorted({alias for other in countries if other["code"] != country["code"]
                           for alias in other["aliases"] if matcher.search(alias)}, key=lambda s: (-len(s), s))
        guard = "(?!.*(?:" + "|".join(literal_pattern(v) for v in blockers) + "))" if blockers else ""
        # An explicit flag wins over text, including misleading transit labels.
        # PCRE2 UTF (subconverter) and Python re both understand this literal range.
        patterns[country["code"]] = f"(?i)(?:{flag(country['code'])}|^(?!.*[🇦-🇿]{{2}}){guard}.*{identity})"
    return patterns


def render_groups(countries):
    patterns = build_patterns(countries)
    choices = ["[]" + group_name(countries[0]), "[]☑️ 手动切换"]
    choices += ["[]" + group_name(c) for c in countries[1:]]
    choices += ["[]♻️ 自动选择", "[]DIRECT"]
    lines = [";国家分组由 scripts/generate_multicountry.py 生成，修改别名后请重新生成。",
             ";按节点名称识别，不查询出口 IP；国旗优先，国家代码忽略大小写并限制字母边界。",
             ";注意：标准 subconverter 会把没有匹配节点的国家组填入 DIRECT，不会自动隐藏。",
             ";保留订阅原有国旗，避免转换器内置的宽泛 Emoji 规则先改错国家。",
             "add_emoji=false",
             "remove_old_emoji=false",
             "custom_proxy_group=🚀 节点选择`select`" + "`".join(choices),
             "custom_proxy_group=☑️ 手动切换`select`.*"]
    for country in countries:
        lines.append(f"custom_proxy_group={group_name(country)}`url-test`"
                     f"{patterns[country['code']]}`{TEST_URL}`300,,150")
    lines += [f"custom_proxy_group=♻️ 自动选择`url-test`.*`{TEST_URL}`300,,50",
              "custom_proxy_group=🎯 全球直连`select`[]DIRECT`[]🚀 节点选择`[]♻️ 自动选择",
              "custom_proxy_group=🐟 漏网之鱼`select`[]🚀 节点选择`[]🎯 全球直连`[]♻️ 自动选择`.*"]
    return "\n".join(lines) + "\n\n"


def updated_config(original):
    # Only replace the group section: all ruleset lines stay exactly as supplied.
    start = original.find(";国家分组由 scripts/generate_multicountry.py")
    if start < 0:
        start = original.index("custom_proxy_group=")
    end = original.index("enable_rule_generator=", start)
    result = original[:start] + render_groups(load_countries()) + original[end:]
    return result.replace(";多国家分组：支持港/日/美", ";多国家分组：支持 ISO 3166-1 的 249 个国家/地区（按节点名称匹配）")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="check generated INI is up to date")
    args = parser.parse_args()
    original = CONFIG.read_text(encoding="utf-8")
    result = updated_config(original)
    if args.check:
        if result != original:
            raise SystemExit("Country groups are stale; run python scripts/generate_multicountry.py")
        print("Country groups are up to date (249 countries/territories).")
    else:
        CONFIG.write_text(result, encoding="utf-8", newline="\n")
        print("Generated 249 country/territory groups.")


if __name__ == "__main__":
    main()
