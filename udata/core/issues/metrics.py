from .signals import on_new_issue, on_issue_closed


@on_new_issue.connect
@on_issue_closed.connect
def update_dataset_issues_metric(issue, **kwargs):
    print("----------------------------------------------------------------------")
    print("IN ISSUE METRIC UPDATE")
    model = issue.subject.__class__
    print(model)
    obj = model.objects(id=issue.subject.id).first()
    print(obj)
    obj.count_issues()
    print(obj.get_metrics)
    print("----------------------------------------------------------------------")