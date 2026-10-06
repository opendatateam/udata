from udata.core.edito_blocs.models import DatasetsListBloc
from udata.core.organization.factories import OrganizationFactory
from udata.core.page.factories import PageFactory
from udata.core.page.models import Page
from udata.core.user.factories import AdminFactory, UserFactory
from udata.models import Member
from udata.tests.api import PytestOnlyAPITestCase


class PageModelTest(PytestOnlyAPITestCase):
    def test_blocs_round_trip(self):
        page = PageFactory(blocs=[DatasetsListBloc(title="Test", datasets=[])])
        page.reload()
        assert len(page.blocs) == 1
        assert page.blocs[0].title == "Test"

    def test_visible_excludes_drafts(self):
        public = PageFactory()
        PageFactory(published=None)
        assert list(Page.objects.visible()) == [public]

    def test_visible_by_user_includes_own_drafts(self):
        user = UserFactory()
        mine = PageFactory(owner=user, published=None)
        PageFactory(published=None)
        public = PageFactory()
        visible = Page.objects.visible_by_user(user, Page.objects.visible()._query_obj)
        assert set(visible) == {mine, public}


class PagePermissionsTest(PytestOnlyAPITestCase):
    def test_owner_can_edit(self):
        user = self.login()
        page = PageFactory(owner=user)
        assert page.permissions["edit"].can()
        assert page.permissions["delete"].can()

    def test_stranger_cannot_edit(self):
        self.login()
        page = PageFactory(owner=UserFactory())
        assert not page.permissions["edit"].can()

    def test_sysadmin_can_edit(self):
        self.login(AdminFactory())
        assert PageFactory(owner=UserFactory()).permissions["edit"].can()

    def test_org_editor_can_edit_but_not_member(self):
        user = UserFactory()
        org = OrganizationFactory(members=[Member(user=user, role="editor")])
        self.login(user)
        assert PageFactory(organization=org).permissions["edit"].can()

        other = UserFactory()
        org = OrganizationFactory(members=[Member(user=other, role="admin")])
        self.login(UserFactory())
        assert not PageFactory(organization=org).permissions["edit"].can()

    def test_draft_page_read(self):
        owner = UserFactory()
        page = PageFactory(owner=owner, published=None)
        self.login()
        assert not page.permissions["read"].can()
        self.login(owner)
        assert page.permissions["read"].can()

    def test_published_page_read(self):
        self.login()
        assert PageFactory().permissions["read"].can()
