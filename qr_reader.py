import os
import sys
import glob
import cv2
import requests

BASE_DIR = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))

def get_latest_qr_image(folder=None):
    """Find the most recent image in the folder."""
    if folder is None:
        folder = BASE_DIR
    patterns = ["*.jpg", "*.jpeg", "*.png", "*.bmp", "*.webp"]
    images = []
    for pat in patterns:
        images.extend(glob.glob(os.path.join(folder, pat)))
    if not images:
        return None
    # Sort by modification time descending
    images.sort(key=os.path.getmtime, reverse=True)
    return images[0]

def decode_qr(image_path=None):
    """
    Decodes the QR code from the specified or latest image.
    Returns (raw_url, final_url, package_name)
    """
    if image_path is None:
        image_path = get_latest_qr_image()
    if not image_path or not os.path.exists(image_path):
        raise FileNotFoundError(f"QR kod rasmi topilmadi: {image_path}")

    img = cv2.imread(image_path)
    if img is None:
        raise ValueError(f"Rasmni o'qib bo'lmadi: {image_path}")

    detector = cv2.QRCodeDetector()
    val, pts, _ = detector.detectAndDecode(img)
    if not val:
        # Try OpenCV WeChat QRCode or grayscale / thresholding if needed
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        val, pts, _ = detector.detectAndDecode(gray)
        if not val:
            raise ValueError(f"Rasmdan QR kod o'qib bo'lmadi: {image_path}")

    raw_url = val.strip()
    
    # Trace redirect to resolve Play Store / final landing page
    final_url = raw_url
    package_name = None
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Linux; Android 13; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36'
        }
        resp = requests.get(raw_url, headers=headers, allow_redirects=True, timeout=10)
        final_url = resp.url
        if 'id=' in final_url:
            package_name = final_url.split('id=')[-1].split('&')[0]
    except Exception as e:
        print(f"[QR Scanner] Redirectni kuzatishda ogohlantirish: {e}")

    return {
        "image_file": os.path.basename(image_path),
        "raw_url": raw_url,
        "final_url": final_url,
        "package_name": package_name or "com.baxtiyorov.security"
    }

if __name__ == "__main__":
    res = decode_qr()
    print("Skaner natijasi:")
    print("Rasm:", res["image_file"])
    print("Referal havola:", res["raw_url"])
    print("Final havola:", res["final_url"])
    print("Ilova paketi:", res["package_name"])
