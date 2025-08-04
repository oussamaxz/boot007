import requests
import json
import time
import os
from concurrent.futures import ThreadPoolExecutor

# ===== بيانات بوت فيسبوك =====
FACEBOOK_PAGE_ACCESS_TOKEN = 'EAAYORJKXFboBPOfCAz2chZC5ptE5ZBGhAtZAE6I8NzZCWnrLDZCpve5ZBKxiDH05r9ZBsyjx3wkJUvI5Ts2qZBto5pAudgxAFfJXM263qlHDZCBkMbdgBi3Kkpfb9w1BBZCdb5BkQyeZBrZAjBGnrEWa51Q6GD3JC06C5b3LjySjhuIWnZAqEjFpZAIwJX3lEVW3bcIY76O3NIFZAkiiQZDZD'
FACEBOOK_GRAPH_API_URL = 'https://graph.facebook.com/v11.0/me/messages'

# ===== API لتوليد الصور =====
AI_IMAGE_API = "http://185.158.132.66:2010/api/tnt/tnt-black-image"

# ===== ملفات البيانات (تحذيرات وحظر) =====
DATA_FILE = "facebook_users_data.json"

if os.path.exists(DATA_FILE):
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
else:
    data = {"warnings": {}, "banned": {}}

warnings = data["warnings"]
banned_users = data["banned"]

# ===== قائمة 30 كلمة مسيئة =====
bad_words = [
    "سكس","نيك","طيز","سوة","زنجي","عارية","كس","زبر","زب","قحبة",
    "شرموطة","لعق","مص","بزازل","بزاز","ممحونة","مفشخة","فرج","عاهرة","خنزير",
    "لوطي","شاذ","قذر","حيوان","شرج","جنس","اباحي","اغتصاب","مني","ممارسة"
]

BAN_DURATION = 7 * 24 * 60 * 60  # أسبوع

# ===== حفظ البيانات =====
def save_data():
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump({"warnings": warnings, "banned": banned_users}, f)

# ===== إرسال رسالة نصية =====
def send_facebook_message(user_id, message_text, quick_replies=None):
    url = FACEBOOK_GRAPH_API_URL
    params = {"access_token": FACEBOOK_PAGE_ACCESS_TOKEN}
    headers = {"Content-Type": "application/json"}
    
    data = {
        "recipient": {"id": user_id},
        "message": {"text": message_text}
    }
    if quick_replies:
        data["message"]["quick_replies"] = quick_replies

    requests.post(url, params=params, headers=headers, data=json.dumps(data))

# ===== إرسال صورة من API =====
def send_facebook_image(user_id, image_url, caption=""):
    url = FACEBOOK_GRAPH_API_URL
    params = {"access_token": FACEBOOK_PAGE_ACCESS_TOKEN}
    headers = {"Content-Type": "application/json"}
    
    data = {
        "recipient": {"id": user_id},
        "message": {
            "attachment": {
                "type": "image",
                "payload": {"url": image_url, "is_reusable": True}
            }
        }
    }
    requests.post(url, params=params, headers=headers, data=json.dumps(data))
    if caption:
        send_facebook_message(user_id, caption)

# ===== استخدام API الخارجي لتوليد صورة تحذير/حظر =====
def generate_alert_image(text):
    try:
        payload = {"User-Prompt": text}
        response = requests.post(AI_IMAGE_API, json=payload, timeout=15)
        if response.status_code == 200:
            images = response.json().get("url-image", [])
            return images[0] if images else None
    except:
        return None
    return None

# ===== معالجة الرسائل =====
def handle_message(sender_id, message_text):
    user_id = str(sender_id)
    text = message_text.lower()

    # ✅ التحقق من الحظر
    if user_id in banned_users:
        if time.time() < banned_users[user_id]:
            send_facebook_message(sender_id, "🚫 تم حظرك لمدة أسبوع بسبب رسائل مسيئة.")
            return
        else:
            del banned_users[user_id]
            warnings[user_id] = 0
            save_data()

    # ✅ التحقق من الكلمات المسيئة
    if any(word in text for word in bad_words):
        warnings[user_id] = warnings.get(user_id, 0) + 1
        save_data()

        if warnings[user_id] < 3:
            img_url = generate_alert_image(f"⚠️ تحذير {warnings[user_id]}/3 - توقف عن إرسال رسائل مسيئة")
            if img_url:
                send_facebook_image(sender_id, img_url, caption=f"⚠️ تحذير {warnings[user_id]}/3: تجنب الكلمات المسيئة!")
            else:
                send_facebook_message(sender_id, f"⚠️ تحذير {warnings[user_id]}/3: تجنب الكلمات المسيئة!")
        else:
            banned_users[user_id] = time.time() + BAN_DURATION
            save_data()
            img_url = generate_alert_image("⛔ تم حظرك لمدة أسبوع بسبب الرسائل المسيئة")
            if img_url:
                send_facebook_image(sender_id, img_url, caption="⛔ لقد تم حظرك لمدة أسبوع.")
            else:
                send_facebook_message(sender_id, "⛔ لقد تم حظرك لمدة أسبوع بسبب تكرار المخالفات.")
        return

    # ✅ إذا الرسالة عادية يتم توليد صورة حسب النص
    if text in ["سلام", "مرحبا", "hi", "hello"]:
        send_facebook_message(sender_id,
            "👋 أهلاً بك! نحن نقوم بتوليد صور مذهلة من وصفك. أرسل أي نص أو رمز وسنحوّل خيالك إلى واقع 🤯")
        return

    send_facebook_message(sender_id, "⏳ جاري إنشاء الصورة، انتظر قليلاً...")
    images = generate_alert_image(text)

    if images:
        send_facebook_image(sender_id, images, caption="اكتب كلمة «المزيد» لي استكشاف 🤓")
    else:
        send_facebook_message(sender_id, "❌ حدث خطأ أثناء توليد الصورة، حاول مرة أخرى.")

# ===== نظام Polling لفحص الرسائل =====
def poll_facebook_messages():
    last_checked = int(time.time())
    processed_ids = set()

    with ThreadPoolExecutor(max_workers=10) as executor:
        while True:
            try:
                url = f"https://graph.facebook.com/v11.0/me/conversations?fields=messages.limit(1){{message,from,id}}&since={last_checked}&access_token={FACEBOOK_PAGE_ACCESS_TOKEN}"
                response = requests.get(url)
                response.raise_for_status()
                conversations = response.json().get('data', [])

                for convo in conversations:
                    for msg in convo['messages']['data']:
                        msg_id = msg['id']
                        if msg_id not in processed_ids:
                            sender = msg['from']['id']
                            text = msg.get('message', '')
                            print(f"[MSG] من {sender} : {text}")
                            executor.submit(handle_message, sender, text)
                            processed_ids.add(msg_id)

            except Exception as e:
                print("⚠️ خطأ في Polling:", e)

            last_checked = int(time.time())
            time.sleep(2)

# ===== تشغيل البوت =====
poll_facebook_messages()
