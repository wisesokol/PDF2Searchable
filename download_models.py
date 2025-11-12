#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для загрузки моделей PaddleOCR в локальную папку models
"""

import os
import sys
from pathlib import Path
import requests
import zipfile
import shutil
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def create_models_directory():
    """
    Создает структуру папок для моделей
    """
    base_path = Path(__file__).parent / "models"
    
    # Создаем папки для разных типов моделей
    directories = ['det', 'rec', 'cls']
    
    for dir_name in directories:
        dir_path = base_path / dir_name
        dir_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"📁 Создана папка: {dir_path}")
    
    return base_path

def download_paddleocr_models(base_path):
    """
    Загружает модели PaddleOCR
    
    Args:
        base_path (Path): Базовый путь к папке models
    """
    
    # URL для загрузки моделей PaddleOCR PP-OCRv5
    model_urls = {
        'det': {
            'url': 'https://paddleocr.bj.bcebos.com/PP-OCRv5/english/en_PP-OCRv5_det_infer.tar',
            'filename': 'en_PP-OCRv5_det_infer.tar',
            'extract_to': base_path / 'det'
        },
        'rec': {
            'url': 'https://paddleocr.bj.bcebos.com/PP-OCRv5/english/en_PP-OCRv5_rec_infer.tar',
            'filename': 'en_PP-OCRv5_rec_infer.tar',
            'extract_to': base_path / 'rec'
        },
        'cls': {
            'url': 'https://paddleocr.bj.bcebos.com/dygraph_v2.0/ch/ch_ppocr_mobile_v2.0_cls_infer.tar',
            'filename': 'ch_ppocr_mobile_v2.0_cls_infer.tar',
            'extract_to': base_path / 'cls'
        }
    }
    
    for model_type, info in model_urls.items():
        logger.info(f"📥 Загрузка модели {model_type}...")
        
        try:
            # Загружаем файл
            response = requests.get(info['url'], stream=True)
            response.raise_for_status()
            
            # Сохраняем во временный файл
            temp_file = base_path / info['filename']
            with open(temp_file, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            logger.info(f"✅ Модель {model_type} загружена: {temp_file}")
            
            # Извлекаем архив
            extract_tar_file(temp_file, info['extract_to'])
            
            # Удаляем временный файл
            temp_file.unlink()
            logger.info(f"🗑️ Временный файл удален: {temp_file}")
            
        except Exception as e:
            logger.error(f"❌ Ошибка загрузки модели {model_type}: {e}")

def extract_tar_file(tar_path, extract_to):
    """
    Извлекает tar файл в указанную папку
    
    Args:
        tar_path (Path): Путь к tar файлу
        extract_to (Path): Папка для извлечения
    """
    try:
        import tarfile
        
        with tarfile.open(tar_path, 'r') as tar:
            tar.extractall(extract_to)
        
        logger.info(f"📦 Архив извлечен в: {extract_to}")
        
        # Показываем содержимое извлеченной папки
        extracted_files = list(extract_to.rglob('*'))
        logger.info(f"📋 Извлеченные файлы: {[f.name for f in extracted_files if f.is_file()]}")
        
    except Exception as e:
        logger.error(f"❌ Ошибка извлечения архива: {e}")

def download_models_alternative():
    """
    Альтернативный способ загрузки моделей через PaddleOCR
    """
    logger.info("🔄 Альтернативный способ загрузки моделей...")
    
    try:
        from paddleocr import PaddleOCR
        
        # Создаем временный OCR объект для загрузки моделей
        logger.info("📥 Загружаем модели через PaddleOCR...")
        ocr = PaddleOCR(use_angle_cls=True, lang='en', show_log=True)
        
        # Модели автоматически загружаются в ~/.paddleocr/
        logger.info("✅ Модели загружены в стандартную папку")
        
        # Копируем модели в локальную папку
        copy_models_from_default_location()
        
    except Exception as e:
        logger.error(f"❌ Ошибка альтернативной загрузки: {e}")

def copy_models_from_default_location():
    """
    Копирует модели из стандартной папки PaddleOCR в локальную папку models
    """
    import os
    from pathlib import Path
    
    # Стандартная папка PaddleOCR
    default_models_path = Path.home() / ".paddleocr"
    
    if not default_models_path.exists():
        logger.warning("⚠️ Стандартная папка PaddleOCR не найдена")
        return
    
    # Локальная папка models
    local_models_path = Path(__file__).parent / "models"
    
    logger.info(f"📂 Копирование моделей из {default_models_path} в {local_models_path}")
    
    try:
        # Копируем папки с моделями
        for model_type in ['det', 'rec', 'cls']:
            src_path = default_models_path / f"en_PP-OCRv5_{model_type}_infer"
            if src_path.exists():
                dst_path = local_models_path / model_type
                shutil.copytree(src_path, dst_path, dirs_exist_ok=True)
                logger.info(f"✅ Скопирована модель {model_type}")
            else:
                logger.warning(f"⚠️ Модель {model_type} не найдена в стандартной папке")
    
    except Exception as e:
        logger.error(f"❌ Ошибка копирования моделей: {e}")

def main():
    """
    Основная функция для загрузки моделей
    """
    logger.info("🚀 Запуск загрузки моделей PaddleOCR")
    
    try:
        # Создаем структуру папок
        base_path = create_models_directory()
        
        # Пробуем загрузить модели напрямую
        logger.info("📥 Попытка прямой загрузки моделей...")
        try:
            download_paddleocr_models(base_path)
        except Exception as e:
            logger.warning(f"⚠️ Прямая загрузка не удалась: {e}")
            logger.info("🔄 Переход к альтернативному способу...")
            download_models_alternative()
        
        logger.info("🎉 Загрузка моделей завершена!")
        
    except Exception as e:
        logger.error(f"💥 Критическая ошибка: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
