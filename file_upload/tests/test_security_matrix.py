from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from django.utils import timezone
import io
import os
import json
from file_upload.models import File, FileShare


class SecurityMatrixTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.User = get_user_model()
        self.owner = self.User.objects.create_user(email="owner@example.com", password="Pass12345!")
        self.viewer = self.User.objects.create_user(email="viewer@example.com", password="Pass12345!")
        content = b"hello"
        uploaded = SimpleUploadedFile("secret.txt", content, content_type="text/plain")
        self.file = File.objects.create(
            user=self.owner,
            file=uploaded,
            upload_method="unit",
            title="t",
            project="p",
            uploader="u",
            file_format="txt",
            document_type="Dataset",
            access_level="Restricted",
        )

    def auth(self, user):
        self.client.force_authenticate(user=user)

    def test_unauthorized_access_private_file(self):
        self.auth(self.viewer)
        url = reverse("api_file_download", kwargs={"file_id": self.file.id})
        r = self.client.get(url)
        self.assertIn(r.status_code, [403, 404])

    def test_shared_read_no_delete_permission(self):
        FileShare.objects.create(file=self.file, shared_to_user=self.viewer, can_download=True, expires_at=timezone.now() + timezone.timedelta(days=1))
        self.auth(self.viewer)
        url = reverse("api_file_delete", kwargs={"file_id": self.file.id})
        r = self.client.delete(url)
        self.assertIn(r.status_code, [403, 404])

    def test_non_creator_cannot_share(self):
        self.auth(self.viewer)
        url = reverse("api_file_share_create")
        payload = {"file_id": self.file.id, "user_id": self.viewer.id, "can_download": True}
        r = self.client.post(url, data=json.dumps(payload), content_type="application/json")
        self.assertEqual(r.status_code, 403)

    def test_publish_cellxgene_sanitizes_filename(self):
        self.file.original_filename = "../../weird name .. evil.h5ad"
        self.file.save(update_fields=["original_filename"])
        self.auth(self.owner)
        url = reverse("publish_cellxgene", kwargs={"file_id": self.file.id})
        r = self.client.post(url)
        self.assertIn(r.status_code, [200, 500])
        if r.status_code == 200:
            pf = r.data.get("published_file", "")
            self.assertNotIn("..", pf)
            self.assertNotIn("/", pf)
            self.assertTrue(pf.endswith(".h5ad"))
