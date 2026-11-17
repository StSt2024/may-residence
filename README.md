# مي رزدنيس | May Residence 107-2

صفحة تفاعلية لمخططات الشقق وأسعارها: 111 شقة في 3 مبانٍ و4 أدوار (الأرضي، الأول، الثاني، الملحق).

## المحتوى

| المجلد | الوصف |
|---|---|
| `site/` | الصفحة: `index.html` و`data.js` (بيانات الوحدات والمخططات)، و`plans/` (مخطط كل شقة بصيغة SVG) |
| `source/` | ملف المخططات الأصلي (PDF) وشعار المشروع |
| `tools/` | سكربتات Python اللي استخرجت المخططات والبيانات من ملف الـPDF |

## التشغيل محليًا

```bash
cd site
python3 -m http.server 8000
# افتح http://localhost:8000
```

## ملاحظات

- حالة الوحدات (متاحة/محجوزة) وتعديل الأسعار وحفظ ورقة الطباعة PDF تعتمد على خدمات صفحة Claude المنشورة (قاعدة البيانات والتنزيل).
  لما تُفتح الصفحة من مكان ثاني (GitHub Pages أو سيرفر خاص) تشتغل كعرض فقط بالأسعار الأصلية، وما يظهر زر الطباعة.
- كلمة مرور وضع الموظف محفوظة في الصفحة كـ SHA-256، وهي حماية واجهة فقط.

## إعادة توليد البيانات من الـPDF

```bash
pip install pymupdf opencv-python numpy potracer
python3 tools/extract.py source/apartment-plans-107-2.pdf out      # مخططات الشقق + units.json
python3 tools/floors.py  source/apartment-plans-107-2.pdf out/floors.json  # حدود الوحدات ومخطط كل دور
```
ثم يُبنى `data.js` بدمج `units.json` و`floors.json`.
