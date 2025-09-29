
# منصة الواجبات والدرجات (Flask)

## التشغيل محليًا
```bash
python -m venv venv && source venv/bin/activate  # على ويندوز: venv\Scripts\activate
pip install -r requirements.txt
export ADMIN_CODE=ostad-secret             # على ويندوز: set ADMIN_CODE=ostad-secret
export SECRET_KEY=your-secret-key          # على ويندوز: set SECRET_KEY=your-secret-key
python app.py
# افتح http://127.0.0.1:5000
```

## النشر على Render (سهل ومجاني)
1. ارفع هذا المشروع إلى GitHub.
2. على Render: Create New -> Web Service -> اختر الريبو.
3. Build command: `pip install -r requirements.txt`
4. Start command: `gunicorn app:app`
5. أضف متغيرات البيئة: `ADMIN_CODE` و `SECRET_KEY`.
6. انشر.

## النشر على Railway
1. اربط حساب GitHub واختر هذا المشروع.
2. Procfile موجود: `web: gunicorn app:app`
3. أضف env vars: `ADMIN_CODE`, `SECRET_KEY`.

## ملفات مهمة
- `app.py`: الكود الرئيسي للتطبيق.
- `requirements.txt`: الحزم المطلوبة.
- `Procfile`: أمر التشغيل لـ gunicorn على منصات PaaS.
- المجلد `uploads/` سيُنشأ تلقائيًا وقت التشغيل (لا ترفعه إلى Git).
