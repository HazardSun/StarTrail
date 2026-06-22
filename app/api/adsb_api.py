import math
import threading
import requests
from datetime import datetime
from typing import Optional

from app.config import config

A = 6378137.0
E2 = 0.00669437999
AIRCRAFT_CACHE = []
AIRCRAFT_CACHE_TIME = 0
AIRCRAFT_REG_CACHE = {}
_CACHE_LOCK = threading.Lock()
OPENSKY_URL = "https://opensky-network.org/api/states/all"

ICAO_TYPE_NAMES = {
    # Boeing
    "B732": "波音 737-200", "B733": "波音 737-300", "B734": "波音 737-400",
    "B735": "波音 737-500", "B736": "波音 737-600", "B737": "波音 737-700",
    "B738": "波音 737-800", "B739": "波音 737-900", "B37M": "波音 737 MAX 7",
    "B38M": "波音 737 MAX 8", "B39M": "波音 737 MAX 9", "B3XM": "波音 737 MAX 10",
    "B741": "波音 747-100", "B742": "波音 747-200", "B743": "波音 747-300",
    "B744": "波音 747-400", "B748": "波音 747-8",
    "B752": "波音 757-200", "B753": "波音 757-300",
    "B762": "波音 767-200", "B763": "波音 767-300", "B764": "波音 767-400",
    "B772": "波音 777-200", "B773": "波音 777-300", "B77L": "波音 777-200LR",
    "B77W": "波音 777-300ER", "B778": "波音 777-8", "B779": "波音 777-9",
    "B787": "波音 787-8", "B788": "波音 787-8", "B789": "波音 787-9",
    "B78X": "波音 787-10",
    "BCS1": "空客 A220-100", "BCS3": "空客 A220-300",
    "BE20": "空客/比奇 空中国王 200",
    # Airbus
    "A318": "空客 A318", "A319": "空客 A319", "A320": "空客 A320",
    "A321": "空客 A321", "A20N": "空客 A320neo", "A21N": "空客 A321neo",
    "A19N": "空客 A319neo",
    "A332": "空客 A330-200", "A333": "空客 A330-300",
    "A337": "空客 A330-700", "A338": "空客 A330-800", "A339": "空客 A330-900",
    "A342": "空客 A340-200", "A343": "空客 A340-300", "A345": "空客 A340-500",
    "A346": "空客 A340-600",
    "A359": "空客 A350-900", "A35K": "空客 A350-1000",
    "A388": "空客 A380-800",
    # Embraer
    "E135": "巴西航空 ERJ 135", "E145": "巴西航空 ERJ 145",
    "E170": "巴西航空 E170", "E175": "巴西航空 E175",
    "E190": "巴西航空 E190", "E195": "巴西航空 E195",
    "E290": "巴西航空 E190-E2", "E295": "巴西航空 E195-E2",
    # Bombardier / Mitsubishi
    "CRJ2": "庞巴迪 CRJ-200", "CRJ7": "庞巴迪 CRJ-700",
    "CRJ9": "庞巴迪 CRJ-900", "CRJX": "庞巴迪 CRJ-1000",
    "DH8A": "庞巴迪 Dash 8 Q100", "DH8B": "庞巴迪 Dash 8 Q200",
    "DH8C": "庞巴迪 Dash 8 Q300", "DH8D": "庞巴迪 Dash 8 Q400",
    "CL60": "庞巴迪 挑战者 600",
    "GLF4": "湾流 G450", "GLF5": "湾流 G500/G550",
    "GLF6": "湾流 G650",
    # COMAC
    "C919": "中国商飞 C919", "ARJ1": "中国商飞 ARJ21",
    # ATR
    "AT43": "ATR 42-300", "AT45": "ATR 42-500",
    "AT72": "ATR 72-200", "AT73": "ATR 72-500", "AT75": "ATR 72-600",
    # Tupolev / Ilyushin / Antonov
    "T154": "图波列夫 Tu-154", "T204": "图波列夫 Tu-204",
    "IL76": "伊尔 Il-76", "IL96": "伊尔 Il-96",
    "AN12": "安东诺夫 An-12", "AN24": "安东诺夫 An-24",
    "AN26": "安东诺夫 An-26", "AN28": "安东诺夫 An-28",
    "AN72": "安东诺夫 An-72", "AN74": "安东诺夫 An-74",
    "AN14": "安东诺夫 An-140", "AN148": "安东诺夫 An-148",
    "SU95": "苏霍伊 SSJ100/SSJ-95",
    "MC21": "伊尔库特 MC-21",
    # Others
    "F50": "福克 50", "F70": "福克 70", "F100": "福克 100",
    "C130": "洛克希德 C-130 大力神",
    "A124": "安东诺夫 An-124 鲁斯兰",
    "A225": "安东诺夫 An-225 梦幻",
    "E135": "巴西航空 ERJ 135", "E145": "巴西航空 ERJ 145",
    "E35L": "巴西航空 莱格赛 600/650",
    "E50P": "巴西航空 飞鸿 100", "E55P": "巴西航空 飞鸿 300",
    "PA27": "派珀 PA-24 科曼奇",
    "C172": "塞斯纳 172", "C182": "塞斯纳 182",
    "C208": "塞斯纳 208 大篷车",
}

CALLSIGN_AIRLINE = {
    "CCA": ("中国国航", "A320/737系列"), "CES": ("中国东航", "A320/737系列"),
    "CSN": ("中国南航", "A320/737系列"), "CSC": ("四川航空", "A320系列"),
    "CSZ": ("深圳航空", "737系列"), "CHH": ("海南航空", "737/787系列"),
    "CXA": ("厦门航空", "737系列"), "DKH": ("吉祥航空", "A320系列"),
    "OKA": ("奥凯航空", "737系列"), "CUA": ("中国联航", "737系列"),
    "TBA": ("西藏航空", "A319"), "GCR": ("天津航空", "E190"),
    "KNA": ("昆明航空", "737系列"), "RLH": ("瑞丽航空", "737系列"),
    "UEA": ("成都航空", "A320/ARJ21"), "EPA": ("河北航空", "737系列"),
    "HXA": ("华夏航空", "A320/CRJ9"), "CQN": ("重庆航空", "A320系列"),
    "DAL": ("达美航空", "717/737系列"), "UAL": ("美联航", "737/777系列"),
    "AAL": ("美国航空", "737/787系列"), "SWA": ("西南航空", "737系列"),
    "BAW": ("英国航空", "A380/777系列"), "AFR": ("法国航空", "A320/A380"),
    "DLH": ("汉莎航空", "A320/A380"), "SIA": ("新加坡航空", "A350/A380"),
    "CPA": ("国泰航空", "A330/777系列"), "HDA": ("港龙航空", "A330系列"),
    "CAL": ("中华航空", "A350/777系列"), "EVA": ("长荣航空", "777/787系列"),
    "JAL": ("日本航空", "737/787系列"), "ANA": ("全日空", "737/787系列"),
    "KAL": ("大韩航空", "737/787系列"), "QFA": ("澳洲航空", "A330/787系列"),
    "THY": ("土耳其航空", "A320/777系列"), "KLM": ("荷兰皇家航空", "737/777系列"),
    "MAS": ("马来西亚航空", "737/A330"), "UAE": ("阿联酋航空", "A380/777系列"),
    "ETD": ("阿提哈德航空", "777/787系列"), "QTR": ("卡塔尔航空", "A350/777系列"),
    "HVN": ("越南航空", "A320/A350"), "FIN": ("芬兰航空", "A320/A350系列"),
    "SAS": ("北欧航空", "A320/A330"), "RYR": ("瑞安航空", "737-800"),
    "EZY": ("易捷航空", "A320系列"), "WJA": ("西捷航空", "737系列"),
    "ACA": ("加拿大航空", "A320/777系列"), "AVA": ("哥伦比亚航空", "A320系列"),
    "LAN": ("智利航空", "A320/787系列"), "TAM": ("巴西航空", "A320系列"),
    "AMX": ("墨西哥航空", "737/787系列"), "ETH": ("埃塞俄比亚航空", "737/787系列"),
    "KQA": ("肯尼亚航空", "737/787系列"), "UZB": ("乌兹别克航空", "A320/767系列"),
    "AAR": ("韩亚航空", "A320/777系列"), "ABW": ("阿拉伯航空", "A320系列"),
    "AFL": ("俄罗斯航空", "A320/777系列"), "AGN": ("爱尔兰航空", "A320/A330系列"),
    "AIQ": ("泰国亚航", "A320系列"), "AIC": ("印度航空", "A320/777系列"),
    "ALK": ("斯里兰卡航空", "A320/A330系列"), "ANA": ("全日空", "737/787系列"),
    "AUA": ("奥地利航空", "A320/777系列"), "AZA": ("意大利航空", "A320/A330系列"),
    "BER": ("柏林航空", "A320系列"), "BMC": ("孟加拉航空", "737系列"),
    "BOX": ("北欧大西洋", "787系列"), "BRU": ("白俄罗斯航空", "737系列"),
    "BTK": ("巴泽航空", "A320系列"), "CAB": ("柬埔寨航空", "A320系列"),
    "CAL": ("中华航空", "A350/777系列"), "CCA": ("中国国航", "A320/737系列"),
    "CCD": ("中国货运航空", "777F系列"), "CDG": ("山东航空", "737系列"),
    "CES": ("中国东航", "A320/737系列"), "CFE": ("英国东方航空", "E195"),
    "CHH": ("海南航空", "737/787系列"), "CI": ("中华航空", "A350/777系列"),
    "CKK": ("中国货运邮政", "737F系列"), "CLH": ("汉莎城市航空", "CRJ/E190"),
    "CPA": ("国泰航空", "A330/777系列"), "CQN": ("重庆航空", "A320系列"),
    "CRA": ("香港快运航空", "A320系列"), "CRK": ("香港航空", "A320/A330系列"),
    "CSA": ("捷克航空", "A320系列"), "CSC": ("四川航空", "A320系列"),
    "CSN": ("中国南航", "A320/737系列"), "CSZ": ("深圳航空", "737系列"),
    "CTN": ("克罗地亚航空", "A320系列"), "CUA": ("中国联航", "737系列"),
    "CXA": ("厦门航空", "737系列"), "CYC": ("中国邮政航空", "737F系列"),
    "DAH": ("阿尔及利亚航空", "A330/737系列"), "DAL": ("达美航空", "717/737系列"),
    "DLH": ("汉莎航空", "A320/A380"), "DNL": ("荷兰精神航空", "A320系列"),
    "DSM": ("哥伦比亚航空", "A320系列"), "DST": ("天西航空", "E175系列"),
    "EAI": ("爱尔兰航空", "A320系列"), "EAL": ("美国东方航空", "737/767系列"),
    "ELB": ("欧罗巴航空", "737/787系列"), "ELY": ("以色列航空", "737/777系列"),
    "EMI": ("阿联酋航空水运", "水上飞机"), "ENY": ("环境航空", "E175系列"),
    "EVA": ("长荣航空", "777/787系列"), "EWG": ("欧翼航空", "A320/A330系列"),
    "EXS": ("捷特2航空", "737系列"), "EZY": ("易捷航空", "A320系列"),
    "FAB": ("日本亚洲航空", "A320系列"), "FFM": ("LATAM货运", "767F系列"),
    "FIN": ("芬兰航空", "A320/A350系列"), "FJI": ("斐济航空", "A330/737系列"),
    "FLI": ("大西洋航空", "737系列"), "FWI": ("加勒比航空", "A330/A350系列"),
    "GAL": ("波罗的海航空", "A220系列"), "GBA": ("大湾区航空", "737系列"),
    "GCR": ("天津航空", "E190"), "GIA": ("印尼鹰航", "A330/777系列"),
    "GJT": ("捷星航空", "A320/787系列"), "GOJ": ("日本捷星航空", "A320系列"),
    "GOW": ("春秋航空", "A320系列"), "GRE": ("捷星太平洋", "A320系列"),
    "GWL": ("海湾航空", "A320/787系列"), "HAL": ("夏威夷航空", "A330/A321"),
    "HDA": ("港龙航空", "A330系列"), "HLN": ("海南航空", "737/787系列"),
    "HKE": ("香港快运", "A320系列"), "HKX": ("香港航空", "A320/A330系列"),
    "HXA": ("华夏航空", "A320/CRJ9"), "HVN": ("越南航空", "A320/A350"),
    "IAD": ("阿斯塔纳航空", "A320/787系列"), "IBE": ("伊比利亚航空", "A320/A330系列"),
    "ICE": ("冰岛航空", "737/757系列"), "IGO": ("靛蓝航空", "A320系列"),
    "IRA": ("伊朗航空", "A320/A330系列"), "IRM": ("马汉航空", "A310/A340系列"),
    "JAL": ("日本航空", "737/787系列"), "JBU": ("捷蓝航空", "A220/A320系列"),
    "JJA": ("济州航空", "737系列"), "JNA": ("真航空", "737系列"),
    "JST": ("捷星航空", "A320/787系列"), "KAL": ("大韩航空", "737/787系列"),
    "KAR": ("哈萨克航空", "A320/E190"), "KLM": ("荷兰皇家航空", "737/777系列"),
    "KNA": ("昆明航空", "737系列"), "KQA": ("肯尼亚航空", "737/787系列"),
    "KZR": ("阿斯塔纳航空", "A320/787系列"), "LAL": ("LATAM智利", "A320/787系列"),
    "LAN": ("智利航空", "A320/787系列"), "LDA": ("拉达姆航空", "737系列"),
    "LGL": ("卢森堡航空", "737系列"), "LHA": ("莱比锡航空", "737系列"),
    "LKA": ("拉基亚航空", "737系列"), "LLR": ("靛蓝航空", "A320系列"),
    "LNE": ("拉美航空", "A320系列"), "LOT": ("波兰航空", "737/787系列"),
    "LPE": ("秘鲁航空", "A320系列"), "LRC": ("哥伦比亚航空", "A320系列"),
    "LYN": ("Lynx航空", "737系列"), "MAS": ("马来西亚航空", "737/A330"),
    "MDA": ("中华航空货运", "747F系列"), "MEA": ("中东航空", "A320/A330系列"),
    "MGL": ("蒙古航空", "737系列"), "MGO": ("蒙古航空货运", "737F系列"),
    "MHD": ("马航货运", "A330F系列"), "MKA": ("毛里求斯航空", "A330/A350"),
    "MLR": ("马尔代夫航空", "A320系列"), "MMA": ("缅甸航空", "A320/737系列"),
    "MNA": ("蒙古航空", "737系列"), "MON": ("蒙古航空", "737系列"),
    "MPE": ("马来西亚飞萤", "ATR72"), "MSR": ("埃及航空", "A320/777系列"),
    "MXA": ("墨西哥航空", "737/787系列"), "MYA": ("缅甸国际航空", "A320系列"),
    "NKS": ("精神航空", "A320系列"), "NMA": ("新几内亚航空", "737/787系列"),
    "NOK": ("飞鸟航空", "737系列"), "NXA": ("北欧航空", "A320系列"),
    "OAL": ("奥林匹克航空", "A320系列"), "OAV": ("柬埔寨竹航空", "A320系列"),
    "OMA": ("阿曼航空", "737/787系列"), "ONE": ("ONE航空", "737系列"),
    "OZN": ("OZ航空", "737系列"), "PAA": ("巴拿马航空", "737系列"),
    "PAL": ("菲律宾航空", "A320/A350"), "PBA": ("PHP航空", "737系列"),
    "PCE": ("和平航空", "737系列"), "PIA": ("巴基斯坦航空", "A320/777系列"),
    "PLF": ("波兰航空", "737系列"), "PRI": ("普里航空", "737系列"),
    "PSA": ("PSA航空", "CRJ系列"), "PUA": ("柬埔寨航空", "A320系列"),
    "QDA": ("青岛航空", "A320系列"), "QFA": ("澳洲航空", "A330/787系列"),
    "QNT": ("捷星太平洋", "A320系列"), "QRL": ("澳洲航空货运", "767F系列"),
    "QTR": ("卡塔尔航空", "A350/777系列"), "RAM": ("摩洛哥航空", "737/787系列"),
    "RBA": ("文莱皇家航空", "A320/787系列"), "RCT": ("R航空", "737系列"),
    "RLH": ("瑞丽航空", "737系列"), "RNA": ("俄罗斯航空", "A320/777系列"),
    "ROU": ("鲁昂航空", "A320系列"), "RPB": ("菲律宾亚洲航空", "A320系列"),
    "RSC": ("R航空", "737系列"), "RSU": ("俄罗斯航空", "A320系列"),
    "RYR": ("瑞安航空", "737-800"), "RZO": ("亚速尔航空", "A320系列"),
    "SAS": ("北欧航空", "A320/A330"), "SBI": ("西伯利亚航空", "A320/737系列"),
    "SCX": ("太阳国航空", "737系列"), "SEY": ("塞舌尔航空", "A320/A330"),
    "SIA": ("新加坡航空", "A350/A380"), "SIL": ("西尔航空", "E175系列"),
    "SKU": ("天空航空", "A320系列"), "SLK": ("捷星亚洲", "A320系列"),
    "SMR": ("萨摩亚航空", "737系列"), "SNG": ("刚果航空", "737系列"),
    "SNY": ("圣尼亚航空", "737系列"), "SOO": ("南方航空", "A320系列"),
    "SPA": ("西班牙航空", "A320系列"), "SPM": ("精神航空", "A320系列"),
    "SRQ": ("空中客车航空", "A320系列"), "SSJ": ("苏霍伊航空", "SSJ100"),
    "STY": ("斯特林航空", "737系列"), "SUD": ("苏丹航空", "A320/737系列"),
    "SVA": ("沙特航空", "A320/777系列"), "SWA": ("西南航空", "737系列"),
    "SWR": ("瑞士航空", "A320/A340"), "SXS": ("太阳快递", "737系列"),
    "SYR": ("叙利亚航空", "A320系列"), "TAM": ("巴西航空", "A320系列"),
    "TAR": ("突尼斯航空", "A320/A330系列"), "TBA": ("西藏航空", "A319"),
    "TCA": ("土耳其货运", "A330F系列"), "TFL": ("TUI航空荷兰", "737/787系列"),
    "TGW": ("酷航", "A320/787系列"), "THA": ("泰国航空", "A320/A350"),
    "THD": ("泰国微笑航空", "A320系列"), "THY": ("土耳其航空", "A320/777系列"),
    "TMA": ("马达加斯加航空", "A340系列"), "TMW": ("托马斯库克航空", "A320系列"),
    "TNU": ("A米亚航空", "737系列"), "TOM": ("托马斯库克航空", "737/787系列"),
    "TPA": ("天马航空", "A320系列"), "TRA": ("荷兰泛航", "737系列"),
    "TTW": ("老虎航空", "A320系列"), "TVF": ("法国泛航", "737系列"),
    "TWA": ("葡萄牙航空", "A320/A330系列"), "TXL": ("柏林航空", "A320系列"),
    "UAL": ("美联航", "737/777系列"), "UAE": ("阿联酋航空", "A380/777系列"),
    "UBA": ("缅甸航空", "A320/737系列"), "UBG": ("蒙古航空货运", "737F系列"),
    "UCA": ("康姆航空", "CRJ系列"), "UCC": ("犹他航空", "737系列"),
    "UEA": ("成都航空", "A320/ARJ21"), "UIA": ("立荣航空", "ATR72"),
    "UKR": ("乌克兰航空", "737系列"), "ULA": ("乌兹别克航空", "A320/767系列"),
    "UPS": ("UPS航空", "747F/767F系列"), "USA": ("美国航空", "737系列"),
    "UZB": ("乌兹别克航空", "A320/767系列"), "VAL": ("沃拉里斯航空", "A320系列"),
    "VAU": ("沃罗格航空", "A320/737系列"), "VIR": ("维珍大西洋", "A330/A350"),
    "VIV": ("沃拉里斯航空", "A320系列"), "VJA": ("越捷航空", "A320/A330"),
    "VLK": ("维珍航空", "A320系列"), "VNA": ("越南航空", "A320/A350"),
    "VNV": ("越南航空", "A320系列"), "VOI": ("沃拉里斯航空", "A320系列"),
    "VPA": ("越捷航空", "A320系列"), "VRE": ("越南航空", "A320系列"),
    "VRG": ("巴西航空", "A320系列"), "VTI": ("维斯塔拉航空", "A320系列"),
    "WAL": ("西捷航空", "737/787系列"), "WAT": ("西非航空", "737系列"),
    "WDL": ("WDL航空", "ATR42"), "WEB": ("Webjet航空", "737系列"),
    "WJA": ("西捷航空", "737系列"), "WMT": ("Wizz航空", "A320/A321"),
    "WOW": ("WOW航空", "A320/A330系列"), "WSG": ("西捷航空", "737/787系列"),
    "XAR": ("夏威夷航空", "A330系列"), "XAX": ("亚洲航空X", "A330/A340"),
    "XNA": ("快运航空", "CRJ系列"), "XSN": ("新航货运", "747F系列"),
    "XYA": ("新航", "A350/A380"), "Y8": ("杨子江快运", "737F系列"),
    "YEL": ("黄航空", "737系列"), "YZR": ("扬子江快运", "737F系列"),
    "ZDA": ("中龙航空", "737系列"), "ZNA": ("中龙航空", "737系列"),
    "ZZM": ("中联航", "737系列"),
}

def _lookup_aircraft(callsign):
    if not callsign or callsign == "----":
        return (None, None)
    raw = callsign.strip().upper()
    prefix = raw[:3]
    result = CALLSIGN_AIRLINE.get(prefix, (None, None))
    if result[0]:
        return result
    prefix2 = raw[:2]
    for k, v in CALLSIGN_AIRLINE.items():
        if k.startswith(prefix2):
            return v
    return (None, None)


def _geodetic_to_ecef(lat_deg, lon_deg, alt_m):
    lat = math.radians(lat_deg)
    lon = math.radians(lon_deg)
    n = A / math.sqrt(1 - E2 * math.sin(lat) ** 2)
    x = (n + alt_m) * math.cos(lat) * math.cos(lon)
    y = (n + alt_m) * math.cos(lat) * math.sin(lon)
    z = (n * (1 - E2) + alt_m) * math.sin(lat)
    return x, y, z


def _ecef_to_altaz(ox, oy, oz, tx, ty, tz, obs_lat_deg, obs_lon_deg):
    dx, dy, dz = tx - ox, ty - oy, tz - oz
    lat_r = math.radians(obs_lat_deg)
    lon_r = math.radians(obs_lon_deg)
    east = -math.sin(lon_r) * dx + math.cos(lon_r) * dy
    north = (-math.sin(lat_r) * math.cos(lon_r) * dx
             - math.sin(lat_r) * math.sin(lon_r) * dy
             + math.cos(lat_r) * dz)
    up = (math.cos(lat_r) * math.cos(lon_r) * dx
          + math.cos(lat_r) * math.sin(lon_r) * dy
          + math.sin(lat_r) * dz)
    range_m = math.sqrt(east * east + north * north + up * up)
    alt = math.degrees(math.atan2(up, math.sqrt(east * east + north * north)))
    az = math.degrees(math.atan2(east, north)) % 360
    return alt, az, range_m


def fetch_aircraft(dt: Optional[datetime] = None):
    global AIRCRAFT_CACHE, AIRCRAFT_CACHE_TIME
    if dt is None:
        dt = datetime.now()
    now = dt.timestamp()
    with _CACHE_LOCK:
        if AIRCRAFT_CACHE and (now - AIRCRAFT_CACHE_TIME) < 60:
            return AIRCRAFT_CACHE

    lat = config.latitude
    lon = config.longitude
    span = 2.0
    params = {"lamin": lat - span, "lomin": lon - span,
              "lamax": lat + span, "lomax": lon + span}
    results = []

    try:
        resp = requests.get(OPENSKY_URL, params=params, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            states = data.get("states", [])
            ox, oy, oz = _geodetic_to_ecef(lat, lon, 0)

            for s in states:
                icao = s[0]
                callsign = (s[1] or "").strip()
                country = s[2] or ""
                plon = s[5]
                plat = s[6]
                palt = s[7]
                velocity = s[9] or 0
                heading = s[10] or 0
                vert_rate = s[11] or 0
                on_ground = s[8] or False

                if plon is None or plat is None or palt is None or on_ground:
                    continue

                aircraft_alt_m = palt * 0.3048
                tx, ty, tz = _geodetic_to_ecef(plat, plon, aircraft_alt_m)
                alt_deg, az_deg, dist_m = _ecef_to_altaz(ox, oy, oz, tx, ty, tz, lat, lon)

                if alt_deg < -5:
                    continue

                airline, model = _lookup_aircraft(callsign)
                results.append({
                    "icao": icao,
                    "callsign": callsign or "----",
                    "country": country,
                    "airline": airline or country,
                    "model": model or "未知",
                    "altitude_m": round(aircraft_alt_m, 0),
                    "altitude_ft": round(palt, 0),
                    "altitude": round(alt_deg, 1),
                    "azimuth": round(az_deg, 1),
                    "distance_km": round(dist_m / 1000, 1),
                    "velocity_kmh": round(velocity * 3.6, 0) if velocity else 0,
                    "heading": round(heading, 0) if heading else 0,
                    "vert_rate_fpm": round(vert_rate, 0) if vert_rate else 0,
                    "lat": plat,
                    "lon": plon,
                })
        else:
            with _CACHE_LOCK:
                if AIRCRAFT_CACHE:
                    return AIRCRAFT_CACHE
    except Exception:
        with _CACHE_LOCK:
            if AIRCRAFT_CACHE:
                return AIRCRAFT_CACHE

    with _CACHE_LOCK:
        AIRCRAFT_CACHE = results
        AIRCRAFT_CACHE_TIME = now
    return results


def add_aircraft_trajectories(aircraft_list):
    """Add trajectory predictions (alt/az over time) to each aircraft."""
    lat = config.latitude
    lon = config.longitude
    ox, oy, oz = _geodetic_to_ecef(lat, lon, 0)
    for ac in aircraft_list:
        ac["trajectory"] = _predict_trajectory(ac, ox, oy, oz, lat, lon)
    return aircraft_list


def _predict_trajectory(ac, ox, oy, oz, obs_lat, obs_lon):
    lat = ac["lat"]
    lon_deg = ac["lon"]
    alt_m = ac["altitude_m"]
    heading = ac["heading"]
    velocity_ms = ac["velocity_kmh"] / 3.6
    if velocity_ms < 5 or not heading:
        return []
    heading_rad = math.radians(heading)
    trajectory = []
    for dt in [30, 60, 90, 120, 180, 240, 300]:
        dist = velocity_ms * dt
        dlat = dist * math.cos(heading_rad) / 111320.0
        dlon = dist * math.sin(heading_rad) / (111320.0 * math.cos(math.radians(lat)))
        new_lat = lat + dlat
        new_lon = lon_deg + dlon
        tx, ty, tz = _geodetic_to_ecef(new_lat, new_lon, alt_m)
        alt_deg, az_deg, _ = _ecef_to_altaz(ox, oy, oz, tx, ty, tz, obs_lat, obs_lon)
        trajectory.append({"alt": round(alt_deg, 1), "az": round(az_deg, 1), "time_offset_s": dt})
    return trajectory


def fetch_aircraft_registrations(aircraft_list):
    """Fetch registration, type, model, year via ICAO24 lookup."""
    with _CACHE_LOCK:
        icaos = [ac["icao"] for ac in aircraft_list if ac.get("icao") and ac["icao"] not in AIRCRAFT_REG_CACHE]
    if icaos:
        try:
            batch = ",".join(icao.lower() for icao in icaos if icao)
            url = f"https://api.airplanes.live/v2/hex/{batch}"
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                with _CACHE_LOCK:
                    for entry in data.get("ac", []):
                        icao = entry.get("hex", "").lower()
                        reg = entry.get("r", "") or entry.get("reg", "")
                        if not icao or not reg:
                            continue
                    atype = entry.get("t", "")
                    aname = entry.get("tn", "")
                    serial = entry.get("cn", "")
                    year = entry.get("yr", "")
                    op = entry.get("op", "")
                    AIRCRAFT_REG_CACHE[icao] = {
                        "registration": reg,
                        "aircraft_type": atype,
                        "aircraft_model": aname,
                        "serial": serial,
                        "year": year,
                        "operator": op,
                    }
        except Exception:
            pass
    with _CACHE_LOCK:
        for ac in aircraft_list:
            icao = ac.get("icao", "").lower()
            if icao in AIRCRAFT_REG_CACHE:
                info = AIRCRAFT_REG_CACHE[icao]
                ac["registration"] = info["registration"]
                if info["aircraft_type"]:
                    atype = info["aircraft_type"]
                    ac["aircraft_type"] = atype
                    if not info["aircraft_model"]:
                        info["aircraft_model"] = ICAO_TYPE_NAMES.get(atype, "")
                if info["aircraft_model"]:
                    ac["aircraft_model"] = info["aircraft_model"]
                if info["serial"]:
                    ac["serial"] = info["serial"]
                if info["year"]:
                    ac["year"] = info["year"]
                if info["operator"]:
                    ac["operator"] = info["operator"]


def check_aircraft_proximity(aircraft_list, target_alt, target_az, max_sep_deg=3.0):
    warnings = []
    for ac in aircraft_list:
        sep = math.sqrt((ac["altitude"] - target_alt) ** 2 +
                        (ac["azimuth"] - target_az) ** 2)
        if sep < max_sep_deg:
            warnings.append({
                "callsign": ac["callsign"],
                "altitude_ft": ac["altitude_ft"],
                "distance_km": ac["distance_km"],
                "separation": round(sep, 1),
                "lat": ac["lat"],
                "lon": ac["lon"],
            })
    return warnings
