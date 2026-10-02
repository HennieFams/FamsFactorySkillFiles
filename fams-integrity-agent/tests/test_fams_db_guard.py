import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "scripts"))
from fams_db import ReadOnlyViolation, _to_pyformat, assert_read_only  # noqa: E402

ALLOWED = [
    "SELECT * FROM UsageDispensing WHERE AccountID = ? AND Createdate >= ?",
    "select top 5 ID, Createdate from UsageDispensing with (nolock)",
    "WITH d AS (SELECT ID, ROW_NUMBER() OVER (PARTITION BY UnqTrID ORDER BY ID) rn FROM UsageDispensing) SELECT * FROM d WHERE rn > 1;",
    "SELECT 'please DELETE me; INSERT INTO x' AS note FROM Account",          # keywords inside a literal
    "SELECT [Update], [Insert Date] FROM T",                                  # keywords as quoted identifiers
    "SELECT 1 -- DROP TABLE x\n",                                             # keyword inside a comment
    "SELECT /* outer /* nested DELETE */ still comment */ 1",
    "SELECT Createdate, CreatedBy FROM UsageDispensing",                      # CREATE as a prefix only
    "SELECT JSON_VALUE(InformationRec, '$.transactionID') FROM UsageDispensing",
    "SELECT @@VERSION",
    "SELECT N'it''s fine' AS x",
    "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = ?",
    "SELECT 1\r\nFROM Account\r\nWHERE ID = ? -- windows line endings\r\n",
    "SELECT * FROM UsageDispensing ORDER BY ID OFFSET 0 ROWS FETCH NEXT 10 ROWS ONLY",
    "SELECT u.ID FROM UsageDispensing u WHERE u.Volume > (SELECT AVG(Volume) FROM UsageDispensing)",
]

BLOCKED = [
    "DELETE FROM UsageDispensing WHERE ID = 1",
    "UPDATE UsageDispensing SET Volume = 0",
    "SELECT 1; DELETE FROM UsageDispensing",
    "SELECT 1 /* x */; DROP TABLE Account",
    "SELECT * INTO #t FROM UsageDispensing",
    "SELECT * INTO dbo.backup_copy FROM UsageDispensing",
    "WITH x AS (SELECT 1 a) DELETE FROM UsageDispensing",
    "WITH x AS (SELECT 1 a) MERGE UsageDispensing USING x ON 1=1 WHEN MATCHED THEN DELETE;",
    "EXEC sp_executesql N'DELETE FROM UsageDispensing'",
    "EXEC('DELETE FROM UsageDispensing')",
    "sp_rename 'Account', 'Account2'",
    "SELECT * FROM OPENROWSET('SQLNCLI', 'x', 'SELECT 1')",
    "SELECT NEXT VALUE FOR dbo.seq",
    "SELECT 1 WAITFOR DELAY '00:10:00'",
    "SET NOCOUNT ON",
    "DECLARE @x int",
    "TRUNCATE TABLE Stock",
    "SELECT * FROM UsageDispensing\nGO\nDELETE FROM Stock",
    "SELECT xp_cmdshell('dir')",
    "SELECT 'unterminated",
    "SELECT 1 /* unterminated",
    "",
    "-- only a comment",
    "EXEC get_ReportinglogbookRev6SARS @account = ?, @from = ?, @to = ?",   # proc without allow_procs
    # found in adversarial review 2026-10-02: -- comment ended by bare CR / other separators
    "SELECT 1 --x\rUPDATE dbo.Account SET Name='x' WHERE 1=1",
    "SELECT 1--\rDROP TABLE dbo.Account",
    "WITH c AS (SELECT 1 AS x) SELECT * FROM c --\rDELETE FROM dbo.Account",
    "SELECT 1 --\rGRANT CONTROL SERVER TO famsapp",
    "SELECT 1 --\x0cDELETE FROM Stock",
    "SELECT 1 --\u2028DELETE FROM Stock",
    "SELECT 1 --\x85DELETE FROM Stock",
    # second statement without ';' using a verb outside the old list
    "SELECT 1 RECEIVE TOP(1) * FROM dbo.TargetQueue",
    "SELECT 1 SETUSER 'dbo'",
    "SELECT 1 REVERT",
    # user / CLR function calls
    "SELECT dbo.fn_do_something('payload')",
    "SELECT [dbo].[fn_x](1)",
]


@pytest.mark.parametrize("sql", ALLOWED)
def test_allowed(sql):
    assert_read_only(sql)


@pytest.mark.parametrize("sql", BLOCKED)
def test_blocked(sql):
    with pytest.raises(ReadOnlyViolation):
        assert_read_only(sql)


def test_allowlisted_proc():
    assert_read_only("EXEC get_ReportinglogbookRev6SARS @account = ?, @from = ?, @to = ?", allow_procs=True)
    assert_read_only("EXEC dbo.get_ReportinglogbookRev6SARS @account = 278, @from = '2025-10-01', @to = '2025-11-01'",
                     allow_procs=True)


@pytest.mark.parametrize("sql", [
    "EXEC some_other_proc @a = ?",
    "EXEC get_ReportinglogbookRev6SARS @account = ?; DELETE FROM Stock",
    "EXEC get_ReportinglogbookRev6SARS @account = (SELECT 1)",
    "EXEC get_reportinglogbookrev6sars @a = ? --\rEXEC xp_cmdshell 'whoami'",
])
def test_proc_allowlist_is_strict(sql):
    with pytest.raises(ReadOnlyViolation):
        assert_read_only(sql, allow_procs=True)


def test_pyformat_conversion():
    assert _to_pyformat("SELECT * FROM T WHERE a = ? AND b LIKE '%x?%'") == \
        "SELECT * FROM T WHERE a = %s AND b LIKE '%%x?%%'"
