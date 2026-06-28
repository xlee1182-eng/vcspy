import os
import glob
import logging
import logging.handlers
from datetime import datetime, timedelta
from colorama import Fore, Style, init

LOG_DIR = os.path.join(os.getcwd(), 'logs')
LOG_PATH = os.path.join(LOG_DIR, 'log')
DATE_FORMAT = '%Y-%m-%d %H:%M:%S'
CONSOLE_FORMAT = '[%(asctime)s][%(levelname)s][%(filename)s:%(lineno)s] %(message)s'
FILE_HANDLER_FORMAT = '[%(asctime)s][%(levelname)s][%(filename)s:%(funcName)s:%(lineno)s] %(message)s'
LOG_RETENTION_DAYS = 30

init()

class ConsoleColorFormatter(logging.Formatter):
  def format(self, record):
    level_colors = {
      'WARNING': Fore.YELLOW,
      'ERROR': Fore.RED,
      'CRITICAL': Fore.RED,
    }
    color = level_colors.get(record.levelname)
    message = super().format(record)
    if color:
      return f'{color}{message}{Style.RESET_ALL}'
    return message

def createLogDirectory():
  try:
    if not os.path.exists(LOG_DIR):
      os.makedirs(LOG_DIR)
  except Exception as error:
    print(error)

def deleteOldLogs():
  """30일 이상 된 로그 파일 자동 삭제"""
  try:
    cutoff_date = datetime.now() - timedelta(days=LOG_RETENTION_DAYS)
    for log_file in glob.glob(os.path.join(LOG_DIR, 'log.*')):
      try:
        # 파일명에서 날짜 추출 (log.2026-03-26 형식)
        date_str = os.path.basename(log_file).replace('log.', '')
        file_date = datetime.strptime(date_str, '%Y-%m-%d')
        if file_date < cutoff_date:
          os.remove(log_file)
      except (ValueError, OSError):
        # 날짜 파싱 실패 또는 삭제 실패 시 무시
        continue
  except Exception as error:
    print(f'로그 파일 정리 중 오류 발생: {error}')

def SETLOGGER() -> logging.Logger:
  createLogDirectory()
  deleteOldLogs()

  # 로거 생성
  logger = logging.getLogger('app')
  logger.setLevel(logging.INFO)

  # 기존 핸들러 제거 (중복 방지)
  logger.handlers.clear()

  # 콘솔 핸들러 설정
  console_handler = logging.StreamHandler()
  console_handler.setLevel(logging.INFO)
  console_handler.setFormatter(ConsoleColorFormatter(CONSOLE_FORMAT, datefmt=DATE_FORMAT))
  logger.addHandler(console_handler)

  # 파일 핸들러 설정 (날짜별 로그 파일 분리)
  file_handler = logging.handlers.TimedRotatingFileHandler(
    LOG_PATH,
    when='midnight',
    interval=1,
    backupCount=0,
    encoding='utf-8'
  )
  file_handler.suffix = '%Y-%m-%d'
  file_handler.setLevel(logging.INFO)
  file_handler.setFormatter(logging.Formatter(FILE_HANDLER_FORMAT, datefmt=DATE_FORMAT))
  logger.addHandler(file_handler)

  return logger

def handleException(exc_type, exc_value, exc_traceback):
  logger = logging.getLogger('app')
  logger.error('Unexpected exception', exc_info = (exc_type, exc_value, exc_traceback))
