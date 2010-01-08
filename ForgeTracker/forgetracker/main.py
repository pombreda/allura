#-*- python -*-
import logging

# Non-stdlib imports
import pkg_resources
from tg import tmpl_context
from tg import expose, validate, redirect
from pylons import g, c, request
from formencode import validators
from pymongo.bson import ObjectId

# Pyforge-specific imports
from pyforge.app import Application, ConfigOption, SitemapEntry
from pyforge.lib.helpers import push_config
from pyforge.lib.search import search
from pyforge.lib.decorators import audit, react
from pyforge.lib.security import require, has_artifact_access
from pyforge.model import ProjectRole

# Local imports
from forgetracker import model
from forgetracker import version

from forgetracker.widgets.issue_form import issue_form

log = logging.getLogger(__name__)

class ForgeTrackerApp(Application):
    __version__ = version.__version__
    permissions = ['configure', 'read', 'write', 'comment']

    def __init__(self, project, config):
        Application.__init__(self, project, config)
        self.root = RootController()

    @audit('Issues.#')
    def auditor(self, routing_key, data):
        log.info('Auditing data from %s (%s)',
                 routing_key, self.config.options.mount_point)

    @react('Issues.#')
    def reactor(self, routing_key, data):
        log.info('Reacting to data from %s (%s)',
                 routing_key, self.config.options.mount_point)

    @property
    def sitemap(self):
        menu_id = 'ForgeTracker (%s)' % self.config.options.mount_point
        with push_config(c, app=self):
            return [
                SitemapEntry(menu_id, '.')[self.sidebar_menu()] ]

    def sidebar_menu(self):
        return [
            SitemapEntry('Home', '.'),
            SitemapEntry('Search', 'search'),
            SitemapEntry('New Issue', '%s/new' % self.config.options.mount_point),
            ]

    @property
    def templates(self):
         return pkg_resources.resource_filename('forgetracker', 'templates')

    def install(self, project):
        'Set up any default permissions and roles here'

        self.uninstall(project)
        # Give the installing user all the permissions
        pr = c.user.project_role()
        for perm in self.permissions:
              self.config.acl[perm] = [ pr._id ]
        self.config.acl['read'].append(
            ProjectRole.query.get(name='*anonymous')._id)
        self.config.acl['comment'].append(
            ProjectRole.query.get(name='*authenticated')._id)
        model.Globals(project_id=c.project._id, last_issue_num=0)

    def uninstall(self, project):
        "Remove all the plugin's artifacts from the database"
        project_id = {'project_id':c.project._id}
        # mapper(model.Issue).remove(project_id)
        # mapper(model.Comment).remove(project_id)
        # mapper(model.Attachment).remove(project_id)
        # mapper(model.Globals).remove(project_id)


class RootController(object):

    @expose('forgetracker.templates.index')
    def index(self):
        issues = model.Issue.query.find(dict(project_id=c.project._id)).all()
        return dict(issues=issues)

    @expose('forgetracker.templates.search')
    @validate(dict(q=validators.UnicodeString(if_empty=None),
                   history=validators.StringBool(if_empty=False)))
    def search(self, q=None, history=None):
        'local plugin search'
        results = []
        count=0
        if not q:
            q = ''
        else:
            search_query = '''%s
            AND is_history_b:%s
            AND mount_point_s:%s''' % (
                q, history, c.app.config.options.mount_point)
            results = search(search_query)
            if results: count=results.hits
        return dict(q=q, history=history, results=results or [], count=count)

    def _lookup(self, issue_num, *remainder):
        return IssueController(issue_num), remainder

    @expose('forgetracker.templates.new_issue')
    def new(self, **kw):
        require(has_artifact_access('write'))
        tmpl_context.form = issue_form
        return dict(modelname='Issue',
            page='New Issue')

    @expose()
    def save_issue(self, issue_num, **post_data):
        require(has_artifact_access('write'))
        if request.method != 'POST':
            raise Exception('save_new must be a POST request')
        if issue_num:
            issue = model.Issue.query.get(project_id=c.project._id,
                                          issue_num=int(issue_num))
            if not issue:
                raise Exception('Issue number not found.')
            del post_data['issue_num']
        else:
            issue = model.Issue()
            issue.project_id = c.project._id
            globals = model.Globals.query.get(project_id=c.project._id)

            # FIX ME: need to lock around this increment or something
            globals.last_issue_num += 1
            post_data['issue_num'] = globals.last_issue_num
            # FIX ME

        for k,v in post_data.iteritems():
            setattr(issue, k, v)
        return "Issue saved."


class IssueController(object):

    def __init__(self, issue_num=None):
        self.issue_num = int(issue_num)
        self.issue = model.Issue.query.get(project_id=c.project._id,
                                                issue_num=self.issue_num)
        self.comments = CommentController(self.issue)

    @expose('forgetracker.templates.issue')
    def index(self, **kw):
        require(has_artifact_access('read', self.issue))
        return dict(issue=self.issue)

class CommentController(object):

    def __init__(self, issue, comment_id=None):
        self.issue = issue
        self.comment_id = comment_id
        self.comment = model.Comment.query.get(_id=self.comment_id)

    @expose()
    def reply(self, text):
        require(has_artifact_access('comment', self.artifact))
        if self.comment_id:
            c = self.comment.reply()
            c.text = text
        else:
            c = self.artifact.reply()
            c.text = text
        redirect(request.referer)

    @expose()
    def delete(self):
        require(lambda:c.user._id == self.comment.author()._id)
        self.comment.text = '[Text deleted by commenter]'
        redirect(request.referer)

    def _lookup(self, next, *remainder):
        if self.comment_id:
            return CommentController(
                self.artifact,
                self.comment_id + '/' + next), remainder
        else:
            return CommentController(
                self.artifact, next), remainder
