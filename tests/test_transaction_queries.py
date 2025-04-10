import gnewcash.gnucash_file as gcf
import gnewcash.file_formats as gff


def test_transaction_select():
    """Get a list of all transactions' date_posted field"""
    gnucash_file = gcf.GnuCashFile.read_file('test_files/Test1.gnucash', file_format=gff.XMLFileFormat)
    query = gnucash_file.books[0].transactions.query()

    result = query.select(lambda t, i: t.date_posted).to_list()
    assert len(result) > 0


def test_transaction_select_many():
    """Get a flattened list of all splits in all transactions"""
    gnucash_file = gcf.GnuCashFile.read_file('test_files/Test1.gnucash', file_format=gff.XMLFileFormat)
    query = gnucash_file.books[0].transactions.query()

    result = query.select_many(lambda t, i: t.splits).to_list()
    assert len(result) > 0


def test_transaction_where():
    """Filter out transactions to only January transactions."""
    gnucash_file = gcf.GnuCashFile.read_file('test_files/Test1.gnucash', file_format=gff.XMLFileFormat)
    query = gnucash_file.books[0].transactions.query()

    result = query.where(lambda t: t.date_posted.month == 1)
    for transaction in result:
        assert transaction.date_posted.month == 1


def test_transaction_all():
    """Check if all transactions are in January."""
    gnucash_file = gcf.GnuCashFile.read_file('test_files/Test1.gnucash', file_format=gff.XMLFileFormat)
    query = gnucash_file.books[0].transactions.query()

    result = query.all(lambda t: t.date_posted.month == 1)
    assert result is False


def test_transaction_any():
    """Check if any transactions are in January."""
    gnucash_file = gcf.GnuCashFile.read_file('test_files/Test1.gnucash', file_format=gff.XMLFileFormat)
    query = gnucash_file.books[0].transactions.query()

    result = query.any(lambda t: t.date_posted.month == 1)
    assert result is True
