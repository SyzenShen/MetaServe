from django.test import TestCase
from django.contrib.auth import get_user_model
from file_upload.models import File, Folder, FileShare
from authentication.models import Organization, Membership
from file_upload.permission_utils import can_view_or_download_file, can_edit_file_metadata

User = get_user_model()

class PermissionSystemTests(TestCase):
    def setUp(self):
        # Users
        self.owner = User.objects.create_user(username='owner', email='owner@example.com', password='password')
        self.viewer = User.objects.create_user(username='viewer', email='viewer@example.com', password='password')
        self.stranger = User.objects.create_user(username='stranger', email='stranger@example.com', password='password')
        
        # Organization
        self.org = Organization.objects.create(name='Test Lab', owner=self.owner)
        Membership.objects.create(user=self.owner, organization=self.org, role='member')
        Membership.objects.create(user=self.viewer, organization=self.org, role='member')
        
        # Files
        self.public_file = File.objects.create(
            user=self.owner, 
            access_level='Public',
            original_filename='public.txt'
        )
        self.internal_file = File.objects.create(
            user=self.owner, 
            access_level='Internal',
            original_filename='internal.txt'
        )
        self.restricted_file = File.objects.create(
            user=self.owner, 
            access_level='Restricted',
            original_filename='restricted.txt'
        )

    def test_public_access(self):
        """Test Public access level"""
        self.assertTrue(can_view_or_download_file(self.stranger, self.public_file))

    def test_internal_access(self):
        """Test Internal access level (Same Organization)"""
        # Viewer is in same org -> True
        self.assertTrue(can_view_or_download_file(self.viewer, self.internal_file))
        # Stranger is not in org -> False
        self.assertFalse(can_view_or_download_file(self.stranger, self.internal_file))

    def test_restricted_access_default(self):
        """Test Restricted access level (Default: Owner only)"""
        self.assertTrue(can_view_or_download_file(self.owner, self.restricted_file))
        self.assertFalse(can_view_or_download_file(self.viewer, self.restricted_file))

    def test_restricted_access_with_share(self):
        """Test Restricted access with explicit FileShare"""
        # Share to viewer
        FileShare.objects.create(
            file=self.restricted_file,
            shared_to_user=self.viewer,
            can_download=True
        )
        self.assertTrue(can_view_or_download_file(self.viewer, self.restricted_file))
        self.assertFalse(can_view_or_download_file(self.stranger, self.restricted_file))

    def test_organization_folder_inheritance(self):
        """Test Organization folder inheritance rule (Most Restrictive Precedence)"""
        org_folder = Folder.objects.create(
            user=self.owner,
            name="Org Folder",
            organization=self.org
        )
        # Mocking the upload view logic where inheritance happens
        # In a real integration test, we would hit the API
        file_in_org = File.objects.create(
            user=self.owner,
            parent_folder=org_folder,
            access_level='Restricted' # Forced by view logic usually
        )
        
        # Verify access
        # Member can view folder?
        # (Assuming can_view_folder logic is correct)
        
        # Verify file access is Restricted (only owner or shared)
        self.assertFalse(can_view_or_download_file(self.viewer, file_in_org))
        
        # Share to org
        FileShare.objects.create(
            file=file_in_org,
            shared_to_organization=self.org,
            can_download=True
        )
        self.assertTrue(can_view_or_download_file(self.viewer, file_in_org))
