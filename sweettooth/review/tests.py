
from django.test import TestCase
from django.core.files.base import File, ContentFile, StringIO

from extensions import models
from review.views import get_old_version, should_auto_approve

from testutils import BasicUserTestCase

from difftests import DiffTests

class DiffViewTest(BasicUserTestCase, TestCase):
    def test_get_zipfiles(self):
        metadata = {"uuid": "test-metadata@mecheye.net",
                    "name": "Test Metadata"}

        extension = models.Extension.objects.create_from_metadata(metadata, creator=self.user)
        version1 = models.ExtensionVersion.objects.create(extension=extension,
                                                          source=File(ContentFile("doot doo"), name="aa"),
                                                          status=models.STATUS_NEW)
        self.assertEquals(None, get_old_version(version1))

        # This one is broken...
        version2 = models.ExtensionVersion.objects.create(extension=extension,
                                                          source="",
                                                          status=models.STATUS_NEW)
        self.assertEquals(version1, get_old_version(version2))

        version3 = models.ExtensionVersion.objects.create(extension=extension,
                                                          source=File(ContentFile("doot doo"), name="bb"),
                                                          status=models.STATUS_NEW)
        self.assertEquals(version1, get_old_version(version3))

class TestAutoApproveLogic(TestCase):
    def build_changeset(self, added=None, deleted=None, changed=None, unchanged=None):
        return dict(added=added or [],
                    deleted=deleted or [],
                    changed=changed or [],
                    unchanged=unchanged or [])

    def test_auto_approve_logic(self):
        self.assertTrue(should_auto_approve(self.build_changeset()))
        self.assertTrue(should_auto_approve(self.build_changeset(changed=['metadata.json'])))
        self.assertTrue(should_auto_approve(self.build_changeset(changed=['metadata.json', 'po/en_GB.po', 'images/new_fedora.png', 'stylesheet.css'])))
        self.assertTrue(should_auto_approve(self.build_changeset(changed=['stylesheet.css'], added=['po/zn_CH.po'])))

        self.assertFalse(should_auto_approve(self.build_changeset(changed=['extension.js'])))
        self.assertFalse(should_auto_approve(self.build_changeset(changed=['secret_keys.json'])))
        self.assertFalse(should_auto_approve(self.build_changeset(changed=['libbignumber/BigInteger.js'])))
        self.assertFalse(should_auto_approve(self.build_changeset(added=['libbignumber/BigInteger.js'])))
