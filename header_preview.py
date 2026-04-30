"""
header_preview.py
إنشاء صورة Header احترافية مع الشعارات الوطنية
يمكن حذف هذا الملف بعد المعاينة بدون تأثر البرنامج
"""

from PIL import Image, ImageDraw, ImageFont
import os

# الحصول على مسار المجلد الحالي
current_dir = os.path.dirname(os.path.abspath(__file__))

# مسارات الصور
eagle_path = os.path.join(current_dir, "png-clipart-kingdom-of-egypt-flag-of-egypt-coat-of-arms-of-egypt-egypt-flag-egypt-thumbnail.png")
health_path = os.path.join(current_dir, "unnamed.jpg")
vision_path = os.path.join(current_dir, "2030Egypts_vision_fda-768x377.png")

# إنشاء صورة جديدة
width = 1400
height = 150
header_image = Image.new('RGB', (width, height), color='#1a1a2e')

# حفظ الصورة الأساسية
draw = ImageDraw.Draw(header_image)

# رسم حد ذهبي في الأسفل
draw.line([(0, height-2), (width, height-2)], fill='#D4AF37', width=2)

# ============================================
# محاولة فتح الصور وإضافتها
# ============================================

try:
    # فتح صورة النسر (اليمين)
    if os.path.exists(eagle_path):
        eagle = Image.open(eagle_path).convert('RGBA')
        # تغيير الحجم
        eagle = eagle.resize((80, 80), Image.Resampling.LANCZOS)
        # إضافة الصورة
        header_image.paste(eagle, (100, 35), eagle)
        print("✓ تم إضافة شعار النسر")
    else:
        print("⚠ صورة النسر غير موجودة")
except Exception as e:
    print(f"✗ خطأ في صورة النسر: {e}")

try:
    # فتح صورة وزارة الصحة (اليسار)
    if os.path.exists(health_path):
        health = Image.open(health_path).convert('RGBA')
        # تغيير الحجم
        health = health.resize((80, 80), Image.Resampling.LANCZOS)
        # إضافة الصورة من اليسار
        health_x = width - 100 - 80
        header_image.paste(health, (health_x, 35), health)
        print("✓ تم إضافة شعار وزارة الصحة")
    else:
        print("⚠ صورة وزارة الصحة غير موجودة")
except Exception as e:
    print(f"✗ خطأ في صورة وزارة الصحة: {e}")

try:
    # فتح صورة رؤية 2030 (الوسط)
    if os.path.exists(vision_path):
        vision = Image.open(vision_path).convert('RGBA')
        # تغيير الحجم
        vision = vision.resize((120, 60), Image.Resampling.LANCZOS)
        # إضافة الصورة في الوسط
        vision_x = (width - 120) // 2
        header_image.paste(vision, (vision_x, 45), vision)
        print("✓ تم إضافة شعار رؤية مصر 2030")
    else:
        print("⚠ صورة رؤية 2030 غير موجودة")
except Exception as e:
    print(f"✗ خطأ في صورة رؤية 2030: {e}")

# ============================================
# إضافة النصوص
# ============================================

try:
    # محاولة استخدام خط عربي (إذا لم يتوفر، سيستخدم الخط الافتراضي)
    try:
        font_large = ImageFont.truetype("arial.ttf", 16)
        font_small = ImageFont.truetype("arial.ttf", 12)
    except:
        font_large = ImageFont.load_default()
        font_small = ImageFont.load_default()

    # نص جمهورية مصر العربية (اليمين)
    draw.text((190, 100), "جمهورية مصر العربية", fill='#D4AF37', font=font_large)
    
    # نص وزارة الصحة والسكان (اليسار)
    draw.text((width - 190, 100), "وزارة الصحة والسكان", fill='#D4AF37', font=font_large)
    
    print("✓ تم إضافة النصوص")
except Exception as e:
    print(f"✗ خطأ في إضافة النصوص: {e}")

# ============================================
# حفظ الصورة
# ============================================

output_path = os.path.join(current_dir, "header_preview.png")
header_image.save(output_path)
print(f"\n✓ تم إنشاء الصورة بنجاح!")
print(f"📍 المسار: {output_path}")
print(f"📏 الحجم: {width}x{height} بكسل")
print("\n💡 يمكنك الآن:")
print("  1. فتح الصورة ومعاينتها")
print("  2. إذا أعجبتك، نطبقها في المشروع")
print("  3. إذا لم تعجبك، احذف هذا الملف (header_preview.py)")
print("  4. Dashboard الأصلي سيبقى كما هو 100%")