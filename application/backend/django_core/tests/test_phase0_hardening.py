from pathlib import Path
from tempfile import TemporaryDirectory

from django.test import SimpleTestCase, override_settings

from common.exceptions import ValidationDomainError
from common.tenant.rls import generate_related_rls_policy_sql, generate_rls_policy_sql
from integrations.storage import LocalSecureStorageAdapter


class FailClosedRLSPolicyTests(SimpleTestCase):
    def test_policy_denies_missing_context_for_reads_and_writes(self):
        sql = generate_rls_policy_sql("documents_document")
        self.assertIn("ENABLE ROW LEVEL SECURITY", sql)
        self.assertNotIn("FORCE ROW LEVEL SECURITY", sql)
        self.assertIn("USING (", sql)
        self.assertIn("WITH CHECK (", sql)
        self.assertIn("IS NOT NULL", sql)
        self.assertNotIn("IS NULL\n            OR", sql)

    def test_identifiers_are_validated(self):
        with self.assertRaises(ValueError):
            generate_rls_policy_sql("documents_document; DROP TABLE users")
        with self.assertRaises(ValueError):
            generate_rls_policy_sql("documents_document", "agency_id) OR TRUE --")

    def test_child_table_policy_uses_parent_agency_and_forces_rls(self):
        class Meta:
            db_table = "documents_document"

        class Parent:
            _meta = Meta()

        class Remote:
            model = Parent

        class Target:
            column = "id"

        class ForeignKey:
            column = "document_id"
            remote_field = Remote()
            target_field = Target()

        class AgencyField:
            column = "agency_id"

        sql = generate_related_rls_policy_sql(
            "documents_documentversion", [([ForeignKey()], AgencyField())]
        )
        self.assertIn("FORCE ROW LEVEL SECURITY", sql)
        self.assertIn('FROM "documents_document"', sql)
        self.assertIn('"agency_id" IS NULL OR', sql)
        self.assertIn('"document_id" IS NOT NULL', sql)
        self.assertIn("WITH CHECK", sql)

    def test_direct_table_policy_validates_tenant_foreign_keys(self):
        class Meta:
            db_table = "properties_property"

        class Parent:
            _meta = Meta()

        class Remote:
            model = Parent

        class Target:
            column = "id"

        class ForeignKey:
            column = "branch_id"
            remote_field = Remote()
            target_field = Target()

        class AgencyField:
            column = "agency_id"

        sql = generate_rls_policy_sql(
            "properties_property", "agency_id", [([ForeignKey()], AgencyField())]
        )
        self.assertIn('"agency_id"::text', sql)
        self.assertIn('"branch_id" IS NULL OR EXISTS', sql)
        self.assertIn("WITH CHECK", sql)


class PrivateLocalStorageTests(SimpleTestCase):
    def test_private_files_are_outside_public_root_and_have_no_public_url(self):
        with TemporaryDirectory() as temp:
            public = Path(temp) / "media"
            private = Path(temp) / "private"
            with override_settings(MEDIA_ROOT=public, PRIVATE_MEDIA_ROOT=private, MEDIA_URL="/media/"):
                adapter = LocalSecureStorageAdapter()
                result = adapter.put_bytes(
                    key_prefix="private/agencies/agency-1/documents",
                    safe_filename="contract.pdf",
                    content=b"%PDF-test",
                    mime_type="application/pdf",
                )
                self.assertTrue(result.file_key.startswith("private/"))
                self.assertEqual(result.url, "")
                self.assertTrue((private / "agencies/agency-1/documents/contract.pdf").is_file())
                self.assertFalse((public / "private/agencies/agency-1/documents/contract.pdf").exists())
                self.assertEqual(adapter.get_bytes(file_key=result.file_key), b"%PDF-test")

    def test_path_traversal_and_sibling_prefix_are_rejected(self):
        with TemporaryDirectory() as temp:
            root = Path(temp) / "media"
            root.mkdir()
            sibling = Path(temp) / "media-evil"
            sibling.mkdir()
            with override_settings(MEDIA_ROOT=root, PRIVATE_MEDIA_ROOT=Path(temp) / "private"):
                adapter = LocalSecureStorageAdapter()
                for key in ("../media-evil/secret", "private/../../secret", "/etc/passwd", "a\\..\\secret"):
                    with self.subTest(key=key), self.assertRaises(ValidationDomainError):
                        adapter.get_bytes(file_key=key)
                with self.assertRaises(ValidationDomainError):
                    adapter._contained_path(root.resolve(), "../media-evil/secret")
