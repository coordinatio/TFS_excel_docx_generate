from datetime import datetime
from re import search

from tfs import TFSAPI

from src.Task import Task


class Handler():
    def __init__(self, pat, date_from, date_to) -> None:
        tasks = []
        for w in self.retrieve(pat, date_from, date_to):
            x = {'title': self.get_title(w),
                 'assignees': self.get_assignees(w),
                 'release': self.get_release(w),
                 'link': self.get_link(w),
                 'parent_title': self.get_parent_title(w),
                 'body': self.get_body(w)}
            tasks.append(Task(**x))
        self.tasks = tasks

    def get_assignees(self, workitem):
        assignees = []
        if (workitem['AssignedTo']):
            assignees.append(
                str(workitem['AssignedTo'][:workitem['AssignedTo'].find(' <')]))
        if workitem['Tags']:
            m = search(r'[\@#]([А-Яа-яё]+[_ ][А-Яа-яё]+)', workitem['Tags'])
            if m:
                assignees.append(str(m.group(1).replace('_', ' ')))
        return assignees

    def retrieve(self, pat, date_from, date_to):
        return []

    def get_parent_title(self, workitem) -> str | None:
        p = workitem.parent
        if not p:
            return None
        return self.get_title(p)

    def get_body(self, workitem) -> str:
        return str(workitem['System.Description'])

    def get_title(self, workitem):
        return str(workitem['Title'])

    def get_release(self, workitem):
        return ''

    def get_link(self, workitem):
        return str(workitem._links['html']['href'])


class HandlerCai(Handler):
    def retrieve(self, pat, date_from, date_to):
        q1 = f"""SELECT [System.AssignedTo], [Tags]
        FROM workitems
        WHERE
            [System.State] = 'Done'
            AND [System.WorkItemType] = 'Task'
            AND (
                ([Closed Date] >= '{date_from}' AND [Closed Date] <= '{date_to}' AND [Closed Date Override] = '')
                OR
                ([Closed Date Override] >= '{date_from}' AND [Closed Date Override] <= '{date_to}')
                )
            AND [System.Tags] NOT CONTAINS 'EXCLUDE_FROM_TIME_REPORTS'
        ORDER BY [System.AssignedTo]
        """
        w = TFSAPI("https://tfs.content.ai/",
                   project="HQ/ContentAI", pat=pat).run_wiql(q1).workitems

        q2 = f"""SELECT [System.AssignedTo], [Tags]
        FROM workitems
        WHERE
            [System.State] = 'Done'
            AND [System.WorkItemType] = 'Product Backlog Item'
            AND [System.AreaPath] = '%s'
            AND (
                ([Closed Date] >= '{date_from}' AND [Closed Date] <= '{date_to}' AND [Closed Date Override] = '')
                OR
                ([Closed Date Override] >= '{date_from}' AND [Closed Date Override] <= '{date_to}')
                )
            AND [System.Tags] NOT CONTAINS 'EXCLUDE_FROM_TIME_REPORTS'
        ORDER BY [System.AssignedTo]
        """
        for a in ('ContentAI\\Документация', 'ContentAI\\Design'):
            w += TFSAPI("https://tfs.content.ai/",
                        project="HQ/ContentAI",
                        pat=pat).run_wiql(q2 % a).workitems
        return w

    def get_release(self, workitem):
        w = workitem
        while True:
            if w['Tags']:
                m = search(r'[A-Z\d]+_\d+\.\d+\.\d+', w['Tags'])
                if m:
                    return str(m.group(0))
            if not w.parent:
                return ''
            w = w.parent


class HandlerIS(Handler):
    def retrieve(self, pat, date_from, date_to):
        q = f"""SELECT [System.AssignedTo], [Tags]
        FROM workitems
        WHERE
            [System.State] = 'Closed'
            AND ([System.WorkItemType] = 'Bug' OR [System.WorkItemType] = 'Task')
            AND (
                ([Closed Date] >= '{date_from}' AND [Closed Date] <= '{date_to}' AND [Closed Date Override] = '')
                OR
                ([Closed Date Override] >= '{date_from}' AND [Closed Date Override] <= '{date_to}')
                )
            AND [System.Tags] NOT CONTAINS 'EXCLUDE_FROM_TIME_REPORTS'
        ORDER BY [System.AssignedTo]
        """
        return TFSAPI("https://tfs.content.ai/", project="NLC/AIS", pat=pat).run_wiql(q).workitems

    def get_release(self, workitem):
        m = search(r'AIS\\(\d+\.\d+)', workitem['system.areapath'])
        if m:
            return "IS_%s" % str(m.group(1))
        return ''


class HandlerLingvo(Handler):
    def retrieve(self, pat, date_from, date_to):
        qs = {'Lingvo':
              f"""SELECT [System.AssignedTo], [Tags]
                FROM workitems
                WHERE
                    [System.State] = 'Closed'
                    AND [System.TeamProject] <> 'lingvo.inbox'
                    AND ([System.WorkItemType] = 'Bug' OR [System.WorkItemType] = 'Feature')
                    AND ([Closed Date] >= '{date_from}' AND [Closed Date] <= '{date_to}')
                    AND [System.Tags] NOT CONTAINS 'EXCLUDE_FROM_TIME_REPORTS'
                ORDER BY [System.AssignedTo]
                """,
              'LingvoLive':
              f"""SELECT [System.AssignedTo], [Tags]
                FROM workitems
                WHERE
                    [System.State] = 'Closed'
                    AND ([System.WorkItemType] = 'Bug' OR [System.WorkItemType] = 'Feature')
                    AND ([Closed Date] >= '{date_from}' AND [Closed Date] <= '{date_to}')
                    AND [System.Tags] NOT CONTAINS 'EXCLUDE_FROM_TIME_REPORTS'
                ORDER BY [System.AssignedTo]
                """}
        w = []
        for p in qs:
            w += TFSAPI("https://tfs.content.ai/", project=p,
                        pat=pat).run_wiql(qs[p]).workitems
        return w

    def get_release(self, workitem):
        spec_a = {'Lingvo X6': 'LX6',
                  'lingvo.mobile.iOS': 'LMI',
                  'lingvo.mobile.android': 'LMA',
                  'lingvo.mac': 'LFM',
                  'lingvo.live.ios': 'LLI',
                  'lingvo.live.android': 'LLA'}
        m = search(r'(.+?)\\(.+\\)?(\d+\.\d+(\.\d+)?)',
                   workitem['system.iterationpath'])
        if m:
            prj = m.group(1)
            ver = m.group(3)
            if prj in spec_a:
                return '%s_%s' % (spec_a[prj], ver)
        spec_b = {'lingvo.mobile.services': 'LLB',
                  'lingvo.live.services': 'LLB',
                  'lingvo.live.web': 'LLWW'}
        m = search(r'(.+?)\\.*', workitem['system.iterationpath'])
        if m:
            prj = m.group(1)
            if prj in spec_b:
                return spec_b[prj]
        return ''
