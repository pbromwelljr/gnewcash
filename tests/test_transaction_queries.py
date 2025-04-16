from decimal import Decimal
from typing import Dict

import pytest

import gnewcash.file_formats as gff
import gnewcash.gnucash_file as gcf
import gnewcash.search as srch
import gnewcash.transaction as trn

LOADED_FILES: Dict[str, gcf.GnuCashFile] = {}


def get_test_file_query(test_file: str) -> srch.Query:
    """Retrieves the base search query object from our test file."""
    if test_file not in LOADED_FILES:
        LOADED_FILES[test_file] = gcf.GnuCashFile.read_file(f'test_files/{test_file}.gnucash',
                                                            file_format=gff.XMLFileFormat)
    return LOADED_FILES[test_file].books[0].transactions.query()


def test_transaction_select():
    """Get a list of all transactions' date_posted field"""
    query = get_test_file_query('Test1')
    result = query.select(lambda t, i: t.date_posted).to_list()
    assert len(result) > 0


def test_transaction_select_many():
    """Get a flattened list of all splits in all transactions"""
    query = get_test_file_query('Test1')
    result = query.select_many(lambda t, i: t.splits).to_list()
    assert len(result) > 0


def test_transaction_where():
    """Filter out transactions to only January transactions."""
    query = get_test_file_query('Test1')
    result = query.where(lambda t: t.date_posted.month == 1)
    for transaction in result:
        assert transaction.date_posted.month == 1


def test_transaction_all():
    """Check if all transactions are in January."""
    query = get_test_file_query('Test1')
    result = query.all_(lambda t: t.date_posted.month == 1)
    assert result is False


def test_transaction_any():
    """Check if any transactions are in January."""
    query = get_test_file_query('Test1')
    result = query.any_(lambda t: t.date_posted.month == 1)
    assert result is True


def test_transaction_contains():
    """Check if the transaction descriptions contains a certain value."""
    query = get_test_file_query('Test1')
    result = (query.select(lambda t, i: t.description)
                    .contains('Paycheck'))
    assert result is True


def test_transaction_concat():
    """Concatenate January transactions between two files."""
    query1 = get_test_file_query('Test1')
    query2 = get_test_file_query('Test2')

    query1_count = query1.where(lambda t: t.date_posted.month == 1).count()
    query2_count = query2.where(lambda t: t.date_posted.month == 1).count()

    result = (query1.where(lambda t: t.date_posted.month == 1)
                    .concat(query2.where(lambda t: t.date_posted.month == 1).to_list())).to_list()
    assert len(result) == query1_count + query2_count


def test_transaction_default_if_empty__empty_collection():
    """Return an empty transaction if we don't have any transactions in month 13."""
    query = get_test_file_query('Test1')
    default_transaction = trn.Transaction()

    result = next(query.where(lambda t: t.date_posted.month == 13).default_if_empty(default_transaction))
    assert result is default_transaction


def test_transaction_default_if_empty__nonempty_collection():
    """Return an empty transaction if we don't have any transactions in January."""
    query = get_test_file_query('Test1')
    default_transaction = trn.Transaction()

    result = next(query.where(lambda t: t.date_posted.month == 1).default_if_empty(default_transaction))
    assert result is not default_transaction


def test_transaction_distinct():
    """Get a distinct list of days of the week that we have transactions for."""
    query = get_test_file_query('Test1')

    result = query.select(lambda t, i: t.date_posted.weekday()).distinct().to_list()
    assert len(result) <= 7


def test_transaction_except():
    """Get a list of transactions that isn't the first or last transaction."""
    temp_query = get_test_file_query('Test1')
    first_transaction = temp_query.first()
    last_transaction = temp_query.last()

    query = get_test_file_query('Test1')
    result = query.except_([first_transaction, last_transaction]).to_list()
    assert first_transaction not in result
    assert last_transaction not in result

def test_transaction_intersect():
    """Get a list of transactions that match the first or last transaction."""
    temp_query = get_test_file_query('Test1')
    first_transaction = temp_query.first()
    last_transaction = temp_query.last()

    query = get_test_file_query('Test1')
    result = query.intersect([first_transaction, last_transaction]).to_list()
    assert first_transaction in result
    assert last_transaction in result

# TODO: UNION

def test_transaction_order_by():
    """Get a list of split amounts, largest to smallest."""
    query = get_test_file_query('Test1')
    result = (query.select_many(lambda t, i: t.splits)
                   .select(lambda s, i: s.amount)
                   .order_by(lambda s: s, descending=True)
                   .to_list())
    assert result[0] >= result[1]


def test_transaction_reverse():
    """Get the last transaction using reverse."""
    query = get_test_file_query('Test1')
    last_transaction = query.last()
    result = query.reverse().first()
    assert result == last_transaction


def test_transaction_group_by():
    """Get max split amounts by month."""
    query = get_test_file_query('Test1')
    result = query.group_by(key=lambda t: t.date_posted.month,
                            element=lambda t: t,
                            result=lambda key, element: {
                                'month': key,
                                'max': element.select_many(lambda t, i: t.splits).select(lambda s, i: s.amount).max_()
                            }).to_list()
    assert len(result) == 12
    assert result[0]['month'] == 1
    assert result[0]['max'] == Decimal(2000)


def test_transaction_group_by__empty_collection():
    """Get the max split amounts by month for month 13."""
    query = get_test_file_query('Test1')
    result = (query.where(lambda t: t.date_posted.month == 13)
                   .group_by(key=lambda t: t.date_posted.month,
                             element=lambda t: t,
                             result=lambda key, element: {
                                 'month': key,
                                 'max': element.select_many(lambda t, i: t.splits).select(lambda s, i: s.amount).max_()
                             })
                   .to_list())
    assert len(result) == 0


def test_transaction_average():
    """Get the average number of positive split amounts for the month of January."""
    query = get_test_file_query('Test1')
    result = (query.where(lambda t: t.date_posted.month == 1)
                   .select_many(lambda t, i: t.splits)
                   .select(lambda s, i: s.amount)
                   .where(lambda amt: amt > Decimal(0))
                   .average())
    assert result == Decimal('657.1428571428571428571428571')


def test_transaction_average__empty_collection():
    """Get the average number of split amounts for month 13."""
    query = get_test_file_query('Test1')
    result = (query.where(lambda t: t.date_posted.month == 13)
                   .select_many(lambda t, i: t.splits)
                   .select(lambda s, i: s.amount)
                   .average())
    assert result is None


def test_transaction_count():
    """Get the number of transactions in the file."""
    query = get_test_file_query('Test1')
    result = query.count()
    assert result == 96


def test_transaction_count__empty_collection():
    """Get the number of transactions in month 13."""
    query = get_test_file_query('Test1')
    result = (query.where(lambda t: t.date_posted.month == 13)
                   .count())
    assert result == 0


def test_transaction_max():
    """Get the max positive split amount."""
    query = get_test_file_query('Test1')
    result = (query.select_many(lambda t, i: t.splits)
                   .select(lambda s, i: s.amount)
                   .where(lambda s: s > Decimal(0))
                   .max_())
    assert result == Decimal(2000)


def test_transaction_max__empty_collection():
    """Get the max split amount from transactions in month 13."""
    query = get_test_file_query('Test1')
    result = (query.where(lambda t: t.date_posted.month == 13)
                   .select_many(lambda t, i: t.splits)
                   .select(lambda s, i: s.amount)
                   .max_())
    assert result is None


def test_transaction_min():
    """Get the min positive split amount."""
    query = get_test_file_query('Test1')
    result = (query.select_many(lambda t, i: t.splits)
                   .select(lambda s, i: s.amount)
                   .where(lambda s: s > Decimal(0))
                   .min_())
    assert result == Decimal(60)


def test_transaction_min__empty_collection():
    """Get the min split amount from transactions in month 13."""
    query = get_test_file_query('Test1')
    result = (query.where(lambda t: t.date_posted.month == 13)
                   .select_many(lambda t, i: t.splits)
                   .select(lambda s, i: s.amount)
                   .min_())
    assert result is None


def test_transaction_sum():
    """Get the sum of all positive splits."""
    query = get_test_file_query('Test1')
    result = (query.select_many(lambda t, i: t.splits)
                   .select(lambda s, i: s.amount)
                   .where(lambda s: s > Decimal(0))
                   .sum_())
    assert result == Decimal(57_520)


def test_transaction_sum__empty_collection():
    """Get the sum of all transactions in month 13."""
    query = get_test_file_query('Test1')
    result = (query.where(lambda t: t.date_posted.month == 13)
                   .select_many(lambda t, i: t.splits)
                   .select(lambda s, i: s.amount)
                   .sum_())
    assert result == 0


def test_transaction_element_at__in_range__no_default():
    """Get the sixth transaction in January."""
    query = get_test_file_query('Test1')
    result = (query.where(lambda t: t.date_posted.month == 1)
                   .element_at(5))
    assert result.guid == '24dee8138f490d233cf90ddb08837809'


def test_transaction_element_at__out_of_range__no_default():
    """Get the first transaction in month 13."""
    query = get_test_file_query('Test1')
    with pytest.raises(IndexError):
        (query.where(lambda t: t.date_posted.month == 13)
              .element_at(0))


def test_transaction_element_at__in_range__with_default():
    """Get the sixth transaction in January with default."""
    query = get_test_file_query('Test1')
    default = trn.Transaction()
    result = query.where(lambda t: t.date_posted.month == 1).element_at(5, default)
    assert result.guid == '24dee8138f490d233cf90ddb08837809'


def test_transaction_element_at__out_of_range__with_default():
    """Get the first transaction in month 13 with default."""
    query = get_test_file_query('Test1')
    default = trn.Transaction()
    result = query.where(lambda t: t.date_posted.month == 13).element_at(0, default)
    assert result is default


def test_transaction_first():
    """Get the first transaction."""
    query = get_test_file_query('Test1')
    result = query.first()
    assert result.guid == '95757a260172a9b05094b568088907c1'


def test_transaction_first__empty_collection():
    """Get the first transaction of month 13."""
    query = get_test_file_query('Test1')
    with pytest.raises(IndexError):
        query.where(lambda t: t.date_posted.month == 13).first()


def test_transaction_first__default_nonempty_collection():
    """Get the first transaction with a specified default."""
    query = get_test_file_query('Test1')
    default = trn.Transaction()
    result = query.first(default)
    assert result is not default


def test_transaction_first__default__empty_collection():
    """Get the first transaction of month 13 with a specified default."""
    query = get_test_file_query('Test1')
    default = trn.Transaction()
    result = query.where(lambda t: t.date_posted.month == 13).first(default)
    assert result is default


def test_transaction_last():
    """Get the last transaction."""
    query = get_test_file_query('Test1')
    result = query.last()
    assert result.guid == 'deed3e094ae4a2b6b02b4f349261f69c'


def test_transaction_last__empty_collection():
    """Get the last transaction of month 13."""
    query = get_test_file_query('Test1')
    with pytest.raises(IndexError):
        query.where(lambda t: t.date_posted.month == 13).last()


def test_transaction_last__default_nonempty_collection():
    """Get the last transaction with a specified default."""
    query = get_test_file_query('Test1')
    default = trn.Transaction()
    result = query.last(default)
    assert result is not default


def test_transaction_last__default__empty_collection():
    """Get the last transaction of month 13 with a specified default."""
    query = get_test_file_query('Test1')
    default = trn.Transaction()
    result = query.where(lambda t: t.date_posted.month == 13).last(default)
    assert result is default


def test_transaction_single__no_default__multiple_elements_in_collection():
    """Get a single transaction in January."""
    query = get_test_file_query('Test1')
    # Should be InvalidOperationException but I'm not re-organizing project structure for a unit test
    with pytest.raises(Exception):
        query.where(lambda t: t.date_posted.month == 1).single()


def test_transaction_single__no_default__single_element_in_collection():
    """Get a single transaction in January where the description is 'Paycheck'"""
    query = get_test_file_query('Test1')
    result = (query.where(lambda t: t.date_posted.month == 1)
                   .where(lambda t: t.description == 'Paycheck')
                   .single())
    assert result.guid == '95757a260172a9b05094b568088907c1'

def test_transaction_single__no_default__empty_collection():
    """Get a single transaction from month 13."""
    query = get_test_file_query('Test1')
    with pytest.raises(IndexError):
        query.where(lambda t: t.date_posted.month == 13).single()


def test_transaction_single__with_default__multiple_elements_in_collection():
    """Get a single transaction in January with default value."""
    query = get_test_file_query('Test1')
    default = trn.Transaction()
    # Should be InvalidOperationException but I'm not re-organizing project structure for a unit test
    with pytest.raises(Exception):
        query.where(lambda t: t.date_posted.month == 1).single(default)


def test_transaction_single__with_default__single_element_in_collection():
    """Get a single transaction in January where the description in 'Paycheck' with default value."""
    query = get_test_file_query('Test1')
    default = trn.Transaction()
    result = (query.where(lambda t: t.date_posted.month == 1)
                   .where(lambda t: t.description == 'Paycheck')
                   .single(default))
    assert result is not default
    assert result.guid == '95757a260172a9b05094b568088907c1'


def test_transaction_single__with_default__empty_collection():
    """Get a single transaction from month 13 with default value."""
    query = get_test_file_query('Test1')
    default = trn.Transaction()
    result = query.where(lambda t: t.date_posted.month == 13).single(default)
    assert result is default


def test_transaction_skip():
    """Gets the second transaction by skipping the first."""
    query = get_test_file_query('Test1')
    second_transaction = query.element_at(1)
    result = query.skip(1).first()
    assert result is second_transaction


def test_transaction_skip_while():
    """Gets the first transaction in February by skipping all the transactions in January."""
    query = get_test_file_query('Test1')
    result = query.skip_while(lambda t: t.date_posted.month == 1).first()
    assert result.date_posted.month == 2


def test_transaction_take():
    """Gets the first five transactions."""
    query = get_test_file_query('Test1')
    result = query.take(5).to_list()
    assert len(result) == 5


def test_transaction_take_while():
    """Gets all the transactions before the first paycheck in February."""
    query = get_test_file_query('Test1')
    result = query.take_while(lambda t: t.description != 'Paycheck' or t.date_posted.month != 2).to_list()
    assert len(result) == 7
