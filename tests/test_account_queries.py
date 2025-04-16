from typing import Dict

import pytest

import gnewcash.account as acc
import gnewcash.file_formats as gff
import gnewcash.gnucash_file as gcf
import gnewcash.search as srch


LOADED_FILES: Dict[str, gcf.GnuCashFile] = {}


def get_test_file_query(test_file: str) -> srch.Query:
    """Retrieves the base search query object from our test file."""
    if test_file not in LOADED_FILES:
        LOADED_FILES[test_file] = gcf.GnuCashFile.read_file(f'test_files/{test_file}.gnucash',
                                                            file_format=gff.XMLFileFormat)
    return LOADED_FILES[test_file].books[0].accounts_query()


def test_account_select():
    """Get a list of all accounts' name fields"""
    query = get_test_file_query('Test1')
    result = query.select(lambda a, i: a.name).to_list()
    assert len(result) > 0


def test_account_select_many():
    """Get a flattened list of all slots in all accounts"""
    query = get_test_file_query('Test1')
    result = query.select_many(lambda a, i: a.slots).to_list()
    assert len(result) > 0


def test_account_where():
    """Filter out accounts to only credit accounts."""
    query = get_test_file_query('Test1')
    result = query.where(lambda a: a.type == acc.AccountType.CREDIT)
    for account in result:
        assert account.type == acc.AccountType.CREDIT


def test_account_all():
    """Check if all accounts are credit accounts."""
    query = get_test_file_query('Test1')
    result = query.all_(lambda a: a.type == acc.AccountType.CREDIT)
    assert result is False


def test_account_any():
    """Check if any accounts are credit accounts."""
    query = get_test_file_query('Test1')
    result = query.any_(lambda a: a.type == acc.AccountType.CREDIT)
    assert result is True


def test_account_contains():
    """Check if our account names contains 'Checking Account'."""
    query = get_test_file_query('Test1')
    result = (query.select(lambda a, i: a.name)
                    .contains('Checking Account'))
    assert result is True


def test_account_concat():
    """Concatenate credit accounts between two files."""
    query1 = get_test_file_query('Test1')
    query2 = get_test_file_query('Test2')

    query1_count = query1.where(lambda a: a.type == acc.AccountType.CREDIT).count()
    query2_count = query2.where(lambda a: a.type == acc.AccountType.CREDIT).count()

    result = (query1.where(lambda a: a.type == acc.AccountType.CREDIT)
                    .concat(query2.where(lambda a: a.type == acc.AccountType.CREDIT).to_list())).to_list()
    assert len(result) == query1_count + query2_count


def test_account_default_if_empty__empty_collection():
    """Return an empty account if we don't have any accounts that are CREDIT and INCOME accounts."""
    query = get_test_file_query('Test1')
    default_account = acc.Account()

    result = next(query.where(lambda a: a.type == acc.AccountType.CREDIT and a.type == acc.AccountType.INCOME)
                       .default_if_empty(default_account))
    assert result is default_account


def test_account_default_if_empty__nonempty_collection():
    """Return an empty account if we don't have any credit accounts."""
    query = get_test_file_query('Test1')
    default_transaction = acc.Account()

    result = next(query.where(lambda a: a.type == acc.AccountType.CREDIT).default_if_empty(default_transaction))
    assert result is not default_transaction


def test_account_distinct():
    """Get a distinct list of account types."""
    query = get_test_file_query('Test1')

    result = query.select(lambda a, i: a.type).distinct().to_list()
    assert len(result) == 7


def test_account_order_by():
    """Get a list of accounts, ordered by account type."""
    query = get_test_file_query('Test1')
    result = (query.order_by(lambda a: a.type)
                   .to_list())
    assert result[0].type == result[1].type


def test_account_reverse():
    """Get the last account using reverse."""
    query = get_test_file_query('Test1')
    last_account = query.last()
    result = query.reverse().first()
    assert result == last_account


def test_account_group_by():
    """Group accounts by type."""
    query = get_test_file_query('Test1')
    result = query.group_by(key=lambda a: a.type,
                            element=lambda a: a,
                            result=lambda key, element: {
                                'type': key,
                                'accounts': element.to_list()
                            }).to_list()
    assert len(result) == 7


def test_account_group_by__empty_collection():
    """Make sure our code doesn't bomb on empty collections."""
    query = get_test_file_query('Test1')
    result = (query.where(lambda t: False)
                   .group_by(key=lambda a: a.type,
                             element=lambda a: a,
                             result=lambda key, element: {
                                 'month': key,
                                 'max': element.to_list()
                             })
                   .to_list())
    assert len(result) == 0


def test_account_count():
    """Get the number of accounts in the file."""
    query = get_test_file_query('Test1')
    result = query.count()
    assert result == 19


def test_account_count__empty_collection():
    """Make sure our code doesn't bomb on empty collections."""
    query = get_test_file_query('Test1')
    result = (query.where(lambda a: False)
                   .count())
    assert result == 0


def test_account_element_at__in_range__no_default():
    """Get the sixth account."""
    query = get_test_file_query('Test1')
    result = (query.element_at(5))
    assert result.guid == 'e56282be51e186e17470dc32bb2b0664'


def test_account_element_at__out_of_range__no_default():
    """Make sure we get an IndexError on an empty collection."""
    query = get_test_file_query('Test1')
    with pytest.raises(IndexError):
        (query.where(lambda a: False)
              .element_at(0))


def test_account_element_at__in_range__with_default():
    """Get the sixth account with default."""
    query = get_test_file_query('Test1')
    default = acc.Account()
    result = query.element_at(5, default)
    assert result.guid == 'e56282be51e186e17470dc32bb2b0664'


def test_account_element_at__out_of_range__with_default():
    """Make sure our default is selected when we have an empty collection."""
    query = get_test_file_query('Test1')
    default = acc.Account()
    result = query.where(lambda a: False).element_at(0, default)
    assert result is default


def test_account_first():
    """Get the first account."""
    query = get_test_file_query('Test1')
    result = query.first()
    assert result.guid == 'bc222a9fec746db35cbac34c25bce632'


def test_account_first__empty_collection():
    """Make sure we get an IndexError on an empty collection."""
    query = get_test_file_query('Test1')
    with pytest.raises(IndexError):
        query.where(lambda a: False).first()


def test_account_first__default_nonempty_collection():
    """Get the first account with a specified default."""
    query = get_test_file_query('Test1')
    default = acc.Account()
    result = query.first(default)
    assert result is not default


def test_account_first__default__empty_collection():
    """Make sure our default value is returned when we have an empty collection."""
    query = get_test_file_query('Test1')
    default = acc.Account()
    result = query.where(lambda a: False).first(default)
    assert result is default


def test_account_last():
    """Get the last account."""
    query = get_test_file_query('Test1')
    result = query.last()
    assert result.guid == 'd9e09a56921f9f78ec53ce02a221e2c4'


def test_account_last__empty_collection():
    """Make sure we get an IndexError on empty collections."""
    query = get_test_file_query('Test1')
    with pytest.raises(IndexError):
        query.where(lambda a: False).last()


def test_account_last__default_nonempty_collection():
    """Get the last account with a specified default."""
    query = get_test_file_query('Test1')
    default = acc.Account()
    result = query.last(default)
    assert result is not default


def test_account_last__default__empty_collection():
    """Make sure we get our default value on an empty collection."""
    query = get_test_file_query('Test1')
    default = acc.Account()
    result = query.where(lambda a: False).last(default)
    assert result is default


def test_account_single__no_default__multiple_elements_in_collection():
    """Get a single transaction in January."""
    query = get_test_file_query('Test1')
    # Should be InvalidOperationException but I'm not re-organizing project structure for a unit test
    with pytest.raises(Exception):
        query.where(lambda t: t.date_posted.month == 1).single()


def test_account_single__no_default__single_element_in_collection():
    """Get a single account where the name is 'Checking Account'"""
    query = get_test_file_query('Test1')
    result = (query.where(lambda a: a.name == 'Checking Account')
                   .single())
    assert result.guid == '98dc3f29ce096088d113f992128736d8'


def test_account_single__no_default__empty_collection():
    """Make sure we get an IndexError on empty collections."""
    query = get_test_file_query('Test1')
    with pytest.raises(IndexError):
        query.where(lambda a: False).single()


def test_account_single__with_default__multiple_elements_in_collection():
    """Make sure we get an InvalidOperationException when we have multiple elements in the collection."""
    query = get_test_file_query('Test1')
    default = acc.Account()
    # Should be InvalidOperationException but I'm not re-organizing project structure for a unit test
    with pytest.raises(Exception):
        query.single(default)


def test_account_single__with_default__single_element_in_collection():
    """Get a single account with the name 'Checking Account' with default value."""
    query = get_test_file_query('Test1')
    default = acc.Account()
    result = (query.where(lambda a: a.name == 'Checking Account')
                   .single(default))
    assert result is not default
    assert result.guid == '98dc3f29ce096088d113f992128736d8'


def test_account_single__with_default__empty_collection():
    """Make sure we get the default value on an empty collection."""
    query = get_test_file_query('Test1')
    default = acc.Account()
    result = query.where(lambda a: False).single(default)
    assert result is default


def test_account_skip():
    """Gets the second account by skipping the first."""
    query = get_test_file_query('Test1')
    second_account = query.element_at(1)
    result = query.skip(1).first()
    assert result is second_account


def test_account_take():
    """Gets the first five accounts."""
    query = get_test_file_query('Test1')
    result = query.take(5).to_list()
    assert len(result) == 5
