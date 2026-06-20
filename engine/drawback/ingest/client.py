"""The live-API seam.

A ``NetSuiteClient`` is the interface where a real SuiteQL / SuiteTalk REST integration would
plug in (``fetch_imports()`` / ``fetch_exports()`` returning the intermediate commercial records).
The shipped implementation, ``StubbedNetSuiteClient``, reads the fixture files instead and is
CLEARLY MARKED NOT CONNECTED — it performs NO network I/O and holds NO OAuth/TBA credentials.

In production, ``LiveNetSuiteClient`` (not implemented here — deliberately) would:
  * authenticate via NetSuite Token-Based Auth (TBA / OAuth 1.0a) against the account's SuiteTalk
    REST or SuiteQL endpoint,
  * run the saved searches / SuiteQL for the IMPORT and EXPORT spines,
  * page through results and map each row through ``ingest.netsuite`` exactly as the stub does.
The rest of the pipeline (customs overlay parse + join + validate) is unchanged — this is the only
place that touches NetSuite, so swapping the stub for the live client is the entire integration.
"""

from __future__ import annotations

from pathlib import Path
from typing import List

from drawback.models import DataQualityReport
from drawback.ingest import netsuite
from drawback.ingest.records import CommercialExport, CommercialImport

#: Banner constant other layers / the UI can surface so it is impossible to mistake fixture
#: data for a live NetSuite pull.
FIXTURE_MODE_BANNER = "NOT CONNECTED — fixture mode (no NetSuite network call; reads local files)"


class NetSuiteClient:
    """Interface for a NetSuite commercial-data source (the import + export spines).

    A real implementation returns the SAME intermediate records the parsers produce, so everything
    downstream (customs join, validation, estimate) is identical regardless of source.
    """

    #: False in every stub; a live client would set True once authenticated.
    connected: bool = False

    def fetch_imports(self, report: DataQualityReport) -> List[CommercialImport]:
        raise NotImplementedError

    def fetch_exports(self, report: DataQualityReport) -> List[CommercialExport]:
        raise NotImplementedError


class StubbedNetSuiteClient(NetSuiteClient):
    """Fixture-backed client. Reads NetSuite-format export files from a directory.

    NOT CONNECTED — fixture mode. No OAuth/TBA, no SuiteQL call, no network. This is the seam where
    a live ``LiveNetSuiteClient`` would replace it; the method contract is identical.
    """

    #: explicit, queryable flag (mirrors the docstring) — stays False for the stub.
    connected = False

    def __init__(self, netsuite_dir):
        self.netsuite_dir = Path(netsuite_dir)
        self.mode = FIXTURE_MODE_BANNER

    def fetch_imports(self, report: DataQualityReport) -> List[CommercialImport]:
        return netsuite.parse_import_dir(self.netsuite_dir, report)

    def fetch_exports(self, report: DataQualityReport) -> List[CommercialExport]:
        return netsuite.parse_export_dir(self.netsuite_dir, report)
