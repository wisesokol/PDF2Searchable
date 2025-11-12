import sys
import os
from pathlib import Path
sys.path.append(r'c:\Esphome\PDF')

import fitz
import cv2
import numpy as np
from paddleocr import PaddleOCR
from ocr_utils_fixed import TechnicalOCRProcessor
import json


INPUT = r'c:\Esphome\OCR\PDF rezerv\0100.pdf'
OUTPUT = r'c:\Esphome\OCR\PDF rezerv\0100_searchable.pdf'


def analyze_page_content(page):
    """Analyze page content and determine its type"""
    try:
        # Получаем текст страницы
        page_text = page.get_text()
        text_length = len(page_text.strip())
        
        # Получаем изображения
        image_list = page.get_images()
        image_count = len(image_list)
        
        # Получаем все объекты страницы
        page_dict = page.get_contents()
        if not page_dict:
            return "empty"
        
        # Анализируем содержимое страницы
        text_objects = 0
        image_objects = 0
        vector_objects = 0
        
        # Получаем все объекты страницы
        for obj in page.get_contents():
            if obj is None:
                continue
                
            # Анализируем тип объекта
            if hasattr(obj, 'get_text'):
                text_objects += 1
            elif hasattr(obj, 'get_pixmap'):
                image_objects += 1
            else:
                vector_objects += 1
        
        # Определяем тип страницы
        if image_count > 0 and text_length < 50:
            return "scanned_image"  # Сканированное изображение
        elif image_count > 0 and text_length > 50:
            return "mixed_content"  # Смешанный контент
        elif text_length > 100:
            return "text_based"  # Текстовый документ
        elif vector_objects > text_objects:
            return "vector_based"  # Векторная графика
        else:
            return "unknown"
            
    except Exception as e:
        print(f"Page analysis error: {e}")
        return "unknown"


def process_pdf(input_path: str,
                output_path: str,
                hide_text: bool = False,
                flip_x: bool = False,
                flip_y: bool = True,
                top_shift_px: float = 20.0,
                font_size: int = 8,
                dump_debug_first_page: bool = True,
                dpi: int = 300,
                log_callback=None):
    """Process a PDF and produce a searchable PDF using PaddleOCR."""

    def log_message(msg):
        """Log message using callback or print"""
        if log_callback:
            log_callback(msg)
        else:
            print(msg)

    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Input file not found: {input_path}")

    # ✅ Инициализация OCR с локальными моделями (как в test.py)
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        models_dir = os.path.join(base_dir, 'models')
        det_dir = os.path.join(models_dir, 'det')
        rec_dir = os.path.join(models_dir, 'rec')
        textline_ori_dir = os.path.join(models_dir, 'textline_ori')  # для textline orientation
        doc_orient_dir = os.path.join(models_dir, 'doc_orient')  # для document orientation
        UVDoc = os.path.join(models_dir, 'UVDoc')  # для doc unwarping

        
        ocr_kwargs = {
            'text_detection_model_dir': det_dir,
            'text_recognition_model_dir': rec_dir,
            'textline_orientation_model_dir': textline_ori_dir,
            'doc_orientation_classify_model_dir': doc_orient_dir,
            'doc_unwarping_model_dir': UVDoc,
            'use_doc_unwarping': False,
            'use_textline_orientation': True,
            'use_doc_orientation_classify': True,
            #'lang': 'en',
        }


        ocr = PaddleOCR(**ocr_kwargs)
    except Exception as e:
        print(f"Failed to initialize PaddleOCR with local models: {e}")
        print("Trying with default models...")
        try:
            ocr = PaddleOCR(use_textline_orientation=True, lang='en')
        except Exception as e2:
            raise RuntimeError(f"Failed to initialize PaddleOCR: {e2}")

    processor = TechnicalOCRProcessor()
    FONT_SIZE = 4

    doc = fitz.open(input_path)
    new_doc = fitz.open()
    total_pages = len(doc)
    total_blocks = 0

    for i in range(total_pages):
        FONT_SIZE = 8
        page = doc[i]
        
        # Analyze page content type
        page_type = analyze_page_content(page)
        log_message(f"📄 Page {i+1}: type = {page_type}")
        
        mat = fitz.Matrix(dpi / 72, dpi / 72)
        pix = page.get_pixmap(matrix=mat)
        img_data = pix.tobytes('png')

        nparr = np.frombuffer(img_data, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        # Сырые результаты для отладки
        raw_ret = []
        try:
            raw_ret = ocr.ocr(img)
        except Exception:
            raw_ret = []

        if dump_debug_first_page and i == 0:
            try:
                input_basename = os.path.splitext(os.path.basename(input_path))[0]
                raw_dbg = os.path.join(os.path.dirname(input_path), f'{input_basename}_page1_ocr_raw.txt')
                with open(raw_dbg, 'w', encoding='utf-8') as fh:
                    fh.write(repr(raw_ret))
                print(f"  Wrote raw OCR dump: {raw_dbg}")
            except Exception:
                pass

        # ⚙️ Process page (includes vertical text correction)
        log_message(f"📄 Processing page {i+1}/{total_pages}")
        ocr_results = processor.process_page_ocr(img, ocr)
        
        # 🔧 Определяем угол поворота из сырых результатов OCR
        rotation_angle = 0
        if raw_ret and isinstance(raw_ret, list) and len(raw_ret) > 0:
            if isinstance(raw_ret[0], dict) and 'doc_preprocessor_res' in raw_ret[0]:
                doc_preprocessor = raw_ret[0]['doc_preprocessor_res']
                if 'angle' in doc_preprocessor:
                    rotation_angle = doc_preprocessor['angle']
                    log_message(f"  Detected rotation angle: {rotation_angle} degrees")
                    if rotation_angle in [90, 270]:
                        log_message(f"  Auto-applying flip operations for vertical page")
                    elif rotation_angle == 180:
                        log_message(f"  Auto-applying flip operations for 180° rotated page")
                    elif rotation_angle == 270:
                        log_message(f"  Auto-applying flip operations for 270° rotated page")
        log_message(f"  OCR blocks: {len(ocr_results)}")

        if dump_debug_first_page and i == 0:
            try:
                input_basename = os.path.splitext(os.path.basename(input_path))[0]
                dbg_path = os.path.join(os.path.dirname(input_path), f'{input_basename}_page1_ocr_normalized.json')
                with open(dbg_path, 'w', encoding='utf-8') as fh:
                    json.dump(ocr_results, fh, ensure_ascii=False, indent=2)
                print(f"  Wrote debug normalized OCR: {dbg_path}")
            except Exception:
                pass
        total_blocks += len(ocr_results)

        # Создаем новую страницу
        new_page = new_doc.new_page(width=page.rect.width, height=page.rect.height)

        # Apply different algorithms depending on page type
        if page_type == "vector_based":
            log_message(f"  🔧 Using precise positioning for vector graphics")
            # Сложная логика с pikepdf для точного позиционирования (строки 124-231 из оригинала)
            import pikepdf
            import tempfile

            # Получаем оригинальные размеры через fitz (points)
            _tmp_doc = fitz.open(input_path)
            _src_page_for_size = _tmp_doc[i]
            src_w, src_h = _src_page_for_size.rect.width, _src_page_for_size.rect.height
            _tmp_doc.close()

            # Подбираем запас (margin) — минимум 72pt (1"), плюс небольшой процент размера страницы
            margin_x = max(300, src_w * 0.12)   # запас по горизонтали (влево и вправо)
            margin_y = max(300, src_h * 0.12)   # запас по вертикали (вверх и вниз)

            # Создаём временный файл и копируем в него страницу, меняя MediaBox
            tmp_no_crop = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
            tmp_no_crop_path = tmp_no_crop.name
            tmp_no_crop.close()

            with pikepdf.open(input_path) as src_pdf:
                new_pdf = pikepdf.Pdf.new()
                new_pdf.pages.append(src_pdf.pages[i])
                pg = new_pdf.pages[0].obj

                # Удаляем обрезающие box'ы, если есть
                for key in ("/CropBox", "/TrimBox", "/BleedBox", "/ArtBox"):
                    if key in pg:
                        try:
                            del pg[key]
                        except Exception:
                            pass

                # Устанавливаем расширенную MediaBox: двустороннее расширение
                # MediaBox = [llx lly urx ury]
                new_llx = -margin_x
                new_lly = -margin_y
                new_urx = src_w + margin_x
                new_ury = src_h + margin_y
                pg["/MediaBox"] = pikepdf.Array([new_llx, new_lly, new_urx, new_ury])

                new_pdf.save(tmp_no_crop_path)

            # Открываем модифицированный PDF через fitz и уменьшаем страницу
            src_full = fitz.open(tmp_no_crop_path)
            full_page = src_full[0]
            full_w, full_h = full_page.rect.width, full_page.rect.height

            # Настройки позиционирования для разных углов поворота
            # 90 уже настроен корректно у вас — сохраняем его поведение
            if rotation_angle == 90:
                page_scale = 1.22
                image_offset_x = -22
                image_offset_y = -275
                rotate_param = rotation_angle  # сохраняем прежний поворот
            elif rotation_angle == 0: # Настроен для 0, проверен
                # блок для 0°
                page_scale = 1
                image_offset_x = 0
                image_offset_y = 0
                rotate_param = 0
            elif rotation_angle == 180:
                # блок для 180°
                page_scale = 1
                image_offset_x = 0
                image_offset_y = 0
                rotate_param = 0
            elif rotation_angle == 270: # Настроен для 270, проверен
                # блок для 270°
                page_scale = 1.22
                image_offset_x = -22
                image_offset_y = -275
                rotate_param = (-rotation_angle)
            else:
                # дефолтные параметры для других углов
                page_scale = 1.22
                image_offset_x = -22
                image_offset_y = -275
                rotate_param = (rotation_angle)

            scaled_w = full_w * page_scale
            scaled_h = full_h * page_scale

            # Создаём временный документ, куда отрисуем всю расширенную страницу в уменьшенном виде
            scaled_doc = fitz.open()
            scaled_page = scaled_doc.new_page(width=scaled_w, height=scaled_h)
            target_rect = fitz.Rect(0, 0, scaled_w, scaled_h)

            # Рисуем ВСЮ страницу (clip=None) — теперь MediaBox расширена, поэтому ничего не обрежется
            scaled_page.show_pdf_page(target_rect, src_full, 0, clip=None)

            # Вставляем в итоговый документ (как в вашем основном потоке)
            # new_page уже создан выше

            adjusted_rect = fitz.Rect(
                (page.rect.width - scaled_w) / 2 + image_offset_x,
                (page.rect.height - scaled_h) / 2 + image_offset_y,
                (page.rect.width - scaled_w) / 2 + image_offset_x + scaled_w,
                (page.rect.height - scaled_h) / 2 + image_offset_y + scaled_h
            )

            # Сохраняем прежнюю логику поворота при вставке
            new_page.show_pdf_page(adjusted_rect, scaled_doc, 0, rotate=rotate_param)

            # Закрываем временные документы и удаляем временный файл
            src_full.close()
            scaled_doc.close()
            try:
                os.remove(tmp_no_crop_path)
            except Exception:
                pass
            # ---- END ----
            
            # === Добавляем OCR текст для vector_based ===
            if hide_text:
                # Сначала вставляем скрытый текст ПОД изображением
                for line in ocr_results:
                    try:
                        if not (isinstance(line, (list, tuple)) and len(line) >= 2):
                            continue
                        bbox = line[0]
                        text_info = line[1]
                        text = text_info[0] if isinstance(text_info, (list, tuple)) and len(text_info) >= 1 else str(text_info)
                        xs = [float(pt[0]) for pt in bbox]
                        ys = [float(pt[1]) for pt in bbox]
                        xmin, xmax = min(xs), max(xs)
                        ymin, ymax = min(ys), max(ys)
                        
                        # 🔧 Коррекция координат с учетом поворота изображения
                        if rotation_angle in [90, 270]:
                            # При повороте на 90 градусов по часовой стрелке:
                            # координаты текста даны в повернутой системе координат
                            # нужно преобразовать их обратно к исходной системе
                            orig_width, orig_height = img.shape[1], img.shape[0]
                            # Поворачиваем координаты обратно на -90 градусов
                            # При повороте на -90 градусов: (x,y) -> (y, width-x)
                            new_xmin = ymin
                            new_xmax = ymax
                            new_ymin = orig_width - xmax
                            new_ymax = orig_width - xmin
                            xmin, xmax, ymin, ymax = new_xmin, new_xmax, new_ymin, new_ymax
                        elif rotation_angle == 270:
                            # При повороте на 270 градусов (против часовой стрелки):
                            # координаты текста даны в повернутой системе координат
                            # нужно преобразовать их обратно к исходной системе
                            orig_width, orig_height = img.shape[1], img.shape[0]
                            # Поворачиваем координаты обратно на -270 градусов (по часовой стрелке на 90)
                            # При повороте на 90 градусов: (x,y) -> (y, width-x)
                            new_xmin = ymin
                            new_xmax = ymax
                            new_ymin = orig_width - xmax
                            new_ymax = orig_width - xmin
                            xmin, xmax, ymin, ymax = new_xmin, new_xmax, new_ymin, new_ymax
                            
                            # 🔧 Смещение текста вверх для вертикальных страниц
                            y_offset = orig_height *-0.48  # Смещение на -52% высоты вверх
                            ymin += y_offset
                            ymax += y_offset
                        
                        scale_x = page.rect.width / img.shape[1]
                        scale_y = page.rect.height / img.shape[0]
                        
                        # 🔧 Для страниц с вертикальными блоками автоматически применяем flip операции
                        if rotation_angle == 90:
                            # Для вертикальных страниц (90°) применяем flip операции
                            px1 = page.rect.width - (xmin * scale_x)
                            px2 = page.rect.width - (xmax * scale_x)
                            py1 = page.rect.height - (ymin * scale_y)
                            py2 = page.rect.height - (ymax * scale_y)
                            
                            # 🔧 Смещение текста вниз для вертикальных страниц после flip
                            y_offset = page.rect.height * 0.43  # Смещение на 40% высоты вниз
                            py1 += y_offset
                            py2 += y_offset
                            
                            # 🔧 Применяем top_shift_px только для блоков выше середины листа
                            page_middle = page.rect.height / 2
                            if min(py1, py2) < page_middle:
                                py1 -= top_shift_px
                                py2 -= top_shift_px
                        elif rotation_angle == 270:
                            # Для страниц с поворотом 270° НЕ применяем flip операции
                            px1 = xmin * scale_x
                            px2 = xmax * scale_x
                            py1 = ymin * scale_y
                            py2 = ymax * scale_y
                            
                            # 🔧 Смещение текста вверх для 270° на уровне страницы
                            y_offset_page = page.rect.height * -0.48  # Смещение на -52% высоты вверх
                            py1 += y_offset_page
                            py2 += y_offset_page
                            
                            # 🔧 Применяем top_shift_px только для блоков выше середины листа
                            page_middle = page.rect.height / 2
                            if min(py1, py2) < page_middle:
                                py1 -= top_shift_px
                                py2 -= top_shift_px
                        elif rotation_angle == 180:
                            # Для страниц с поворотом 180° принудительно применяем flip операции
                            px1 = page.rect.width - (xmin * scale_x)
                            px2 = page.rect.width - (xmax * scale_x)
                            py1 = page.rect.height - (ymin * scale_y)
                            py2 = page.rect.height - (ymax * scale_y)
                            
                            # 🔧 Применяем top_shift_px только для блоков выше середины листа
                            page_middle = page.rect.height / 2
                            if min(py1, py2) < page_middle:
                                # Для листов с rotation 180° добавляем поправку +13 к top_shift_px
                                adjusted_shift = top_shift_px + 23
                                py1 -= adjusted_shift
                                py2 -= adjusted_shift
                        else:
                            # Для обычных страниц применяем flip операции согласно настройкам GUI
                            if flip_x:
                                px1 = page.rect.width - (xmin * scale_x)
                                px2 = page.rect.width - (xmax * scale_x)
                            else:
                                px1 = xmin * scale_x
                                px2 = xmax * scale_x
                            if flip_y:
                                py1 = page.rect.height - (ymin * scale_y)
                                py2 = page.rect.height - (ymax * scale_y)
                            else:
                                py1 = ymin * scale_y
                                py2 = ymax * scale_y
                        
                        # 🔧 Применяем top_shift_px только для блоков выше середины листа
                        page_middle = page.rect.height / 2
                        if min(py1, py2) < page_middle:
                            py1 -= top_shift_px
                            py2 -= top_shift_px
                        
                        left = min(px1, px2)
                        right = max(px1, px2)
                        top = min(py1, py2)
                        bottom = max(py1, py2)
                        rect = fitz.Rect(left, top, right, bottom)
                        new_page.insert_text(rect.tl, text, fontsize=font_size, color=(0, 0, 0), render_mode=3)
                    except Exception:
                        continue
            else:
                # Видимый текст поверх изображения
                for line in ocr_results:
                    try:
                        if not (isinstance(line, (list, tuple)) and len(line) >= 2):
                            continue
                        bbox = line[0]
                        text_info = line[1]
                        text = text_info[0] if isinstance(text_info, (list, tuple)) and len(text_info) >= 1 else str(text_info)
                        xs = [float(pt[0]) for pt in bbox]
                        ys = [float(pt[1]) for pt in bbox]
                        xmin, xmax = min(xs), max(xs)
                        ymin, ymax = min(ys), max(ys)
                        
                        # 🔧 Коррекция координат с учетом поворота изображения
                        if rotation_angle == 90:
                            # При повороте на 90 градусов по часовой стрелке:
                            # координаты текста даны в повернутой системе координат
                            # нужно преобразовать их обратно к исходной системе
                            orig_width, orig_height = img.shape[1], img.shape[0]
                            # Поворачиваем координаты обратно на -90 градусов
                            # При повороте на -90 градусов: (x,y) -> (y, width-x)
                            new_xmin = ymin
                            new_xmax = ymax
                            new_ymin = orig_width - xmax
                            new_ymax = orig_width - xmin
                            xmin, xmax, ymin, ymax = new_xmin, new_xmax, new_ymin, new_ymax
                            
                            # 🔧 Смещение текста вниз для вертикальных страниц
                            y_offset = orig_height * 0.3  # Смещение на 30% высоты вниз
                            ymin += y_offset
                            ymax += y_offset
                        elif rotation_angle == 270:
                            # При повороте на 270 градусов (против часовой стрелки):
                            # координаты текста даны в повернутой системе координат
                            # нужно преобразовать их обратно к исходной системе
                            orig_width, orig_height = img.shape[1], img.shape[0]
                            # Поворачиваем координаты обратно на -270 градусов (по часовой стрелке на 90)
                            # При повороте на 90 градусов: (x,y) -> (y, width-x)
                            new_xmin = ymin
                            new_xmax = ymax
                            new_ymin = orig_width - xmax
                            new_ymax = orig_width - xmin
                            xmin, xmax, ymin, ymax = new_xmin, new_xmax, new_ymin, new_ymax
                        
                        scale_x = page.rect.width / img.shape[1]
                        scale_y = page.rect.height / img.shape[0]
                        
                        # 🔧 Для страниц с вертикальными блоками автоматически применяем flip операции
                        if rotation_angle == 90:
                            # Для вертикальных страниц (90°) применяем flip операции
                            px1 = page.rect.width - (xmin * scale_x)
                            px2 = page.rect.width - (xmax * scale_x)
                            py1 = page.rect.height - (ymin * scale_y)
                            py2 = page.rect.height - (ymax * scale_y)
                            
                            # 🔧 Смещение текста вниз для вертикальных страниц после flip
                            y_offset = page.rect.height * 0.54  # Смещение на 50% высоты вниз
                            py1 += y_offset
                            py2 += y_offset
                            
                            # 🔧 Применяем top_shift_px только для блоков выше середины листа
                            page_middle = page.rect.height / 2
                            if min(py1, py2) < page_middle:
                                py1 -= top_shift_px
                                py2 -= top_shift_px
                            
                            # 🔧 Дополнительное смещение текста вниз для вертикальных страниц
                            y_offset = page.rect.height * 0.2  # Смещение на 20% высоты вниз
                            py1 += y_offset
                            py2 += y_offset
                        elif rotation_angle == 270:
                            # Для страниц с поворотом 270° НЕ применяем flip операции
                            px1 = xmin * scale_x
                            px2 = xmax * scale_x
                            py1 = ymin * scale_y
                            py2 = ymax * scale_y
                            
                            # 🔧 Смещение текста вверх для 270° на уровне страницы
                            y_offset_page = page.rect.height * -0.48  # Смещение на -52% высоты вверх
                            py1 += y_offset_page
                            py2 += y_offset_page
                            
                            # 🔧 Применяем top_shift_px только для блоков выше середины листа
                            page_middle = page.rect.height / 2
                            if min(py1, py2) < page_middle:
                                py1 -= top_shift_px
                                py2 -= top_shift_px
                        elif rotation_angle == 180:
                            # Для страниц с поворотом 180° принудительно применяем flip операции
                            px1 = page.rect.width - (xmin * scale_x)
                            px2 = page.rect.width - (xmax * scale_x)
                            py1 = page.rect.height - (ymin * scale_y)
                            py2 = page.rect.height - (ymax * scale_y)
                            
                            # 🔧 Применяем top_shift_px только для блоков выше середины листа
                            page_middle = page.rect.height / 2
                            if min(py1, py2) < page_middle:
                                # Для листов с rotation 180° добавляем поправку +13 к top_shift_px
                                adjusted_shift = top_shift_px + 23
                                py1 -= adjusted_shift
                                py2 -= adjusted_shift
                        else:
                            # Для обычных страниц применяем flip операции согласно настройкам GUI
                            if flip_x:
                                px1 = page.rect.width - (xmin * scale_x)
                                px2 = page.rect.width - (xmax * scale_x)
                            else:
                                px1 = xmin * scale_x
                                px2 = xmax * scale_x
                            if flip_y:
                                py1 = page.rect.height - (ymin * scale_y)
                                py2 = page.rect.height - (ymax * scale_y)
                            else:
                                py1 = ymin * scale_y
                                py2 = ymax * scale_y
                        
                        # 🔧 Применяем top_shift_px только для блоков выше середины листа
                        page_middle = page.rect.height / 2
                        if min(py1, py2) < page_middle:
                            py1 -= top_shift_px
                            py2 -= top_shift_px
                        
                        left = min(px1, px2)
                        right = max(px1, px2)
                        top = min(py1, py2)
                        bottom = max(py1, py2)
                        rect = fitz.Rect(left, top, right, bottom)
                        new_page.insert_text(rect.tl, text, fontsize=font_size, color=(0, 0, 0), overlay=True)
                    except Exception as ex:
                        print(f"  Error inserting text: {ex}")
                        continue
        else:
            log_message(f"  🔧 Applying full processing logic for type: {page_type}")
            # Full logic with flips, shifts and rotation
            if hide_text:
                page_is_landscape = page.rect.width >= page.rect.height
                if page_is_landscape:
                    # Сначала вставляем скрытый текст
                    for line in ocr_results:
                        try:
                            if not (isinstance(line, (list, tuple)) and len(line) >= 2):
                                continue
                            bbox = line[0]
                            text_info = line[1]
                            text = text_info[0] if isinstance(text_info, (list, tuple)) and len(text_info) >= 1 else str(text_info)
                            xs = [float(pt[0]) for pt in bbox]
                            ys = [float(pt[1]) for pt in bbox]
                            xmin, xmax = min(xs), max(xs)
                            ymin, ymax = min(ys), max(ys)
                            # 🔧 Коррекция координат с учетом поворота изображения
                            if rotation_angle in [90, 270]:
                                orig_width, orig_height = img.shape[1], img.shape[0]
                                new_xmin = ymin
                                new_xmax = ymax
                                new_ymin = orig_width - xmax
                                new_ymax = orig_width - xmin
                                xmin, xmax, ymin, ymax = new_xmin, new_xmax, new_ymin, new_ymax
                            elif rotation_angle == 270:
                                orig_width, orig_height = img.shape[1], img.shape[0]
                                new_xmin = ymin
                                new_xmax = ymax
                                new_ymin = orig_width - xmax
                                new_ymax = orig_width - xmin
                                xmin, xmax, ymin, ymax = new_xmin, new_xmax, new_ymin, new_ymax
                                y_offset = orig_height *-0.48
                                ymin += y_offset
                                ymax += y_offset
                            scale_x = page.rect.width / img.shape[1]
                            scale_y = page.rect.height / img.shape[0]
                            if rotation_angle == 90:
                                px1 = page.rect.width - (xmin * scale_x)
                                px2 = page.rect.width - (xmax * scale_x)
                                py1 = page.rect.height - (ymin * scale_y)
                                py2 = page.rect.height - (ymax * scale_y)
                                y_offset = page.rect.height * 0.43
                                py1 += y_offset
                                py2 += y_offset
                                page_middle = page.rect.height / 2
                                if min(py1, py2) < page_middle:
                                    py1 -= top_shift_px
                                    py2 -= top_shift_px
                            elif rotation_angle == 270:
                                px1 = xmin * scale_x
                                px2 = xmax * scale_x
                                py1 = ymin * scale_y
                                py2 = ymax * scale_y
                                y_offset_page = page.rect.height * -0.48
                                py1 += y_offset_page
                                py2 += y_offset_page
                                page_middle = page.rect.height / 2
                                if min(py1, py2) < page_middle:
                                    py1 -= top_shift_px
                                    py2 -= top_shift_px
                            elif rotation_angle == 180:
                                px1 = page.rect.width - (xmin * scale_x)
                                px2 = page.rect.width - (xmax * scale_x)
                                py1 = page.rect.height - (ymin * scale_y)
                                py2 = page.rect.height - (ymax * scale_y)
                                page_middle = page.rect.height / 2
                                if min(py1, py2) < page_middle:
                                    adjusted_shift = top_shift_px + 23
                                    py1 -= adjusted_shift
                                    py2 -= adjusted_shift
                            else:
                                if flip_x:
                                    px1 = page.rect.width - (xmin * scale_x)
                                    px2 = page.rect.width - (xmax * scale_x)
                                else:
                                    px1 = xmin * scale_x
                                    px2 = xmax * scale_x
                                if flip_y:
                                    py1 = page.rect.height - (ymin * scale_y)
                                    py2 = page.rect.height - (ymax * scale_y)
                                else:
                                    py1 = ymin * scale_y
                                    py2 = ymax * scale_y
                            page_middle = page.rect.height / 2
                            if min(py1, py2) < page_middle:
                                py1 -= top_shift_px
                                py2 -= top_shift_px
                            left = min(px1, px2)
                            right = max(px1, px2)
                            top = min(py1, py2)
                            bottom = max(py1, py2)
                            rect = fitz.Rect(left, top, right, bottom)
                            new_page.insert_text(rect.tl, text, fontsize=font_size, color=(0, 0, 0), render_mode=3)
                        except Exception:
                            continue
                else:
                    # Портретная ориентация — используем те же правила позиционирования (копия логики)
                    for line in ocr_results:
                        try:
                            if not (isinstance(line, (list, tuple)) and len(line) >= 2):
                                continue
                            bbox = line[0]
                            text_info = line[1]
                            text = text_info[0] if isinstance(text_info, (list, tuple)) and len(text_info) >= 1 else str(text_info)
                            xs = [float(pt[0]) for pt in bbox]
                            ys = [float(pt[1]) for pt in bbox]
                            xmin, xmax = min(xs), max(xs)
                            ymin, ymax = min(ys), max(ys)
                            if rotation_angle in [90, 270]:
                                orig_width, orig_height = img.shape[1], img.shape[0]
                                new_xmin = ymin
                                new_xmax = ymax
                                new_ymin = orig_width - xmax
                                new_ymax = orig_width - xmin
                                xmin, xmax, ymin, ymax = new_xmin, new_xmax, new_ymin, new_ymax
                            elif rotation_angle == 270:
                                orig_width, orig_height = img.shape[1], img.shape[0]
                                new_xmin = ymin
                                new_xmax = ymax
                                new_ymin = orig_width - xmax
                                new_ymax = orig_width - xmin
                                xmin, xmax, ymin, ymax = new_xmin, new_xmax, new_ymin, new_ymax
                                y_offset = orig_height *-0.48
                                ymin += y_offset
                                ymax += y_offset
                            scale_x = page.rect.width / img.shape[1]
                            scale_y = page.rect.height / img.shape[0]
                            if rotation_angle == 90:
                                px1 = page.rect.width - (xmin * scale_x)
                                px2 = page.rect.width - (xmax * scale_x)
                                py1 = page.rect.height - (ymin * scale_y)
                                py2 = page.rect.height - (ymax * scale_y)
                                y_offset = page.rect.height * -0.31
                                py1 += y_offset
                                py2 += y_offset
                                page_middle = page.rect.height / 2
                                if min(py1, py2) < page_middle:
                                    py1 -= top_shift_px
                                    py2 -= top_shift_px
                            elif rotation_angle == 270:
                                px1 = xmin * scale_x
                                px2 = xmax * scale_x
                                py1 = ymin * scale_y
                                py2 = ymax * scale_y
                                y_offset_page = page.rect.height * 0.28
                                py1 += y_offset_page
                                py2 += y_offset_page
                                page_middle = page.rect.height / 2
                                if min(py1, py2) < page_middle:
                                    py1 -= top_shift_px
                                    py2 -= top_shift_px
                            elif rotation_angle == 180:
                                px1 = page.rect.width - (xmin * scale_x)
                                px2 = page.rect.width - (xmax * scale_x)
                                py1 = page.rect.height - (ymin * scale_y)
                                py2 = page.rect.height - (ymax * scale_y)
                                page_middle = page.rect.height / 2
                                if min(py1, py2) < page_middle:
                                    adjusted_shift = top_shift_px + 23
                                    py1 -= adjusted_shift
                                    py2 -= adjusted_shift
                            else:
                                if flip_x:
                                    px1 = page.rect.width - (xmin * scale_x)
                                    px2 = page.rect.width - (xmax * scale_x)
                                else:
                                    px1 = xmin * scale_x
                                    px2 = xmax * scale_x
                                if flip_y:
                                    py1 = page.rect.height - (ymin * scale_y)
                                    py2 = page.rect.height - (ymax * scale_y)
                                else:
                                    py1 = ymin * scale_y
                                    py2 = ymax * scale_y
                            page_middle = page.rect.height / 2
                            if min(py1, py2) < page_middle:
                                py1 -= top_shift_px
                                py2 -= top_shift_px
                            left = min(px1, px2)
                            right = max(px1, px2)
                            top = min(py1, py2)
                            bottom = max(py1, py2)
                            rect = fitz.Rect(left, top, right, bottom)
                            new_page.insert_text(rect.tl, text, fontsize=font_size, color=(0, 0, 0), render_mode=3)
                        except Exception:
                            continue
                # Затем вставляем изображение поверх текста
                new_page.insert_image(page.rect, stream=img_data)
            else:
                page_is_landscape = page.rect.width >= page.rect.height
                # Сначала вставляем изображение
                new_page.insert_image(page.rect, stream=img_data)
                # Затем добавляем видимый текст поверх изображения
                if page_is_landscape:
                    for line in ocr_results:
                        try:
                            if not (isinstance(line, (list, tuple)) and len(line) >= 2):
                                continue
                            bbox = line[0]
                            text_info = line[1]
                            text = text_info[0] if isinstance(text_info, (list, tuple)) and len(text_info) >= 1 else str(text_info)
                            xs = [float(pt[0]) for pt in bbox]
                            ys = [float(pt[1]) for pt in bbox]
                            xmin, xmax = min(xs), max(xs)
                            ymin, ymax = min(ys), max(ys)
                            # 🔧 Коррекция координат с учетом поворота изображения
                            if rotation_angle == 90:
                                orig_width, orig_height = img.shape[1], img.shape[0]
                                new_xmin = ymin
                                new_xmax = ymax
                                new_ymin = orig_width - xmax
                                new_ymax = orig_width - xmin
                                xmin, xmax, ymin, ymax = new_xmin, new_xmax, new_ymin, new_ymax
                                y_offset = orig_height * 0.3
                                ymin += y_offset
                                ymax += y_offset
                            elif rotation_angle == 270:
                                orig_width, orig_height = img.shape[1], img.shape[0]
                                new_xmin = ymin
                                new_xmax = ymax
                                new_ymin = orig_width - xmax
                                new_ymax = orig_width - xmin
                                xmin, xmax, ymin, ymax = new_xmin, new_xmax, new_ymin, new_ymax
                            scale_x = page.rect.width / img.shape[1]
                            scale_y = page.rect.height / img.shape[0]
                            if rotation_angle == 90:
                                px1 = page.rect.width - (xmin * scale_x)
                                px2 = page.rect.width - (xmax * scale_x)
                                py1 = page.rect.height - (ymin * scale_y)
                                py2 = page.rect.height - (ymax * scale_y)
                                y_offset = page.rect.height * 0.54
                                py1 += y_offset
                                py2 += y_offset
                                page_middle = page.rect.height / 2
                                if min(py1, py2) < page_middle:
                                    py1 -= top_shift_px
                                    py2 -= top_shift_px
                                y_offset = page.rect.height * 0.2
                                py1 += y_offset
                                py2 += y_offset
                            elif rotation_angle == 270:
                                px1 = xmin * scale_x
                                px2 = xmax * scale_x
                                py1 = ymin * scale_y
                                py2 = ymax * scale_y
                                y_offset_page = page.rect.height * -0.48
                                py1 += y_offset_page
                                py2 += y_offset_page
                                page_middle = page.rect.height / 2
                                if min(py1, py2) < page_middle:
                                    py1 -= top_shift_px
                                    py2 -= top_shift_px
                            elif rotation_angle == 180:
                                px1 = page.rect.width - (xmin * scale_x)
                                px2 = page.rect.width - (xmax * scale_x)
                                py1 = page.rect.height - (ymin * scale_y)
                                py2 = page.rect.height - (ymax * scale_y)
                                page_middle = page.rect.height / 2
                                if min(py1, py2) < page_middle:
                                    adjusted_shift = top_shift_px + 23
                                    py1 -= adjusted_shift
                                    py2 -= adjusted_shift
                            else:
                                if flip_x:
                                    px1 = page.rect.width - (xmin * scale_x)
                                    px2 = page.rect.width - (xmax * scale_x)
                                else:
                                    px1 = xmin * scale_x
                                    px2 = xmax * scale_x
                                if flip_y:
                                    py1 = page.rect.height - (ymin * scale_y)
                                    py2 = page.rect.height - (ymax * scale_y)
                                else:
                                    py1 = ymin * scale_y
                                    py2 = ymax * scale_y
                            page_middle = page.rect.height / 2
                            if min(py1, py2) < page_middle:
                                py1 -= top_shift_px
                                py2 -= top_shift_px
                            left = min(px1, px2)
                            right = max(px1, px2)
                            top = min(py1, py2)
                            bottom = max(py1, py2)
                            rect = fitz.Rect(left, top, right, bottom)
                            new_page.insert_text(rect.tl, text, fontsize=font_size, color=(0, 0, 0), overlay=True)
                        except Exception as ex:
                            print(f"  Error inserting text: {ex}")
                            continue
                else:
                    # Портретная ориентация — используем те же правила позиционирования (копия логики)
                    for line in ocr_results:
                        try:
                            if not (isinstance(line, (list, tuple)) and len(line) >= 2):
                                continue
                            bbox = line[0]
                            text_info = line[1]
                            text = text_info[0] if isinstance(text_info, (list, tuple)) and len(text_info) >= 1 else str(text_info)
                            xs = [float(pt[0]) for pt in bbox]
                            ys = [float(pt[1]) for pt in bbox]
                            xmin, xmax = min(xs), max(xs)
                            ymin, ymax = min(ys), max(ys)
                            if rotation_angle == 90:
                                orig_width, orig_height = img.shape[1], img.shape[0]
                                new_xmin = ymin
                                new_xmax = ymax
                                new_ymin = orig_width - xmax
                                new_ymax = orig_width - xmin
                                xmin, xmax, ymin, ymax = new_xmin, new_xmax, new_ymin, new_ymax
                                y_offset = orig_height * 0.3
                                ymin += y_offset
                                ymax += y_offset
                            elif rotation_angle == 270:
                                orig_width, orig_height = img.shape[1], img.shape[0]
                                new_xmin = ymin
                                new_xmax = ymax
                                new_ymin = orig_width - xmax
                                new_ymax = orig_width - xmin
                                xmin, xmax, ymin, ymax = new_xmin, new_xmax, new_ymin, new_ymax
                            scale_x = page.rect.width / img.shape[1]
                            scale_y = page.rect.height / img.shape[0]
                            if rotation_angle == 90:
                                px1 = page.rect.width - (xmin * scale_x)
                                px2 = page.rect.width - (xmax * scale_x)
                                py1 = page.rect.height - (ymin * scale_y)
                                py2 = page.rect.height - (ymax * scale_y)
                                y_offset = page.rect.height * -0.21
                                py1 += y_offset
                                py2 += y_offset
                                page_middle = page.rect.height / 2
                                if min(py1, py2) < page_middle:
                                    py1 -= top_shift_px
                                    py2 -= top_shift_px
                                y_offset = page.rect.height * 0.2
                                py1 += y_offset
                                py2 += y_offset
                            elif rotation_angle == 270:
                                px1 = xmin * scale_x
                                px2 = xmax * scale_x
                                py1 = ymin * scale_y
                                py2 = ymax * scale_y
                                y_offset_page = page.rect.height * 0.28
                                py1 += y_offset_page
                                py2 += y_offset_page
                                page_middle = page.rect.height / 2
                                if min(py1, py2) < page_middle:
                                    py1 -= top_shift_px
                                    py2 -= top_shift_px
                            elif rotation_angle == 180:
                                px1 = page.rect.width - (xmin * scale_x)
                                px2 = page.rect.width - (xmax * scale_x)
                                py1 = page.rect.height - (ymin * scale_y)
                                py2 = page.rect.height - (ymax * scale_y)
                                page_middle = page.rect.height / 2
                                if min(py1, py2) < page_middle:
                                    adjusted_shift = top_shift_px + 23
                                    py1 -= adjusted_shift
                                    py2 -= adjusted_shift
                            else:
                                if flip_x:
                                    px1 = page.rect.width - (xmin * scale_x)
                                    px2 = page.rect.width - (xmax * scale_x)
                                else:
                                    px1 = xmin * scale_x
                                    px2 = xmax * scale_x
                                if flip_y:
                                    py1 = page.rect.height - (ymin * scale_y)
                                    py2 = page.rect.height - (ymax * scale_y)
                                else:
                                    py1 = ymin * scale_y
                                    py2 = ymax * scale_y
                            page_middle = page.rect.height / 2
                            if min(py1, py2) < page_middle:
                                py1 -= top_shift_px
                                py2 -= top_shift_px
                            left = min(px1, px2)
                            right = max(px1, px2)
                            top = min(py1, py2)
                            bottom = max(py1, py2)
                            rect = fitz.Rect(left, top, right, bottom)
                            new_page.insert_text(rect.tl, text, fontsize=font_size, color=(0, 0, 0), overlay=True)
                        except Exception as ex:
                            print(f"  Error inserting text: {ex}")
                            continue



    new_doc.save(output_path)
    new_doc.close()
    doc.close()
    print(f"Done. Pages: {total_pages}, OCR blocks: {total_blocks}")
    print(f"Saved output: {output_path}")
    # Удаляем служебные файлы после записи выходного PDF
    try:
        input_basename = os.path.splitext(os.path.basename(input_path))[0]
        src_dir = os.path.dirname(input_path)
        tmp_files = [
            os.path.join(src_dir, f"{input_basename}_page1_ocr_raw.txt"),
            os.path.join(src_dir, f"{input_basename}_page1_ocr_normalized.json"),
        ]
        for tmp in tmp_files:
            if os.path.exists(tmp):
                os.remove(tmp)
                print(f"Removed temp file: {tmp}")
    except Exception as cleanup_err:
        print(f"Warning: failed to remove temp files: {cleanup_err}")


def main():
    try:
        process_pdf(
            INPUT,
            OUTPUT,
            hide_text=False,
            flip_x=True,
            flip_y=True,
            top_shift_px=-23.0,
            font_size=4,
            dump_debug_first_page=True,
            dpi=300
        )
    except Exception as e:
        print(f"Processing failed: {e}")


if __name__ == '__main__':
    main()