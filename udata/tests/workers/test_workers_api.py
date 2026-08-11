from unittest import skip

from flask import url_for

from udata.core.jobs.models import PeriodicTask
from udata.core.user.factories import AdminFactory
from udata.tasks import celery, job
from udata.tests.api import APITestCase
from udata.utils import faker


class JobsAPITest(APITestCase):
    def test_schedulable_jobs_list_need_admin(self):
        @celery.task(name="a-schedulable-job", schedulable=True)
        def test_job():
            pass

        self.login()
        response = self.get(url_for("api.schedulable_jobs"))
        self.assert403(response)

    def test_schedulable_jobs_list(self):
        @celery.task(name="a-schedulable-job", schedulable=True)
        def test_job():
            pass

        self.login(AdminFactory())
        response = self.get(url_for("api.schedulable_jobs"))
        self.assert200(response)
        self.assertIn("a-schedulable-job", response.json)

    def test_schedulable_jobs_list_with_decorator(self):
        @job("a-job")
        def test_job():
            pass

        self.login(AdminFactory())
        response = self.get(url_for("api.schedulable_jobs"))
        self.assert200(response)
        self.assertIn("a-job", response.json)

    def test_scheduled_jobs_list_need_admin(self):
        self.login()
        response = self.get(url_for("api.jobs"))
        self.assert403(response)

    def test_scheduled_jobs_list(self):
        @job("a-job")
        def test_job():
            pass

        for i in range(6):
            params = {"name": faker.name(), "description": faker.sentence(), "task": "a-job"}
            if i % 2:
                params["crontab"] = PeriodicTask.Crontab(minute=str(i))
            else:
                params["interval"] = PeriodicTask.Interval(every=i, period="minutes")
            PeriodicTask.objects.create(**params)

        self.login(AdminFactory())
        response = self.get(url_for("api.jobs"))
        self.assert200(response)

    def test_create_job_need_admin(self):
        @job("a-job")
        def test_job():
            pass

        data = {
            "name": "A crontab job",
            "description": "A simple crontab job doing nothing",
            "task": "a-job",
        }

        self.login()
        response = self.post(url_for("api.jobs"), data)
        self.assert403(response)

    def test_create_crontab_job(self):
        @job("a-job")
        def test_job():
            pass

        data = {
            "name": "A crontab job",
            "description": "A simple crontab job doing nothing",
            "task": "a-job",
            "crontab": {"minute": "0", "hour": "0"},
        }

        self.login(AdminFactory())
        response = self.post(url_for("api.jobs"), data)
        self.assert201(response)

        self.assertEqual(response.json["name"], data["name"])
        self.assertEqual(response.json["description"], data["description"])
        self.assertEqual(response.json["task"], data["task"])
        self.assertEqual(
            response.json["crontab"],
            {
                "minute": "0",
                "hour": "0",
                "day_of_week": "*",
                "day_of_month": "*",
                "month_of_year": "*",
            },
        )

    def test_create_interval_job(self):
        @job("a-job")
        def test_job():
            pass

        data = {
            "name": "An interval job",
            "description": "A simple interval job doing nothing",
            "task": "a-job",
            "interval": {"every": 5, "period": "minutes"},
        }

        self.login(AdminFactory())
        response = self.post(url_for("api.jobs"), data)
        self.assert201(response)

        self.assertEqual(response.json["name"], data["name"])
        self.assertEqual(response.json["description"], data["description"])
        self.assertEqual(response.json["task"], data["task"])
        self.assertEqual(response.json["interval"], data["interval"])

    def test_fail_on_create_with_both_crontab_and_interval(self):
        @job("a-job")
        def test_job():
            pass

        data = {
            "name": "A mixed job",
            "description": "A simple crontab job doing nothing",
            "task": "a-job",
            "crontab": {"minute": "0", "hour": "0"},
            "interval": {"every": 5, "period": "minutes"},
        }

        self.login(AdminFactory())
        response = self.post(url_for("api.jobs"), data)
        self.assertStatus(response, 400)

    def test_create_job_with_args_and_kwargs(self):
        @job("a-job")
        def test_job():
            pass

        data = {
            "name": "A parameterized job",
            "task": "a-job",
            "crontab": {"minute": "0"},
            "args": ["an-arg", 42],
            "kwargs": {"a-key": "a-value"},
        }

        self.login(AdminFactory())
        response = self.post(url_for("api.jobs"), data)
        self.assert201(response)

        self.assertEqual(response.json["args"], ["an-arg", 42])
        self.assertEqual(response.json["kwargs"], {"a-key": "a-value"})

        task = PeriodicTask.objects.get(name=data["name"])
        self.assertEqual(task.args, ["an-arg", 42])
        self.assertEqual(task.kwargs, {"a-key": "a-value"})

    def test_fail_on_create_with_a_non_object_body(self):
        self.login(AdminFactory())
        response = self.post(url_for("api.jobs"), ["not", "an", "object"])
        self.assertStatus(response, 400)

    def test_create_manual_job(self):
        pass

    def test_get_job_need_admin(self):
        @job("a-job")
        def test_job():
            pass

        task = PeriodicTask.objects.create(
            name=faker.name(),
            description=faker.sentence(),
            task="a-job",
            crontab=PeriodicTask.Crontab(minute="5"),
        )

        self.login()
        response = self.get(url_for("api.job", id=task.id))
        self.assert403(response)

    def test_get_job(self):
        @job("a-job")
        def test_job():
            pass

        task = PeriodicTask.objects.create(
            name=faker.name(),
            description=faker.sentence(),
            task="a-job",
            crontab=PeriodicTask.Crontab(minute="5"),
        )

        self.login(AdminFactory())
        response = self.get(url_for("api.job", id=task.id))
        self.assert200(response)
        self.assertEqual(response.json["id"], str(task.id))
        self.assertEqual(response.json["name"], task.name)
        self.assertEqual(response.json["description"], task.description)
        self.assertEqual(response.json["task"], task.task)
        self.assertEqual(response.json["schedule"], "5 * * * *")

    def test_update_job_need_admin(self):
        @job("a-job")
        def test_job():
            pass

        task = PeriodicTask.objects.create(
            name=faker.name(),
            description=faker.sentence(),
            task="a-job",
            crontab=PeriodicTask.Crontab(minute="5"),
        )

        self.login()
        response = self.put(
            url_for("api.job", id=task.id),
            {
                "name": task.name,
                "description": "New description",
                "task": task.task,
                "crontab": task.crontab.to_json(),
            },
        )
        self.assert403(response)

    def test_update_job(self):
        @job("a-job")
        def test_job():
            pass

        task = PeriodicTask.objects.create(
            name=faker.name(),
            description=faker.sentence(),
            task="a-job",
            crontab=PeriodicTask.Crontab(minute="5"),
        )

        self.login(AdminFactory())
        response = self.put(
            url_for("api.job", id=task.id),
            {
                "name": task.name,
                "description": "New description",
                "task": task.task,
                "crontab": {"minute": "5", "hour": "2"},
            },
        )
        self.assert200(response)

        self.assertEqual(response.json["id"], str(task.id))
        self.assertEqual(response.json["name"], task.name)
        self.assertEqual(response.json["task"], task.task)
        self.assertEqual(response.json["description"], "New description")
        self.assertEqual(response.json["crontab"]["minute"], "5")
        self.assertEqual(response.json["crontab"]["hour"], "2")
        self.assertIsNone(response.json["interval"])

    def test_update_job_change_type(self):
        @job("a-job")
        def test_job():
            pass

        task = PeriodicTask.objects.create(
            name=faker.name(),
            description=faker.sentence(),
            task="a-job",
            crontab=PeriodicTask.Crontab(minute="5"),
        )

        self.login(AdminFactory())
        response = self.put(
            url_for("api.job", id=task.id),
            {
                "name": task.name,
                "description": task.description,
                "task": task.task,
                "interval": {
                    "every": 5,
                    "period": "minutes",
                },
            },
        )
        self.assert200(response)

        self.assertEqual(response.json["id"], str(task.id))
        self.assertEqual(response.json["name"], task.name)
        self.assertEqual(response.json["task"], task.task)
        self.assertEqual(response.json["description"], task.description)
        self.assertEqual(response.json["interval"]["every"], 5)
        self.assertEqual(response.json["interval"]["period"], "minutes")
        self.assertIsNone(response.json["crontab"])

    def test_update_job_change_type_back_to_crontab(self):
        @job("a-job")
        def test_job():
            pass

        task = PeriodicTask.objects.create(
            name=faker.name(),
            task="a-job",
            interval=PeriodicTask.Interval(every=5, period="minutes"),
        )

        self.login(AdminFactory())
        response = self.put(
            url_for("api.job", id=task.id),
            {"name": task.name, "task": task.task, "crontab": {"minute": "5"}},
        )
        self.assert200(response)

        self.assertEqual(response.json["crontab"]["minute"], "5")
        self.assertIsNone(response.json["interval"])

    def test_update_job_keeps_the_schedule_when_the_payload_carries_none(self):
        @job("a-job")
        def test_job():
            pass

        task = PeriodicTask.objects.create(
            name=faker.name(),
            task="a-job",
            crontab=PeriodicTask.Crontab(minute="5"),
        )

        self.login(AdminFactory())
        response = self.put(url_for("api.job", id=task.id), {"description": "New description"})
        self.assert200(response)

        self.assertEqual(response.json["description"], "New description")
        self.assertEqual(response.json["crontab"]["minute"], "5")

    def test_update_job_drops_a_schedule_set_to_null(self):
        """Sending `{"crontab": {...}, "interval": null}` is the REST-natural way to
        switch schedule type, and must not be mistaken for carrying both."""

        @job("a-job")
        def test_job():
            pass

        task = PeriodicTask.objects.create(
            name=faker.name(),
            task="a-job",
            interval=PeriodicTask.Interval(every=5, period="minutes"),
        )

        self.login(AdminFactory())
        response = self.put(
            url_for("api.job", id=task.id),
            {"crontab": {"minute": "5"}, "interval": None},
        )
        self.assert200(response)

        self.assertEqual(response.json["crontab"]["minute"], "5")
        self.assertIsNone(response.json["interval"])

    def test_fail_on_update_with_both_crontab_and_interval(self):
        @job("a-job")
        def test_job():
            pass

        task = PeriodicTask.objects.create(
            name=faker.name(),
            task="a-job",
            crontab=PeriodicTask.Crontab(minute="5"),
        )

        self.login(AdminFactory())
        response = self.put(
            url_for("api.job", id=task.id),
            {
                "crontab": {"minute": "0"},
                "interval": {"every": 5, "period": "minutes"},
            },
        )
        self.assertStatus(response, 400)

        task.reload()
        self.assertEqual(task.crontab.minute, "5")
        self.assertIsNone(task.interval)

    def test_delete_job_need_admin(self):
        @job("a-job")
        def test_job():
            pass

        task = PeriodicTask.objects.create(
            name=faker.name(),
            description=faker.sentence(),
            task="a-job",
            crontab=PeriodicTask.Crontab(minute="5"),
        )

        self.login()
        response = self.delete(url_for("api.job", id=task.id))
        self.assert403(response)

    def test_delete_job(self):
        @job("a-job")
        def test_job():
            pass

        task = PeriodicTask.objects.create(
            name=faker.name(),
            description=faker.sentence(),
            task="a-job",
            crontab=PeriodicTask.Crontab(minute="5"),
        )

        self.login(AdminFactory())
        response = self.delete(url_for("api.job", id=task.id))
        self.assert204(response)

        self.assertIsNone(PeriodicTask.objects(id=task.id).first())

    def test_get_task_need_admin(self):
        self.login()
        response = self.get(url_for("api.task", id=faker.md5()))
        self.assert403(response)

    @skip("Need to be mocked and more details")
    def test_get_task(self):
        @celery.task
        def test_task():
            print("hello")

        result = test_task.delay()  # Always eager so no async

        self.login(AdminFactory())
        response = self.get(url_for("api.task", id=result.id))
        self.assert200(response)
        self.assertEqual(response.json["id"], result.id)
