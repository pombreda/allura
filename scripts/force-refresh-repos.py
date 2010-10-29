import sys
import logging

from pylons import c

from allura import model as M
from forgegit import model as GM
from forgehg import model as HM
from forgesvn import model as SM

log = logging.getLogger(__name__)

def main():
    shortnames = sys.argv[1:]
    for sn in shortnames:
        c.project = M.Project.query.get(shortname=sn)
        for cls in (GM.Repository, HM.Repository, SM.Repository):
            for repo in cls.query.find():
                try:
                    c.app = repo.app
                except:
                    log.exception('Error looking up app for %r', repo)
                try:
                    repo.refresh()
                except:
                    log.exception('Error refreshing %r', repo)
                try:
                    repo._impl._setup_receive_hook()
                except:
                    log.exception('Error setting up receive hook for %r', repo)

if __name__ == '__main__':
    main()