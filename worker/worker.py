import time

from apscheduler.schedulers.blocking import BlockingScheduler

# 스케줄러 생성 및 작업 추가
scheduler = BlockingScheduler()
scheduler.add_job(my_job, 'interval', seconds=30)

# 스케줄러 시작
scheduler.start()

# 프로그램이 종료되지 않도록 대기
try:
    while True:
        time.sleep(2)
except (KeyboardInterrupt, SystemExit):
    scheduler.shutdown()
