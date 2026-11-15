import argparse
import json
import logging
from .engine import process_files, read_folder, ROOT, DB
parser = argparse.ArgumentParser(description='Process JSON medical reports locally')
parser.add_argument('folder',nargs='?',default=str(ROOT/'sample-data'))
parser.add_argument('--db',default=str(DB))
parser.add_argument('--config',default=str(ROOT/'config'))
parser.add_argument('--reprocess',action='store_true',help='Recalculate records with a changed configuration, preserving the previous output')
parser.add_argument('--watch',action='store_true',help='Watch the supplied folder for settled JSON files')
parser.add_argument('--interval',type=float,default=2,help='Folder polling interval in seconds')
args = parser.parse_args()
logging.basicConfig(level=logging.INFO,format='%(message)s')
if args.watch:
    from .operations import FolderWatcher
    watcher=FolderWatcher(args.db,args.config,args.folder)
    watcher.enabled=True
    watcher.config['poll_seconds']=max(.1,args.interval)
    try:watcher.run()
    except KeyboardInterrupt:watcher.close()
else:
    print(json.dumps(process_files(read_folder(args.folder),args.db,args.config,reprocess=args.reprocess),indent=2))
