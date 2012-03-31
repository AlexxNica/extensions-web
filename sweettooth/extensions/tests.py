
import os.path
import tempfile
import unittest
from uuid import uuid4
from zipfile import ZipFile

try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

from django.test import TestCase, TransactionTestCase
from django.core.files.base import File
from django.core.urlresolvers import reverse
from django.utils import simplejson as json
from extensions import models

from testutils import BasicUserTestCase

testdata_dir = os.path.join(os.path.dirname(__file__), 'testdata')

def get_test_zipfile(testname):
    original = open(os.path.join(testdata_dir, testname, testname + ".zip"), 'rb')
    new_temp = tempfile.NamedTemporaryFile(suffix=testname + ".zip.temp")
    new_temp.write(original.read())
    new_temp.seek(0)
    original.close()

    return new_temp

class UUIDPolicyTest(TestCase):
    def test_uuid_policy(self):
        self.assertTrue(models.validate_uuid("foo@mecheye.net"))
        self.assertTrue(models.validate_uuid("foo_2@mecheye.net"))
        self.assertTrue(models.validate_uuid("foo-3@mecheye.net"))
        self.assertTrue(models.validate_uuid("Foo4@mecheye.net"))

        for i in xrange(10):
            self.assertTrue(models.validate_uuid(str(uuid4())))

        self.assertFalse(models.validate_uuid("<Wonderful>"))

        self.assertFalse(models.validate_uuid("foo@gnome.org"))
        self.assertFalse(models.validate_uuid("bar@people.gnome.org"))

        self.assertTrue(models.validate_uuid("bar@i-love-gnome.org"))

class ExtensionPropertiesTest(BasicUserTestCase, TestCase):
    def test_description_parsing(self):
        metadata = {"uuid": "test-metadata@mecheye.net",
                    "name": "Test Metadata",
                    "description": "Simple test metadata"}

        extension = models.Extension.objects.create_from_metadata(metadata, creator=self.user)
        self.assertEquals(extension.first_line_of_description, "Simple test metadata")

        metadata = {"uuid": "test-metadata-2@mecheye.net",
                    "name": "Test Metadata",
                    "description": "First line\n\Second line"}

        extension = models.Extension.objects.create_from_metadata(metadata, creator=self.user)
        self.assertEquals(extension.first_line_of_description, "First line")

        metadata = {"uuid": "test-metadata-3@mecheye.net",
                    "name": "Test Metadata",
                    "description": ""}

        extension = models.Extension.objects.create_from_metadata(metadata, creator=self.user)
        self.assertEquals(extension.first_line_of_description, "")

    def test_shell_versions_json(self):
        metadata = {"uuid": "test-metadata@mecheye.net",
                    "name": "Test Metadata",
                    "shell-version": ["3.2", "3.2.1"]}

        extension = models.Extension.objects.create_from_metadata(metadata, creator=self.user)
        version = models.ExtensionVersion.objects.create(extension=extension,
                                                         status=models.STATUS_NEW)
        version.parse_metadata_json(metadata)

        self.assertEquals(version.shell_versions_json, '["3.2", "3.2.1"]')

class ParseZipfileTest(BasicUserTestCase, TestCase):
    def test_simple_metadata(self):
        metadata = {"uuid": "test-metadata@mecheye.net",
                    "name": "Test Metadata",
                    "description": "Simple test metadata",
                    "url": "http://test-metadata.gnome.org"}

        extension = models.Extension.objects.create_from_metadata(metadata, creator=self.user)
        version = models.ExtensionVersion(extension=extension)
        version.parse_metadata_json(metadata)

        self.assertEquals(extension.name, "Test Metadata")
        self.assertEquals(extension.description, "Simple test metadata")
        self.assertEquals(extension.url, "http://test-metadata.gnome.org")

    def test_simple_zipdata_data(self):
        with get_test_zipfile('SimpleExtension') as f:
            metadata = models.parse_zipfile_metadata(f)

        extension = models.Extension.objects.create_from_metadata(metadata, creator=self.user)
        version = models.ExtensionVersion(extension=extension)
        version.parse_metadata_json(metadata)

        self.assertEquals(extension.uuid, "test-extension@mecheye.net")
        self.assertEquals(extension.name, "Test Extension")
        self.assertEquals(extension.description, "Simple test metadata")
        self.assertEquals(extension.url, "http://test-metadata.gnome.org")

    def test_extra_metadata(self):
        with get_test_zipfile('ExtraMetadata') as f:
            metadata = models.parse_zipfile_metadata(f)

        extension = models.Extension.objects.create_from_metadata(metadata, creator=self.user)
        version = models.ExtensionVersion(extension=extension)
        version.parse_metadata_json(metadata)

        extra = json.loads(version.extra_json_fields)
        self.assertEquals(extension.uuid, "test-extension-2@mecheye.net")
        self.assertEquals(extra["extra"], "This is some good data")
        self.assertTrue("description" not in extra)
        self.assertTrue("url" not in extra)

    def test_bad_zipfile_metadata(self):
        bad_data = StringIO("deadbeef")
        self.assertRaises(models.InvalidExtensionData, models.parse_zipfile_metadata, bad_data)

        with get_test_zipfile('TooLarge') as f:
            with self.assertRaises(models.InvalidExtensionData) as cm:
                models.parse_zipfile_metadata(f)
            self.assertEquals(cm.exception.message, "Zip file is too large")

        with get_test_zipfile('NoMetadata') as f:
            with self.assertRaises(models.InvalidExtensionData) as cm:
                models.parse_zipfile_metadata(f)
            self.assertEquals(cm.exception.message, "Missing metadata.json")

        with get_test_zipfile('BadMetadata') as f:
            with self.assertRaises(models.InvalidExtensionData) as cm:
                models.parse_zipfile_metadata(f)
            self.assertEquals(cm.exception.message, "Invalid JSON data")

class ReplaceMetadataTest(BasicUserTestCase, TestCase):
    @unittest.expectedFailure
    def test_replace_metadata(self):
        old_zip_file = get_test_zipfile('LotsOfFiles')

        metadata = models.parse_zipfile_metadata(old_zip_file)
        old_zip_file.seek(0)

        extension = models.Extension.objects.create_from_metadata(metadata, creator=self.user)
        version = models.ExtensionVersion(extension=extension,
                                          source=File(old_zip_file))

        version.parse_metadata_json(metadata)

        new_zip = version.get_zipfile('r')

        old_zip = ZipFile(File(old_zip_file), 'r')
        self.assertEqual(len(old_zip.infolist()), len(new_zip.infolist()))
        self.assertEqual(new_zip.read("metadata.json"),
                         version.make_metadata_json_string())

        for old_info in old_zip.infolist():
            if old_info.filename == "metadata.json":
                continue

            new_info = new_zip.getinfo(old_info.filename)
            self.assertEqual(old_zip.read(old_info), new_zip.read(new_info))
            self.assertEqual(old_info.date_time, new_info.date_time)

        old_zip.close()
        new_zip.close()

class UploadTest(BasicUserTestCase, TransactionTestCase):
    def upload_file(self, zipfile):
        with get_test_zipfile(zipfile) as f:
            return self.client.post(reverse('extensions-upload-file'),
                                    dict(source=f,
                                         gplv2_compliant=True,
                                         tos_compliant=True), follow=True)

    def test_upload_page_works(self):
        response = self.client.get(reverse('extensions-upload-file'))
        self.assertEquals(response.status_code, 200)

    def test_upload_parsing(self):
        response = self.upload_file('SimpleExtension')
        extension = models.Extension.objects.get(uuid="test-extension@mecheye.net")
        version1 = extension.versions.order_by("-version")[0]

        self.assertEquals(version1.status, models.STATUS_NEW)
        self.assertEquals(extension.creator, self.user)
        self.assertEquals(extension.name, "Test Extension")
        self.assertEquals(extension.description, "Simple test metadata")
        self.assertEquals(extension.url, "http://test-metadata.gnome.org")

        url = reverse('extensions-version-detail', kwargs=dict(pk=version1.pk,
                                                               ext_pk=extension.pk,
                                                               slug=extension.slug))
        self.assertRedirects(response, url)

        version1.status = models.STATUS_ACTIVE
        version1.save()

        # Try again, hoping to get a new version
        self.upload_file('SimpleExtension')

        version2 = extension.versions.order_by("-version")[0]
        self.assertNotEquals(version1, version2)
        self.assertEquals(version2.status, models.STATUS_NEW)
        self.assertEquals(version2.version, version1.version+1)

    def test_upload_large_uuid(self):
        self.upload_file('LargeUUID')

        large_uuid = '1234567890'*9 + '@mecheye.net'
        extension = models.Extension.objects.get(uuid=large_uuid)
        version1 = extension.versions.order_by("-version")[0]

        self.assertEquals(version1.status, models.STATUS_NEW)
        self.assertEquals(extension.creator, self.user)
        self.assertEquals(extension.name, "Large UUID test")
        self.assertEquals(extension.description, "Simple test metadata")
        self.assertEquals(extension.url, "http://test-metadata.gnome.org")

    def test_upload_bad_shell_version(self):
        response = self.upload_file('BadShellVersion')
        extension = models.Extension.objects.get(uuid="bad-shell-version@mecheye.net")
        version1 = extension.versions.order_by("-version")[0]
        self.assertIsNotNone(version1.source)

class ExtensionVersionTest(BasicUserTestCase, TestCase):
    def test_single_version(self):
        metadata = {"name": "Test Metadata",
                    "uuid": "test-1@mecheye.net",
                    "description": "Simple test metadata",
                    "url": "http://test-metadata.gnome.org"}

        extension = models.Extension.objects.create_from_metadata(metadata, creator=self.user)
        version = models.ExtensionVersion.objects.create(extension=extension,
                                                         status=models.STATUS_ACTIVE)
        self.assertEquals(version.version, 1)
        # Make sure that saving again doesn't change the version.
        version.save()
        self.assertEquals(version.version, 1)
        version.save()
        self.assertEquals(version.version, 1)

        self.assertEquals(version.version, 1)
        self.assertEquals(extension.latest_version, version)

    def test_multiple_versions(self):
        metadata = {"name": "Test Metadata 2",
                    "uuid": "test-2@mecheye.net",
                    "description": "Simple test metadata",
                    "url": "http://test-metadata.gnome.org"}

        extension = models.Extension.objects.create_from_metadata(metadata, creator=self.user)

        v1 = models.ExtensionVersion.objects.create(extension=extension,
                                                    status=models.STATUS_ACTIVE)
        self.assertEquals(v1.version, 1)

        v2 = models.ExtensionVersion.objects.create(extension=extension,
                                                    status=models.STATUS_ACTIVE)
        self.assertEquals(v2.version, 2)

        self.assertEquals(list(extension.visible_versions.order_by('version')), [v1, v2])
        self.assertEquals(extension.latest_version, v2)

    def test_unpublished_version(self):
        metadata = {"name": "Test Metadata 3",
                    "uuid": "test-3@mecheye.net",
                    "description": "Simple test metadata",
                    "url": "http://test-metadata.gnome.org"}

        extension = models.Extension.objects.create_from_metadata(metadata, creator=self.user)

        v1 = models.ExtensionVersion.objects.create(extension=extension,
                                                    status=models.STATUS_ACTIVE)
        self.assertEquals(v1.version, 1)

        v2 = models.ExtensionVersion.objects.create(extension=extension,
                                                    status=models.STATUS_NEW)
        self.assertEquals(v2.version, 2)

        self.assertEquals(list(extension.visible_versions.order_by('version')), [v1])
        self.assertEquals(extension.latest_version, v1)

        v3 = models.ExtensionVersion.objects.create(extension=extension,
                                                    status=models.STATUS_ACTIVE)
        self.assertEquals(v3.version, 3)

        self.assertEquals(list(extension.visible_versions.order_by('version')), [v1, v3])
        self.assertEquals(extension.latest_version, v3)

    def test_shell_versions_simple(self):
        metadata = {"name": "Test Metadata 4",
                    "uuid": "test-4@mecheye.net",
                    "description": "Simple test metadata",
                    "url": "http://test-metadata.gnome.org",
                    "shell-version": ["3.0.0", "3.0.1", "3.0.2"]}

        extension = models.Extension.objects.create_from_metadata(metadata, creator=self.user)
        version = models.ExtensionVersion.objects.create(extension=extension,
                                                         status=models.STATUS_ACTIVE)
        version.parse_metadata_json(metadata)

        shell_versions = sorted(sv.version_string for sv in version.shell_versions.all())
        self.assertEquals(shell_versions, ["3.0.0", "3.0.1", "3.0.2"])

    def test_shell_versions_stable(self):
        metadata = {"name": "Test Metadata 5",
                    "uuid": "test-5@mecheye.net",
                    "description": "Simple test metadata",
                    "url": "http://test-metadata.gnome.org",
                    "shell-version": ["3.0", "3.2"]}

        extension = models.Extension.objects.create_from_metadata(metadata, creator=self.user)

        version = models.ExtensionVersion.objects.create(extension=extension,
                                                         status=models.STATUS_ACTIVE)
        version.parse_metadata_json(metadata)

        shell_versions = sorted(sv.version_string for sv in version.shell_versions.all())
        self.assertEquals(shell_versions, ["3.0", "3.2"])

class ShellVersionTest(TestCase):
    def test_shell_version_parsing(self):
        lookup_version = models.ShellVersion.objects.lookup_for_version_string
        get_version = models.ShellVersion.objects.get_for_version_string

        # Make sure we don't create a new version
        self.assertEquals(lookup_version("3.0.0"), None)
        version = get_version("3.0.0")
        self.assertEquals(lookup_version("3.0.0"), version)
        self.assertEquals(version.major, 3)
        self.assertEquals(version.minor, 0)
        self.assertEquals(version.point, 0)

        self.assertEquals(lookup_version("3.2"), None)
        version = get_version("3.2")
        self.assertEquals(lookup_version("3.2"), version)
        self.assertEquals(version.major, 3)
        self.assertEquals(version.minor, 2)
        self.assertEquals(version.point, -1)

        with self.assertRaises(models.InvalidShellVersion):
            get_version("3.1")
            lookup_version("3.1")

    def test_bad_shell_versions(self):
        with self.assertRaises(models.InvalidShellVersion):
            models.parse_version_string("3", ignore_micro=False)

        with self.assertRaises(models.InvalidShellVersion):
            models.parse_version_string("3.2.2.2.1", ignore_micro=False)

        with self.assertRaises(models.InvalidShellVersion):
            models.parse_version_string("a.b", ignore_micro=False)

        with self.assertRaises(models.InvalidShellVersion):
            models.parse_version_string("3.2.a", ignore_micro=False)

    def test_ignore_micro(self):
        with self.assertRaises(models.InvalidShellVersion):
            models.parse_version_string("4.3.2.1", ignore_micro=False)

        major, minor, point = models.parse_version_string("4.3.2.1", ignore_micro=True)
        self.assertEquals(major, 4)
        self.assertEquals(minor, 3)
        self.assertEquals(point, 2)

class DownloadExtensionTest(BasicUserTestCase, TestCase):
    def download(self, uuid, shell_version):
        url = reverse('extensions-shell-download', kwargs=dict(uuid=uuid))
        return self.client.get(url, dict(shell_version=shell_version), follow=True)

    def test_basic(self):
        zipfile = get_test_zipfile("SimpleExtension")

        metadata = {"name": "Test Metadata 6",
                    "uuid": "test-6@gnome.org",
                    "description": "Simple test metadata",
                    "url": "http://test-metadata.gnome.org"}

        extension = models.Extension.objects.create_from_metadata(metadata, creator=self.user)

        v1 = models.ExtensionVersion.objects.create(extension=extension,
                                                    status=models.STATUS_ACTIVE,
                                                    source=File(zipfile, "version1.zip"))
        v1.parse_metadata_json({"shell-version": ['3.2']})

        v2 = models.ExtensionVersion.objects.create(extension=extension,
                                                    status=models.STATUS_ACTIVE,
                                                    source=File(zipfile, "version1.zip"))
        v2.parse_metadata_json({"shell-version": ['3.4']})

        self.assertRedirects(self.download(metadata['uuid'], '3.2'), v1.source.url)
        self.assertRedirects(self.download(metadata['uuid'], '3.4'), v2.source.url)

    def test_bare_versions(self):
        zipfile = get_test_zipfile("SimpleExtension")

        metadata = {"name": "Test Metadata 7",
                    "uuid": "test-7@gnome.org",
                    "description": "Simple test metadata",
                    "url": "http://test-metadata.gnome.org"}

        extension = models.Extension.objects.create_from_metadata(metadata, creator=self.user)

        v1 = models.ExtensionVersion.objects.create(extension=extension,
                                                    status=models.STATUS_ACTIVE,
                                                    source=File(zipfile, "version1.zip"))
        v1.parse_metadata_json({"shell-version": ['3.2']})

        v2 = models.ExtensionVersion.objects.create(extension=extension,
                                                    status=models.STATUS_ACTIVE,
                                                    source=File(zipfile, "version2.zip"))
        v2.parse_metadata_json({"shell-version": ['3.2.1']})

        self.assertRedirects(self.download(metadata['uuid'], '3.2.0'), v1.source.url)
        self.assertRedirects(self.download(metadata['uuid'], '3.2.1'), v2.source.url)
        self.assertRedirects(self.download(metadata['uuid'], '3.2.2'), v1.source.url)

        v3 = models.ExtensionVersion.objects.create(extension=extension,
                                                    status=models.STATUS_ACTIVE,
                                                    source=File(zipfile, "version3.zip"))
        v3.parse_metadata_json({"shell-version": ['3.2']})

        self.assertRedirects(self.download(metadata['uuid'], '3.2.0'), v3.source.url)
        self.assertRedirects(self.download(metadata['uuid'], '3.2.1'), v3.source.url)
        self.assertRedirects(self.download(metadata['uuid'], '3.2.2'), v3.source.url)

    def test_multiple_versions(self):
        zipfile = get_test_zipfile("SimpleExtension")

        metadata = {"name": "Test Metadata 8",
                    "uuid": "test-8@gnome.org",
                    "description": "Simple test metadata",
                    "url": "http://test-metadata.gnome.org"}

        extension = models.Extension.objects.create_from_metadata(metadata, creator=self.user)

        v1 = models.ExtensionVersion.objects.create(extension=extension,
                                                    status=models.STATUS_ACTIVE,
                                                    source=File(zipfile, "version1.zip"))
        v1.parse_metadata_json({"shell-version": ['3.2.0', '3.2.1', '3.2.2']})

        v2 = models.ExtensionVersion.objects.create(extension=extension,
                                                    status=models.STATUS_ACTIVE,
                                                    source=File(zipfile, "version2.zip"))
        v2.parse_metadata_json({"shell-version": ['3.2.2']})

        self.assertRedirects(self.download(metadata['uuid'], '3.2.0'), v1.source.url)
        self.assertRedirects(self.download(metadata['uuid'], '3.2.1'), v1.source.url)
        self.assertRedirects(self.download(metadata['uuid'], '3.2.2'), v2.source.url)

class UpdateVersionTest(TestCase):
    fixtures = [os.path.join(testdata_dir, 'test_upgrade_data.json')]

    upgrade_uuid = 'upgrade-extension@testcases.sweettooth.mecheye.net'
    reject_uuid = 'reject-extension@testcases.sweettooth.mecheye.net'
    downgrade_uuid = 'downgrade-extension@testcases.sweettooth.mecheye.net'
    nonexistant_uuid = "blah-blah-blah@testcases.sweettooth.mecheye.net"

    def setUp(self):
        upgrade_pk = models.Extension.objects.get(uuid=self.upgrade_uuid).latest_version.pk
        downgrade_pk = models.Extension.objects.get(uuid=self.downgrade_uuid).latest_version.pk

        self.full_expected = { self.upgrade_uuid: dict(operation='upgrade',
                                                       version=upgrade_pk),
                               self.reject_uuid: dict(operation='blacklist'),
                               self.downgrade_uuid: dict(operation='downgrade',
                                                         version=downgrade_pk) }

    def grab_response(self, installed):
        post_data = dict(installed=json.dumps(installed))

        response = self.client.post(reverse('extensions-shell-update'),
                                    post_data)

        return json.loads(response.content)

    def test_upgrade_me(self):
        uuid = self.upgrade_uuid

        # The user has an old version, upgrade him
        expected = { uuid: self.full_expected[uuid] }
        response = self.grab_response({ uuid: 1 })
        self.assertEqual(response, expected)

        # The user has a newer version on his machine.
        response = self.grab_response({ uuid: 2 })
        self.assertEqual(response, {})

    def test_reject_me(self):
        uuid = self.reject_uuid

        expected = { uuid: self.full_expected[uuid] }
        response = self.grab_response({ uuid: 1 })
        self.assertEqual(response, expected)

        # The user has a newer version than what's on the site.
        response = self.grab_response({ uuid: 2 })
        self.assertEqual(response, {})

    def test_downgrade_me(self):
        uuid = self.downgrade_uuid

        # The user has a rejected version, so downgrade.
        expected = { uuid: self.full_expected[uuid] }
        response = self.grab_response({ uuid: 2 })
        self.assertEqual(response, expected)

        # The user has the appropriate version on his machine.
        response = self.grab_response({ uuid: 1 })
        self.assertEqual(response, {})

    def test_nonexistent_uuid(self):
        # The user has an extension that's not on the site.
        response = self.grab_response({ self.nonexistant_uuid: 1 })
        self.assertEqual(response, {})

    def test_multiple(self):
        installed = { self.upgrade_uuid: 1,
                      self.reject_uuid: 1,
                      self.downgrade_uuid: 2,
                      self.nonexistant_uuid: 2 }

        response = self.grab_response(installed)
        self.assertEqual(self.full_expected, response)

class QueryExtensionsTest(BasicUserTestCase, TestCase):
    def get_response(self, params):
        response = self.client.get(reverse('extensions-query'), params)
        return json.loads(response.content)

    def gather_uuids(self, params):
        if 'sort' not in params:
            params['sort'] = 'name'

        response = self.get_response(params)
        extensions = response['extensions']
        return [details['uuid'] for details in extensions]

    def create_extension(self, name, **kwargs):
        metadata = dict(uuid=name + "@mecheye.net", name=name)
        return models.Extension.objects.create_from_metadata(metadata,
                                                             creator=self.user,
                                                             **kwargs)

    def test_basic(self):
        one = self.create_extension("one")
        two = self.create_extension("two")

        models.ExtensionVersion.objects.create(extension=one, status=models.STATUS_ACTIVE)
        models.ExtensionVersion.objects.create(extension=two, status=models.STATUS_ACTIVE)

        uuids = self.gather_uuids(dict(uuid=one.uuid))
        self.assertEqual(uuids, [one.uuid])

        uuids = self.gather_uuids(dict(uuid=[one.uuid, two.uuid]))
        self.assertEqual(uuids, [one.uuid, two.uuid])

    def test_basic_visibility(self):
        one = self.create_extension("one")
        two = self.create_extension("two")

        models.ExtensionVersion.objects.create(extension=one, status=models.STATUS_ACTIVE)
        models.ExtensionVersion.objects.create(extension=two, status=models.STATUS_NEW)

        # Since two is new, it shouldn't be visible.
        uuids = self.gather_uuids(dict(uuid=[one.uuid, two.uuid]))
        self.assertEqual(uuids, [one.uuid])

        models.ExtensionVersion.objects.create(extension=two, status=models.STATUS_ACTIVE)

        # And now that we have a new version on two, we should have both...
        uuids = self.gather_uuids(dict(uuid=[one.uuid, two.uuid]))
        self.assertEqual(uuids, [one.uuid, two.uuid])

    def test_shell_versions(self):
        one = self.create_extension("one")
        two = self.create_extension("two")

        v = models.ExtensionVersion.objects.create(extension=one, status=models.STATUS_ACTIVE)
        v.parse_metadata_json({"shell-version": ["3.2"]})

        v = models.ExtensionVersion.objects.create(extension=two, status=models.STATUS_ACTIVE)
        v.parse_metadata_json({"shell-version": ["3.3.90"]})

        # Basic querying...
        uuids = self.gather_uuids(dict(shell_version="3.2"))
        self.assertEqual(uuids, [one.uuid])

        uuids = self.gather_uuids(dict(shell_version="3.3.90"))
        self.assertEqual(uuids, [two.uuid])

        # Base version querying.
        uuids = self.gather_uuids(dict(shell_version="3.2.2"))
        self.assertEqual(uuids, [one.uuid])

    def test_complex_visibility(self):
        one = self.create_extension("one")

        v = models.ExtensionVersion.objects.create(extension=one, status=models.STATUS_ACTIVE)
        v.parse_metadata_json({"shell-version": ["3.2"]})

        v = models.ExtensionVersion.objects.create(extension=one, status=models.STATUS_NEW)
        v.parse_metadata_json({"shell-version": ["3.3.90"]})

        # Make sure that we don't see one, here - the version that
        # has this shell version is NEW.
        uuids = self.gather_uuids(dict(shell_version="3.3.90"))
        self.assertEqual(uuids, [])

    def test_sort(self):
        one = self.create_extension("one", downloads=50, popularity=15)
        models.ExtensionVersion.objects.create(extension=one, status=models.STATUS_ACTIVE)

        two = self.create_extension("two", downloads=40, popularity=20)
        models.ExtensionVersion.objects.create(extension=two, status=models.STATUS_ACTIVE)

        uuids = self.gather_uuids(dict(sort="name"))
        self.assertEqual(uuids, [one.uuid, two.uuid])
        # name gets asc sort by default
        uuids = self.gather_uuids(dict(sort="name", order="asc"))
        self.assertEqual(uuids, [one.uuid, two.uuid])
        uuids = self.gather_uuids(dict(sort="name", order="desc"))
        self.assertEqual(uuids, [two.uuid, one.uuid])

        uuids = self.gather_uuids(dict(sort="popularity"))
        self.assertEqual(uuids, [two.uuid, one.uuid])
        uuids = self.gather_uuids(dict(sort="popularity", order="desc"))
        self.assertEqual(uuids, [two.uuid, one.uuid])
        uuids = self.gather_uuids(dict(sort="popularity", order="asc"))
        self.assertEqual(uuids, [one.uuid, two.uuid])

        uuids = self.gather_uuids(dict(sort="downloads"))
        self.assertEqual(uuids, [one.uuid, two.uuid])
        uuids = self.gather_uuids(dict(sort="downloads", order="desc"))
        self.assertEqual(uuids, [one.uuid, two.uuid])
        uuids = self.gather_uuids(dict(sort="downloads", order="asc"))
        self.assertEqual(uuids, [two.uuid, one.uuid])
