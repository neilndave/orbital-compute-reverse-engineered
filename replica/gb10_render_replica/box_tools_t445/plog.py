import json,sys,datetime
msg=json.loads(sys.argv[1]); now=datetime.datetime.now().astimezone()
pt=now.astimezone(datetime.timezone(datetime.timedelta(hours=-8)))
rec={"t_box_iso":now.isoformat(timespec='seconds'),"t_pt_iso":pt.isoformat(timespec='seconds'),"stream":"t442"}; rec.update(msg)
open('replica/process_log/t442.jsonl','a').write(json.dumps(rec)+"\n")
