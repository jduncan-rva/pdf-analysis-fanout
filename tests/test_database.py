import os
import tempfile
import unittest

# Set temporary DB path for testing
test_db_dir = tempfile.mkdtemp()
os.environ["DB_PATH"] = os.path.join(test_db_dir, "test_pdf_fanout.db")

import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../webapp")))

import database

class TestDatabaseFTS(unittest.TestCase):
    def setUp(self):
        database.init_db()

    def test_upsert_and_bm25_search(self):
        # Insert sample ingested bank statements
        database.upsert_document_ingest(
            doc_id="chase_stmt_001",
            filename="chase_statement_march_2026.pdf",
            gcs_uri="gs://test-bucket/chase_statement_march_2026.pdf",
            page_count=3,
            institution="JPMorgan Chase",
            doc_date="03/31/2026",
            account_numbers="1234-5678",
            raw_metadata_uri="gs://data-bucket/extracted_metadata/chase_stmt_001.json",
            searchable_text="JPMorgan Chase Bank Statement Account ending in 5678. Total deposits $50,000.00 Wire transfer from Acme Corp."
        )

        database.upsert_document_ingest(
            doc_id="wf_stmt_002",
            filename="wells_fargo_feb_2026.pdf",
            gcs_uri="gs://test-bucket/wells_fargo_feb_2026.pdf",
            page_count=2,
            institution="Wells Fargo",
            doc_date="02/28/2026",
            account_numbers="9876-5432",
            raw_metadata_uri="gs://data-bucket/extracted_metadata/wf_stmt_002.json",
            searchable_text="Wells Fargo Business Checking. Account 9876-5432. Payroll direct deposit $12,450.00."
        )

        # 1. Search for Chase & Wire
        results = database.search_documents_bm25("Chase wire")
        self.assertGreaterEqual(len(results), 1)
        self.assertEqual(results[0]["id"], "chase_stmt_001")
        self.assertIn("Acme Corp", results[0]["match_snippet"])

        # 2. Search for Payroll
        results_wf = database.search_documents_bm25("Payroll")
        self.assertGreaterEqual(len(results_wf), 1)
        self.assertEqual(results_wf[0]["id"], "wf_stmt_002")

        # 3. Test Deep Analysis Result Recording
        database.record_analysis_result(
            doc_id="chase_stmt_001",
            summary="Verified Chase statement with single wire transaction.",
            structured_json='{"transactions": [{"amount": 50000.0, "description": "Wire from Acme Corp"}]}',
            report_gcs_uri="gs://data-bucket/analysis_reports/chase_stmt_001.json"
        )

        doc = database.get_document_by_id("chase_stmt_001")
        self.assertEqual(doc["status"], "ANALYZED")
        self.assertIsNotNone(doc["analysis"])
        self.assertEqual(doc["analysis"]["summary"], "Verified Chase statement with single wire transaction.")

if __name__ == "__main__":
    unittest.main()
