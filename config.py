
ruleset = [
    ["🤖 ChatBot", "https://raw.githubusercontent.com/SubConv/ZJU-Rule/main/Clash/Ruleset/OpenAi.list"],
    ["🤖 ChatBot", "https://raw.githubusercontent.com/SubConv/ZJU-Rule/main/Clash/Ruleset/ChatBot.list"],
    ["🎯 全球直连", "https://raw.githubusercontent.com/SubConv/ZJU-Rule/main/Clash/LocalAreaNetwork.list"],
    ["🎯 全球直连", "https://raw.githubusercontent.com/SubConv/ZJU-Rule/main/Clash/UnBan.list"],
    ["🛑 广告拦截", "https://raw.githubusercontent.com/SubConv/ZJU-Rule/main/Clash/BanAD.list"],
    ["🍃 应用净化", "https://raw.githubusercontent.com/SubConv/ZJU-Rule/main/Clash/BanProgramAD.list"],
    ["🛑 广告拦截", "https://raw.githubusercontent.com/SubConv/ZJU-Rule/main/Clash/BanEasyList.list"],
    ["🛑 广告拦截", "https://raw.githubusercontent.com/SubConv/ZJU-Rule/main/Clash/BanEasyListChina.list"],
    ["🛡️ 隐私防护", "https://raw.githubusercontent.com/SubConv/ZJU-Rule/main/Clash/BanEasyPrivacy.list"],
    ["📢 谷歌FCM", "https://raw.githubusercontent.com/SubConv/ZJU-Rule/main/Clash/Ruleset/GoogleFCM.list"],
    # ["🎯 全球直连", "https://raw.githubusercontent.com/SubConv/ZJU-Rule/main/Clash/GoogleCN.list"],
    ["🎯 全球直连", "https://raw.githubusercontent.com/SubConv/ZJU-Rule/main/Clash/Ruleset/Adobe.list"],
    ["Ⓜ️ 微软云盘", "https://raw.githubusercontent.com/SubConv/ZJU-Rule/main/Clash/OneDrive.list"],
    ["Ⓜ️ 微软服务", "https://raw.githubusercontent.com/SubConv/ZJU-Rule/main/Clash/Microsoft.list"],
    ["🍎 苹果服务", "https://raw.githubusercontent.com/SubConv/ZJU-Rule/main/Clash/Apple.list"],
    ["📲 电报消息", "https://raw.githubusercontent.com/SubConv/ZJU-Rule/main/Clash/Telegram.list"],
    ["🎶 网易音乐", "https://raw.githubusercontent.com/SubConv/ZJU-Rule/main/Clash/Ruleset/NetEaseMusic.list"],
    ["🎶 Spotify", "https://raw.githubusercontent.com/SubConv/ZJU-Rule/main/Clash/Ruleset/Spotify.list"],
    ["🎮 游戏平台", "https://raw.githubusercontent.com/SubConv/ZJU-Rule/main/Clash/Ruleset/Epic.list"],
    ["🎮 游戏平台", "https://raw.githubusercontent.com/SubConv/ZJU-Rule/main/Clash/Ruleset/Origin.list"],
    ["🎮 游戏平台", "https://raw.githubusercontent.com/SubConv/ZJU-Rule/main/Clash/Ruleset/Sony.list"],
    ["🎮 游戏平台", "https://raw.githubusercontent.com/SubConv/ZJU-Rule/main/Clash/Ruleset/Steam.list"],
    ["🎮 游戏平台", "https://raw.githubusercontent.com/SubConv/ZJU-Rule/main/Clash/Ruleset/Nintendo.list"],
    ["📹 油管视频", "https://raw.githubusercontent.com/SubConv/ZJU-Rule/main/Clash/Ruleset/YouTube.list"],
    ["🎥 奈飞视频", "https://raw.githubusercontent.com/SubConv/ZJU-Rule/main/Clash/Ruleset/Netflix.list"],
    ["📺 巴哈姆特", "https://raw.githubusercontent.com/SubConv/ZJU-Rule/main/Clash/Ruleset/Bahamut.list"],
    ["📺 哔哩哔哩", "https://raw.githubusercontent.com/SubConv/ZJU-Rule/main/Clash/Ruleset/BilibiliHMT.list"],
    ["📺 哔哩哔哩", "https://raw.githubusercontent.com/SubConv/ZJU-Rule/main/Clash/Ruleset/Bilibili.list"],
    ["🌏 国内媒体", "https://raw.githubusercontent.com/SubConv/ZJU-Rule/main/Clash/ChinaMedia.list"],
    ["🌍 国外媒体", "https://raw.githubusercontent.com/SubConv/ZJU-Rule/main/Clash/ProxyMedia.list"],
    ["🚀 节点选择", "https://raw.githubusercontent.com/SubConv/ZJU-Rule/main/Clash/ProxyGFWlist.list"],
    ["🎯 全球直连", "https://raw.githubusercontent.com/SubConv/ZJU-Rule/main/Clash/ChinaIp.list"],
    ["🎯 全球直连", "https://raw.githubusercontent.com/SubConv/ZJU-Rule/main/Clash/ChinaDomain.list"],
    ["🎯 全球直连", "https://raw.githubusercontent.com/SubConv/ZJU-Rule/main/Clash/ChinaCompanyIp.list"],
    ["🎯 全球直连", "https://raw.githubusercontent.com/SubConv/ZJU-Rule/main/Clash/Download.list"],
    ["🎯 全球直连", "[]GEOIP,CN"],
    ["🐟 漏网之鱼", "[]FINAL"]
]

region_dict = {
    "HK": [r"🇭🇰|HK|Hong|Kong|HGC|WTT|CMI|港", "🇭🇰 香港节点"],
    "TW": [r"🇹🇼|TW|Taiwan|新北|彰化|CHT|台|HINET", "🇨🇳 台湾节点"],
    "SG": [r"🇸🇬|SG|Singapore|狮城|^新[^节北]|[^刷更]新[^节北]", "🇸🇬 狮城节点"],
    "JP": [r"🇯🇵|JP|Japan|Tokyo|Osaka|Saitama|东京|大阪|埼玉|日", "🇯🇵 日本节点"],
    "KR": [r"🇰🇷|KO?R|Korea|首尔|韩|韓", "🇰🇷 韩国节点"],
    "US": [r"🇺🇸|US|America|United.*?States|美|波特兰|达拉斯|俄勒冈|凤凰城|费利蒙|硅谷|拉斯维加斯|洛杉矶|圣何塞|圣克拉拉|西雅图|芝加哥", "🇺🇸 美国节点"]
}

custom_proxy_group = [
    {
        "name": "♻️ 自动选择",
        "type": "url-test",
        "rule": False
    },
    {
        "name": "🚀 手动切换",
        "type": "select",
        "manual": True,
        "rule": False
    },
    {
        "name": "🔯 故障转移",
        "type": "fallback",
        "rule": False
    },
    {
        "name": "🔮 负载均衡",
        "type": "load-balance",
        "rule": False
    },
    {
        "name": "🔮 香港负载均衡",
        "type": "load-balance",
        "rule": False,
        "region": ["HK"]
    },
    {
        "name": "🤖 ChatBot",
        "type": "select",
        "prior": "PROXY"
    },
    {
        "name": "📲 电报消息",
        "type": "select",
        "prior": "PROXY"
    },
    {
        "name": "📹 油管视频",
        "type": "select",
        "prior": "PROXY"
    },
    {
        "name": "🎥 奈飞视频",
        "type": "select",
        "prior": "PROXY"
    },
    {
        "name": "📺 巴哈姆特",
        "type": "select",
        "prior": "PROXY"
    },
    {
        "name": "📺 哔哩哔哩",
        "type": "select",
        "prior": "DIRECT"
    },
    {
        "name": "🌍 国外媒体",
        "type": "select",
        "prior": "PROXY"
    },
    {
        "name": "🌏 国内媒体",
        "type": "select",
        "prior": "DIRECT"
    },
    {
        "name": "📢 谷歌FCM",
        "type": "select",
        "prior": "DIRECT"
    },
    {
        "name": "Ⓜ️ 微软云盘",
        "type": "select",
        "prior": "DIRECT"
    },
    {
        "name": "Ⓜ️ 微软服务",
        "type": "select",
        "prior": "DIRECT"
    },
    {
        "name": "🍎 苹果服务",
        "type": "select",
        "prior": "DIRECT"
    },
    {
        "name": "🎮 游戏平台",
        "type": "select",
        "prior": "DIRECT"
    },
    {
        "name": "🎶 网易音乐",
        "type": "select",
        "prior": "DIRECT"
    },
    {
        "name": "🎶 Spotify",
        "type": "select",
        "prior": "DIRECT"
    },
    {
        "name": "🎯 全球直连",
        "type": "select",
        "prior": "DIRECT"
    },
    {
        "name": "🛑 广告拦截",
        "type": "select",
        "prior": "REJECT"
    },
    {
        "name": "🍃 应用净化",
        "type": "select",
        "prior": "REJECT"
    },
    {
        "name": "🛡️ 隐私防护",
        "type": "select",
        "prior": "REJECT"
    },
    {
        "name": "🐟 漏网之鱼",
        "type": "select",
        "prior": "PROXY"
    }
]
