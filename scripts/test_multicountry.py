"""Country-name regressions. Optional real conversion: SUBCONVERTER_DIR + PyYAML."""

import contextlib
import http.server
import json
import os
import re
import shutil
import socket
import subprocess
import tempfile
import threading
import time
import unittest
import urllib.parse
import urllib.request
from pathlib import Path

import generate_multicountry as generator

CASES = {
    "巴西 01": "BR", "巴基斯坦 01": "PK", "巴拿马 01": "PA",
    "巴勒斯坦 01": "PS", "🇵🇰 巴基斯坦 香港中转": "PK",
    "俄勒冈 01": "US", "俄罗斯 01": "RU", "Los Angeles 01": "US",
    "新墨西哥 01": "US", "New Mexico 01": "US", "墨西哥 01": "MX",
    "AUS01": "AU", "RUS01": "RU", "US01": "US", "[us]-02": "US",
    "CA-01": "CA", "hk01": "HK", "HKG02": "HK", "HongKong 01": "HK",
    "香港 01": "HK", "新加坡 01": "SG", "獅城 01": "SG",
    "🇸🇬 香港中转 日本专线": "SG", "United Kingdom 01": "GB", "UK01": "GB",
    "South Sudan 01": "SS", "南苏丹 01": "SS", "Sudan 01": "SD",
    "Guinea-Bissau 01": "GW", "Equatorial Guinea 01": "GQ", "Guinea 01": "GN",
    "巴布亚新几内亚 01": "PG", "英属印度洋领地 01": "IO",
    "British Indian Ocean Territory 01": "IO", "北马其顿 01": "MK",
    "United States Minor Outlying Islands 01": "UM", "🇺🇲 01": "UM",
    "Hong Kong SAR China 01": "HK", "Taiwan, Province of China 01": "TW",
    "American Samoa 01": "AS", "St. Barthélemy 01": "BL",
    "Trinidad and Tobago 01": "TT", "Bosnia and Herzegovina 01": "BA",
    "Democratic Republic of the Congo 01": "CD", "Congo 01": "CG",
    "台湾 01": "TW", "臺灣 01": "TW", "日本 01": "JP", "首爾 01": "KR",
    "迪拜 01": "AE", "Turkey 01": "TR", "Türkiye 01": "TR",
    "高速节点 01": None, "Premium 01": None, "剩余流量 500GB": None,
    "Relay-CACHE-01": None, "BASIC-01": None, "BRONZE-01": None,
    "Business-01": None, "Inside-01": None, "Global-01": None,
}


def fixtures(countries):
    result = dict(CASES)
    for country in countries:
        code = country["code"]
        for value in [generator.flag(code), code, code.lower() + "01",
                      country["alpha3"], *country["aliases"]]:
            result[value + " 测试"] = code
    return result


class CountryGroupsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.countries = generator.load_countries()
        cls.patterns = {code: re.compile(p) for code, p in
                        generator.build_patterns(cls.countries).items()}

    def test_catalog_and_generated_file(self):
        self.assertEqual(len(self.countries), 249)
        self.assertEqual(len({c["code"] for c in self.countries}), 249)
        text = generator.CONFIG.read_text(encoding="utf-8")
        self.assertEqual(text, generator.updated_config(text))
        lines = [line for line in text.splitlines() if line.startswith("custom_proxy_group=")]
        names = [line.split("=", 1)[1].split("`")[0] for line in lines]
        self.assertEqual(len(names), len(set(names)))
        self.assertEqual(len(names), 254)
        refs = re.findall(r"`\[\]([^`\n]+)", text)
        self.assertTrue(set(refs) <= set(names) | {"DIRECT"})
        self.assertEqual(len(lines[0].split("`")), 254)

    def test_aliases_and_regressions(self):
        samples = fixtures(self.countries)
        for name, expected in samples.items():
            with self.subTest(name=name):
                actual = [code for code, pattern in self.patterns.items() if pattern.search(name)]
                self.assertEqual(actual, [expected] if expected else [])
        print(f"Checked {len(samples)} node-name fixtures against all 249 country groups.")

    @unittest.skipUnless(os.environ.get("SUBCONVERTER_DIR"), "set SUBCONVERTER_DIR for real conversion")
    def test_real_subconverter(self):
        import yaml  # Optional; needed only for checking the actual Clash output.

        runtime = Path(os.environ["SUBCONVERTER_DIR"]).resolve()
        executable = runtime / ("subconverter.exe" if os.name == "nt" else "subconverter")
        samples = fixtures(self.countries)
        with tempfile.TemporaryDirectory(prefix="acl4ssr-test-") as temporary:
            work = Path(temporary)
            shutil.copytree(runtime / "base", work / "base")
            # The Windows binary switches to its own executable directory.
            # Copy it so both preferences and all generated files stay isolated.
            for dependency in runtime.iterdir():
                if dependency.suffix.lower() in {".exe", ".dll"}:
                    shutil.copy2(dependency, work / dependency.name)
            executable = work / executable.name
            (work / "pref.ini").write_text(
                "[common]\napi_mode=false\nenable_insert=false\n"
                "clash_rule_base=base/simple_base.yml\n"
                "proxy_config=NONE\nproxy_ruleset=NONE\nproxy_subscription=NONE\n"
                "[emojis]\nadd_emoji=true\nremove_old_emoji=true\n"
                "[ruleset]\nenabled=false\n"
                "[server]\nlisten=127.0.0.1\nport=PORT\n"
                "[advanced]\nlog_level=warn\nenable_cache=false\n", encoding="utf-8")
            # Exercise the exact group configuration without fetching unrelated
            # remote rulesets. All nodes are non-routable synthetic fixtures.
            (work / "groups.ini").write_text(
                "[custom]\n" + generator.render_groups(self.countries) +
                "enable_rule_generator=false\noverwrite_original_rules=false\n", encoding="utf-8")
            nodes = [{"name": name, "type": "ss", "server": "192.0.2.1", "port": 8388,
                      "cipher": "aes-128-gcm", "password": "test-fixture-only"} for name in samples]
            payload = json.dumps({"proxies": nodes}, ensure_ascii=False).encode()

            class Handler(http.server.BaseHTTPRequestHandler):
                def do_GET(self):
                    self.send_response(200)
                    self.end_headers()
                    self.wfile.write(payload)

                def log_message(self, *args):
                    pass

            server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
            threading.Thread(target=server.serve_forever, daemon=True).start()
            with socket.socket() as reserved:
                reserved.bind(("127.0.0.1", 0))
                port = reserved.getsockname()[1]
            pref = work / "pref.ini"
            pref.write_text(pref.read_text(encoding="utf-8").replace("PORT", str(port)), encoding="utf-8")
            try:
                with (work / "converter.log").open("wb") as log:
                    process = subprocess.Popen([str(executable)], cwd=work, stdout=log, stderr=log,
                                               creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
                    try:
                        for _ in range(100):
                            if process.poll() is not None:
                                self.fail((work / "converter.log").read_text(errors="replace"))
                            try:
                                with socket.create_connection(("127.0.0.1", port), timeout=0.2):
                                    break
                            except OSError:
                                time.sleep(0.1)
                        else:
                            self.fail("Converter did not listen on the isolated loopback port")
                        params = urllib.parse.urlencode({
                            "target": "clash", "url": f"http://127.0.0.1:{server.server_port}/nodes",
                            "config": "groups.ini", "append_type": "false",
                            "new_name": "true",
                        })
                        with urllib.request.urlopen(f"http://127.0.0.1:{port}/sub?{params}", timeout=90) as response:
                            output = yaml.safe_load(response.read())
                        groups = {g["name"]: g for g in output["proxy-groups"]}
                        self.assertEqual(len(groups), 254)
                        self.assertEqual(len(output["proxies"]), len(samples))
                        for country in self.countries:
                            group = groups[generator.group_name(country)]
                            expected = {name for name, code in samples.items() if code == country["code"]}
                            self.assertEqual(set(group["proxies"]), expected, country["code"])
                            self.assertEqual(group["type"], "url-test")
                            self.assertEqual(group["interval"], 300)
                            self.assertEqual(group["tolerance"], 150)
                        manual = groups["☑️ 手动切换"]["proxies"]
                        self.assertEqual(set(manual), set(samples))
                        self.assertEqual(groups["🚀 节点选择"]["proxies"][0], "🇺🇸 美国节点")
                        print(f"Real subconverter: {len(samples)} nodes, 254 valid groups, memberships verified.")
                        # A sparse subscription exercises the real backend's
                        # empty-group behavior, documented beside the INI.
                        payload = json.dumps({"proxies": [dict(nodes[0], name="🇺🇸 唯一节点")]},
                                             ensure_ascii=False).encode()
                        with urllib.request.urlopen(f"http://127.0.0.1:{port}/sub?{params}", timeout=30) as response:
                            sparse = yaml.safe_load(response.read())
                        sparse_groups = {g["name"]: g for g in sparse["proxy-groups"]}
                        for country in self.countries:
                            expected = ["🇺🇸 唯一节点"] if country["code"] == "US" else ["DIRECT"]
                            self.assertEqual(sparse_groups[generator.group_name(country)]["proxies"], expected)
                        print("Sparse subscription: original flag retained; 248 empty groups contain DIRECT.")
                    finally:
                        process.terminate()
                        with contextlib.suppress(subprocess.TimeoutExpired):
                            process.wait(timeout=5)
                        if process.poll() is None:
                            process.kill()
                            process.wait()
            finally:
                server.shutdown()
                server.server_close()


if __name__ == "__main__":
    unittest.main()
