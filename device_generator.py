import random
import string

MODELS = [
    {"manufacturer": "samsung", "model": "SM-S918B", "pname": "Galaxy S23 Ultra"},
    {"manufacturer": "samsung", "model": "SM-A546B", "pname": "Galaxy A54 5G"},
    {"manufacturer": "samsung", "model": "SM-A145F", "pname": "Galaxy A14"},
    {"manufacturer": "samsung", "model": "SM-G998B", "pname": "Galaxy S21 Ultra"},
    {"manufacturer": "xiaomi", "model": "2201116PG", "pname": "POCO X4 Pro 5G"},
    {"manufacturer": "xiaomi", "model": "21091116UG", "pname": "Redmi Note 11 Pro"},
    {"manufacturer": "xiaomi", "model": "23049PCD8G", "pname": "POCO F5"},
    {"manufacturer": "google", "model": "Pixel 7 Pro", "pname": "Pixel 7 Pro"},
    {"manufacturer": "google", "model": "Pixel 6a", "pname": "Pixel 6a"},
    {"manufacturer": "oppo", "model": "CPH2305", "pname": "Oppo Find X5 Pro"},
    {"manufacturer": "vivo", "model": "V2219", "pname": "Vivo Y35"},
    {"manufacturer": "realme", "model": "RMX3363", "pname": "Realme GT Master Edition"}
]

OPERATORS = [
    {"sim": "Ucell", "operator": "COSCOM", "mcc": "434", "mnc": "05"},
    {"sim": "Beeline UZ", "operator": "Unitel LLC", "mcc": "434", "mnc": "04"},
    {"sim": "Mobiuz", "operator": "UMS", "mcc": "434", "mnc": "07"},
    {"sim": "Uztelecom", "operator": "UzMobile", "mcc": "434", "mnc": "08"}
]

def generate_luhn_imei(tac_prefix="86"):
    """Generates a mathematically valid 15-digit IMEI using the Luhn algorithm."""
    # 8 digits TAC, 6 digits serial, 1 check digit
    imei_body = tac_prefix + "".join([str(random.randint(0, 9)) for _ in range(12)])
    # Calculate Luhn checksum
    total = 0
    for i, char in enumerate(imei_body):
        num = int(char)
        if i % 2 == 1:
            num *= 2
            if num > 9:
                num -= 9
        total += num
    check_digit = (10 - (total % 10)) % 10
    return imei_body + str(check_digit)

def generate_android_id():
    """Generates a 16-character hexadecimal Android ID."""
    return "".join(random.choices("0123456789abcdef", k=16))

def generate_mac_address():
    """Generates a valid randomized MAC address."""
    # Set locally administered bit and unicast bit
    first_byte = (random.randint(0x00, 0xFF) & 0xFC) | 0x02
    mac_bytes = [first_byte] + [random.randint(0x00, 0xFF) for _ in range(5)]
    return ":".join(f"{b:02x}" for b in mac_bytes)

def generate_phone_identity():
    dev = random.choice(MODELS)
    op = random.choice(OPERATORS)
    imei = generate_luhn_imei(tac_prefix=random.choice(["35", "86", "99", "01"]))
    android_id = generate_android_id()
    mac = generate_mac_address()
    
    phone_number = f"+9989{random.choice(['0','1','3','4','7','8','9'])}{random.randint(1000000, 9999999)}"
    imsi = f"{op['mcc']}{op['mnc']}" + "".join([str(random.randint(0, 9)) for _ in range(10)])
    sim_serial = f"89998{op['mnc']}" + "".join([str(random.randint(0, 9)) for _ in range(13)])

    return {
        "manufacturer": dev["manufacturer"],
        "model": dev["model"],
        "display_name": dev["pname"],
        "imei": imei,
        "android_id": android_id,
        "mac": mac,
        "phone_number": phone_number,
        "imsi": imsi,
        "sim_serial": sim_serial,
        "sim_operator": op["sim"],
        "network_operator": op["operator"],
        "mcc": op["mcc"],
        "mnc": op["mnc"],
        "cpu_cores": 2,
        "ram_mb": 2048,
        "width": 720,
        "height": 1280,
        "dpi": 320
    }

if __name__ == "__main__":
    ident = generate_phone_identity()
    import json
    print(json.dumps(ident, indent=2))
