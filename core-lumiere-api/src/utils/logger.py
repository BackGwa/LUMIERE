import logging
import os
from datetime import datetime
import zipfile
import asyncio
from typing import Optional

class LogManager:
    def __init__(self, log_dir: str = "logs/latest"):
        self.project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        self.log_dir = os.path.join(self.project_root, "logs", "latest")
        self.archive_dir = os.path.join(self.project_root, "logs")
        self.output_dir = os.path.join(self.log_dir, "output")
        self.setup_logging()
        self._archive_task = None
    
    def setup_logging(self):
        os.makedirs(self.log_dir, exist_ok=True)
        os.makedirs(self.output_dir, exist_ok=True)
        
        log_filename = datetime.now().strftime("%y%m%d.log")
        log_path = os.path.join(self.log_dir, log_filename)
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s [%(levelname)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S',
            handlers=[
                logging.FileHandler(log_path, encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
    
    def setup_daily_archiving(self):
        try:
            asyncio.create_task(self._cleanup_old_logs())
            
            loop = asyncio.get_running_loop()
            self._archive_task = loop.create_task(self._daily_archive_scheduler())
        except RuntimeError:
            pass
    
    async def _daily_archive_scheduler(self):
        while True:
            now = datetime.now()
            tomorrow = now.replace(hour=0, minute=0, second=0, microsecond=0)
            tomorrow = tomorrow.replace(day=tomorrow.day + 1)
            
            sleep_seconds = (tomorrow - now).total_seconds()
            await asyncio.sleep(sleep_seconds)
            
            await self._cleanup_old_logs()
    
    async def _cleanup_old_logs(self):
        try:
            today = datetime.now().strftime("%y%m%d")
            today_log = f"{today}.log"
            
            if os.path.exists(self.log_dir):
                files_to_archive = []
                for root, dirs, files in os.walk(self.log_dir):
                    for file in files:
                        if file.endswith('.log') and file != today_log:
                            file_path = os.path.join(root, file)
                            files_to_archive.append((file_path, file))
                        elif file.endswith('.png'):
                            file_path = os.path.join(root, file)
                            try:
                                file_date = datetime.fromtimestamp(os.path.getctime(file_path)).strftime("%y%m%d")
                                if file_date != today:
                                    files_to_archive.append((file_path, file))
                                elif file.startswith('preview_'):
                                    file_time = datetime.fromtimestamp(os.path.getctime(file_path))
                                    if (datetime.now() - file_time).total_seconds() > 600:
                                        try:
                                            os.remove(file_path)
                                        except:
                                            pass
                            except:
                                pass
                
                if files_to_archive:
                    root_logger = logging.getLogger()
                    handlers = root_logger.handlers[:]
                    for handler in handlers:
                        if isinstance(handler, logging.FileHandler):
                            handler.close()
                            root_logger.removeHandler(handler)
                    
                    import time
                    time.sleep(0.5)

                    files_by_date = {}
                    for file_path, file_name in files_to_archive:
                        if file_name.endswith('.log'):
                            date_str = file_name.replace('.log', '')
                        else:
                            try:
                                date_str = datetime.fromtimestamp(os.path.getctime(file_path)).strftime("%y%m%d")
                            except:
                                date_str = "unknown"
                        
                        if date_str not in files_by_date:
                            files_by_date[date_str] = []
                        files_by_date[date_str].append(file_path)
                    
                    for date_str, file_paths in files_by_date.items():
                        archive_name = f"{date_str}.zip"
                        archive_path = os.path.join(self.archive_dir, archive_name)
                        
                        try:
                            with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                                for file_path in file_paths:
                                    try:
                                        arcname = os.path.relpath(file_path, self.log_dir)
                                        zipf.write(file_path, arcname)
                                    except PermissionError:
                                        continue
                            
                            for file_path in file_paths:
                                try:
                                    os.remove(file_path)
                                except PermissionError:
                                    pass
                            
                            logging.info(f"Archived old logs to {archive_path}")
                        except Exception as e:
                            logging.error(f"Failed to archive {date_str}: {str(e)}")
                    
                    self.setup_logging()
        
        except Exception as e:
            logging.error(f"Failed to cleanup old logs: {str(e)}")

log_manager: Optional[LogManager] = None

def get_logger(name: str) -> logging.Logger:
    global log_manager
    if log_manager is None:
        log_manager = LogManager()
    return logging.getLogger(name)

def start_log_archiving():
    global log_manager
    if log_manager and log_manager._archive_task is None:
        log_manager.setup_daily_archiving()

def get_output_dir() -> str:
    """이미지 저장을 위한 output 디렉토리 경로 반환"""
    global log_manager
    if log_manager is None:
        log_manager = LogManager()
    return log_manager.output_dir