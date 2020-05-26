from .signals import on_new_issue, on_issue_closed


@on_new_issue.connect
@on_issue_closed.connect
def update_issues_metric(issue, **kwargs):
    model = issue.subject.__class__
    obj = model.objects(id=issue.subject.id).first()
    obj.count_issues()
